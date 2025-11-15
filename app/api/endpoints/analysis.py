"""
============================================
分析任务 API 端点
============================================
分析任务的创建、查询和管理接口
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.redis import RedisCache, CacheKey
from app.models.analysis import AnalysisTask, AnalysisResult, TaskStatus
from app.models.schemas import (
    CreateAnalysisTaskRequest,
    AnalysisTaskResponse,
    TaskListResponse,
    TaskStatusResponse,
    AnalysisSummaryResponse,
    AnalysisResultResponse,
    PaginationParams,
    PaginationResponse,
    SuccessResponse,
    ErrorResponse
)
from app.services.task_service import TaskService
from app.tasks.collection import collect_tweets
from app.tasks.analysis import analyze_tweets

router = APIRouter()


@router.post("/tasks", response_model=AnalysisTaskResponse)
async def create_analysis_task(
    task_request: CreateAnalysisTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = None
) -> AnalysisTaskResponse:
    """
    创建分析任务

    - **task_request**: 任务创建请求
    - **user_id**: 用户ID（可选，用于多用户系统）
    """
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建任务
        task_data = {
            "id": task_id,
            "user_id": user_id,
            "title": task_request.title,
            "description": task_request.description,
            "search_query": task_request.search_query,
            "target_count": task_request.target_count,
            "parameters": task_request.parameters or {},
            "status": TaskStatus.PENDING,
            "progress": 0,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": "NOW()",
            "updated_at": "NOW()"
        }

        # 保存任务到数据库
        await db.execute(
            """
            INSERT INTO analysis_tasks (
                id, user_id, title, description, search_query, target_count,
                parameters, status, progress, retry_count, max_retries,
                created_at, updated_at
            ) VALUES (
                :id, :user_id, :title, :description, :search_query, :target_count,
                :parameters, :status, :progress, :retry_count, :max_retries,
                NOW(), NOW()
            )
            """,
            task_data
        )

        await db.commit()

        logger.info(f"创建分析任务: {task_id}, 标题: {task_request.title}")

        # 在后台启动采集任务
        background_tasks.add_task(
            start_analysis_workflow,
            task_id,
            task_request.dict()
        )

        # 返回任务信息
        result = await db.execute(
            "SELECT * FROM analysis_tasks WHERE id = :task_id",
            {"task_id": task_id}
        )
        task = result.first()

        return AnalysisTaskResponse.from_orm(task)

    except Exception as e:
        logger.error(f"创建分析任务失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks", response_model=TaskListResponse)
async def get_analysis_tasks(
    pagination: PaginationParams = Depends(),
    status: Optional[TaskStatus] = Query(None, description="任务状态过滤"),
    user_id: Optional[str] = Query(None, description="用户ID过滤"),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """
    获取分析任务列表

    - **pagination**: 分页参数
    - **status**: 任务状态过滤
    - **user_id**: 用户ID过滤
    """
    try:
        # 构建查询条件
        where_conditions = []
        params = {}

        if status:
            where_conditions.append("status = :status")
            params["status"] = status

        if user_id:
            where_conditions.append("user_id = :user_id")
            params["user_id"] = user_id

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # 获取总数
        count_result = await db.execute(
            f"SELECT COUNT(*) FROM analysis_tasks WHERE {where_clause}",
            params
        )
        total = count_result.scalar()

        # 获取任务列表
        offset = (pagination.page - 1) * pagination.page_size
        params.update({
            "offset": offset,
            "limit": pagination.page_size
        })

        result = await db.execute(
            f"""
            SELECT * FROM analysis_tasks
            WHERE {where_clause}
            ORDER BY created_at DESC
            OFFSET :offset LIMIT :limit
            """,
            params
        )

        tasks = result.fetchall()

        # 构建分页响应
        pages = (total + pagination.page_size - 1) // pagination.page_size

        pagination_response = PaginationResponse(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
            pages=pages,
            has_prev=pagination.page > 1,
            has_next=pagination.page < pages
        )

        return TaskListResponse(
            items=[AnalysisTaskResponse.from_orm(task) for task in tasks],
            pagination=pagination_response
        )

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=AnalysisTaskResponse)
async def get_analysis_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> AnalysisTaskResponse:
    """
    获取单个分析任务详情

    - **task_id**: 任务ID
    """
    try:
        # 先检查缓存
        cached_status = await RedisCache.get_json(CacheKey.task_status(task_id))
        if cached_status:
            logger.info(f"从缓存获取任务状态: {task_id}")

        # 从数据库获取任务
        result = await db.execute(
            "SELECT * FROM analysis_tasks WHERE id = :task_id",
            {"task_id": task_id}
        )
        task = result.first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return AnalysisTaskResponse.from_orm(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> TaskStatusResponse:
    """
    获取任务状态

    - **task_id**: 任务ID
    """
    try:
        # 先检查缓存
        cached_status = await RedisCache.get_json(CacheKey.task_status(task_id))
        if cached_status:
            return TaskStatusResponse(
                id=task_id,
                status=cached_status["status"],
                progress=cached_status["progress"],
                current_step=cached_status.get("current_step"),
                estimated_remaining_time=None  # 可以添加预估时间逻辑
            )

        # 从数据库获取
        result = await db.execute(
            "SELECT status, progress FROM analysis_tasks WHERE id = :task_id",
            {"task_id": task_id}
        )
        task = result.first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return TaskStatusResponse(
            id=task_id,
            status=task.status,
            progress=task.progress,
            current_step=None,
            estimated_remaining_time=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/tasks/{task_id}/results", response_model=List[AnalysisResultResponse])
async def get_task_results(
    task_id: str,
    result_type: Optional[str] = Query(None, description="结果类型过滤"),
    db: AsyncSession = Depends(get_db)
) -> List[AnalysisResultResponse]:
    """
    获取任务分析结果

    - **task_id**: 任务ID
    - **result_type**: 结果类型过滤（可选）
    """
    try:
        # 构建查询条件
        where_conditions = ["task_id = :task_id"]
        params = {"task_id": task_id}

        if result_type:
            where_conditions.append("result_type = :result_type")
            params["result_type"] = result_type

        where_clause = " AND ".join(where_conditions)

        result = await db.execute(
            f"SELECT * FROM analysis_results WHERE {where_clause} ORDER BY created_at DESC",
            params
        )

        results = result.fetchall()

        return [AnalysisResultResponse.from_orm(result) for result in results]

    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.get("/tasks/{task_id}/summary", response_model=AnalysisSummaryResponse)
async def get_task_summary(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> AnalysisSummaryResponse:
    """
    获取任务分析汇总

    - **task_id**: 任务ID
    """
    try:
        # 获取任务信息
        task_result = await db.execute(
            "SELECT * FROM analysis_tasks WHERE id = :task_id",
            {"task_id": task_id}
        )
        task = task_result.first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取分析结果
        results_result = await db.execute(
            "SELECT * FROM analysis_results WHERE task_id = :task_id ORDER BY created_at DESC",
            {"task_id": task_id}
        )
        results = results_result.fetchall()

        # 计算统计信息
        statistics = await calculate_task_statistics(db, task_id)

        return AnalysisSummaryResponse(
            task=AnalysisTaskResponse.from_orm(task),
            results=[AnalysisResultResponse.from_orm(result) for result in results],
            statistics=statistics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务汇总失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务汇总失败: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse:
    """
    删除分析任务（软删除）

    - **task_id**: 任务ID
    """
    try:
        # 检查任务是否存在
        result = await db.execute(
            "SELECT id FROM analysis_tasks WHERE id = :task_id AND deleted_at IS NULL",
            {"task_id": task_id}
        )
        task = result.first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在或已删除")

        # 软删除任务
        await db.execute(
            "UPDATE analysis_tasks SET deleted_at = NOW() WHERE id = :task_id",
            {"task_id": task_id}
        )

        await db.commit()

        # 清除相关缓存
        await RedisCache.delete(CacheKey.task_status(task_id))
        await RedisCache.delete(CacheKey.analysis_result(task_id))

        logger.info(f"删除任务: {task_id}")

        return SuccessResponse(
            message="任务删除成功",
            data={"task_id": task_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/tasks/{task_id}/retry", response_model=SuccessResponse)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> SuccessResponse:
    """
    重试失败的任务

    - **task_id**: 任务ID
    """
    try:
        # 获取任务信息
        result = await db.execute(
            "SELECT * FROM analysis_tasks WHERE id = :task_id",
            {"task_id": task_id}
        )
        task = result.first()

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status != TaskStatus.FAILED:
            raise HTTPException(status_code=400, detail="任务状态不是失败状态，无法重试")

        if task.retry_count >= task.max_retries:
            raise HTTPException(status_code=400, detail="已达到最大重试次数")

        # 更新任务状态
        await db.execute(
            """
            UPDATE analysis_tasks
            SET status = :status,
                progress = 0,
                retry_count = retry_count + 1,
                error_message = NULL,
                updated_at = NOW()
            WHERE id = :task_id
            """,
            {
                "status": TaskStatus.PENDING,
                "task_id": task_id
            }
        )

        await db.commit()

        # 在后台重新启动任务
        background_tasks.add_task(
            start_analysis_workflow,
            task_id,
            {
                "title": task.title,
                "description": task.description,
                "search_query": task.search_query,
                "target_count": task.target_count,
                "parameters": task.parameters
            }
        )

        logger.info(f"重试任务: {task_id}")

        return SuccessResponse(
            message="任务重试已启动",
            data={"task_id": task_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


# ===========================
# 辅助函数
# ===========================

async def start_analysis_workflow(task_id: str, task_data: dict):
    """
    启动分析工作流

    1. 采集推文数据
    2. 分析推文数据
    """
    try:
        logger.info(f"启动分析工作流: {task_id}")

        # 第一步：采集推文
        collection_result = collect_tweets.delay(
            task_id=task_id,
            parameters=task_data
        )

        logger.info(f"采集任务已启动: {collection_result.id}")

        # 这里可以添加等待采集完成的逻辑
        # 或者直接返回，让前端轮询状态

    except Exception as e:
        logger.error(f"启动分析工作流失败: {task_id}, 错误: {e}")


async def calculate_task_statistics(db: AsyncSession, task_id: str) -> dict:
    """
    计算任务统计信息

    Args:
        db: 数据库会话
        task_id: 任务ID

    Returns:
        统计信息
    """
    try:
        # 获取推文数量统计
        tweets_result = await db.execute(
            """
            SELECT
                COUNT(*) as total_tweets,
                COUNT(DISTINCT author_id) as unique_authors,
                AVG(like_count) as avg_likes,
                AVG(retweet_count) as avg_retweets,
                AVG(reply_count) as avg_replies
            FROM tweet_data
            WHERE tweet_id IN (
                SELECT tweet_id FROM analysis_results
                WHERE task_id = :task_id
            )
            """,
            {"task_id": task_id}
        )
        tweet_stats = tweets_result.first()

        # 获取结果数量统计
        results_result = await db.execute(
            """
            SELECT
                result_type,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality
            FROM analysis_results
            WHERE task_id = :task_id
            GROUP BY result_type
            """,
            {"task_id": task_id}
        )
        result_stats = results_result.fetchall()

        return {
            "tweets": {
                "total": tweet_stats.total_tweets if tweet_stats else 0,
                "unique_authors": tweet_stats.unique_authors if tweet_stats else 0,
                "avg_likes": float(tweet_stats.avg_likes) if tweet_stats and tweet_stats.avg_likes else 0,
                "avg_retweets": float(tweet_stats.avg_retweets) if tweet_stats and tweet_stats.avg_retweets else 0,
                "avg_replies": float(tweet_stats.avg_replies) if tweet_stats and tweet_stats.avg_replies else 0,
            },
            "results": {
                stat.result_type: {
                    "count": stat.count,
                    "avg_quality": float(stat.avg_quality) if stat.avg_quality else 0
                }
                for stat in result_stats
            }
        }

    except Exception as e:
        logger.error(f"计算任务统计失败: {task_id}, 错误: {e}")
        return {"error": str(e)}