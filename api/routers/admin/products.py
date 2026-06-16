import hashlib
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery

from api.bq_client import get_bq_client, query_to_list
from api.cache import invalidate_prefix
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.routers.product_helpers import json_value, validate_specs
from api.schemas.request_schemas import (
    ProductAliasCreateRequest,
    ProductCreateRequest,
    ProductDetailChangeRequestReview,
    ProductSpecTemplateCreateRequest,
    ProductUpdateRequest,
    ProductResolutionCandidateReview,
    VideoProductMappingOverride,
)
from api.schemas.response_schemas import (
    ProductAliasItem,
    ProductConfigItem,
    ProductDetailChangeRequestItem,
    ProductSpecTemplateItem,
)

router = APIRouter(prefix="/admin/products", tags=["product-catalog"])


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = value.replace("+", " plus ")
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", value)).strip("-")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=list[ProductConfigItem])
def list_products(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    return query_to_list(f"""
        SELECT product_id, product_name, brand, category, release_year, is_active, created_at, updated_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        ORDER BY is_active DESC, product_name
    """)


@router.post("", response_model=ProductConfigItem, status_code=201)
def create_product(body: ProductCreateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    product_id = _slugify(body.product_id or body.product_name)
    if not product_id:
        raise HTTPException(status_code=422, detail="product_id is empty after normalization")
    existing = query_to_list(
        f"SELECT product_id, product_name, is_active FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` WHERE product_id = @product_id",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if existing:
        row = existing[0]
        status = "đang hoạt động" if row["is_active"] else "đã bị tắt"
        raise HTTPException(
            status_code=409, 
            detail=f"Sản phẩm với mã '{product_id}' đã tồn tại dưới tên '{row['product_name']}' (trạng thái: {status})."
        )
    now = _now()
    get_bq_client().query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        (product_id, product_name, brand, category, release_year, is_active, created_at, updated_at)
        VALUES (@product_id, @product_name, @brand, @category, @release_year, TRUE, @now, @now)
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("product_name", "STRING", body.product_name.strip()),
            bigquery.ScalarQueryParameter("brand", "STRING", body.brand),
            bigquery.ScalarQueryParameter("category", "STRING", body.category),
            bigquery.ScalarQueryParameter("release_year", "INT64", body.release_year),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()
    return ProductConfigItem(
        product_id=product_id, product_name=body.product_name.strip(), brand=body.brand,
        category=body.category, release_year=body.release_year, is_active=True,
        created_at=datetime.fromisoformat(now), updated_at=datetime.fromisoformat(now),
    )


@router.put("/{product_id}", response_model=ProductConfigItem)
def update_product(product_id: str, body: ProductUpdateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    rows = query_to_list(
        f"SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` WHERE product_id = @product_id",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Product not found")
    row = rows[0]
    values = {
        "product_name": body.product_name.strip() if body.product_name else row["product_name"],
        "brand": body.brand if body.brand is not None else row.get("brand"),
        "category": body.category if body.category is not None else row.get("category"),
        "release_year": body.release_year if body.release_year is not None else row.get("release_year"),
    }
    get_bq_client().query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        SET product_name=@product_name, brand=@brand, category=@category,
            release_year=@release_year, updated_at=CURRENT_TIMESTAMP()
        WHERE product_id=@product_id
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("product_name", "STRING", values["product_name"]),
            bigquery.ScalarQueryParameter("brand", "STRING", values["brand"]),
            bigquery.ScalarQueryParameter("category", "STRING", values["category"]),
            bigquery.ScalarQueryParameter("release_year", "INT64", values["release_year"]),
        ]),
    ).result()
    invalidate_prefix("products:")
    return ProductConfigItem(
        product_id=product_id, is_active=row["is_active"], created_at=row["created_at"],
        updated_at=datetime.now(timezone.utc), **values,
    )


@router.delete("/{product_id}", status_code=204)
def deactivate_product(product_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    get_bq_client().query(
        f"UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` SET is_active=FALSE, updated_at=CURRENT_TIMESTAMP() WHERE product_id=@product_id",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
        ]),
    ).result()
    invalidate_prefix("products:")


@router.get("/aliases", response_model=list[ProductAliasItem])
def list_aliases(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    return query_to_list(f"""
        SELECT alias_id, product_id, alias_text, alias_type, is_active, created_at
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_aliases`
        ORDER BY product_id, alias_text
    """)


@router.post("/aliases", response_model=ProductAliasItem, status_code=201)
def create_alias(body: ProductAliasCreateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    alias_id = hashlib.md5(f"{body.product_id}|{body.alias_text.strip().lower()}".encode()).hexdigest()
    now = _now()
    get_bq_client().query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.product_aliases`
        (alias_id, product_id, alias_text, alias_type, is_active, created_at)
        VALUES (@alias_id, @product_id, @alias_text, @alias_type, TRUE, @now)
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("alias_id", "STRING", alias_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", body.product_id),
            bigquery.ScalarQueryParameter("alias_text", "STRING", body.alias_text.strip()),
            bigquery.ScalarQueryParameter("alias_type", "STRING", body.alias_type),
            bigquery.ScalarQueryParameter("now", "TIMESTAMP", now),
        ]),
    ).result()
    return ProductAliasItem(
        alias_id=alias_id, product_id=body.product_id, alias_text=body.alias_text.strip(),
        alias_type=body.alias_type, is_active=True, created_at=datetime.fromisoformat(now),
    )


@router.delete("/aliases/{alias_id}", status_code=204)
def deactivate_alias(alias_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    get_bq_client().query(
        f"UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_aliases` SET is_active=FALSE WHERE alias_id=@alias_id",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("alias_id", "STRING", alias_id),
        ]),
    ).result()


