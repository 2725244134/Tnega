"""
============================================
API 路由注册
============================================
集中注册所有 API 路由
"""

from fastapi import APIRouter

from app.api.endpoints import analysis, tasks, health

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(analysis.router, prefix="/analysis", tags=["分析"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(health.router, prefix="/health", tags=["系统健康"])