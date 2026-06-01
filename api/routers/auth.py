import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.auth import create_access_token, hash_password, verify_password
from api.database import get_db
from api.dependencies import get_current_user
from api.models import AppUser
from api.schemas.request_schemas import LoginRequest, RegisterRequest
from api.schemas.response_schemas import TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserInfo, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(AppUser).filter(AppUser.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = AppUser(
        id=str(uuid.uuid4()),
        email=body.email,
        display_name=body.display_name,
        hashed_password=hash_password(body.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserInfo(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AppUser).filter(AppUser.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenResponse(access_token=token, role=user.role)


@router.post("/logout", status_code=204)
def logout(current_user: AppUser = Depends(get_current_user)):
    return None


@router.get("/me", response_model=UserInfo)
def me(current_user: AppUser = Depends(get_current_user)):
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        created_at=current_user.created_at,
    )