@router.get("/templates", response_model=list[ProductSpecTemplateItem])
def list_templates(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    return query_to_list(f"""
        SELECT category, spec_key, display_label, value_type, unit, is_active
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_spec_templates`
        ORDER BY category, spec_key
    """)


@router.post("/templates", response_model=ProductSpecTemplateItem, status_code=201)
def create_template(body: ProductSpecTemplateCreateRequest, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    get_bq_client().query(
        f"""
        INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.product_spec_templates`
        (category, spec_key, display_label, value_type, unit, is_active, created_at, updated_at)
        VALUES (@category, @spec_key, @display_label, @value_type, @unit, TRUE, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("category", "STRING", body.category),
            bigquery.ScalarQueryParameter("spec_key", "STRING", body.spec_key),
            bigquery.ScalarQueryParameter("display_label", "STRING", body.display_label),
            bigquery.ScalarQueryParameter("value_type", "STRING", body.value_type),
            bigquery.ScalarQueryParameter("unit", "STRING", body.unit),
        ]),
    ).result()
    return ProductSpecTemplateItem(**body.model_dump(), is_active=True)


@router.delete("/templates/{category}/{spec_key}", status_code=204)
def deactivate_template(category: str, spec_key: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    get_bq_client().query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_spec_templates`
        SET is_active=FALSE, updated_at=CURRENT_TIMESTAMP()
        WHERE category=@category AND spec_key=@spec_key
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("category", "STRING", category),
            bigquery.ScalarQueryParameter("spec_key", "STRING", spec_key),
        ]),
    ).result()


@router.get("/detail-requests", response_model=list[ProductDetailChangeRequestItem])
def list_detail_requests(status: str = "pending", _: AppUser = Depends(require_admin)):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
        WHERE status = @status
        ORDER BY created_at DESC
        """,
        [bigquery.ScalarQueryParameter("status", "STRING", status)],
    )
    for row in rows:
        row["proposed_specs"] = json_value(row.get("proposed_specs"))
    return rows


@router.post("/detail-requests/{request_id}/review")
def review_detail_request(
    request_id: str,
    body: ProductDetailChangeRequestReview,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    rows = query_to_list(
        f"SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests` WHERE request_id=@request_id AND status IN ('pending', 'processing')",
        [bigquery.ScalarQueryParameter("request_id", "STRING", request_id)],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Pending or processing request not found")
    request = rows[0]
    
    if body.action == "processing":
        get_bq_client().query(
            f"""
            UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
            SET status='processing', reviewed_by=@admin_id, reviewed_at=CURRENT_TIMESTAMP()
            WHERE request_id=@request_id
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("request_id", "STRING", request_id),
                bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
            ]),
        ).result()
        invalidate_prefix("products:")
        return {"request_id": request_id, "status": "processing"}

    specs = json_value(request.get("proposed_specs"))
    if body.action == "approve":
        validate_specs(request["product_id"], specs)
        get_bq_client().query(
            f"""
            MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` target
            USING (SELECT @product_id AS product_id) source
            ON target.product_id = source.product_id
            WHEN MATCHED THEN UPDATE SET
                specs=JSON_MERGE_PATCH(COALESCE(target.specs, PARSE_JSON('{{}}')), PARSE_JSON(@specs)),
                description=COALESCE(@description, target.description),
                official_url=COALESCE(@official_url, target.official_url),
                image_url=COALESCE(@image_url, target.image_url),
                updated_at=CURRENT_TIMESTAMP(), updated_by=@admin_id
            WHEN NOT MATCHED THEN INSERT
                (product_id, specs, description, official_url, image_url, updated_at, updated_by)
            VALUES
                (@product_id, PARSE_JSON(@specs), @description, @official_url, @image_url, CURRENT_TIMESTAMP(), @admin_id)
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", request["product_id"]),
                bigquery.ScalarQueryParameter("specs", "STRING", json.dumps(specs or {})),
                bigquery.ScalarQueryParameter("description", "STRING", request.get("proposed_description")),
                bigquery.ScalarQueryParameter("official_url", "STRING", request.get("proposed_official_url")),
                bigquery.ScalarQueryParameter("image_url", "STRING", request.get("proposed_image_url")),
                bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
            ]),
        ).result()
    status = "approved" if body.action == "approve" else "rejected"
    get_bq_client().query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
        SET status=@status, reviewed_by=@admin_id, reviewed_at=CURRENT_TIMESTAMP(), review_note=@review_note
        WHERE request_id=@request_id
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("request_id", "STRING", request_id),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
            bigquery.ScalarQueryParameter("review_note", "STRING", body.review_note),
        ]),
    ).result()
    invalidate_prefix("products:")
    return {"request_id": request_id, "status": status}


@router.get("/video-mappings")
def list_video_mappings(limit: int = 100, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    return query_to_list(f"""
        SELECT video_id, product_id, role, match_source, confidence_score
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_video_product_mentions`
        ORDER BY _dbt_processed_at DESC
        LIMIT {min(max(limit, 1), 500)}
    """)


@router.put("/video-mappings/{video_id}")
def override_video_mapping(
    video_id: str,
    body: VideoProductMappingOverride,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    get_bq_client().query(
        f"""
        MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.video_product_overrides` target
        USING (SELECT @video_id AS video_id, @product_id AS product_id) source
        ON target.video_id=source.video_id AND target.product_id=source.product_id
        WHEN MATCHED THEN UPDATE SET role=@role, is_active=TRUE, updated_by=@admin_id, updated_at=CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT (video_id, product_id, role, is_active, updated_by, updated_at)
        VALUES (@video_id, @product_id, @role, TRUE, @admin_id, CURRENT_TIMESTAMP())
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            bigquery.ScalarQueryParameter("product_id", "STRING", body.product_id),
            bigquery.ScalarQueryParameter("role", "STRING", body.role),
            bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
        ]),
    ).result()
    return {"video_id": video_id, "product_id": body.product_id, "role": body.role}


@router.get("/resolution-candidates/counts")
def get_resolution_candidate_counts(_: AppUser = Depends(require_admin)):
    settings = get_settings()
    
    reviewed_counts = query_to_list(f"""
        SELECT status, COUNT(*) as cnt 
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates`
        GROUP BY status
    """)
    
    pending_computed_result = query_to_list(f"""
        SELECT COUNT(*) as cnt
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_product_resolution_candidates` c
        LEFT JOIN `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates` r
          ON c.candidate_id = r.candidate_id
        WHERE r.candidate_id IS NULL
    """)
    
    counts = {"pending": 0, "approved": 0, "rejected": 0}
    for row in reviewed_counts:
        st = row.get("status")
        if st in counts:
            counts[st] = row.get("cnt", 0)
            
    pending_computed = pending_computed_result[0].get("cnt", 0) if pending_computed_result else 0
    counts["pending"] += pending_computed
    
    return counts

@router.get("/resolution-candidates")
def list_resolution_candidates(status: str = "pending", page: int = 1, limit: int = 20, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    offset = (page - 1) * limit
    
    if status != "pending":
        query = f"""
            SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates`
            WHERE status=@status
            ORDER BY created_at DESC
            LIMIT @limit OFFSET @offset
        """
        return query_to_list(
            query,
            [
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
                bigquery.ScalarQueryParameter("offset", "INT64", offset),
            ],
        )

    query = f"""
        SELECT * FROM (
            SELECT candidate_id, source_type, source_id, candidate_text, status,
                   resolved_product_id, reviewed_by, reviewed_at, created_at,
                   resolver_confidence, resolver_reason, resolution_method
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates`
            WHERE status='pending'
            
            UNION ALL
            
            SELECT c.candidate_id, c.source_type, c.source_id, c.candidate_text, 'pending' as status,
                   CAST(NULL AS STRING) as resolved_product_id, CAST(NULL AS STRING) as reviewed_by, 
                   CAST(NULL AS TIMESTAMP) as reviewed_at, c.created_at, 
                   CAST(NULL AS FLOAT64) as resolver_confidence, CAST(NULL AS STRING) as resolver_reason, 
                   CAST(NULL AS STRING) as resolution_method
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_product_resolution_candidates` c
            LEFT JOIN `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates` r
              ON c.candidate_id = r.candidate_id
            WHERE r.candidate_id IS NULL
        )
        ORDER BY created_at DESC
        LIMIT @limit OFFSET @offset
    """
    
    return query_to_list(
        query,
        [
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ],
    )


@router.post("/resolution-candidates/{candidate_id}/review")
def review_resolution_candidate(
    candidate_id: str,
    body: ProductResolutionCandidateReview,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    computed = query_to_list(
        f"SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_product_resolution_candidates` WHERE candidate_id=@candidate_id",
        [bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id)],
    )
    if not computed:
        raise HTTPException(status_code=404, detail="Resolution candidate not found")
    candidate = computed[0]
    if candidate["source_type"] == "sentence" and body.sentiment_label is None:
        raise HTTPException(status_code=422, detail="sentiment_label is required for sentence candidates")
    get_bq_client().query(
        f"""
        MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates` target
        USING (SELECT @candidate_id AS candidate_id) source
        ON target.candidate_id=source.candidate_id
        WHEN MATCHED THEN UPDATE SET status='approved', resolved_product_id=@product_id,
            reviewed_by=@admin_id, reviewed_at=CURRENT_TIMESTAMP(), resolution_method='admin',
            resolver_confidence=1.0, resolver_reason='Approved manually by admin'
        WHEN NOT MATCHED THEN INSERT
            (candidate_id, source_type, source_id, candidate_text, status, resolved_product_id,
             reviewed_by, reviewed_at, created_at, resolver_confidence, resolver_reason, resolution_method)
        VALUES
            (@candidate_id, @source_type, @source_id, @candidate_text, 'approved', @product_id,
             @admin_id, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), 1.0, 'Approved manually by admin', 'admin')
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id),
            bigquery.ScalarQueryParameter("source_type", "STRING", candidate["source_type"]),
            bigquery.ScalarQueryParameter("source_id", "STRING", candidate["source_id"]),
            bigquery.ScalarQueryParameter("candidate_text", "STRING", candidate["candidate_text"]),
            bigquery.ScalarQueryParameter("product_id", "STRING", body.product_id),
            bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
        ]),
    ).result()
    if candidate["source_type"] == "video":
        override_video_mapping(candidate["source_id"], VideoProductMappingOverride(product_id=body.product_id), admin)
    else:
        get_bq_client().query(
            f"""
            MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.sentence_product_target_overrides` target
            USING (SELECT @sentence_id sentence_id, @product_id product_id) source
            ON target.sentence_id=source.sentence_id AND target.product_id=source.product_id
            WHEN MATCHED THEN UPDATE SET sentiment_label=@sentiment_label, target_source='admin_override',
                target_confidence=1.0, updated_by=@admin_id, updated_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT
                (sentence_id, product_id, sentiment_label, target_source, target_confidence, updated_by, updated_at)
            VALUES (@sentence_id, @product_id, @sentiment_label, 'admin_override', 1.0, @admin_id, CURRENT_TIMESTAMP())
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("sentence_id", "STRING", candidate["source_id"]),
                bigquery.ScalarQueryParameter("product_id", "STRING", body.product_id),
                bigquery.ScalarQueryParameter("sentiment_label", "STRING", body.sentiment_label),
                bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
            ]),
        ).result()
    if body.alias_text:
        create_alias(ProductAliasCreateRequest(product_id=body.product_id, alias_text=body.alias_text), admin)
    return {"candidate_id": candidate_id, "status": "approved", "product_id": body.product_id}


@router.post("/resolution-candidates/{candidate_id}/reject")
def reject_resolution_candidate(
    candidate_id: str,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    rows = query_to_list(
        f"SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}_intermediate.int_product_resolution_candidates` WHERE candidate_id=@candidate_id",
        [bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id)],
    )
    if not rows:
        rows = query_to_list(
            f"SELECT * FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates` WHERE candidate_id=@candidate_id",
            [bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id)],
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Resolution candidate not found")
    candidate = rows[0]
    get_bq_client().query(
        f"""
        MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.product_resolution_candidates` target
        USING (SELECT @candidate_id AS candidate_id) source
        ON target.candidate_id=source.candidate_id
        WHEN MATCHED THEN UPDATE SET status='rejected', resolved_product_id=NULL,
            reviewed_by=@admin_id, reviewed_at=CURRENT_TIMESTAMP(), resolution_method='admin',
            resolver_confidence=0.0, resolver_reason='Rejected manually by admin'
        WHEN NOT MATCHED THEN INSERT
            (candidate_id, source_type, source_id, candidate_text, status, resolved_product_id,
             reviewed_by, reviewed_at, created_at, resolver_confidence, resolver_reason, resolution_method)
        VALUES
            (@candidate_id, @source_type, @source_id, @candidate_text, 'rejected', NULL,
             @admin_id, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), 0.0, 'Rejected manually by admin', 'admin')
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("candidate_id", "STRING", candidate_id),
            bigquery.ScalarQueryParameter("source_type", "STRING", candidate["source_type"]),
            bigquery.ScalarQueryParameter("source_id", "STRING", candidate["source_id"]),
            bigquery.ScalarQueryParameter("candidate_text", "STRING", candidate["candidate_text"]),
            bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
        ]),
    ).result()
    return {"candidate_id": candidate_id, "status": "rejected"}
