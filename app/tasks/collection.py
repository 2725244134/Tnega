"""
============================================
数据采集任务
============================================
Twitter 数据采集和预处理任务
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import Task
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import RedisCache, CacheKey
from app.models.analysis import TweetData, AnalysisTask, TaskStatus
from app.tasks.celery_app import celery_app
from src.x_crawl.twitter_client import create_client
from src.x_crawl.tweet_fetcher import collect_tweet_discussions
from src.x_crawl.models import Tweet, User, TweetWithContext, TweetDiscussionCollection


class CollectionTask(Task):
    """采集任务基类"""

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

                    self.logger.info(f"更新采集任务进度: {task_id} - {status} - {progress}%")

            except Exception as e:
                self.logger.error(f"更新任务进度失败: {e}")
                await session.rollback()


@celery_app.task(bind=True, base=CollectionTask, name="app.tasks.collection.collect_tweets")
def collect_tweets(self, task_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    采集推文任务

    Args:
        task_id: 任务ID
        parameters: 采集参数

    Returns:
        采集结果
    """
    logger.info(f"开始采集推文任务: {task_id}")

    async def run_collection():
        try:
            # 更新任务状态
            await self.update_task_progress(
                task_id=task_id,
                progress=10,
                status=TaskStatus.RUNNING,
                current_step="初始化采集器"
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

                # 构建搜索查询
                search_query = build_search_query(task.description, task.search_query)

                # 检查缓存
                cached_results = await check_collection_cache(search_query)
                if cached_results:
                    logger.info(f"使用缓存的采集结果: {len(cached_results)} 条推文")
                    await save_cached_tweets(session, cached_results, task_id)

                    await self.update_task_progress(
                        task_id=task_id,
                        progress=100,
                        status=TaskStatus.COMPLETED,
                        current_step="采集完成（使用缓存）"
                    )

                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "tweets_collected": len(cached_results),
                        "used_cache": True
                    }

                # 开始采集
                await self.update_task_progress(
                    task_id=task_id,
                    progress=20,
                    status=TaskStatus.RUNNING,
                    current_step="开始采集推文"
                )

                # 创建 Twitter 客户端
                async with create_client() as client:
                    # 采集推文讨论
                    collection_result = await collect_tweet_discussions(
                        query=search_query,
                        client=client,
                        max_seed_tweets=task.target_count,
                        max_replies_per_tweet=50,
                    )

                    await self.update_task_progress(
                        task_id=task_id,
                        progress=60,
                        status=TaskStatus.RUNNING,
                        current_step="保存采集数据"
                    )

                    # 保存采集结果到数据库
                    saved_count = await save_collection_results(
                        session, collection_result, task_id
                    )

                    # 缓存采集结果
                    await cache_collection_results(search_query, collection_result)

                    # 更新任务状态
                    await self.update_task_progress(
                        task_id=task_id,
                        progress=100,
                        status=TaskStatus.COMPLETED,
                        current_step="采集完成"
                    )

                    logger.info(f"推文采集任务完成: {task_id}, 采集了 {saved_count} 条推文")

                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "tweets_collected": saved_count,
                        "used_cache": False
                    }

        except Exception as e:
            logger.error(f"推文采集任务失败: {task_id}, 错误: {e}")

            # 更新任务状态为失败
            await self.update_task_progress(
                task_id=task_id,
                progress=100,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )

            raise

    # 运行异步函数
    return asyncio.run(run_collection())


def build_search_query(description: str, search_query: Optional[str] = None) -> str:
    """
    构建搜索查询

    Args:
        description: 任务描述
        search_query: 用户提供的搜索查询

    Returns:
        搜索查询字符串
    """
    if search_query:
        return search_query

    # 基于描述生成搜索查询（这里可以集成 AI 优化）
    # 简单的关键词提取
    keywords = extract_keywords(description)

    # 构建查询
    query_parts = []
    if keywords:
        query_parts.append(" OR ".join(keywords))

    # 添加语言过滤（阿拉伯语）
    query_parts.append("lang:ar")

    # 添加时间范围（最近一年）
    from datetime import datetime, timedelta
    since_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    query_parts.append(f"since:{since_date}")

    return " ".join(query_parts)


