# ============================================
# Twitter 数据采集统一接口
# ============================================
# 这是 x_crawl 层暴露给 agent 层的唯一入口
# 职责：封装所有 Twitter API 调用逻辑，提供类型安全的数据获取接口

from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field

from .models import TweetDiscussionCollection
from .tweet_fetcher import collect_tweet_discussions
from .twitter_client import create_client

# ============================================
# 数据模型定义
# ============================================


class CollectionRequest(BaseModel):
    """数据采集请求"""

    query: str = Field(description="Twitter 搜索查询字符串")
    max_seed_tweets: int = Field(default=500, description="最多采集多少条种子推文")
    max_replies_per_tweet: int = Field(
        default=10, description="每条推文最多采集多少条回复"
    )
    include_thread: bool = Field(default=True, description="是否包含推文串")
    max_concurrent: int = Field(default=10, description="最大并发数")


class CollectionResponse(BaseModel):
    """数据采集响应"""

    success: bool = Field(description="是否成功")
    tweet_count: int = Field(description="采集到的推文总数")
    seed_count: int = Field(description="种子推文数量")
    reply_count: int = Field(description="回复数量")
    thread_count: int = Field(description="推文串数量")
    success_rate: float = Field(description="成功率")
    collection: TweetDiscussionCollection = Field(description="完整的推文集合对象")
    error_message: Optional[str] = Field(
        default=None, description="错误信息（如果失败）"
    )
    collected_at: datetime = Field(
        default_factory=datetime.utcnow, description="采集时间"
    )


# ============================================
# 统一数据采集接口
# ============================================


async def collect_twitter_data(request: CollectionRequest) -> CollectionResponse:
    """
    统一的 Twitter 数据采集接口

    这是 x_crawl 层提供给 agent 层的唯一公开函数。
    所有 Twitter API 调用都在这里完成，agent 层无需关心底层实现。

    Args:
        request: 采集请求参数

    Returns:
        CollectionResponse: 采集结果（包含完整的 TweetDiscussionCollection 对象）

    Examples:
        >>> request = CollectionRequest(
        ...     query="China lang:ar since:2020-01-01",
        ...     max_seed_tweets=500
        ... )
        >>> response = await collect_twitter_data(request)
        >>> print(f"采集到 {response.tweet_count} 条推文")
    """
    try:
        # 创建客户端并执行采集
        async with create_client() as client:
            collection = await collect_tweet_discussions(
                query=request.query,
                client=client,
                max_seed_tweets=request.max_seed_tweets,
                max_replies_per_tweet=request.max_replies_per_tweet,
                include_thread=request.include_thread,
                max_concurrent=request.max_concurrent,
            )

        logger.debug(
            "collect_twitter_data: items=%d, total_tweets=%d, replies=%d, threads=%d",
            len(collection.items),
            len(collection.all_tweets),
            collection.total_replies,
            collection.total_threads,
        )

        # 构造响应
        return CollectionResponse(
            success=True,
            tweet_count=len(collection.all_tweets),
            seed_count=len(collection.items),
            reply_count=collection.total_replies,
            thread_count=collection.total_threads,
            success_rate=collection.success_rate,
            collection=collection,
            collected_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.exception("collect_twitter_data 调用失败: %s", e)
        # 采集失败，返回错误响应
        # 创建默认的 metadata（避免 None 导致的 Pydantic 验证错误）
        from .models import CollectionMetadata

        default_metadata = CollectionMetadata(
            query=request.query,
            query_type="Latest",
            seed_tweet_count=0,
            total_reply_count=0,
            total_thread_count=0,
            max_seed_tweets=request.max_seed_tweets,
            max_replies_per_tweet=request.max_replies_per_tweet,
            max_concurrent=request.max_concurrent,
        )

        return CollectionResponse(
            success=False,
            tweet_count=0,
            seed_count=0,
            reply_count=0,
            thread_count=0,
            success_rate=0.0,
            collection=TweetDiscussionCollection(
                items=[],
                metadata=default_metadata,
            ),
            error_message=str(e),
            collected_at=datetime.utcnow(),
        )


# ============================================
# 辅助函数
# ============================================


def validate_query(query: str) -> tuple[bool, Optional[str]]:
    """
    验证 Twitter 查询字符串的合法性

    Args:
        query: 查询字符串

    Returns:
        (is_valid, error_message): 是否合法及错误信息
    """
    if not query or not query.strip():
        return False, "查询字符串不能为空"

    if len(query) > 500:
        return False, "查询字符串过长（最多 500 字符）"

    # 检查括号匹配
    if query.count("(") != query.count(")"):
        return False, "括号不匹配"

    return True, None
