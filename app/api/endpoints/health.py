"""
============================================
系统健康检查 API 端点
============================================
系统健康状态检查接口
"""

import asyncio
import time
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger

from app.core.database import get_db, DatabaseUtils
from app.core.redis import RedisCache
from app.models.schemas import (
    HealthResponse,
    HealthStatus,
    ServiceHealth
)

router = APIRouter()

# 应用启动时间（用于计算运行时间）
app_start_time = datetime.utcnow()


@router.get("", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    系统健康检查

    检查以下服务状态：
    - 数据库连接
    - Redis 连接
    - 应用状态
    """
    try:
        # 获取各服务健康状态
        services_health = await check_all_services_health(db)

        # 计算整体健康状态
        overall_status = calculate_overall_health(services_health)

        # 计算运行时间
        uptime = (datetime.utcnow() - app_start_time).total_seconds()

        return HealthResponse(
            status=overall_status,
            version="0.2.0",
            timestamp=datetime.utcnow(),
            services=services_health,
            uptime=uptime
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"健康检查失败: {str(e)}")


@router.get("/database")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """
    数据库健康检查
    """
    try:
        start_time = time.time()

        # 执行简单查询测试连接
        result = await db.execute(text("SELECT 1"))
        db_result = result.scalar()

        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        if db_result == 1:
            return {
                "status": "healthy",
                "response_time": response_time,
                "message": "数据库连接正常"
            }
        else:
            return {
                "status": "unhealthy",
                "response_time": response_time,
                "message": "数据库查询结果异常"
            }

    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "response_time": None,
            "message": f"数据库连接失败: {str(e)}"
        }


@router.get("/redis")
async def redis_health_check():
    """
    Redis 健康检查
    """
    try:
        start_time = time.time()

        # 测试 Redis 连接
        redis_info = await RedisCache.get_connection_info()

        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        if redis_info.get("status") == "connected":
            return {
                "status": "healthy",
                "response_time": response_time,
                "message": "Redis 连接正常",
                "info": redis_info
            }
        else:
            return {
                "status": "unhealthy",
                "response_time": response_time,
                "message": "Redis 连接失败",
                "info": redis_info
            }

    except Exception as e:
        logger.error(f"Redis 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "response_time": None,
            "message": f"Redis 连接失败: {str(e)}"
        }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    详细健康检查

    包含更详细的系统信息和性能指标
    """
    try:
        # 并行检查所有服务
        health_checks = await asyncio.gather(
            check_database_health_detailed(db),
            check_redis_health_detailed(),
            check_application_health(),
            return_exceptions=True
        )

        # 处理检查结果
        services = []
        for i, check_result in enumerate(health_checks):
            if isinstance(check_result, Exception):
                # 处理异常情况
                service_name = ["database", "redis", "application"][i]
                services.append(ServiceHealth(
                    name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"检查失败: {str(check_result)}"
                ))
            else:
                services.append(check_result)

        # 计算整体状态
        overall_status = calculate_overall_health(services)

        # 计算运行时间
        uptime = (datetime.utcnow() - app_start_time).total_seconds()

        # 添加系统信息
        system_info = await get_system_info()

        return {
            "status": overall_status,
            "version": "0.2.0",
            "timestamp": datetime.utcnow(),
            "services": services,
            "uptime": uptime,
            "system": system_info
        }

    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"详细健康检查失败: {str(e)}")


# ===========================
# 辅助函数
# ===========================

async def check_all_services_health(db: AsyncSession) -> List[ServiceHealth]:
    """
    检查所有服务的健康状态

    Args:
        db: 数据库会话

    Returns:
        服务健康状态列表
    """
    services = []

    # 检查数据库
    db_health = await check_database_health(db)
    services.append(db_health)

    # 检查 Redis
    redis_health = await check_redis_health()
    services.append(redis_health)

    # 检查应用状态
    app_health = await check_application_health()
    services.append(app_health)

    return services


async def check_database_health(db: AsyncSession) -> ServiceHealth:
    """
    检查数据库健康状态

    Args:
        db: 数据库会话

    Returns:
        数据库健康状态
    """
    try:
        start_time = time.time()

        # 执行简单查询
        result = await db.execute(text("SELECT 1"))
        db_result = result.scalar()

        response_time = (time.time() - start_time) * 1000

        if db_result == 1:
            return ServiceHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message="数据库连接正常"
            )
        else:
            return ServiceHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message="数据库查询结果异常"
            )

    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return ServiceHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"数据库连接失败: {str(e)}"
        )