def extract_keywords(text: str) -> List[str]:
    """
    提取关键词

    Args:
        text: 文本

    Returns:
        关键词列表
    """
    # 简单的关键词提取（可以集成更复杂的 NLP）
    # 这里只是示例，实际应该使用专业的关键词提取算法

    keywords = []

    # 中文关键词
    chinese_keywords = ["中国", "阅兵", "93阅兵", "军事", "国防"]
    for keyword in chinese_keywords:
        if keyword in text:
            keywords.append(keyword)

    # 阿拉伯语关键词（简化的转写）
    arabic_keywords = ["الصين", "العربية", "العسكرية", "الدفاع"]
    # 这里应该使用更智能的关键词匹配

    return keywords[:5]  # 限制关键词数量


async def check_collection_cache(search_query: str) -> Optional[List[Dict[str, Any]]]:
    """
    检查采集缓存

    Args:
        search_query: 搜索查询

    Returns:
        缓存的推文数据，如果没有缓存返回 None
    """
    import hashlib
    query_hash = hashlib.md5(search_query.encode()).hexdigest()
    cache_key = CacheKey.search_results(query_hash)

    cached_data = await RedisCache.get_json(cache_key)
    if cached_data:
        # 检查缓存是否过期（24小时）
        cached_time = datetime.fromisoformat(cached_data.get("cached_at", ""))
        if datetime.utcnow() - cached_time < timedelta(hours=24):
            return cached_data.get("tweets", [])

    return None


async def cache_collection_results(search_query: str, collection_result: TweetDiscussionCollection):
    """
    缓存采集结果

    Args:
        search_query: 搜索查询
        collection_result: 采集结果
    """
    import hashlib
    query_hash = hashlib.md5(search_query.encode()).hexdigest()
    cache_key = CacheKey.search_results(query_hash)

    # 转换数据格式
    tweets_data = []
    for item in collection_result.items:
        tweets_data.append({
            "tweet_id": item.tweet.id,
            "text": item.tweet.text,
            "author_id": item.author.id,
            "author_name": item.author.name,
            "created_at": item.tweet.created_at.isoformat(),
            "engagement": item.total_engagement
        })

    cache_data = {
        "tweets": tweets_data,
        "cached_at": datetime.utcnow().isoformat(),
        "total_count": len(tweets_data)
    }

    # 缓存24小时
    await RedisCache.set_json(cache_key, cache_data, ttl=86400)
    logger.info(f"缓存采集结果: {len(tweets_data)} 条推文")


async def save_collection_results(
    session: AsyncSession,
    collection_result: TweetDiscussionCollection,
    task_id: str
) -> int:
    """
    保存采集结果到数据库

    Args:
        session: 数据库会话
        collection_result: 采集结果
        task_id: 任务ID

    Returns:
        保存的推文数量
    """
    saved_count = 0

    for item in collection_result.items:
        try:
            # 保存种子推文
            await save_tweet_data(session, item.tweet, item.author, task_id)
            saved_count += 1

            # 保存回复
            for reply in item.replies:
                await save_tweet_data(session, reply, item.author, task_id)
                saved_count += 1

            # 保存 thread 上下文
            for thread_tweet in item.thread_context:
                await save_tweet_data(session, thread_tweet, item.author, task_id)
                saved_count += 1

        except Exception as e:
            logger.error(f"保存推文数据失败: {e}")
            continue

    await session.commit()
    return saved_count


