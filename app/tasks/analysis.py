"""
============================================
分析任务
============================================
推文分析和结果生成任务
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List

from celery import Task
from loguru import logger
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.analysis import AnalysisTask, AnalysisResult, TaskStatus, TweetData
from app.models.schemas import TaskStatus as TaskStatusSchema
from app.tasks.celery_app import celery_app, get_celery_app
from app.tasks.twitter_client import TwitterClient
from app.core.redis import RedisCache, CacheKey


class AnalysisTask(Task):
    """分析任务基类"""

    def __init__(self):
        super().__init__()
        self.task_id = None
        self.logger = logger

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        status: TaskStatus,
        current_step: str = None,
        error_message: str = None
    ):
        """更新任务进度"""
        async with AsyncSessionLocal() as session:
            try:
                # 获取任务
                result = await session.execute(
                    "SELECT * FROM analysis_tasks WHERE id = :task_id",
                    {"task_id": task_id}
                )
                task = result.first()

                if task:
                    # 更新任务状态
                    update_data = {
                        "progress": progress,
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }

                    if status == TaskStatus.RUNNING and not task.started_at:
                        update_data["started_at"] = datetime.utcnow()
                    elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        update_data["completed_at"] = datetime.utcnow()

                    if current_step:
                        update_data["current_step"] = current_step

                    if error_message:
                        update_data["error_message"] = error_message

                    # 执行更新
                    await session.execute(
                        """
                        UPDATE analysis_tasks
                        SET progress = :progress,
                            status = :status,
                            updated_at = :updated_at,
                            started_at = COALESCE(:started_at, started_at),
                            completed_at = COALESCE(:completed_at, completed_at),
                            current_step = COALESCE(:current_step, current_step),
                            error_message = COALESCE(:error_message, error_message)
                        WHERE id = :task_id
                        """,
                        {**update_data, "task_id": task_id}
                    )

                    await session.commit()

                    # 更新 Redis 缓存
                    await RedisCache.set_json(
                        CacheKey.task_status(task_id),
                        {
                            "status": status,
                            "progress": progress,
                            "current_step": current_step,
                            "updated_at": datetime.utcnow().isoformat()
                        },
                        ttl=300  # 缓存5分钟
                    )

                    self.logger.info(f"更新任务进度: {task_id} - {status} - {progress}%")

            except Exception as e:
                self.logger.error(f"更新任务进度失败: {e}")
                await session.rollback()


@celery_app.task(bind=True, base=AnalysisTask, name="app.tasks.analysis.analyze_tweets")
def analyze_tweets(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析推文任务

    Args:
        task_id: 任务ID
        parameters: 分析参数

    Returns:
        分析结果
    """
    logger.info(f"开始分析推文任务: {task_id}")

    async def run_analysis():
        try:
            # 更新任务状态
            await self.update_task_progress(
                task_id=task_id,
                progress=10,
                status=TaskStatus.RUNNING,
                current_step="初始化分析器"
            )

            # 获取任务信息
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    "SELECT * FROM analysis_tasks WHERE id = :task_id",
                    {"task_id": task_id}
                )
                task = result.first()

                if not task:
                    raise ValueError(f"任务不存在: {task_id}")

                # 获取推文数据
                await self.update_task_progress(
                    task_id=task_id,
                    progress=20,
                    status=TaskStatus.RUNNING,
                    current_step="获取推文数据"
                )

                tweets = await get_tweets_for_analysis(session, task.parameters)

                if not tweets:
                    raise ValueError("没有找到推文数据")

                # 缓存推文数据
                await self.update_task_progress(
                    task_id=task_id,
                    progress=30,
                    status=TaskStatus.RUNNING,
                    current_step="缓存数据"
                )

                # 执行情感分析
                await self.update_task_progress(
                    task_id=task_id,
                    progress=50,
                    status=TaskStatus.RUNNING,
                    current_step="情感分析"
                )

                sentiment_result = await perform_sentiment_analysis(tweets)

                # 生成趋势分析
                await self.update_task_progress(
                    task_id=task_id,
                    progress=70,
                    status=TaskStatus.RUNNING,
                    current_step="趋势分析"
                )

                trend_result = await perform_trend_analysis(tweets)

                # 生成摘要分析
                await self.update_task_progress(
                    task_id=task_id,
                    progress=90,
                    status=TaskStatus.RUNNING,
                    current_step="生成摘要"
                )

                summary_result = await perform_summary_analysis(tweets, task.description)

                # 保存分析结果
                await self.update_task_progress(
                    task_id=task_id,
                    progress=95,
                    status=TaskStatus.RUNNING,
                    current_step="保存结果"
                )

                await save_analysis_results(session, task_id, [
                    sentiment_result,
                    trend_result,
                    summary_result
                ])

                # 完成任务
                await self.update_task_progress(
                    task_id=task_id,
                    progress=100,
                    status=TaskStatus.COMPLETED,
                    current_step="分析完成"
                )

                logger.info(f"推文分析任务完成: {task_id}")

                return {
                    "task_id": task_id,
                    "status": "completed",
                    "results_count": 3,
                    "tweets_analyzed": len(tweets)
                }

        except Exception as e:
            logger.error(f"推文分析任务失败: {task_id}, 错误: {e}")

            # 更新任务状态为失败
            await self.update_task_progress(
                task_id=task_id,
                progress=100,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )

            raise

    # 运行异步函数
    return asyncio.run(run_analysis())


async def get_tweets_for_analysis(session: AsyncSession, parameters: Dict[str, Any]) -> List[TweetData]:
    """
    获取用于分析的推文数据

    Args:
        session: 数据库会话
        parameters: 分析参数

    Returns:
        推文数据列表
    """
    # 这里实现获取推文数据的逻辑
    # 可以根据参数中的查询条件、时间范围等筛选推文

    query = """
    SELECT * FROM tweet_data
    WHERE is_analyzed = false
    ORDER BY created_at DESC
    LIMIT 1000
    """

    result = await session.execute(query)
    tweets = result.fetchall()

    return tweets


