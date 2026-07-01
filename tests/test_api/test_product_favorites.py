from datetime import datetime, timezone
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

from api.database import Base
from api.models import AppUser, ProductFavorite

sys.modules.setdefault(
    "jose",
    SimpleNamespace(
        JWTError=Exception,
        jwt=SimpleNamespace(encode=lambda *_args, **_kwargs: "", decode=lambda *_args, **_kwargs: {}),
    ),
)
sys.modules.setdefault("passlib", SimpleNamespace())
sys.modules.setdefault(
    "passlib.context",
    SimpleNamespace(
        CryptContext=lambda *_args, **_kwargs: SimpleNamespace(
            hash=lambda value: value,
            verify=lambda plain, hashed: plain == hashed,
        )
    ),
)


class ProductDetailChangeRequestCreate(BaseModel):
    proposed_specs: dict | None = None
    proposed_description: str | None = None
    proposed_official_url: str | None = None
    proposed_image_url: str | None = None


sys.modules.setdefault(
    "api.schemas.request_schemas",
    SimpleNamespace(ProductDetailChangeRequestCreate=ProductDetailChangeRequestCreate),
)

from api.routers.user import products


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def users(db_session):
    user_a = AppUser(
        id="user-a",
        email="a@example.com",
        display_name="User A",
        hashed_password="hash",
    )
    user_b = AppUser(
        id="user-b",
        email="b@example.com",
        display_name="User B",
        hashed_password="hash",
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()
    return user_a, user_b


def _product_rows(product_ids: list[str]):
    return [
        {
            "product_id": product_id,
            "product_name": f"Product {product_id}",
            "brand": "Brand",
            "category": "Laptop",
            "bayesian_score": 0.75,
            "controversy_label": "low",
            "total_mentions": 12,
        }
        for product_id in product_ids
    ]


def test_user_favorites_are_isolated_and_not_duplicated(monkeypatch, db_session, users):
    user_a, user_b = users

    def fake_query_to_list(_sql, params=None):
        if params and params[0].name == "product_id":
            return [{"product_id": "product-1"}]
        if params and params[0].name == "product_ids":
            return _product_rows(["product-1"])
        return []

    monkeypatch.setattr(products, "query_to_list", fake_query_to_list)

    products.add_product_favorite("product-1", current_user=user_a, db=db_session)
    products.add_product_favorite("product-1", current_user=user_a, db=db_session)

    assert db_session.query(ProductFavorite).count() == 1
    assert products.get_product_favorite_status("product-1", current_user=user_a, db=db_session).is_favorite is True
    assert products.get_product_favorite_status("product-1", current_user=user_b, db=db_session).is_favorite is False
    assert [item.product_id for item in products.list_favorite_products(current_user=user_a, db=db_session)] == ["product-1"]
    assert products.list_favorite_products(current_user=user_b, db=db_session) == []


def test_remove_favorite_is_idempotent(db_session, users):
    user_a, _ = users
    db_session.add(ProductFavorite(user_id=user_a.id, product_id="product-1", created_at=datetime.now(timezone.utc)))
    db_session.commit()

    products.remove_product_favorite("product-1", current_user=user_a, db=db_session)
    products.remove_product_favorite("product-1", current_user=user_a, db=db_session)

    assert db_session.query(ProductFavorite).count() == 0
    assert products.get_product_favorite_status("product-1", current_user=user_a, db=db_session).is_favorite is False


def test_add_favorite_rejects_missing_or_inactive_product(monkeypatch, db_session, users):
    user_a, _ = users
    monkeypatch.setattr(products, "query_to_list", lambda *_args, **_kwargs: [])

    with pytest.raises(HTTPException) as exc_info:
        products.add_product_favorite("missing-product", current_user=user_a, db=db_session)

    assert exc_info.value.status_code == 404
    assert db_session.query(ProductFavorite).count() == 0
