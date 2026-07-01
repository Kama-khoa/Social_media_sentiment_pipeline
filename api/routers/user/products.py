import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from sqlalchemy.orm import Session

from api.bq_client import get_bq_client, normalize_controversy, query_to_list
from api.config import get_settings
from api.database import get_db
from api.dependencies import get_current_user
from api.models import AppUser, ProductFavorite
from api.routers.product_helpers import json_value, validate_specs
from api.schemas.request_schemas import ProductDetailChangeRequestCreate
from api.schemas.response_schemas import FavoriteProductItem, ProductFavoriteStatus, ProductDetailChangeRequestItem

router = APIRouter(prefix="/products", tags=["products"])


def _ensure_active_product(product_id: str) -> None:
    settings = get_settings()
    products = query_to_list(
        f"""
        SELECT product_id
        FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_config`
        WHERE product_id = @product_id AND is_active = TRUE
        """,
        [bigquery.ScalarQueryParameter("product_id", "STRING", product_id)],
    )
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")


@router.get("/favorites", response_model=list[FavoriteProductItem])
def list_favorite_products(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorites = (
        db.query(ProductFavorite)
        .filter(ProductFavorite.user_id == current_user.id)
        .order_by(ProductFavorite.created_at.desc())
        .all()
    )
    if not favorites:
        return []

    product_ids = [favorite.product_id for favorite in favorites]
    created_at_by_id = {favorite.product_id: favorite.created_at for favorite in favorites}
    settings = get_settings()
    rows = query_to_list(
        f"""
        WITH requested_products AS (
            SELECT product_id
            FROM UNNEST(@product_ids) AS product_id
        ),
        latest_ranking AS (
            SELECT product_id, bayesian_score, controversy_label, total_mention_count, total_mentions, statement_count, positive_count, negative_count
            FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            WHERE ranking_date = (
                SELECT MAX(ranking_date)
                FROM `{settings.gcp_project_id}.{settings.bq_marts_dataset}.agg_daily_product_ranking`
            )
        )
        SELECT
            p.product_id,
            p.product_name,
            p.brand,
            p.category,
            r.bayesian_score,
            r.controversy_label,
            COALESCE(r.total_mention_count, r.total_mentions, 0) AS total_mentions,
            COALESCE(r.statement_count, 0) AS statement_count,
            SAFE_DIVIDE(COALESCE(r.positive_count, 0) * 100.0, r.statement_count) AS positive_pct,
            SAFE_DIVIDE(COALESCE(r.negative_count, 0) * 100.0, r.statement_count) AS negative_pct
        FROM requested_products requested
        JOIN `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p
          ON requested.product_id = p.product_id
        LEFT JOIN latest_ranking r
          ON p.product_id = r.product_id
        WHERE p.is_active = TRUE
        """,
        [bigquery.ArrayQueryParameter("product_ids", "STRING", product_ids)],
    )

    product_by_id = {row["product_id"]: row for row in rows}
    return [
        FavoriteProductItem(
            product_id=row["product_id"],
            product_name=row["product_name"],
            brand=row.get("brand"),
            category=row.get("category"),
            bayesian_score=round(float(row.get("bayesian_score") or 0), 4),
            controversy_label=normalize_controversy(row.get("controversy_label")),
            total_mentions=int(row.get("total_mentions") or 0),
            statement_count=int(row.get("statement_count") or 0),
            positive_pct=round(float(row.get("positive_pct") or 0), 1),
            negative_pct=round(float(row.get("negative_pct") or 0), 1),
            created_at=created_at_by_id[row["product_id"]],
        )
        for product_id in product_ids
        if (row := product_by_id.get(product_id))
    ]


@router.get("/{product_id}/favorite", response_model=ProductFavoriteStatus)
def get_product_favorite_status(
    product_id: str,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_favorite = (
        db.query(ProductFavorite)
        .filter(
            ProductFavorite.user_id == current_user.id,
            ProductFavorite.product_id == product_id,
        )
        .first()
        is not None
    )
    return ProductFavoriteStatus(product_id=product_id, is_favorite=is_favorite)


@router.post("/{product_id}/favorite", response_model=ProductFavoriteStatus, status_code=201)
def add_product_favorite(
    product_id: str,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_active_product(product_id)
    favorite = (
        db.query(ProductFavorite)
        .filter(
            ProductFavorite.user_id == current_user.id,
            ProductFavorite.product_id == product_id,
        )
        .first()
    )
    if not favorite:
        db.add(ProductFavorite(user_id=current_user.id, product_id=product_id))
        db.commit()
    return ProductFavoriteStatus(product_id=product_id, is_favorite=True)


@router.delete("/{product_id}/favorite", response_model=ProductFavoriteStatus)
def remove_product_favorite(
    product_id: str,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favorite = (
        db.query(ProductFavorite)
        .filter(
            ProductFavorite.user_id == current_user.id,
            ProductFavorite.product_id == product_id,
        )
        .first()
    )
    if favorite:
        db.delete(favorite)
        db.commit()
    return ProductFavoriteStatus(product_id=product_id, is_favorite=False)


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


@router.get("/details/requests", response_model=list[ProductDetailChangeRequestItem])
def list_my_detail_requests(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT r.*, p.product_name FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests` r
        LEFT JOIN `{settings.gcp_project_id}.{settings.bq_marts_dataset}.dim_products` p ON r.product_id = p.product_id
        WHERE r.submitted_by = @submitted_by
        ORDER BY r.created_at DESC
        """,
        [bigquery.ScalarQueryParameter("submitted_by", "STRING", current_user.id)],
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


@router.delete("/details/requests/{request_id}", status_code=204)
def cancel_detail_request(
    request_id: str,
    current_user: AppUser = Depends(get_current_user)
):
    settings = get_settings()
    rows = query_to_list(
        f"""
        SELECT submitted_by, status FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
        WHERE request_id = @request_id
        """,
        [bigquery.ScalarQueryParameter("request_id", "STRING", request_id)]
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Phiếu yêu cầu không tồn tại.")
        
    req = rows[0]
    if req["submitted_by"] != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền hủy phiếu này.")
        
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Chỉ có thể hủy phiếu đang ở trạng thái Đang chờ.")
        
    get_bq_client().query(
        f"""
        DELETE FROM `{settings.gcp_project_id}.{settings.bq_dataset}.product_detail_change_requests`
        WHERE request_id = @request_id
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("request_id", "STRING", request_id)
        ])
    ).result()

