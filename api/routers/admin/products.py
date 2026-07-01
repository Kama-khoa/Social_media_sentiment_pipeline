import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from google.cloud import bigquery

from api.bq_client import get_bq_client, query_to_list
from api.cache import invalidate_prefix
from api.config import get_settings
from api.dependencies import require_admin
from api.models import AppUser
from api.database import get_db
from sqlalchemy.orm import Session
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
from api.services.keyword_service import KeywordService
from api.schemas.response_schemas import (
    ProductAliasItem,
    ProductConfigItem,
    ProductDetailChangeRequestItem,
    ProductSpecTemplateItem,
    ProductAdminDetailResponse,
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
def list_products(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    _: AppUser = Depends(require_admin)
):
    settings = get_settings()
    where_clauses = []
    params = []
    if category:
        where_clauses.append("category = @category")
        params.append(bigquery.ScalarQueryParameter("category", "STRING", category))
    if q:
        q_clean = f"%{q.strip().lower()}%"
        where_clauses.append("(LOWER(product_name) LIKE @q OR LOWER(product_id) LIKE @q OR LOWER(brand) LIKE @q)")
        params.append(bigquery.ScalarQueryParameter("q", "STRING", q_clean))
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    limit_sql = ""
    if limit is not None:
        limit_sql = f"LIMIT @limit"
        params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
    if offset is not None:
        limit_sql += f" OFFSET @offset"
        params.append(bigquery.ScalarQueryParameter("offset", "INT64", offset))
        
    return query_to_list(f"""
        SELECT 
            *,
            (SELECT COUNT(1) FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` dp WHERE dp.product_id = t.product_id) > 0 AS is_synced,
            EXISTS(
                SELECT 1 
                FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config` k 
                WHERE k.search_cluster = t.product_id AND k.is_active = TRUE
            ) AS has_keyword
        FROM (
            SELECT product_id, product_name, brand, category, release_year, is_active, created_at, updated_at
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
            {where_sql}
        ) t
        ORDER BY t.created_at DESC
        {limit_sql}
    """, params)


@router.get("/count", response_model=dict[str, int])
def get_products_count(
    category: Optional[str] = None,
    q: Optional[str] = None,
    _: AppUser = Depends(require_admin)
):
    settings = get_settings()
    where_clauses = []
    params = []
    if category:
        where_clauses.append("category = @category")
        params.append(bigquery.ScalarQueryParameter("category", "STRING", category))
    if q:
        q_clean = f"%{q.strip().lower()}%"
        where_clauses.append("(LOWER(product_name) LIKE @q OR LOWER(product_id) LIKE @q OR LOWER(brand) LIKE @q)")
        params.append(bigquery.ScalarQueryParameter("q", "STRING", q_clean))
        
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    rows = query_to_list(f"""
        SELECT COUNT(*) as cnt
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        {where_sql}
    """, params)
    return {"count": rows[0]["cnt"] if rows else 0}


@router.post("", response_model=ProductConfigItem, status_code=201)
def create_product(body: ProductCreateRequest, admin: AppUser = Depends(require_admin)):
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
    
    if body.specs is not None:
        get_bq_client().query(
            f"""
            INSERT INTO `{settings.gcp_project_id}.{settings.bq_dataset}.product_details`
            (product_id, specs, updated_at, updated_by)
            VALUES (@product_id, PARSE_JSON(@specs), CURRENT_TIMESTAMP(), @admin_id)
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("specs", "STRING", json.dumps(body.specs)),
                bigquery.ScalarQueryParameter("admin_id", "STRING", admin.id),
            ])
        ).result()
        
    invalidate_prefix("products:")
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
        "is_active": body.is_active if body.is_active is not None else row.get("is_active"),
    }
    get_bq_client().query(
        f"""
        UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        SET product_name=@product_name, brand=@brand, category=@category,
            release_year=@release_year, is_active=@is_active, updated_at=CURRENT_TIMESTAMP()
        WHERE product_id=@product_id
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("product_name", "STRING", values["product_name"]),
            bigquery.ScalarQueryParameter("brand", "STRING", values["brand"]),
            bigquery.ScalarQueryParameter("category", "STRING", values["category"]),
            bigquery.ScalarQueryParameter("release_year", "INT64", values["release_year"]),
            bigquery.ScalarQueryParameter("is_active", "BOOL", values["is_active"]),
        ]),
    ).result()

    if body.specs is not None or body.description is not None or body.official_url is not None or body.image_url is not None:
        existing_details = query_to_list(
            f"SELECT specs FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` WHERE product_id = @product_id",
            [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)]
        )
        existing_specs = json_value(existing_details[0].get("specs")) if existing_details else {}
        if not isinstance(existing_specs, dict):
            existing_specs = {}
        merged_specs = {**existing_specs, **(body.specs or {})}

        get_bq_client().query(
            f"""
            MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` target
            USING (SELECT @product_id AS product_id) source
            ON target.product_id = source.product_id
            WHEN MATCHED THEN UPDATE SET
                specs=PARSE_JSON(@merged_specs),
                description=COALESCE(@description, target.description),
                official_url=COALESCE(@official_url, target.official_url),
                image_url=COALESCE(@image_url, target.image_url),
                updated_at=CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT
                (product_id, specs, description, official_url, image_url, updated_at)
            VALUES
                (@product_id, PARSE_JSON(@merged_specs), @description, @official_url, @image_url, CURRENT_TIMESTAMP())
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("merged_specs", "STRING", json.dumps(merged_specs, ensure_ascii=False)),
                bigquery.ScalarQueryParameter("description", "STRING", body.description),
                bigquery.ScalarQueryParameter("official_url", "STRING", body.official_url),
                bigquery.ScalarQueryParameter("image_url", "STRING", body.image_url),
            ]),
        ).result()

    invalidate_prefix("products:")
    return ProductConfigItem(
        product_id=product_id, created_at=row["created_at"],
        updated_at=datetime.now(timezone.utc), **values,
    )



@router.delete("/{product_id}", status_code=204)
def deactivate_product(product_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    bq_client = get_bq_client()
    bq_client.query(
        f"UPDATE `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` SET is_active=FALSE, updated_at=CURRENT_TIMESTAMP() WHERE product_id=@product_id",
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
        ])
    ).result()
    invalidate_prefix("products:")
    
    keyword_service = KeywordService(bq_client, settings.gcp_project_id, settings.bq_dataset)
    keywords_deactivated = keyword_service.deactivate_by_product(product_id)
    
    return {"message": "Product deactivated successfully", "keywords_deactivated": keywords_deactivated}


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
def list_detail_requests(
    status: str = "pending",
    db: Session = Depends(get_db),
    _: AppUser = Depends(require_admin),
):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT r.*, p.product_name FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests` r
        LEFT JOIN `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p ON r.product_id = p.product_id
        WHERE r.status = @status
        ORDER BY r.created_at DESC
        """,
        [bigquery.ScalarQueryParameter("status", "STRING", status)],
    )
    
    # Resolve user details from Postgres
    user_ids = set()
    for row in rows:
        if row.get("submitted_by"):
            user_ids.add(row["submitted_by"])
        if row.get("reviewed_by"):
            user_ids.add(row["reviewed_by"])
            
    user_map = {}
    if user_ids:
        users = db.query(AppUser).filter(AppUser.id.in_(list(user_ids))).all()
        user_map = {u.id: u.display_name for u in users}
        
    for row in rows:
        row["proposed_specs"] = json_value(row.get("proposed_specs"))
        row["submitted_by"] = user_map.get(row.get("submitted_by"), row.get("submitted_by"))
        if row.get("reviewed_by"):
            row["reviewed_by"] = user_map.get(row.get("reviewed_by"), row.get("reviewed_by"))
            
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
        
        # Fetch existing specs to perform python-side merge instead of relying on non-existent BQ JSON_MERGE_PATCH
        existing_rows = query_to_list(
            f"SELECT specs FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` WHERE product_id=@product_id",
            [bigquery.ScalarQueryParameter("product_id", "STRING", request["product_id"])],
        )
        existing_specs = json_value(existing_rows[0].get("specs")) if existing_rows else {}
        if not isinstance(existing_specs, dict):
            existing_specs = {}
            
        merged_specs = {**existing_specs, **(specs or {})}
        
        get_bq_client().query(
            f"""
            MERGE `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` target
            USING (SELECT @product_id AS product_id) source
            ON target.product_id = source.product_id
            WHEN MATCHED THEN UPDATE SET
                specs=PARSE_JSON(@merged_specs),
                description=COALESCE(@description, target.description),
                official_url=COALESCE(@official_url, target.official_url),
                image_url=COALESCE(@image_url, target.image_url),
                updated_at=CURRENT_TIMESTAMP(), updated_by=@admin_id
            WHEN NOT MATCHED THEN INSERT
                (product_id, specs, description, official_url, image_url, updated_at, updated_by)
            VALUES
                (@product_id, PARSE_JSON(@merged_specs), @description, @official_url, @image_url, CURRENT_TIMESTAMP(), @admin_id)
            """,
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", request["product_id"]),
                bigquery.ScalarQueryParameter("merged_specs", "STRING", json.dumps(merged_specs, ensure_ascii=False)),
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


@router.post("/{product_id}/sync")
def sync_product(
    product_id: str,
    background_tasks: BackgroundTasks,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    bq_client = get_bq_client()
    products = query_to_list(
        f"SELECT product_id, product_name FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` WHERE product_id = @product_id",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not products:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    product = products[0]
    product_name = product["product_name"]

    # Check if keyword already exists
    existing_kws = query_to_list(
        f"SELECT keyword_id FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config` WHERE search_cluster = @product_id AND LOWER(keyword_text) = @kw_text AND is_active = TRUE",
        [
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("kw_text", "STRING", product_name.strip().lower()),
        ],
    )
    if not existing_kws:
        keyword_service = KeywordService(bq_client, settings.gcp_project_id, settings.bq_dataset)
        from api.schemas.keyword_schemas import KeywordCreateRequest
        keyword_service.create_keyword(
            KeywordCreateRequest(
                keyword_text=product_name.strip(),
                search_cluster=product_id
            )
        )

    def run_dbt_sync():
        import subprocess
        import sys
        from pathlib import Path
        
        logger = logging.getLogger("api.products.sync")
        logger.info(f"Background sync task started for product {product_id}")
        
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        dbt_runner_path = project_root / "scripts" / "dbt" / "dbt_runner.py"
        
        cmd = [sys.executable, str(dbt_runner_path), "run", "--select", "dim_products agg_daily_product_ranking"]
        logger.info(f"Running cmd: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"DBT sync failed: {result.stderr or result.stdout}")
        else:
            logger.info("DBT sync completed successfully")
            from api.cache import invalidate_prefix
            invalidate_prefix("products:")

    background_tasks.add_task(run_dbt_sync)
    return {"message": "Đã bắt đầu tiến trình đồng bộ sản phẩm", "product_id": product_id}


@router.post("/{product_id}/crawl")
def crawl_product(
    product_id: str,
    background_tasks: BackgroundTasks,
    use_ytdlp: bool = False,
    admin: AppUser = Depends(require_admin),
):
    settings = get_settings()
    bq_client = get_bq_client()
    
    products = query_to_list(
        f"SELECT product_id, product_name FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` WHERE product_id = @product_id",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not products:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    product = products[0]
    product_name = product["product_name"]

    if not use_ytdlp:
        quota_logs = query_to_list(f"""
            SELECT SUM(units_used) AS total
            FROM `{settings.gcp_project_id}.{settings.bq_dataset}.quota_operation_log`
            WHERE DATE(created_at) = CURRENT_DATE()
        """)
        quota_used = quota_logs[0]["total"] if quota_logs and quota_logs[0]["total"] is not None else 0
        
        if quota_used >= 10000:
            return {
                "status": "quota_exhausted",
                "message": "Đã hết quota YouTube API trong ngày (10,000 units). Bạn có muốn sử dụng chế độ tìm kiếm dự phòng bằng yt-dlp (0 quota) không?"
            }

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    from pathlib import Path
    task_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "crawl_tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    
    with open(task_dir / f"{task_id}.json", "w", encoding="utf-8") as f:
        json.dump({
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Đang xếp hàng tiến trình...",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, f, ensure_ascii=False, indent=2)

    def run_crawl_script():
        import subprocess
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        script_path = project_root / "scripts" / "run_product_crawl.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--product-id", product_id,
            "--keyword", product_name,
            "--method", "ytdlp" if use_ytdlp else "api",
            "--task-id", task_id
        ]
        
        logger = logging.getLogger("api.products.crawl")
        logger.info(f"Starting product crawl background task: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Crawl script failed: {result.stderr or result.stdout}")
        else:
            logger.info("Crawl script completed successfully")
            from api.cache import invalidate_prefix
            invalidate_prefix("products:")

    background_tasks.add_task(run_crawl_script)
    return {"status": "accepted", "task_id": task_id, "message": "Đã tiếp nhận yêu cầu thu thập dữ liệu"}


@router.get("/crawl-tasks/{task_id}")
def get_crawl_task_status(task_id: str, _: AppUser = Depends(require_admin)):
    from pathlib import Path
    task_file = Path(__file__).resolve().parent.parent.parent.parent / "data" / "crawl_tasks" / f"{task_id}.json"
    if not task_file.exists():
        raise HTTPException(status_code=404, detail="Task không tồn tại")
        
    with open(task_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/{product_id}", response_model=ProductAdminDetailResponse)
def get_product(product_id: str, _: AppUser = Depends(require_admin)):
    settings = get_settings()
    configs = query_to_list(
        f"""
        SELECT 
            *,
            (SELECT COUNT(1) FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` dp WHERE dp.product_id = t.product_id) > 0 AS is_synced,
            EXISTS(
                SELECT 1 
                FROM `{settings.gcp_project_id}.{settings.bq_dataset}.keyword_config` k 
                WHERE k.search_cluster = t.product_id AND k.is_active = TRUE
            ) AS has_keyword
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config` t
        WHERE t.product_id = @product_id
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not configs:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
    config = configs[0]

    details = query_to_list(
        f"SELECT specs, description, official_url, image_url FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_details` WHERE product_id = @product_id",
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )

    specs = None
    description = None
    official_url = None
    image_url = None
    if details:
        detail = details[0]
        specs = json_value(detail.get("specs"))
        description = detail.get("description")
        official_url = detail.get("official_url")
        image_url = detail.get("image_url")

    return ProductAdminDetailResponse(
        product_id=config["product_id"],
        product_name=config["product_name"],
        brand=config.get("brand"),
        category=config.get("category"),
        release_year=config.get("release_year"),
        is_active=config["is_active"],
        created_at=config["created_at"],
        updated_at=config["updated_at"],
        is_synced=config.get("is_synced"),
        has_keyword=config.get("has_keyword"),
        specs=specs,
        description=description,
        official_url=official_url,
        image_url=image_url,
    )
