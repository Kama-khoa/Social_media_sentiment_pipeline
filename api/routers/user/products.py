import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery

from api.bq_client import get_bq_client, query_to_list
from api.config import get_settings
from api.dependencies import get_current_user
from api.models import AppUser
from api.routers.product_helpers import validate_specs
from api.schemas.request_schemas import ProductDetailChangeRequestCreate

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/{product_id}/details/requests", status_code=201)
def submit_product_detail_request(
    product_id: str,
    body: ProductDetailChangeRequestCreate,
    current_user: AppUser = Depends(get_current_user),
):
    settings = get_settings()
    products = query_to_list(
        f"SELECT product_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` WHERE product_id = @product_id AND is_active = TRUE",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    if not any((body.proposed_specs, body.proposed_description, body.proposed_official_url, body.proposed_image_url)):
        raise HTTPException(status_code=422, detail="At least one proposed change is required")
    validate_specs(product_id, body.proposed_specs)

    request_id = str(uuid.uuid4())
    client = get_bq_client()
    client.query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
        (request_id, product_id, proposed_specs, proposed_description, proposed_official_url,
         proposed_image_url, submitted_by, status, created_at)
        VALUES (@request_id, @product_id, PARSE_JSON(@specs), @description, @official_url,
                @image_url, @submitted_by, 'pending', CURRENT_TIMESTAMP())
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("request_id", "STRING", request_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("specs", "STRING", json.dumps(body.proposed_specs) if body.proposed_specs is not None else "null"),
            bigquery.ScalarQueryParameter("description", "STRING", body.proposed_description),
            bigquery.ScalarQueryParameter("official_url", "STRING", body.proposed_official_url),
            bigquery.ScalarQueryParameter("image_url", "STRING", body.proposed_image_url),
            bigquery.ScalarQueryParameter("submitted_by", "STRING", current_user.id),
        ]),
    ).result()
    return {"request_id": request_id, "status": "pending"}
