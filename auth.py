"""
简易 JWT 认证模块
生产环境建议使用更完善的方案（OAuth2、数据库存储用户等）
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

# 从环境变量读取，未设置则随机生成（重启后旧 token 失效）
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# 默认管理员密码，强烈建议通过环境变量 ADMIN_PASSWORD 覆盖
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or "admin123"

# 启动时生成 bcrypt 哈希
_admin_hash = bcrypt.hashpw(DEFAULT_ADMIN_PASSWORD.encode(), bcrypt.gensalt())


def verify_password(plain: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed)


def authenticate_user(username: str, password: str) -> bool:
    if username != "admin":
        return False
    return verify_password(password, _admin_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


# 允许公开访问的路径前缀
PUBLIC_PATHS = {"/api/health", "/api/auth/login", "/api/docs", "/api/redoc", "/api/openapi.json"}


def is_public_path(path: str) -> bool:
    for public in PUBLIC_PATHS:
        if path == public or path.startswith(public + "/"):
            return True
    return False


async def auth_middleware(request: Request, call_next):
    if is_public_path(request.url.path):
        return await call_next(request)

    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    bearer = HTTPBearer(auto_error=False)
    try:
        creds: HTTPAuthorizationCredentials = await bearer(request)
        if not creds:
            return JSONResponse(status_code=401, content={"detail": "未提供认证令牌"})
        payload = decode_token(creds.credentials)
        if not payload or payload.get("sub") != "admin":
            return JSONResponse(status_code=401, content={"detail": "认证令牌无效或已过期"})
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "认证失败"})

    return await call_next(request)
