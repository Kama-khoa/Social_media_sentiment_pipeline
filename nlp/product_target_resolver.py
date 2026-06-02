"""Resolve ambiguous product targets with Gemini after deterministic dbt matching."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from google.cloud import bigquery

from nlp.gemini_gateway import GeminiGateway

load_dotenv()

_VALID_SENTIMENTS = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
_DEFAULT_BATCH_SIZE = 10

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)


class ProductTargetResolver:
    def __init__(self, client=None, gemini_gateway: GeminiGateway | None = None) -> None:
        self.project_id = os.environ["GCP_PROJECT_ID"]
        self.dataset = os.environ["BQ_DATASET"]
        self.client = client or bigquery.Client(project=self.project_id)
        self.gemini = gemini_gateway or GeminiGateway()

    def _table(self, name: str) -> str:
        return f"`{self.project_id}.{self.dataset}.{name}`"

    def _intermediate(self, name: str) -> str:
        return f"`{self.project_id}.{self.dataset}_intermediate.{name}`"

    def _catalog(self) -> list[dict]:
        rows = self.client.query(f"""
            SELECT p.product_id, p.product_name, ARRAY_AGG(a.alias_text IGNORE NULLS) aliases
            FROM {self._table("product_config")} p
            LEFT JOIN {self._table("product_aliases")} a
              ON p.product_id=a.product_id AND a.is_active=TRUE
            WHERE p.is_active=TRUE
            GROUP BY p.product_id, p.product_name
            ORDER BY p.product_name
        """).result()
        return [dict(row) for row in rows]

    def _candidates(self, limit: int) -> list[dict]:
        rows = self.client.query(f"""
            SELECT c.*
            FROM {self._intermediate("int_product_resolution_candidates")} c
            LEFT JOIN {self._table("product_resolution_candidates")} r USING (candidate_id)
            WHERE r.candidate_id IS NULL OR r.status = 'pending'
            ORDER BY c.created_at
            LIMIT @limit
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ])).result()
        return [dict(row) for row in rows]

    def _ask_gemini_batch(self, candidates: list[dict], catalog: list[dict]) -> dict[str, dict]:
        prompt = (
            "You resolve Vietnamese technology product mentions. Use only product_id values from the catalog. "
            "Resolve every candidate independently. For source_type=video, return product_ids for models reviewed "
            "by the video; return one id for a single review and all ids for comparison videos. "
            "For source_type=sentence, return each explicitly discussed target and its target-specific sentiment. "
            "Do not infer an implicit video target for a sentence. Use empty arrays when ambiguous.\n"
            f"Candidates: {json.dumps(candidates, ensure_ascii=False, default=str)}\n"
            f"Catalog: {json.dumps(catalog, ensure_ascii=False)}\n"
            "Return JSON only as an array with one item per candidate. Shape: "
            '[{"candidate_id":"id","product_ids":["catalog-product-id"],'
            '"targets":[{"product_id":"catalog-product-id","sentiment_label":"POSITIVE|NEGATIVE|NEUTRAL"}]}]'
        )
        parsed = _extract_json(self.gemini.generate(prompt))
        if not isinstance(parsed, list):
            raise ValueError("Gemini product resolver response must be a JSON array")
        return {
            str(item["candidate_id"]): item
            for item in parsed
            if isinstance(item, dict) and item.get("candidate_id")
        }

    def _merge_video_override(self, video_id: str, product_id: str, role: str) -> None:
        self.client.query(f"""
            MERGE {self._table("video_product_overrides")} target
            USING (SELECT @video_id video_id, @product_id product_id) source
            ON target.video_id=source.video_id AND target.product_id=source.product_id
            WHEN MATCHED THEN UPDATE SET role=@role, is_active=TRUE, updated_by=@model, updated_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (video_id, product_id, role, is_active, updated_by, updated_at)
            VALUES (@video_id, @product_id, @role, TRUE, @model, CURRENT_TIMESTAMP())
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("role", "STRING", role),
            bigquery.ScalarQueryParameter("model", "STRING", self.gemini.last_model or "gemini"),
        ])).result()

    def _merge_sentence_override(self, sentence_id: str, product_id: str, sentiment_label: str) -> None:
        self.client.query(f"""
            MERGE {self._table("sentence_product_target_overrides")} target
            USING (SELECT @sentence_id sentence_id, @product_id product_id) source
            ON target.sentence_id=source.sentence_id AND target.product_id=source.product_id
            WHEN MATCHED THEN UPDATE SET sentiment_label=@sentiment_label, target_source='llm_fallback',
                target_confidence=0.80, updated_by=@model, updated_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT
                (sentence_id, product_id, sentiment_label, target_source, target_confidence, updated_by, updated_at)
            VALUES (@sentence_id, @product_id, @sentiment_label, 'llm_fallback', 0.80, @model, CURRENT_TIMESTAMP())
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("sentence_id", "STRING", sentence_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("sentiment_label", "STRING", sentiment_label),
            bigquery.ScalarQueryParameter("model", "STRING", self.gemini.last_model or "gemini"),
        ])).result()

    def _audit(self, candidate: dict, status: str, product_id: str | None = None) -> None:
        self.client.query(f"""
            MERGE {self._table("product_resolution_candidates")} target
            USING (SELECT @candidate_id candidate_id) source
            ON target.candidate_id=source.candidate_id
            WHEN MATCHED THEN UPDATE SET status=@status, resolved_product_id=@product_id,
                reviewed_by=@model, reviewed_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT
                (candidate_id, source_type, source_id, candidate_text, status, resolved_product_id,
                 reviewed_by, reviewed_at, created_at)
            VALUES
                (@candidate_id, @source_type, @source_id, @candidate_text, @status, @product_id,
                 @model, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate["candidate_id"]),
            bigquery.ScalarQueryParameter("source_type", "STRING", candidate["source_type"]),
            bigquery.ScalarQueryParameter("source_id", "STRING", candidate["source_id"]),
            bigquery.ScalarQueryParameter("candidate_text", "STRING", candidate["candidate_text"]),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("model", "STRING", self.gemini.last_model or "gemini"),
        ])).result()

    def _apply_result(self, candidate: dict, result: dict, valid_ids: set[str]) -> bool:
        if candidate["source_type"] == "video":
            product_ids = [item for item in result.get("product_ids", []) if item in valid_ids]
            role = "primary" if len(product_ids) == 1 else "secondary"
            for product_id in product_ids:
                self._merge_video_override(candidate["source_id"], product_id, role)
        else:
            targets = [
                item for item in result.get("targets", [])
                if item.get("product_id") in valid_ids
                and str(item.get("sentiment_label", "")).upper() in _VALID_SENTIMENTS
            ]
            product_ids = [item["product_id"] for item in targets]
            for item in targets:
                self._merge_sentence_override(
                    candidate["source_id"], item["product_id"], item["sentiment_label"].upper()
                )
        if product_ids:
            self._audit(candidate, "approved", product_ids[0] if len(product_ids) == 1 else None)
            return True
        self._audit(candidate, "pending")
        return False

    def run(self, limit: int, batch_size: int = _DEFAULT_BATCH_SIZE) -> dict[str, int]:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        catalog = self._catalog()
        valid_ids = {item["product_id"] for item in catalog}
        resolved = 0
        pending = 0
        candidates = self._candidates(limit)
        for offset in range(0, len(candidates), batch_size):
            batch = candidates[offset:offset + batch_size]
            try:
                results = self._ask_gemini_batch(batch, catalog)
            except Exception:
                logger.exception("Gemini resolver batch failed")
                results = {}
            for candidate in batch:
                result = results.get(str(candidate["candidate_id"]))
                if result is None:
                    self._audit(candidate, "pending")
                    pending += 1
                elif self._apply_result(candidate, result, valid_ids):
                    resolved += 1
                else:
                    pending += 1
        return {"processed": resolved + pending, "resolved": resolved, "pending": pending}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    print(ProductTargetResolver().run(args.limit, args.batch_size))


if __name__ == "__main__":
    main()