async def check_redis_health() -> ServiceHealth:
    """
    检查 Redis 健康状态

    Returns:
        Redis 健康状态
    """
    try:
        start_time = time.time()

        # 测试 Redis 连接
        redis_info = await RedisCache.get_connection_info()

        response_time = (time.time() - start_time) * 1000

        if redis_info.get("status") == "connected":
            return ServiceHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message="Redis 连接正常"
            )
        else:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message="Redis 连接失败"
            )

    except Exception as e:
        logger.error(f"Redis 健康检查失败: {e}")
        return ServiceHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis 连接失败: {str(e)}"
        )


async def check_application_health() -> ServiceHealth:
    """
    检查应用健康状态

    Returns:
        应用健康状态
    """
    try:
        start_time = time.time()

        # 检查应用基本状态
        uptime = (datetime.utcnow() - app_start_time).total_seconds()

        response_time = (time.time() - start_time) * 1000

        # 简单的应用状态检查
        if uptime > 0:
            return ServiceHealth(
                name="application",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message=f"应用运行正常，运行时间: {uptime:.0f}秒"
            )
        else:
            return ServiceHealth(
                name="application",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message="应用状态异常"
            )

    except Exception as e:
        logger.error(f"应用健康检查失败: {e}")
        return ServiceHealth(
            name="application",
            status=HealthStatus.UNHEALTHY,
            message=f"应用状态检查失败: {str(e)}"
        )


async def check_database_health_detailed(db: AsyncSession) -> ServiceHealth:
    """
    详细的数据库健康检查

    Args:
        db: 数据库会话

    Returns:
        详细的数据库健康状态
    """
    try:
        start_time = time.time()

        # 执行多个检查
        checks = await asyncio.gather(
            db.execute(text("SELECT COUNT(*) FROM analysis_tasks")),
            db.execute(text("SELECT COUNT(*) FROM analysis_results")),
            db.execute(text("SELECT COUNT(*) FROM tweet_data")),
            return_exceptions=True
        )

        response_time = (time.time() - start_time) * 1000

        # 处理检查结果
        task_count = checks[0].scalar() if not isinstance(checks[0], Exception) else 0
        result_count = checks[1].scalar() if not isinstance(checks[1], Exception) else 0
        tweet_count = checks[2].scalar() if not isinstance(checks[2], Exception) else 0

        # 获取数据库连接信息
        db_info = await DatabaseUtils.get_connection_info()

        return ServiceHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            response_time=response_time,
            message=f"数据库连接正常，任务: {task_count}, 结果: {result_count}, 推文: {tweet_count}"
        )

    except Exception as e:
        logger.error(f"详细数据库健康检查失败: {e}")
        return ServiceHealth(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"详细数据库检查失败: {str(e)}"
        )


async def check_redis_health_detailed() -> ServiceHealth:
    """
    详细的 Redis 健康检查

    Returns:
        详细的 Redis 健康状态
    """
    try:
        start_time = time.time()

        # 获取详细的 Redis 信息
        redis_info = await RedisCache.get_connection_info()

        response_time = (time.time() - start_time) * 1000

        if redis_info.get("status") == "connected":
            return ServiceHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                message=f"Redis 连接正常，版本: {redis_info.get('version', 'unknown')}"
            )
        else:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message="Redis 连接失败"
            )

    except Exception as e:
        logger.error(f"详细 Redis 健康检查失败: {e}")
        return ServiceHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"详细 Redis 检查失败: {str(e)}"
        )


def calculate_overall_health(services: List[ServiceHealth]) -> HealthStatus:
    """
    计算整体健康状态

    Args:
        services: 各服务健康状态列表

    Returns:
        整体健康状态
    """
    if not services:
        return HealthStatus.UNHEALTHY

    unhealthy_count = sum(1 for service in services if service.status == HealthStatus.UNHEALTHY)
    degraded_count = sum(1 for service in services if service.status == HealthStatus.DEGRADED)

    if unhealthy_count > 0:
        return HealthStatus.UNHEALTHY
    elif degraded_count > 0:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.HEALTHY


async def get_system_info() -> dict:
    """
    获取系统信息

    Returns:
        系统信息字典
    """
    try:
        import psutil

        # 获取系统资源使用情况
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": psutil.cpu_count()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used_percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "used_percent": (disk.used / disk.total) * 100
            }
        }

    except ImportError:
        # 如果没有安装 psutil，返回基本信息
        return {
            "cpu": {"usage_percent": 0, "core_count": 1},
            "memory": {"total": 0, "available": 0, "used_percent": 0},
            "disk": {"total": 0, "free": 0, "used_percent": 0}
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return {"error": str(e)}"}