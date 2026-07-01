import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import hash_password
from api.database import get_db
from api.dependencies import require_admin
from api.models import AppUser
from api.schemas.request_schemas import AdminUserCreateRequest, AdminUserUpdateRequest
from api.schemas.response_schemas import AdminUserItem

router = APIRouter(prefix="/admin/users", tags=["users"])


def _to_item(user: AppUser) -> AdminUserItem:
    return AdminUserItem(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("", response_model=list[AdminUserItem])
def list_users(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(AppUser).order_by(AppUser.created_at.desc()).all()
    return [_to_item(user) for user in users]


@router.post("", response_model=AdminUserItem, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreateRequest,
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(AppUser).filter(AppUser.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email đã tồn tại.")

    user = AppUser(
        id=str(uuid.uuid4()),
        email=body.email,
        display_name=body.display_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_item(user)


@router.put("/{user_id}", response_model=AdminUserItem)
def update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    current_user: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.password:
        user.hashed_password = hash_password(body.password)
    if body.is_active is not None:
        if user.id == current_user.id and body.is_active is False:
            raise HTTPException(status_code=422, detail="Không thể vô hiệu hóa tài khoản đang đăng nhập.")
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)
    return _to_item(user)
