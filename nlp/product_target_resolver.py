"""Resolve ambiguous product targets with Gemini after deterministic dbt matching."""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

_MODEL = "gemini-2.5-flash"
_GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"
_VALID_SENTIMENTS = {"POSITIVE", "NEGATIVE", "NEUTRAL"}


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)


class ProductTargetResolver:
    def __init__(self) -> None:
        self.project_id = os.environ["GCP_PROJECT_ID"]
        self.dataset = os.environ["BQ_DATASET"]
        self.api_key = os.environ["GEMINI_API_KEY"]
        self.client = bigquery.Client(project=self.project_id)

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

    def _ask_gemini(self, candidate: dict, catalog: list[dict]) -> dict:
        if candidate["source_type"] == "video":
            task = (
                "Return product_ids for models reviewed by this video. "
                "If exactly one model is reviewed, return one id. For comparison videos return all compared ids."
            )
            shape = '{"product_ids": ["catalog-product-id"]}'
        else:
            task = (
                "Return each product target explicitly discussed in this sentence and its target-specific sentiment. "
                "Do not infer an implicit video target. Use an empty list if the sentence is ambiguous."
            )
            shape = '{"targets": [{"product_id": "catalog-product-id", "sentiment_label": "POSITIVE|NEGATIVE|NEUTRAL"}]}'
        prompt = (
            "You resolve Vietnamese technology product mentions. Use only product_id values from the catalog. "
            f"{task}\nCandidate: {candidate['candidate_text']}\n"
            f"Catalog: {json.dumps(catalog, ensure_ascii=False)}\n"
            f"Return JSON only with shape: {shape}"
        )
        response = requests.post(
            _GEMINI_URL,
            params={"key": self.api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json(text)

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
            bigquery.ScalarQueryParameter("model", "STRING", _MODEL),
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
            bigquery.ScalarQueryParameter("model", "STRING", _MODEL),
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
            bigquery.ScalarQueryParameter("model", "STRING", _MODEL),
        ])).result()

    def run(self, limit: int) -> dict[str, int]:
        catalog = self._catalog()
        valid_ids = {item["product_id"] for item in catalog}
        resolved = 0
        pending = 0
        for candidate in self._candidates(limit):
            try:
                result = self._ask_gemini(candidate, catalog)
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
                    resolved += 1
                else:
                    self._audit(candidate, "pending")
                    pending += 1
            except Exception:
                self._audit(candidate, "pending")
                pending += 1
        return {"processed": resolved + pending, "resolved": resolved, "pending": pending}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    print(ProductTargetResolver().run(args.limit))


if __name__ == "__main__":
    main()
