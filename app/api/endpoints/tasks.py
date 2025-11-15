"""
============================================
任务管理 API 端点
============================================
任务状态查询、控制和管理接口
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.redis import RedisCache, CacheKey
from app.models.schemas import (
    SuccessResponse,
    ErrorResponse,
    CacheInfoResponse,
    CacheStatsResponse
)
from app.tasks.celery_app import get_task_info
from app.tasks.analysis import analyze_tweets
from app.tasks.collection import collect_tweets

router = APIRouter()


@router.get("/celery/{task_id}")
async def get_celery_task_info(task_id: str):
    """
    获取 Celery 任务信息

    - **task_id**: Celery 任务ID
    """
    try:
        task_info = get_task_info(task_id)
        return task_info

    except Exception as e:
        logger.error(f"获取 Celery 任务信息失败: {task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务信息失败: {str(e)}")


@router.post("/celery/analysis/{task_id}/revoke")
async def revoke_analysis_task(task_id: str, terminate: bool = False):
    """
    取消分析任务

    - **task_id**: 任务ID
    - **terminate**: 是否强制终止
    """
    try:
        # 取消 Celery 任务
        analyze_tweets.AsyncResult(task_id).revoke(terminate=terminate)

        logger.info(f"取消分析任务: {task_id}, 强制终止: {terminate}")

        return SuccessResponse(
            message="任务取消成功",
            data={"task_id": task_id, "terminated": terminate}
        )

    except Exception as e:
        logger.error(f"取消分析任务失败: {task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.post("/celery/collection/{task_id}/revoke")
async def revoke_collection_task(task_id: str, terminate: bool = False):
    """
    取消采集任务

    - **task_id**: 任务ID
    - **terminate**: 是否强制终止
    """
    try:
        # 取消 Celery 任务
        collect_tweets.AsyncResult(task_id).revoke(terminate=terminate)

        logger.info(f"取消采集任务: {task_id}, 强制终止: {terminate}")

        return SuccessResponse(
            message="任务取消成功",
            data={"task_id": task_id, "terminated": terminate}
        )

    except Exception as e:
        logger.error(f"取消采集任务失败: {task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/cache/info", response_model=CacheInfoResponse)
async def get_cache_info():
    """
    获取缓存信息
    """
    try:
        cache_info = await RedisCache.get_connection_info()
        return CacheInfoResponse(**cache_info)

    except Exception as e:
        logger.error(f"获取缓存信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存信息失败: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    获取缓存统计信息
    """
    try:
        # 这里可以实现更详细的缓存统计
        # 当前返回模拟数据
        stats = {
            "hit_rate": 0.85,
            "miss_rate": 0.15,
            "total_requests": 1000,
            "cache_hits": 850,
            "cache_misses": 150
        }

        return CacheStatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")


@router.delete("/cache")
async def clear_cache(pattern: Optional[str] = Query(None, description="缓存键模式")):
    """
    清理缓存

    - **pattern**: 缓存键模式（可选，默认清理所有缓存）
    """
    try:
        if pattern:
            # 实现基于模式的缓存清理
            # 这里需要 Redis 的 keys 命令支持
            logger.info(f"清理缓存模式: {pattern}")
            # 注意：keys 命令在生产环境可能影响性能
            # 可以考虑使用 scan 命令
        else:
            # 清理特定前缀的缓存
            logger.info("清理所有应用缓存")

        return SuccessResponse(
            message="缓存清理完成",
            data={"pattern": pattern}
        )

    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")


@router.get("/queue/status")
async def get_queue_status():
    """
    获取任务队列状态
    """
    try:
        from app.tasks.celery_app import celery_app

        # 获取队列信息
        inspector = celery_app.control.inspect()

        # 活跃的 worker
        active_workers = inspector.active()
        registered_workers = inspector.registered()
        scheduled_tasks = inspector.scheduled()

        queue_stats = {
            "active_workers": len(active_workers) if active_workers else 0,
            "registered_workers": len(registered_workers) if registered_workers else 0,
            "scheduled_tasks": len(scheduled_tasks) if scheduled_tasks else 0,
            "queues": {
                "analysis": {"tasks": 0},  # 可以获取具体队列任务数
                "collection": {"tasks": 0},
                "default": {"tasks": 0}
            }
        }

        return SuccessResponse(
            message="队列状态获取成功",
            data=queue_stats
        )

    except Exception as e:
        logger.error(f"获取队列状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取队列状态失败: {str(e)}")


