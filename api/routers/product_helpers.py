import json

from fastapi import HTTPException
from google.cloud import bigquery

from api.bq_client import query_to_list
from api.config import get_settings


def json_value(value):
    if value is None or isinstance(value, dict):
        return value
    return json.loads(value)


def validate_specs(product_id: str, specs: dict | None) -> None:
    if not specs:
        return
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT t.spec_key, t.value_type
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` p
        JOIN `{settings.gcp_project_id}.{settings.bq_dataset}.product_spec_templates` t
          ON p.category = t.category
        WHERE p.product_id = @product_id AND t.is_active = TRUE
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    types = {r["spec_key"]: r["value_type"] for r in rows}
    unknown = sorted(set(specs) - set(types))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown specification keys: {', '.join(unknown)}")
    expected_types = {"string": str, "number": (int, float), "boolean": bool}
    for key, value in specs.items():
        if (
            value is not None
            and (
                not isinstance(value, expected_types[types[key]])
                or (types[key] == "number" and isinstance(value, bool))
            )
        ):
            raise HTTPException(status_code=422, detail=f"Invalid value type for specification: {key}")
