from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from auth import authenticate_user, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Dict[str, Any])
def login(req: LoginRequest):
    if not authenticate_user(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    access_token = create_access_token({"sub": "admin"}, expires_delta=timedelta(days=7))
    return {"access_token": access_token, "token_type": "bearer"}
