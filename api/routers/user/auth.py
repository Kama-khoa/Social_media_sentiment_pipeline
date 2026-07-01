from fastapi import APIRouter, Depends

from api.dependencies import get_current_user
from api.models import AppUser
from api.schemas.response_schemas import UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout", status_code=204)
def logout(_: AppUser = Depends(get_current_user)):
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
