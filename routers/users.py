from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import get_current_user, require_master
from user_manager import create_user, delete_user, load_users, update_user

router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "sub"
    allowed_stores: List[str] = []


class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    allowed_stores: Optional[List[str]] = None


@router.get("", response_model=List[Dict[str, Any]])
def list_users(_: dict = Depends(require_master)):
    users = load_users()
    return [{"username": k, **{name: v for name, v in u.items() if name != "password_hash"}} for k, u in users.items()]


@router.post("", response_model=Dict[str, Any])
def create_user_endpoint(req: CreateUserRequest, _: dict = Depends(require_master)):
    if req.role not in {"master", "sub"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色只能是 master 或 sub")
    try:
        return create_user(req.username, req.password, req.role, req.allowed_stores)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{username}", response_model=Dict[str, Any])
def update_user_endpoint(
    username: str,
    req: UpdateUserRequest,
    current_user: dict = Depends(require_master),
):
    # 主账号不能通过这里把自己降级为子账号
    if username == current_user.get("sub") and req.allowed_stores is not None:
        # 主账号始终拥有全部店铺，忽略 allowed_stores 修改
        req.allowed_stores = None
    try:
        return update_user(username, password=req.password, allowed_stores=req.allowed_stores)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{username}", response_model=Dict[str, Any])
def delete_user_endpoint(
    username: str,
    current_user: dict = Depends(require_master),
):
    if username == current_user.get("sub"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    try:
        delete_user(username)
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
