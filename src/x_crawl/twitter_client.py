"""
============================================
Twitter API 异步客户端
============================================
封装 HTTP 请求和通用分页逻辑
使用传入的 httpx.AsyncClient，支持连接复用
"""

from typing import Any, AsyncIterator

import httpx
from loguru import logger

from .config import get_config

# ============================================
# 通用分页获取
# ============================================


async def fetch_paginated(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict[str, Any],
    max_results: int | None = None,
) -> AsyncIterator[list[dict[str, Any]]]:
    """
    异步分页获取数据（通用函数）

    自动处理：
    - cursor 分页
    - has_next_page / has_more 判断
    - 推文去重（基于 ID）
    - 结果数量限制

    Args:
        client: httpx.AsyncClient 实例
        endpoint: API 端点路径（如 "/twitter/tweet/advanced_search"）
        params: 请求参数（不含 cursor）
        max_results: 最大结果数（None = 获取全部）

    Yields:
        每页的推文列表（已去重）

    Example:
        >>> async with create_client() as client:
        ...     async for page in fetch_paginated(
        ...         client,
        ...         "/twitter/tweet/advanced_search",
        ...         {"query": "China", "queryType": "Latest"},
        ...         max_results=100
        ...     ):
        ...         print(f"获取了 {len(page)} 条推文")
    """
    config = get_config()
    base_url = config.twitter_api_base_url

    cursor = ""  # 初始 cursor 为空字符串
    seen_ids = set()
    total_collected = 0

    while True:
        # 构造请求参数
        request_params = params.copy()
        request_params["cursor"] = cursor

        # 发起请求
        url = f"{base_url}{endpoint}"
        logger.debug(f"请求: {url}, cursor={cursor}")

        try:
            response = await client.get(url, params=request_params)

            # 记录 HTTP 状态
            logger.debug(f"HTTP 状态码: {response.status_code}")

            # 尝试解析 JSON
            try:
                data = response.json()
                logger.debug(f"响应数据: {data}")
            except Exception as json_err:
                logger.error(f"JSON 解析失败: {json_err}")
                logger.error(f"原始响应: {response.text[:500]}")
                raise

            # 检查 HTTP 状态码
            if response.status_code != 200:
                logger.error(f"HTTP 错误 {response.status_code}: {response.text[:500]}")
                response.raise_for_status()

            # 检查 API 响应状态
            # 注意：成功响应没有 status 字段，只有 tweets/has_next_page/next_cursor
            # 失败响应才有 status: "error" 和 msg 字段
            if "status" in data and data["status"] != "success":
                error_msg = data.get("msg", "Unknown error")
                logger.error(f"API 返回错误: {error_msg}")
                logger.error(f"完整响应: {data}")
                break

        except httpx.HTTPStatusError as http_err:
            logger.error(f"HTTP 请求失败: {http_err}")
            logger.error(f"状态码: {http_err.response.status_code}")
            logger.error(f"响应体: {http_err.response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"请求异常: {type(e).__name__}: {e}")
            raise

        # 提取推文
        tweets = data.get("tweets", [])

        # 去重
        new_tweets = []
        for tweet in tweets:
            tweet_id = tweet.get("id")
            if tweet_id and tweet_id not in seen_ids:
                seen_ids.add(tweet_id)
                new_tweets.append(tweet)

        # 如果本页没有新推文，停止
        if not new_tweets:
            logger.debug("本页无新推文，停止分页")
            break

        # 检查是否达到数量限制
        if max_results:
            remaining = max_results - total_collected
            if remaining <= 0:
                break
            if len(new_tweets) > remaining:
                new_tweets = new_tweets[:remaining]

        # 返回本页数据
        yield new_tweets
        total_collected += len(new_tweets)

        logger.debug(f"本页获取 {len(new_tweets)} 条推文，累计 {total_collected} 条")

        # 检查是否有下一页
        has_next = data.get("has_next_page") or data.get("has_more")
        if not has_next:
            logger.debug("无下一页，停止分页")
            break

        # 更新 cursor
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            logger.debug("无 next_cursor，停止分页")
            break

        cursor = next_cursor

        # 检查是否达到数量限制
        if max_results and total_collected >= max_results:
            logger.debug(f"已达到数量限制 {max_results}，停止分页")
            break


# ============================================
# 辅助函数：创建配置好的客户端
# ============================================


def create_client(api_key: str | None = None) -> httpx.AsyncClient:
    """
    创建配置好的 Twitter API 客户端

    自动从环境变量读取配置，设置合理的超时和连接池

    Args:
        api_key: API Key（可选，默认从环境变量 TWITTER_API_KEY 读取）

    Returns:
        httpx.AsyncClient: 配置好的客户端（需要使用 async with）

    Example:
        >>> # 简单使用
        >>> async with create_client() as client:
        ...     result = await collect_tweet_discussions("query", client)
        >>>
        >>> # 复用 client（推荐）
        >>> async with create_client() as client:
        ...     result1 = await collect_tweet_discussions("query1", client)
        ...     result2 = await collect_tweet_discussions("query2", client)
        >>>
        >>> # 自定义 API Key
        >>> async with create_client(api_key="custom_key") as client:
        ...     result = await collect_tweet_discussions("query", client)
    """
    config = get_config()

    # 使用传入的 api_key，如果没有则从配置读取
    key = api_key or config.twitter_api_key

    return httpx.AsyncClient(
        timeout=config.http_timeout,
        headers={"x-api-key": key},
        limits=httpx.Limits(
            max_connections=config.max_concurrent_requests,
            max_keepalive_connections=config.max_concurrent_requests,
        ),
    )
