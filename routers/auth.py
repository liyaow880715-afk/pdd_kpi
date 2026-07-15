from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import authenticate_user, create_access_token, get_current_user
from user_manager import get_user, update_user, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str


@router.post("/login", response_model=Dict[str, Any])
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    access_token = create_access_token(
        {
            "sub": req.username,
            "role": user["role"],
            "allowed_stores": user.get("allowed_stores", []),
        },
        expires_delta=timedelta(days=7),
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}


@router.get("/me", response_model=Dict[str, Any])
def me(current_user: dict = Depends(get_current_user)):
    username = current_user.get("sub")
    user = get_user(username) if username else None
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {
        "username": username,
        "role": user.get("role", "sub"),
        "allowed_stores": user.get("allowed_stores", []),
    }


@router.post("/change-password", response_model=Dict[str, Any])
def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    username = current_user.get("sub")
    user = get_user(username) if username else None
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 修改密码必须提供原密码；主账号可通过用户管理重置子账号密码
    if not req.old_password or not verify_password(req.old_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    update_user(username, password=req.new_password)
    return {"ok": True}
