import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from user_manager import (
    allowed_page_names,
    allowed_store_names,
    can_access_page,
    can_access_store,
    ensure_admin,
    get_user,
    verify_password,
)

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"

PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


def is_public_path(path: str) -> bool:
    for public in PUBLIC_PATHS:
        if path == public or path.startswith(public + "/"):
            return True
    return False


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


async def auth_middleware(request: Request, call_next):
    if is_public_path(request.url.path):
        return await call_next(request)

    bearer = HTTPBearer(auto_error=False)
    creds: Optional[HTTPAuthorizationCredentials] = await bearer(request)
    if not creds:
        return JSONResponse(status_code=401, content={"detail": "未提供认证令牌"})

    payload = decode_token(creds.credentials)
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "认证令牌无效或已过期"})

    request.state.user = payload
    return await call_next(request)


def get_current_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    return user


def require_master(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return user


def authorize_store(user: dict, store_name: str):
    if not can_access_store(user, store_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该店铺",
        )


def authorize_stores(user: dict, store_names: List[str]) -> List[str]:
    """返回用户有权限访问的店铺名列表；master 返回全部"""
    if user.get("role") == "master":
        return list(store_names)
    allowed = set(user.get("allowed_stores") or [])
    return [s for s in store_names if s in allowed]


def accessible_stores(user: dict, all_stores: List[str]) -> List[str]:
    return allowed_store_names(user, all_stores)


def authorize_page(user: dict, page: str):
    if not can_access_page(user, page):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该功能",
        )


def require_page(page: str):
    def checker(user: dict = Depends(get_current_user)):
        authorize_page(user, page)
        return user
    return checker


def accessible_pages(user: dict) -> List[str]:
    return allowed_page_names(user)


def init_auth():
    """启动时确保 admin 主账号存在"""
    # 如果通过环境变量设置了密码，认为已经完成首次修改
    password_changed = os.getenv("ADMIN_PASSWORD") is not None
    ensure_admin(DEFAULT_ADMIN_PASSWORD, password_changed=password_changed)
