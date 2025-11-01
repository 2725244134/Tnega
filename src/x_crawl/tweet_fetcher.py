"""
============================================
推文讨论采集函数
============================================
核心业务逻辑：搜索推文 + 获取回复 + 获取 Thread
"""

import asyncio
from datetime import datetime, timezone
from typing import Literal

import httpx
from loguru import logger

from .models import (
    CollectionMetadata,
    Tweet,
    TweetDiscussionCollection,
    TweetWithContext,
    User,
)
from .parsers import parse_tweets_batch
from .twitter_client import fetch_paginated

# ============================================
# 底层 API 调用函数
# ============================================


async def _search_tweets(
    client: httpx.AsyncClient,
    query: str,
    query_type: Literal["Latest", "Top"],
    max_results: int,
) -> tuple[list[Tweet], dict[str, User]]:
    """
    搜索推文（内部函数）

    Args:
        client: httpx.AsyncClient 实例
        query: 完整的搜索查询（由 LLM 生成）
        query_type: Latest 或 Top
        max_results: 最大结果数

    Returns:
        tuple[list[Tweet], dict[str, User]]: (推文列表, 用户映射)
    """
    logger.info(f"开始搜索推文: query='{query}', type={query_type}")

    params = {"query": query, "queryType": query_type}

    all_tweets = []
    all_users = {}

    async for page in fetch_paginated(
        client, "/twitter/tweet/advanced_search", params, max_results
    ):
        tweets, users = parse_tweets_batch(page)
        all_tweets.extend(tweets)
        all_users.update(users)

    logger.info(f"搜索完成: 获取 {len(all_tweets)} 条推文，{len(all_users)} 个用户")
    return all_tweets, all_users


async def _get_replies(
    client: httpx.AsyncClient,
    tweet_id: str,
    max_results: int,
) -> list[Tweet]:
    """
    获取推文回复（内部函数）

    失败时返回空列表（不抛异常）

    Args:
        client: httpx.AsyncClient 实例
        tweet_id: 推文 ID
        max_results: 最大回复数

    Returns:
        list[Tweet]: 回复列表（失败返回空列表）
    """
    try:
        params = {"tweetId": tweet_id}
        replies = []

        async for page in fetch_paginated(
            client, "/twitter/tweet/replies", params, max_results
        ):
            tweets, _ = parse_tweets_batch(page)
            replies.extend(tweets)

        logger.debug(f"推文 {tweet_id}: 获取 {len(replies)} 条回复")
        return replies

    except Exception as e:
        logger.error(f"获取推文 {tweet_id} 的回复失败: {e}")
        return []


async def _get_thread_context(
    client: httpx.AsyncClient,
    tweet_id: str,
) -> list[Tweet]:
    """
    获取 Thread 上下文（内部函数）

    失败时返回空列表（不抛异常）

    Args:
        client: httpx.AsyncClient 实例
        tweet_id: 推文 ID

    Returns:
        list[Tweet]: Thread 推文列表（失败返回空列表）
    """
    try:
        params = {"tweetId": tweet_id}
        thread_tweets = []

        async for page in fetch_paginated(
            client, "/twitter/tweet/thread_context", params, max_results=None
        ):
            tweets, _ = parse_tweets_batch(page)
            thread_tweets.extend(tweets)

        logger.debug(f"推文 {tweet_id}: 获取 {len(thread_tweets)} 条 Thread 推文")
        return thread_tweets

    except Exception as e:
        logger.error(f"获取推文 {tweet_id} 的 Thread 失败: {e}")
        return []


# ============================================
# 核心函数：采集推文讨论
# ============================================


