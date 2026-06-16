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
    for key, value in list(specs.items()):
        if value is None:
            continue
        expected = types[key]
        if expected == "number":
            if isinstance(value, bool):
                raise HTTPException(status_code=422, detail=f"Invalid value type for specification: {key}")
            if not isinstance(value, (int, float)):
                try:
                    specs[key] = float(value) if "." in str(value) else int(value)
                except ValueError:
                    raise HTTPException(status_code=422, detail=f"Invalid value type for specification: {key}")
        elif expected == "boolean":
            if not isinstance(value, bool):
                if str(value).lower() in ("true", "1", "yes", "có"):
                    specs[key] = True
                elif str(value).lower() in ("false", "0", "no", "không"):
                    specs[key] = False
                else:
                    raise HTTPException(status_code=422, detail=f"Invalid value type for specification: {key}")
        elif expected == "string":
            if not isinstance(value, str):
                specs[key] = str(value)
