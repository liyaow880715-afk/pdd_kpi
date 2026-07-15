"""
用户管理
- 维护 data/users.json
- 主账号(role=master) 拥有全部权限
- 子账号(role=sub) 仅可访问 allowed_stores 中的店铺
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import bcrypt

USERS_FILE = Path("data/users.json")


def _ensure_dir():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_raw() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_users(users: Dict[str, dict]):
    _ensure_dir()
    USERS_FILE.write_text(
        json.dumps({"users": users}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def ensure_admin(default_password: str, password_changed: bool = False):
    """初始化时保证 admin 主账号存在"""
    data = _load_raw()
    users = data.get("users", {})
    if "admin" in users:
        # 兼容旧数据：若字段不存在，默认按已修改处理，避免强制已存在账号改密
        if "password_changed" not in users["admin"]:
            users["admin"]["password_changed"] = True
            _save_users(users)
        return
    users["admin"] = {
        "role": "master",
        "password_hash": hash_password(default_password),
        "allowed_stores": [],
        "password_changed": password_changed,
    }
    _save_users(users)


def load_users() -> Dict[str, dict]:
    return _load_raw().get("users", {})


def get_user(username: str) -> Optional[dict]:
    return load_users().get(username)


def user_exists(username: str) -> bool:
    return username in load_users()


def sanitize_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password_hash"}


def create_user(
    username: str,
    password: str,
    role: str = "sub",
    allowed_stores: Optional[List[str]] = None,
) -> dict:
    users = load_users()
    if username in users:
        raise ValueError("用户已存在")
    users[username] = {
        "role": role,
        "password_hash": hash_password(password),
        "allowed_stores": list(allowed_stores or []),
        "password_changed": False,
    }
    _save_users(users)
    return {"username": username, **sanitize_user(users[username])}


def update_user(
    username: str,
    password: Optional[str] = None,
    allowed_stores: Optional[List[str]] = None,
) -> dict:
    users = load_users()
    user = users.get(username)
    if not user:
        raise ValueError("用户不存在")
    if password is not None:
        user["password_hash"] = hash_password(password)
        user["password_changed"] = True
    if allowed_stores is not None:
        user["allowed_stores"] = list(allowed_stores)
    _save_users(users)
    return {"username": username, **sanitize_user(user)}


def delete_user(username: str):
    users = load_users()
    user = users.get(username)
    if not user:
        raise ValueError("用户不存在")
    if user.get("role") == "master":
        raise ValueError("不能删除主账号")
    del users[username]
    _save_users(users)


def can_access_store(user: dict, store_name: str) -> bool:
    if user.get("role") == "master":
        return True
    allowed = user.get("allowed_stores") or []
    return store_name in allowed


def allowed_store_names(user: dict, all_stores: List[str]) -> List[str]:
    if user.get("role") == "master":
        return list(all_stores)
    allowed = set(user.get("allowed_stores") or [])
    return [s for s in all_stores if s in allowed]
