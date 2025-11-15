"""
============================================
Tnega FastAPI 主应用
============================================
基于 FastAPI + Redis + Celery 的社交内容分析服务
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis, close_redis
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理

    启动时：
    - 初始化数据库连接
    - 初始化 Redis 连接
    - 设置日志配置

    关闭时：
    - 清理 Redis 连接
    - 关闭数据库连接
    """
    # 启动
    logger.info("🚀 启动 Tnega 服务...")

    # 设置日志
    setup_logging()

    # 初始化数据库
    logger.info("📊 初始化数据库连接...")
    await init_db()

    # 初始化 Redis
    logger.info("🔄 初始化 Redis 连接...")
    await init_redis()

    logger.info("✅ 服务启动完成")
    yield

    # 关闭
    logger.info("🛑 关闭服务...")

    # 关闭 Redis 连接
    logger.info("🔄 关闭 Redis 连接...")
    await close_redis()

    logger.info("✅ 服务已关闭")


# 创建 FastAPI 应用实例
def create_app() -> FastAPI:
    """
    工厂函数创建 FastAPI 应用实例
    """
    app = FastAPI(
        title="Tnega",
        description="基于 FastAPI + Redis 的社交内容分析服务",
        version="0.2.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 添加中间件
    setup_middlewares(app)

    # 注册路由
    app.include_router(api_router, prefix="/api/v1")

    # 健康检查端点
    @app.get("/health")
    async def health_check() -> dict:
        """健康检查"""
        return {
            "status": "healthy",
            "version": "0.2.0",
            "service": "tnega"
        }

    # 根路径
    @app.get("/")
    async def root() -> dict:
        """根路径信息"""
        return {
            "message": "欢迎使用 Tnega 社交内容分析服务",
            "version": "0.2.0",
            "docs": "/docs" if settings.DEBUG else None
        }

    return app


def setup_middlewares(app: FastAPI) -> None:
    """
    配置中间件
    """
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip 压缩中间件
    app.add_middleware(GZipMiddleware, minimum_size=1000)


# 创建全局应用实例
app = create_app()


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理
    """
    logger.error(f"全局异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "内部服务器错误",
            "error": str(exc),
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )