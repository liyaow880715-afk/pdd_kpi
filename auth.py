import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    load_users,
    verify_password,
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

_SECRET_KEY_FILE = Path("data/.jwt_secret")


def _load_or_create_jwt_secret() -> str:
    """优先从环境变量读取 JWT Secret；未设置则持久化到本地文件，避免每次重启失效。"""
    env_secret = os.getenv("JWT_SECRET_KEY")
    if env_secret:
        return env_secret
    if _SECRET_KEY_FILE.exists():
        return _SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    _SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_KEY_FILE.write_text(secret, encoding="utf-8")
    logging.warning(
        "JWT_SECRET_KEY 未设置，已自动生成并持久化到 %s，建议后续通过环境变量显式配置。",
        _SECRET_KEY_FILE,
    )
    return secret


SECRET_KEY = _load_or_create_jwt_secret()
if len(SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY 长度过短（建议至少 32 个字符），请重新配置。")

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


def _is_strong_password(password: str) -> bool:
    """基础密码强度：至少 8 位，且同时包含字母和数字"""
    if not password or len(password) < 8:
        return False
    has_alpha = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_alpha and has_digit


def _get_admin_initial_password() -> str:
    """
    返回 admin 初始密码。
    - 若 admin 已存在（无论是否修改过密码），允许不设置 ADMIN_PASSWORD，避免已有部署无法启动。
    - 若 admin 不存在，则必须从环境变量读取强密码进行初始化。
    """
    env_password = os.getenv("ADMIN_PASSWORD")
    users = load_users()
    admin_exists = users.get("admin") is not None

    if not admin_exists and not env_password:
        raise RuntimeError(
            "ADMIN_PASSWORD 环境变量未设置，请在启动前配置 admin 初始密码。"
        )
    if env_password and not _is_strong_password(env_password):
        raise RuntimeError(
            "ADMIN_PASSWORD 强度不足：请设置至少 8 位且同时包含字母和数字的密码。"
        )
    return env_password or "placeholder"


def init_auth():
    """启动时校验安全配置并确保 admin 主账号存在"""
    admin_password = _get_admin_initial_password()
    password_changed = os.getenv("ADMIN_PASSWORD") is not None or admin_password == "placeholder"
    ensure_admin(admin_password, password_changed=password_changed)