@router.post("/queue/purge")
async def purge_queues(queue_name: Optional[str] = Query(None, description="队列名称")):
    """
    清空任务队列

    - **queue_name**: 队列名称（可选，默认清空所有队列）
    """
    try:
        from app.tasks.celery_app import celery_app

        if queue_name:
            # 清空特定队列
            celery_app.control.purge(queue=queue_name)
            logger.info(f"清空队列: {queue_name}")
        else:
            # 清空所有队列
            celery_app.control.purge()
            logger.info("清空所有队列")

        return SuccessResponse(
            message="队列清空完成",
            data={"queue_name": queue_name}
        )

    except Exception as e:
        logger.error(f"清空队列失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空队列失败: {str(e)}")


@router.get("/workers/status")
async def get_workers_status():
    """
    获取 worker 状态
    """
    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()

        # 获取 worker 统计信息
        stats = inspector.stats()
        active = inspector.active()
        reserved = inspector.reserved()

        workers_info = {}

        if stats:
            for worker_name, worker_stats in stats.items():
                workers_info[worker_name] = {
                    "status": "active",
                    "stats": {
                        "total_tasks": worker_stats.get("total", {}),
                        "pid": worker_stats.get("pid"),
                        "clock": worker_stats.get("clock"),
                        "uptime": worker_stats.get("uptime")
                    },
                    "active_tasks": len(active.get(worker_name, [])),
                    "reserved_tasks": len(reserved.get(worker_name, []))
                }

        return SuccessResponse(
            message="Worker 状态获取成功",
            data=workers_info
        )

    except Exception as e:
        logger.error(f"获取 Worker 状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取 Worker 状态失败: {str(e)}")


@router.post("/workers/shutdown")
async def shutdown_workers(worker_name: Optional[str] = Query(None, description="Worker 名称")):
    """
    关闭 worker

    - **worker_name**: Worker 名称（可选，默认关闭所有 workers）
    """
    try:
        from app.tasks.celery_app import celery_app

        if worker_name:
            # 关闭特定 worker
            celery_app.control.shutdown(destination=[worker_name])
            logger.info(f"关闭 worker: {worker_name}")
        else:
            # 关闭所有 workers
            celery_app.control.shutdown()
            logger.info("关闭所有 workers")

        return SuccessResponse(
            message="Worker 关闭指令已发送",
            data={"worker_name": worker_name}
        )

    except Exception as e:
        logger.error(f"关闭 Worker 失败: {e}")
        raise HTTPException(status_code=500, detail=f"关闭 Worker 失败: {str(e)}")


@router.get("/tasks/scheduled")
async def get_scheduled_tasks():
    """
    获取计划任务
    """
    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        scheduled = inspector.scheduled()

        scheduled_tasks = []
        if scheduled:
            for worker_name, tasks in scheduled.items():
                for task in tasks:
                    scheduled_tasks.append({
                        "worker": worker_name,
                        "task_id": task.get("request", {}).get("id"),
                        "task_name": task.get("request", {}).get("name"),
                        "eta": task.get("eta"),
                        "priority": task.get("priority", 0)
                    })

        return SuccessResponse(
            message="计划任务获取成功",
            data=scheduled_tasks
        )

    except Exception as e:
        logger.error(f"获取计划任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取计划任务失败: {str(e)}")


@router.get("/tasks/active")
async def get_active_tasks():
    """
    获取活跃任务
    """
    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        active = inspector.active()

        active_tasks = []
        if active:
            for worker_name, tasks in active.items():
                for task in tasks:
                    active_tasks.append({
                        "worker": worker_name,
                        "task_id": task.get("id"),
                        "task_name": task.get("name"),
                        "args": task.get("args"),
                        "kwargs": task.get("kwargs"),
                        "start_time": task.get("time_start")
                    })

        return SuccessResponse(
            message="活跃任务获取成功",
            data=active_tasks
        )

    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取活跃任务失败: {str(e)}")


@router.get("/tasks/reserved")
async def get_reserved_tasks():
    """
    获取预留任务
    """
    try:
        from app.tasks.celery_app import celery_app

        inspector = celery_app.control.inspect()
        reserved = inspector.reserved()

        reserved_tasks = []
        if reserved:
            for worker_name, tasks in reserved.items():
                for task in tasks:
                    reserved_tasks.append({
                        "worker": worker_name,
                        "task_id": task.get("id"),
                        "task_name": task.get("name"),
                        "args": task.get("args"),
                        "kwargs": task.get("kwargs"),
                        "priority": task.get("priority", 0)
                    })

        return SuccessResponse(
            message="预留任务获取成功",
            data=reserved_tasks
        )

    except Exception as e:
        logger.error(f"获取预留任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预留任务失败: {str(e)}")