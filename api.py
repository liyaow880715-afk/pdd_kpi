"""
PDD KPI Dashboard - FastAPI 后端
为 React + shadcn/ui 前端提供 REST API
"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import stores, imports, orders, metrics, costs, ai, wecom, exports, auth, dashboard, users, backups, douyin, douyin_costs, douyin_ai, douyin_wecom
from auth import auth_middleware, init_auth, is_public_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保数据目录存在
    from storage import init_storage
    init_storage()
    init_auth()
    yield


app = FastAPI(
    title="PDD KPI Dashboard API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS：开发环境允许全部来源，生产环境应收紧
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def http_auth_middleware(request: Request, call_next):
    return await auth_middleware(request, call_next)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(stores.router, prefix="/api/stores", tags=["stores"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(costs.router, prefix="/api/costs", tags=["costs"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(wecom.router, prefix="/api/wecom", tags=["wecom"])
app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(backups.router, prefix="/api/backups", tags=["backups"])
app.include_router(douyin.router, prefix="/api/douyin", tags=["douyin"])
app.include_router(douyin_costs.router, prefix="/api/douyin/costs", tags=["douyin-costs"])
app.include_router(douyin_ai.router, prefix="/api/douyin/ai", tags=["douyin-ai"])
app.include_router(douyin_wecom.router, prefix="/api/douyin/wecom", tags=["douyin-wecom"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