async def save_tweet_data(
    session: AsyncSession,
    tweet: Tweet,
    author: User,
    task_id: str
):
    """
    保存单条推文数据

    Args:
        session: 数据库会话
        tweet: 推文数据
        author: 作者数据
        task_id: 任务ID
    """
    # 检查是否已存在
    existing = await session.execute(
        "SELECT tweet_id FROM tweet_data WHERE tweet_id = :tweet_id",
        {"tweet_id": tweet.id}
    )

    if existing.first():
        logger.debug(f"推文已存在，跳过: {tweet.id}")
        return

    # 插入新推文
    await session.execute(
        """
        INSERT INTO tweet_data (
            tweet_id, text, author_id, author_name, author_username,
            lang, created_at, like_count, retweet_count, reply_count, view_count,
            conversation_id, is_reply, in_reply_to_id, raw_data, is_analyzed,
            created_at, updated_at
        ) VALUES (
            :tweet_id, :text, :author_id, :author_name, :author_username,
            :lang, :created_at, :like_count, :retweet_count, :reply_count, :view_count,
            :conversation_id, :is_reply, :in_reply_to_id, :raw_data, :is_analyzed,
            :now, :now
        )
        """,
        {
            "tweet_id": tweet.id,
            "text": tweet.text,
            "author_id": author.id,
            "author_name": author.name,
            "author_username": author.username,
            "lang": tweet.lang,
            "created_at": tweet.created_at,
            "like_count": tweet.like_count,
            "retweet_count": tweet.retweet_count,
            "reply_count": tweet.reply_count,
            "view_count": tweet.view_count,
            "conversation_id": tweet.conversation_id,
            "is_reply": tweet.is_reply,
            "in_reply_to_id": tweet.in_reply_to_id,
            "raw_data": tweet.dict() if hasattr(tweet, 'dict') else {},
            "is_analyzed": False,
            "now": datetime.utcnow()
        }
    )

    logger.debug(f"保存推文数据: {tweet.id}")


async def save_cached_tweets(session: AsyncSession, cached_tweets: List[Dict[str, Any]], task_id: str):
    """
    保存缓存的推文数据

    Args:
        session: 数据库会话
        cached_tweets: 缓存的推文数据
        task_id: 任务ID
    """
    for tweet_data in cached_tweets:
        try:
            # 创建模拟的 Tweet 和 User 对象
            tweet = Tweet(
                id=tweet_data["tweet_id"],
                text=tweet_data["text"],
                created_at=datetime.fromisoformat(tweet_data["created_at"]),
                lang="ar",  # 默认阿拉伯语
                like_count=0,
                retweet_count=0,
                reply_count=0,
                view_count=0,
                conversation_id=None,
                is_reply=False,
                in_reply_to_id=None,
            )

            author = User(
                id=tweet_data["author_id"],
                name=tweet_data["author_name"],
                username=tweet_data.get("author_username", "unknown"),
                location=None,
                verified=False,
                followers_count=0,
                created_at=None,
            )

            await save_tweet_data(session, tweet, author, task_id)

        except Exception as e:
            logger.error(f"保存缓存推文失败: {e}")
            continue

    await session.commit()


@celery_app.task(name="app.tasks.collection.cleanup_old_tweets")
def cleanup_old_tweets():
    """
    清理旧的推文数据

    定期任务，清理超过保留期限的推文数据
    """
    logger.info("开始清理旧的推文数据")

    async def cleanup():
        async with AsyncSessionLocal() as session:
            try:
                # 删除超过 90 天的推文数据
                cutoff_date = datetime.utcnow() - timedelta(days=90)

                result = await session.execute(
                    """
                    DELETE FROM tweet_data
                    WHERE created_at < :cutoff_date
                    AND is_analyzed = true
                    """,
                    {"cutoff_date": cutoff_date}
                )

                deleted_count = result.rowcount
                await session.commit()

                logger.info(f"清理旧的推文数据完成: 删除了 {deleted_count} 条推文")

            except Exception as e:
                logger.error(f"清理旧的推文数据失败: {e}")
                await session.rollback()

    asyncio.run(cleanup())


@celery_app.task(name="app.tasks.collection.validate_tweet_data")
def validate_tweet_data():
    """
    验证推文数据完整性

    定期任务，检查和修复推文数据
    """
    logger.info("开始验证推文数据完整性")

    async def validate():
        async with AsyncSessionLocal() as session:
            try:
                # 检查缺失的字段
                result = await session.execute(
                    """
                    SELECT tweet_id, text, author_id
                    FROM tweet_data
                    WHERE text IS NULL OR author_id IS NULL
                    LIMIT 100
                    """
                )

                invalid_tweets = result.fetchall()

                if invalid_tweets:
                    logger.warning(f"发现 {len(invalid_tweets)} 条无效推文数据")
                    # 可以在这里添加修复逻辑

                logger.info("推文数据验证完成")

            except Exception as e:
                logger.error(f"推文数据验证失败: {e}")

    asyncio.run(validate())