async def collect_tweet_discussions(
    query: str,
    client: httpx.AsyncClient,
    *,
    query_type: Literal["Latest", "Top"] = "Latest",
    max_seed_tweets: int = 500,
    max_replies_per_tweet: int = 200,
    include_thread: bool = True,
    max_concurrent: int = 10,
) -> TweetDiscussionCollection:
    """
    一站式采集推文讨论数据（高级组合操作）

    工作流程：
    1. 通过 advanced_search 搜索种子推文
    2. 并发获取每条种子推文的 replies
    3. 并发获取每条种子推文的 thread_context（如果 include_thread=True）
    4. 返回结构化的讨论数据

    Args:
        query: 搜索查询语句（完整的 query，由 LLM 生成）
               支持 Twitter 高级语法，例如：
               - "(China parade OR 93阅兵) lang:ar"
               - "九三阅兵 lang:ar since:2021-01-01 until:2025-01-15"
               完整语法参考：https://github.com/igorbrigadir/twitter-advanced-search

        client: httpx.AsyncClient 实例（使用 create_client() 创建）

        query_type: 查询类型
                   - "Latest": 最新推文（按时间倒序）
                   - "Top": 热门推文（按互动量排序）
                   默认 "Latest"

        max_seed_tweets: 最多获取多少条种子推文
                        默认 500
                        建议根据 API 配额调整

        max_replies_per_tweet: 每条推文最多获取多少回复
                              默认 200
                              热门推文可能有数千条回复，此参数限制获取量

        include_thread: 是否获取 thread context
                       默认 True
                       如果只关心回复，可设为 False 提升性能

        max_concurrent: 最大并发请求数
                       根据 API QPS 限制调整
                       twitterapi.io 充值后 QPS = 20，建议设为 10（留余量）
                       免费用户 QPS = 0.2，建议设为 1

    Returns:
        TweetDiscussionCollection: 包含所有推文及其讨论上下文

    Raises:
        ValueError: query 为空或无效
        httpx.HTTPStatusError: API 请求失败（4xx/5xx）
        asyncio.TimeoutError: 请求超时

    Example:
        >>> from src.x_crawl import create_client, collect_tweet_discussions
        >>>
        >>> # 搜索阿拉伯语推文及其讨论
        >>> async with create_client() as client:
        ...     result = await collect_tweet_discussions(
        ...         query="(China parade OR 93阅兵) lang:ar since:2021-01-01",
        ...         client=client,
        ...         max_seed_tweets=100,
        ...         max_replies_per_tweet=50
        ...     )
        >>>
        >>> print(f"采集了 {len(result.items)} 条推文的讨论")
        >>> print(f"总推文数: {result.total_tweets}")
        >>> print(f"总回复数: {result.total_replies}")
        >>> print(f"成功率: {result.success_rate:.1%}")
    """
    # ========== 参数验证 ==========
    if not query or not query.strip():
        raise ValueError("query 不能为空")

    logger.info("=" * 60)
    logger.info("开始采集推文讨论")
    logger.info(f"查询: {query}")
    logger.info(f"类型: {query_type}")
    logger.info(f"最大种子推文数: {max_seed_tweets}")
    logger.info(f"每条推文最大回复数: {max_replies_per_tweet}")
    logger.info(f"获取 Thread: {include_thread}")
    logger.info(f"并发数: {max_concurrent}")
    logger.info("=" * 60)

    start_time = datetime.now(timezone.utc)

    # ========== 步骤 1: 搜索种子推文 ==========
    seed_tweets, seed_users = await _search_tweets(
        client, query, query_type, max_seed_tweets
    )

    if not seed_tweets:
        logger.warning("未搜索到任何推文")
        return TweetDiscussionCollection(
            items=[],
            metadata=CollectionMetadata(
                query=query,
                query_type=query_type,
                collected_at=start_time,
                seed_tweet_count=0,
                max_seed_tweets=max_seed_tweets,
                max_replies_per_tweet=max_replies_per_tweet,
                max_concurrent=max_concurrent,
            ),
        )

    # ========== 步骤 2: 并发获取回复和 Thread ==========
    logger.info(f"开始并发获取 {len(seed_tweets)} 条推文的回复和 Thread...")

    # 创建并发任务
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_tweet_context(tweet: Tweet, author: User) -> TweetWithContext:
        """获取单条推文的完整上下文（带并发控制）"""
        async with semaphore:
            # 获取回复
            replies = await _get_replies(client, tweet.id, max_replies_per_tweet)

            # 获取 Thread（如果需要）
            thread_context = []
            if include_thread:
                thread_context = await _get_thread_context(client, tweet.id)

            return TweetWithContext(
                tweet=tweet,
                author=author,
                replies=replies,
                thread_context=thread_context,
            )

    # 并发执行
    tasks = [
        fetch_tweet_context(tweet, seed_users[tweet.author_id]) for tweet in seed_tweets
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ========== 步骤 3: 处理结果 ==========
    items = []
    failed_tweet_ids = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # 记录失败
            tweet_id = seed_tweets[i].id
            failed_tweet_ids.append(tweet_id)
            logger.error(f"推文 {tweet_id} 处理失败: {result}")
        else:
            # 成功
            items.append(result)

    # ========== 步骤 4: 统计元信息 ==========
    total_reply_count = sum(len(item.replies) for item in items)
    total_thread_count = sum(len(item.thread_context) for item in items)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    metadata = CollectionMetadata(
        query=query,
        query_type=query_type,
        collected_at=start_time,
        seed_tweet_count=len(seed_tweets),
        total_reply_count=total_reply_count,
        total_thread_count=total_thread_count,
        failed_tweet_ids=failed_tweet_ids,
        max_seed_tweets=max_seed_tweets,
        max_replies_per_tweet=max_replies_per_tweet,
        max_concurrent=max_concurrent,
    )

    # ========== 步骤 5: 返回结果 ==========
    collection = TweetDiscussionCollection(items=items, metadata=metadata)

    logger.info("=" * 60)
    logger.info("采集完成！")
    logger.info(f"耗时: {duration:.1f} 秒")
    logger.info(f"种子推文: {len(seed_tweets)} 条")
    logger.info(f"成功处理: {len(items)} 条")
    logger.info(f"失败: {len(failed_tweet_ids)} 条")
    logger.info(f"总推文数: {collection.total_tweets} 条（含回复和 Thread）")
    logger.info(f"总回复数: {total_reply_count} 条")
    logger.info(f"总 Thread 数: {total_thread_count} 条")
    logger.info(f"成功率: {collection.success_rate:.1%}")
    logger.info("=" * 60)

    return collection