async def perform_sentiment_analysis(tweets: List[TweetData]) -> Dict[str, Any]:
    """
    执行情感分析

    Args:
        tweets: 推文列表

    Returns:
        情感分析结果
    """
    logger.info(f"开始情感分析: {len(tweets)} 条推文")

    # 这里集成 AI 模型进行情感分析
    # 使用现有的 pydantic-ai 集成

    # 模拟情感分析结果
    positive_count = len([t for t in tweets if "好" in t.text or "赞" in t.text])
    negative_count = len([t for t in tweets if "坏" in t.text or "差" in t.text])
    neutral_count = len(tweets) - positive_count - negative_count

    return {
        "result_type": "sentiment",
        "title": "情感分析结果",
        "description": f"分析了 {len(tweets)} 条推文的情感倾向",
        "data": {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "positive_rate": positive_count / len(tweets) if tweets else 0,
            "negative_rate": negative_count / len(tweets) if tweets else 0,
            "neutral_rate": neutral_count / len(tweets) if tweets else 0,
        },
        "quality_score": 85.0
    }


async def perform_trend_analysis(tweets: List[TweetData]) -> Dict[str, Any]:
    """
    执行趋势分析

    Args:
        tweets: 推文列表

    Returns:
        趋势分析结果
    """
    logger.info(f"开始趋势分析: {len(tweets)} 条推文")

    # 按时间分组统计
    from collections import defaultdict
    daily_counts = defaultdict(int)

    for tweet in tweets:
        date = tweet.created_at.date().isoformat()
        daily_counts[date] += 1

    return {
        "result_type": "trend",
        "title": "趋势分析结果",
        "description": f"分析了 {len(tweets)} 条推文的时间趋势",
        "data": {
            "daily_counts": dict(daily_counts),
            "total_tweets": len(tweets),
            "date_range": {
                "start": min(daily_counts.keys()) if daily_counts else None,
                "end": max(daily_counts.keys()) if daily_counts else None,
            },
            "peak_day": max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None,
        },
        "quality_score": 90.0
    }


async def perform_summary_analysis(tweets: List[TweetData], query_description: str) -> Dict[str, Any]:
    """
    执行摘要分析

    Args:
        tweets: 推文列表
        query_description: 查询描述

    Returns:
        摘要分析结果
    """
    logger.info(f"开始摘要分析: {len(tweets)} 条推文")

    # 使用 AI 生成摘要
    # 这里可以集成更复杂的 AI 分析逻辑

    # 模拟 AI 生成的摘要
    summary = f"基于 {len(tweets)} 条推文的分析显示，用户对于'{query_description}'话题的讨论主要集中在以下几个方面："

    return {
        "result_type": "summary",
        "title": "分析摘要",
        "description": "基于 AI 的智能分析摘要",
        "data": {
            "summary": summary,
            "key_points": [
                "用户普遍关注该话题的最新进展",
                "讨论热度呈上升趋势",
                "正面评价占主导地位"
            ],
            "recommendations": [
                "建议继续关注该话题的发展",
                "可以适时发布相关内容",
                "注意用户反馈和情感变化"
            ]
        },
        "quality_score": 95.0
    }


async def save_analysis_results(session: AsyncSession, task_id: str, results: List[Dict[str, Any]]):
    """
    保存分析结果

    Args:
        session: 数据库会话
        task_id: 任务ID
        results: 分析结果列表
    """
    for result in results:
        result_id = str(uuid.uuid4())

        await session.execute(
            """
            INSERT INTO analysis_results (
                id, task_id, result_type, title, description, data, quality_score, created_at, updated_at
            ) VALUES (
                :id, :task_id, :result_type, :title, :description, :data, :quality_score, :created_at, :updated_at
            )
            """,
            {
                "id": result_id,
                "task_id": task_id,
                "result_type": result["result_type"],
                "title": result["title"],
                "description": result.get("description"),
                "data": result["data"],
                "quality_score": result.get("quality_score"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )

    await session.commit()
    logger.info(f"保存分析结果: {len(results)} 个结果, 任务ID: {task_id}")


@celery_app.task(name="app.tasks.analysis.cleanup_old_results")
def cleanup_old_results():
    """
    清理旧的分析结果

    定期任务，清理超过保留期限的分析结果
    """
    logger.info("开始清理旧的分析结果")

    # 这里实现清理逻辑
    # 可以删除超过一定时间的已完成任务和结果

    logger.info("完成清理旧的分析结果")


@celery_app.task(name="app.tasks.analysis.update_tweet_analysis_status")
def update_tweet_analysis_status(tweet_ids: List[str], is_analyzed: bool = True):
    """
    更新推文分析状态

    Args:
        tweet_ids: 推文ID列表
        is_analyzed: 是否已分析
    """
    logger.info(f"更新推文分析状态: {len(tweet_ids)} 条推文")

    async def update_status():
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(
                    """
                    UPDATE tweet_data
                    SET is_analyzed = :is_analyzed, updated_at = :updated_at
                    WHERE tweet_id = ANY(:tweet_ids)
                    """,
                    {
                        "tweet_ids": tweet_ids,
                        "is_analyzed": is_analyzed,
                        "updated_at": datetime.utcnow()
                    }
                )
                await session.commit()
                logger.info(f"更新推文分析状态完成: {len(tweet_ids)} 条推文")
            except Exception as e:
                logger.error(f"更新推文分析状态失败: {e}")
                await session.rollback()

    asyncio.run(update_status())