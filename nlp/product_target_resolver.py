"""Resolve ambiguous product targets with Gemini after deterministic dbt matching."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from dotenv import load_dotenv
from google.cloud import bigquery

from nlp.config import load_nlp_config
from nlp.gemini_gateway import GeminiGateway

load_dotenv()

_VALID_SENTIMENTS = {"POSITIVE", "NEGATIVE", "NEUTRAL"}
_DEFAULT_BATCH_SIZE = 10
_GENERIC_ALIAS_TEXT = {
    "ban pro",
    "ban plus",
    "ban thuong",
    "cai thu 2",
    "cai thu hai",
    "con nay",
    "may nay",
    "may",
    "model nay",
}

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return json.loads(cleaned)


def _result_confidence(result: dict) -> float:
    try:
        return float(result.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _target_confidence(target: dict, result: dict) -> float:
    try:
        return float(target.get("confidence") if target.get("confidence") is not None else _result_confidence(result))
    except (TypeError, ValueError):
        return 0.0


def _normalize_alias(value: str) -> str:
    normalized = re.sub(r"[^\w\s-]", " ", value.lower().strip())
    return re.sub(r"\s+", " ", normalized).strip()


def _alias_is_eligible(alias: str, alias_index: set[str]) -> bool:
    normalized = _normalize_alias(alias)
    if not normalized or normalized in alias_index or normalized in _GENERIC_ALIAS_TEXT:
        return False
    if len(normalized) < 3 or len(normalized) > 80:
        return False
    if normalized.isdigit():
        return False
    return True


class ProductTargetResolver:
    def __init__(self, client=None, gemini_gateway: GeminiGateway | None = None) -> None:
        self.project_id = os.environ["GCP_PROJECT_ID"]
        self.dataset = os.environ["BQ_DATASET"]
        self.client = client or bigquery.Client(project=self.project_id)
        self.gemini = gemini_gateway or GeminiGateway()
        config = load_nlp_config()
        self.auto_approve_threshold = config.product_resolver_auto_approve_threshold
        self.auto_alias_threshold = config.product_resolver_auto_alias_threshold
        self.recheck_batch_size = config.product_resolver_recheck_batch_size

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

    def _active_aliases(self) -> set[str]:
        rows = self.client.query(f"""
            SELECT alias_text
            FROM {self._table("product_aliases")}
            WHERE is_active=TRUE
        """).result()
        aliases = set()
        for row in rows:
            item = dict(row)
            if item.get("alias_text"):
                aliases.add(_normalize_alias(item["alias_text"]))
        return aliases

    def _recent_resolutions(self, limit: int = 15) -> list[dict]:
        if not getattr(self, "project_id", None) or not getattr(self, "dataset", None):
            return []
        query = f"""
            SELECT candidate_text, resolved_product_id, resolver_reason
            FROM {self._table("product_resolution_candidates")}
            WHERE status = 'approved' AND resolved_product_id IS NOT NULL
            ORDER BY reviewed_at DESC
            LIMIT @limit
        """
        params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
        try:
            rows = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning("Failed to fetch recent resolutions for few-shot prompting: %s", e)
            return []


    def _candidates(self, limit: int, product_id: str | None = None) -> list[dict]:
        product_filter = ""
        params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
        if product_id:
            product_filter = """
            AND (
                (c.source_type = 'video' AND EXISTS(
                    SELECT 1 FROM `{project_id}.{dataset}_intermediate.int_video_product_mentions` m
                    WHERE m.video_id = c.source_id AND m.product_id = @product_id
                ))
                OR
                (c.source_type = 'sentence' AND EXISTS(
                    SELECT 1 FROM `{project_id}.{dataset}_intermediate.int_sentence_product_targets` t
                    WHERE t.sentence_id = c.source_id AND t.product_id = @product_id
                ))
            )
            """
            params.append(bigquery.ScalarQueryParameter("product_id", "STRING", product_id))

        query = f"""
            SELECT c.*
            FROM {self._intermediate("int_product_resolution_candidates")} c
            LEFT JOIN {self._table("product_resolution_candidates")} r USING (candidate_id)
            WHERE (r.candidate_id IS NULL OR r.status = 'pending')
              {product_filter}
            ORDER BY c.created_at DESC
            LIMIT @limit
        """
        query = query.replace("{project_id}", self.project_id).replace("{dataset}", self.dataset)
        rows = self.client.query(query, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
        return [dict(row) for row in rows]

    def _ask_gemini_batch(self, candidates: list[dict], catalog: list[dict], examples: list[dict] | None = None) -> dict[str, dict]:
        examples_str = ""
        if examples:
            examples_str = "Examples of recent successful resolutions (learn mapping patterns from these):\n"
            for ex in examples:
                examples_str += f"- Text: \"{ex.get('candidate_text')}\" -> Mapped Product ID: \"{ex.get('resolved_product_id')}\" (Reason: {ex.get('resolver_reason')})\n"
            examples_str += "\n"

        prompt = (
            "You resolve Vietnamese technology product mentions. Use only product_id values from the catalog. "
            "Resolve every candidate independently. For source_type=video, return product_ids for models reviewed "
            "by the video; return one id for a single review and all ids for comparison videos. "
            "For source_type=sentence, return each explicitly discussed target and its target-specific sentiment. "
            "Do not infer an implicit video target for a sentence. Use empty arrays when ambiguous. "
            "Return confidence from 0.0 to 1.0, a short reason, and alias_suggestion only when the candidate "
            "contains a concrete slang or alternate product name worth saving.\n\n"
            f"{examples_str}"
            f"Candidates: {json.dumps(candidates, ensure_ascii=False, default=str)}\n"
            f"Catalog: {json.dumps(catalog, ensure_ascii=False)}\n"
            "Return JSON only as an array with one item per candidate. Shape: "
            '[{"candidate_id":"id","product_ids":["catalog-product-id"],'
            '"targets":[{"product_id":"catalog-product-id","sentiment_label":"POSITIVE|NEGATIVE|NEUTRAL",'
            '"confidence":0.0}],"confidence":0.0,"reason":"short reason","alias_suggestion":"optional alias"}]'
        )
        return self._parse_gemini_result_map(self.gemini.generate(prompt))

    def _ask_gemini_recheck_batch(self, candidates: list[dict], catalog: list[dict], examples: list[dict] | None = None) -> dict[str, dict]:
        examples_str = ""
        if examples:
            examples_str = "Examples of recent successful resolutions (learn mapping patterns from these):\n"
            for ex in examples:
                examples_str += f"- Text: \"{ex.get('candidate_text')}\" -> Mapped Product ID: \"{ex.get('resolved_product_id')}\" (Reason: {ex.get('resolver_reason')})\n"
            examples_str += "\n"

        prompt = (
            "Verify ambiguous Vietnamese technology product resolution candidates. This is a second-pass audit. "
            "Split multiple targets when a sentence or video compares more than one product. For sentence targets, "
            "assign sentiment separately for each product. Only use product_id values from the catalog. "
            "Keep confidence below 0.85 if the text is still vague, implicit, or depends on unknown video context. "
            "Return empty product_ids/targets when the candidate should stay pending for a human.\n\n"
            f"{examples_str}"
            f"Candidates: {json.dumps(candidates, ensure_ascii=False, default=str)}\n"
            f"Catalog: {json.dumps(catalog, ensure_ascii=False)}\n"
            "Return JSON only as an array with one item per candidate. Shape: "
            '[{"candidate_id":"id","product_ids":["catalog-product-id"],'
            '"targets":[{"product_id":"catalog-product-id","sentiment_label":"POSITIVE|NEGATIVE|NEUTRAL",'
            '"confidence":0.0}],"confidence":0.0,"reason":"short reason","alias_suggestion":"optional alias"}]'
        )
        return self._parse_gemini_result_map(self.gemini.generate(prompt))

    def _parse_gemini_result_map(self, response_text: str) -> dict[str, dict]:
        parsed = _extract_json(response_text)
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

    def _audit(
        self,
        candidate: dict,
        status: str,
        product_id: str | None = None,
        confidence: float | None = None,
        reason: str | None = None,
        method: str | None = None,
    ) -> None:
        self.client.query(f"""
            MERGE {self._table("product_resolution_candidates")} target
            USING (SELECT @candidate_id candidate_id) source
            ON target.candidate_id=source.candidate_id
            WHEN MATCHED THEN UPDATE SET status=@status, resolved_product_id=@product_id,
                reviewed_by=@model, reviewed_at=CURRENT_TIMESTAMP(),
                resolver_confidence=@confidence, resolver_reason=@reason, resolution_method=@method
            WHEN NOT MATCHED THEN INSERT
                (candidate_id, source_type, source_id, candidate_text, status, resolved_product_id,
                 reviewed_by, reviewed_at, created_at, resolver_confidence, resolver_reason, resolution_method)
            VALUES
                (@candidate_id, @source_type, @source_id, @candidate_text, @status, @product_id,
                 @model, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), @confidence, @reason, @method)
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate["candidate_id"]),
            bigquery.ScalarQueryParameter("source_type", "STRING", candidate["source_type"]),
            bigquery.ScalarQueryParameter("source_id", "STRING", candidate["source_id"]),
            bigquery.ScalarQueryParameter("candidate_text", "STRING", candidate["candidate_text"]),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("confidence", "FLOAT64", confidence),
            bigquery.ScalarQueryParameter("reason", "STRING", reason),
            bigquery.ScalarQueryParameter("method", "STRING", method),
            bigquery.ScalarQueryParameter("model", "STRING", self.gemini.last_model or "gemini"),
        ])).result()

    def _apply_result(
        self,
        candidate: dict,
        result: dict,
        valid_ids: set[str],
        method: str,
        alias_index: set[str],
    ) -> bool:
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
                and _target_confidence(item, result) >= self.auto_approve_threshold
            ]
            product_ids = [item["product_id"] for item in targets]
            for item in targets:
                self._merge_sentence_override(
                    candidate["source_id"],
                    item["product_id"],
                    item["sentiment_label"].upper(),
                    _target_confidence(item, result),
                    method,
                )
        if product_ids:
            self._audit(
                candidate,
                "approved",
                product_ids[0] if len(product_ids) == 1 else None,
                confidence=_result_confidence(result),
                reason=str(result.get("reason") or "")[:500],
                method=method,
            )
            self._maybe_create_alias(result, product_ids, alias_index)
            return True
        self._audit(
            candidate,
            "pending",
            confidence=_result_confidence(result),
            reason=str(result.get("reason") or "")[:500],
            method=method,
        )
        return False

    def _result_is_auto_approvable(self, candidate: dict, result: dict, valid_ids: set[str]) -> bool:
        if _result_confidence(result) < self.auto_approve_threshold:
            return False
        if candidate["source_type"] == "video":
            return any(product_id in valid_ids for product_id in result.get("product_ids", []))
        targets = [
            item for item in result.get("targets", [])
            if item.get("product_id") in valid_ids
            and str(item.get("sentiment_label", "")).upper() in _VALID_SENTIMENTS
            and _target_confidence(item, result) >= self.auto_approve_threshold
        ]
        return bool(targets)

    def _merge_sentence_override(
        self,
        sentence_id: str,
        product_id: str,
        sentiment_label: str,
        confidence: float = 0.80,
        method: str = "llm_auto",
    ) -> None:
        self.client.query(f"""
            MERGE {self._table("sentence_product_target_overrides")} target
            USING (SELECT @sentence_id sentence_id, @product_id product_id) source
            ON target.sentence_id=source.sentence_id AND target.product_id=source.product_id
            WHEN MATCHED THEN UPDATE SET sentiment_label=@sentiment_label, target_source=@method,
                target_confidence=@confidence, updated_by=@model, updated_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT
                (sentence_id, product_id, sentiment_label, target_source, target_confidence, updated_by, updated_at)
            VALUES (@sentence_id, @product_id, @sentiment_label, @method, @confidence, @model, CURRENT_TIMESTAMP())
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("sentence_id", "STRING", sentence_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("sentiment_label", "STRING", sentiment_label),
            bigquery.ScalarQueryParameter("confidence", "FLOAT64", confidence),
            bigquery.ScalarQueryParameter("method", "STRING", method),
            bigquery.ScalarQueryParameter("model", "STRING", self.gemini.last_model or "gemini"),
        ])).result()

    def _maybe_create_alias(self, result: dict, product_ids: list[str], alias_index: set[str]) -> None:
        if _result_confidence(result) < self.auto_alias_threshold or len(product_ids) != 1:
            return
        alias = str(result.get("alias_suggestion") or "").strip()
        if not _alias_is_eligible(alias, alias_index):
            return
        product_id = product_ids[0]
        alias_id = hashlib.md5(f"{product_id}|{alias.lower()}".encode()).hexdigest()
        self.client.query(f"""
            INSERT INTO {self._table("product_aliases")}
            (alias_id, product_id, alias_text, alias_type, is_active, created_at)
            VALUES (@alias_id, @product_id, @alias_text, 'llm_suggestion', TRUE, CURRENT_TIMESTAMP())
        """, job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("alias_id", "STRING", alias_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("alias_text", "STRING", alias),
        ])).result()
        alias_index.add(_normalize_alias(alias))

    def run(self, limit: int, batch_size: int = _DEFAULT_BATCH_SIZE, product_id: str | None = None) -> dict[str, int]:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        if self.recheck_batch_size <= 0:
            raise ValueError("product_resolver_recheck_batch_size must be greater than zero")
        catalog = self._catalog()
        valid_ids = {item["product_id"] for item in catalog}
        alias_index = self._active_aliases()
        examples = self._recent_resolutions(limit=15)
        resolved = 0
        pending = 0
        try:
            candidates = self._candidates(limit, product_id=product_id)
        except TypeError:
            candidates = self._candidates(limit)
        
        # Define helper functions to call Gemini batch resolver methods safely (defending against mock test lambda signature differences)
        def run_first_pass(batch):
            try:
                return self._ask_gemini_batch(batch, catalog, examples)
            except TypeError:
                return self._ask_gemini_batch(batch, catalog)

        def run_recheck_pass(batch):
            try:
                return self._ask_gemini_recheck_batch(batch, catalog, examples)
            except TypeError:
                return self._ask_gemini_recheck_batch(batch, catalog)

        # Split candidates into batches
        batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
        
        # Parallel Execution of first pass Gemini calls
        first_pass_results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_batch = {
                executor.submit(run_first_pass, batch): batch
                for batch in batches
            }
            for future in future_to_batch:
                try:
                    batch_results = future.result()
                    first_pass_results.update(batch_results)
                except Exception:
                    logger.exception("Gemini resolver batch failed")
        
        # Sequential Processing & BigQuery DB writing on main thread
        recheck_candidates: list[dict] = []
        for candidate in candidates:
            result = first_pass_results.get(str(candidate["candidate_id"]))
            if result is None:
                recheck_candidates.append(candidate)
            elif not self._result_is_auto_approvable(candidate, result, valid_ids):
                recheck_candidates.append({**candidate, "first_pass_result": result})
            elif self._apply_result(candidate, result, valid_ids, "llm_auto", alias_index):
                resolved += 1
            else:
                recheck_candidates.append({**candidate, "first_pass_result": result})
                
        # Split recheck candidates into batches
        recheck_batches = [
            recheck_candidates[i:i + self.recheck_batch_size]
            for i in range(0, len(recheck_candidates), self.recheck_batch_size)
        ]
        
        # Parallel Execution of second pass Gemini recheck calls
        second_pass_results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_batch = {
                executor.submit(
                    run_recheck_pass,
                    [{k: v for k, v in candidate.items() if k != "first_pass_result"} for candidate in batch]
                ): batch
                for batch in recheck_batches
            }
            for future in future_to_batch:
                try:
                    batch_results = future.result()
                    second_pass_results.update(batch_results)
                except Exception:
                    logger.exception("Gemini resolver recheck batch failed")
                    
        # Sequential Processing & BigQuery DB writing on main thread
        for candidate in recheck_candidates:
            result = second_pass_results.get(str(candidate["candidate_id"])) or candidate.get("first_pass_result") or {}
            if self._result_is_auto_approvable(candidate, result, valid_ids) and self._apply_result(
                candidate, result, valid_ids, "llm_batch_recheck", alias_index
            ):
                resolved += 1
            else:
                self._audit(
                    candidate,
                    "pending",
                    confidence=_result_confidence(result),
                    reason=str(result.get("reason") or "")[:500],
                    method="llm_batch_recheck",
                )
                pending += 1
        return {"processed": resolved + pending, "resolved": resolved, "pending": pending}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--product-id", type=str, default=None, help="Filter candidates by product_id")
    args = parser.parse_args()
    print(ProductTargetResolver().run(args.limit, args.batch_size, product_id=args.product_id))


if __name__ == "__main__":
    main()
