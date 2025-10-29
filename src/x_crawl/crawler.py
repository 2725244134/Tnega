"""
============================================
Twitter 数据采集核心模块
============================================
基于 tweepy 的异步 API 封装
所有方法返回类型安全的 Pydantic 模型
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from tweepy.asynchronous import AsyncClient #pyright:ignore[reportMissingTypeStubs]
from tweepy.errors import TooManyRequests

from .models import User, Tweet, SearchResults, SearchMetadata


# ============================================
# 配置加载
# ============================================

# 自动加载 .env 文件（如果存在）
load_dotenv()


def _load_bearer_token() -> str:
    """
    从环境变量加载 Bearer Token（不区分大小写）
    
    前提：已通过 load_dotenv() 加载 .env 文件
    """
    # 统一转小写匹配，并去除键名中的引号
    env_dict_lower = {k.lower().strip('"').strip("'"): v for k, v in os.environ.items()}
    
    if "bearer_token" in env_dict_lower:
        logger.info("✅ Bearer Token 加载成功")
        return env_dict_lower["bearer_token"]
    
    raise ValueError(
        "未找到 BEARER_TOKEN 环境变量\n"
        "请设置环境变量或在项目根目录创建 .env 文件"
    )


# ============================================
# 工具函数
# ============================================

def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 strings (including trailing Z) into aware datetimes."""
    if value is None:
        return None

    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning(f"⚠️ 无法解析时间字符串: {value}")
        return None


def _coerce_iso_string(value: datetime | str | None) -> str | None:
    """Ensure datetime inputs are rendered as ISO 8601 strings with Z suffix."""
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return value


def _extract_lang_token(query: str | None) -> str | None:
    """Extract lang:xx token from a query string if present."""
    if not query:
        return None

    parts = query.split()
    for part in parts:
        token = part.strip().lower()
        if token.startswith("lang:") and len(token) > 5:
            return token.split(":", 1)[1]
    return None


def _normalize_datetime(value: datetime | None) -> datetime:
    """Coerce datetimes to timezone-aware UTC for sorting and metadata."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# ============================================
# Twitter API 客户端
# ============================================

class TwitterCrawler:
    """
    Twitter API 异步客户端
    
    核心职责：
    1. 封装 tweepy AsyncClient
    2. 将 API 响应转换为 Pydantic 模型
    3. 处理错误和速率限制
    """
    
    def __init__(self, bearer_token: str | None = None):
        """
        初始化 Twitter 客户端
        
        Args:
            bearer_token: Twitter API Bearer Token (不提供则自动从 .env 加载)
        """
        if bearer_token is None:
            bearer_token = _load_bearer_token()
        
        self._client = AsyncClient(bearer_token=bearer_token)
        logger.info("🚀 TwitterCrawler 初始化完成")
    
    async def close(self):
        """关闭客户端连接"""
        # tweepy AsyncClient 当前版本不需要显式关闭
        logger.info("🔌 TwitterCrawler 连接关闭")
    
    # ============================================
    # 核心 API - 主题抓取专用
    # ============================================
    
    async def search_all_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: str | None = None,
        end_time: str | None = None,
        next_token: str | None = None
    ) -> SearchResults:
        """
        搜索完整历史推文（需要 Academic Research 权限）
        
        Args:
            query: 搜索查询（Twitter 搜索语法，最多 1024 字符）
            max_results: 返回结果数 (10-500，默认 100)
            start_time: 起始时间 (ISO 8601 格式: YYYY-MM-DDTHH:mm:ssZ)
            end_time: 结束时间 (ISO 8601 格式)
            next_token: 分页令牌（用于获取下一页）
        
        Returns:
            SearchResults 对象
        
        Example:
            >>> # 搜索 2023 年关于 AI 的推文
            >>> results = await crawler.search_all_tweets(
            ...     "AI agents",
            ...     max_results=500,
            ...     start_time="2023-01-01T00:00:00Z",
            ...     end_time="2023-12-31T23:59:59Z"
            ... )
        
        Note:
            - 默认返回最近 30 天的推文（如不指定 start_time）
            - 需要 Academic Research Track 权限
            - 推文从 2006-03-26 首条推文开始可搜索
        """
        logger.info(f"📡 搜索完整历史: query='{query}', max_results={max_results}")
        
        response = await self._client.search_all_tweets(
            query=query,
            max_results=min(max_results, 500),
            start_time=start_time,
            end_time=end_time,
            next_token=next_token,
            tweet_fields=[
                "id", "text", "created_at", "author_id",
                "public_metrics", "lang", "possibly_sensitive",
                "referenced_tweets", "attachments", "conversation_id",
                "context_annotations", "entities", "geo", "in_reply_to_user_id"
            ],
            expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
            user_fields=["id", "username", "name", "verified", "public_metrics"],
            media_fields=["media_key", "type", "url", "preview_image_url"]
        )
        
        if not response.data:
            logger.warning(f"⚠️ 未找到匹配推文: {query}")
            return SearchResults(
                tweets=[],
                users={},
                media={},
                result_count=0
            )
        
        # 解析推文
        tweets = [self._parse_tweet_data(tweet) for tweet in response.data]
        
        # 解析用户
        users = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                user_data = self._parse_user_data(user)
                users[user_data["id"]] = User(**user_data)
        
        # 解析媒体
        media = {}
        if response.includes and "media" in response.includes:
            for m in response.includes["media"]:
                media_data = self._parse_media_data(m)
                media[media_data["media_key"]] = media_data
        
        meta = response.meta or {}
        
        total_count = meta.get("total_tweet_count")
        metadata = SearchMetadata(
            query=query,
            start_time=_parse_iso_datetime(start_time),
            end_time=_parse_iso_datetime(end_time),
            source="search_all",
            language=_extract_lang_token(query),
            page_count=1,
            total_collected=meta.get("result_count", len(tweets)),
            request_parameters={
                "max_results": max_results,
                "next_token": next_token,
                "start_time": start_time,
                "end_time": end_time,
            },
        )

        results = SearchResults(
            tweets=[Tweet(**t) for t in tweets],
            users=users,
            media=media,
            next_token=meta.get("next_token"),
            result_count=meta.get("result_count", len(tweets)),
            total_count=total_count,
            metadata=metadata,
        )

        logger.success(f"✅ 搜索成功: {results.result_count} 条推文")
        return results

    async def search_recent_tweets(
        self,
        query: str,
        max_results: int = 10,
        start_time: str | None = None,
        end_time: str | None = None,
        next_token: str | None = None
    ) -> SearchResults:
        """
        搜索最近 7 天的推文（不需要特殊权限）
        
        Args:
            query: 搜索查询（Twitter 搜索语法）
            max_results: 返回结果数 (10-100，默认 10)
            start_time: 起始时间 (ISO 8601 格式，最多 7 天前)
            end_time: 结束时间 (ISO 8601 格式)
            next_token: 分页令牌
        
        Returns:
            SearchResults 对象
        
        Example:
            >>> # 搜索最近的推文
            >>> results = await crawler.search_recent_tweets(
            ...     "China military parade",
            ...     max_results=100
            ... )
        
        Note:
            - 只能搜索最近 7 天的推文
            - 不需要 Academic Research 权限
            - 适合测试和小规模数据采集
        """
        logger.info(f"📡 搜索最近推文: query='{query}', max_results={max_results}")
        
        response = await self._client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            start_time=start_time,
            end_time=end_time,
            next_token=next_token,
            tweet_fields=[
                "id", "text", "created_at", "author_id",
                "public_metrics", "lang", "possibly_sensitive",
                "referenced_tweets", "attachments", "conversation_id",
                "context_annotations", "entities", "geo", "in_reply_to_user_id"
            ],
            expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
            user_fields=["id", "username", "name", "verified", "public_metrics"],
            media_fields=["media_key", "type", "url", "preview_image_url"]
        )
        
        if not response.data:
            logger.warning(f"⚠️ 未找到匹配推文: {query}")
            return SearchResults(
                tweets=[],
                users={},
                media={},
                result_count=0
            )
        
        # 解析推文
        tweets = [self._parse_tweet_data(tweet) for tweet in response.data]
        
        # 解析用户
        users = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                user_data = self._parse_user_data(user)
                users[user_data["id"]] = User(**user_data)
        
        # 解析媒体
        media = {}
        if response.includes and "media" in response.includes:
            for m in response.includes["media"]:
                media_data = self._parse_media_data(m)
                media[media_data["media_key"]] = media_data
        
        meta = response.meta or {}
        
        total_count = meta.get("total_tweet_count")
        metadata = SearchMetadata(
            query=query,
            start_time=_parse_iso_datetime(start_time),
            end_time=_parse_iso_datetime(end_time),
            source="search_recent",
            language=_extract_lang_token(query),
            page_count=1,
            total_collected=meta.get("result_count", len(tweets)),
            request_parameters={
                "max_results": max_results,
                "next_token": next_token,
                "start_time": start_time,
                "end_time": end_time,
            },
        )

        results = SearchResults(
            tweets=[Tweet(**t) for t in tweets],
            users=users,
            media=media,
            next_token=meta.get("next_token"),
            result_count=meta.get("result_count", len(tweets)),
            total_count=total_count,
            metadata=metadata,
        )

        logger.success(f"✅ 搜索成功: {results.result_count} 条推文")
        return results

    async def search_all_tweets_paginated(
        self,
        query: str,
        *,
        start_time: datetime | str | None = None,
        end_time: datetime | str | None = None,
        max_results: int = 500,
        max_pages: int | None = None,
        page_pause: float = 2.0,
        label: str | None = None,
        language: str | None = None,
    ) -> SearchResults:
        """
        自动分页抓取历史推文并合并结果。

        Args:
            query: Twitter 搜索语句
            start_time: 起始时间（datetime 或 ISO 字符串）
            end_time: 结束时间（datetime 或 ISO 字符串）
            max_results: 单页抓取数量（10-500）
            max_pages: 限制分页次数（None 表示尽可能多）
            page_pause: 每页抓取后的等待秒数，缓解速率限制
            label: 数据集标签，用于记录 metadata
            language: 如果提供且查询中未包含 lang: 过滤，则自动追加

        Returns:
            合并后的搜索结果
        """

        prepared_query = query.strip()
        language = language or _extract_lang_token(prepared_query)
        if language and "lang:" not in prepared_query.lower():
            prepared_query = f"{prepared_query} lang:{language}"

        start_iso = _coerce_iso_string(start_time)
        end_iso = _coerce_iso_string(end_time)

        all_tweets: dict[str, Tweet] = {}
        aggregated_users: dict[str, User] = {}
        aggregated_media: dict[str, Any] = {}

        next_token: str | None = None
        page_count = 0
        approximate_total: int | None = None
        final_next_token: str | None = None

        retry = 0

        while True:
            if max_pages is not None and page_count >= max_pages:
                logger.info("🛑 达到分页上限，停止抓取")
                break

            try:
                page = await self.search_all_tweets(
                    query=prepared_query,
                    max_results=max_results,
                    start_time=start_iso,
                    end_time=end_iso,
                    next_token=next_token,
                )
            except TooManyRequests:
                wait_seconds = min(900, 60 * (2 ** retry))
                retry += 1
                logger.warning(f"⏳ 速率限制，等待 {wait_seconds}s 后重试 (page={page_count + 1})")
                await asyncio.sleep(wait_seconds)
                continue

            retry = 0
            page_count += 1

            approximate_total = page.total_count or approximate_total
            final_next_token = page.next_token

            for tweet in page.tweets:
                all_tweets[tweet.id] = tweet

            aggregated_users.update(page.users)
            aggregated_media.update(page.media)

            if not page.next_token:
                break

            next_token = page.next_token

            if page_pause > 0:
                await asyncio.sleep(page_pause)

        if not all_tweets:
            logger.warning(f"⚠️ 未抓取到任何推文: {prepared_query}")

        sorted_tweets = sorted(
            all_tweets.values(),
            key=lambda t: _normalize_datetime(t.created_at),
        )

        metadata = SearchMetadata(
            query=prepared_query,
            label=label,
            start_time=_parse_iso_datetime(start_iso),
            end_time=_parse_iso_datetime(end_iso),
            source="search_all",
            language=language,
            page_count=page_count,
            total_collected=len(sorted_tweets),
            request_parameters={
                "max_results": max_results,
                "max_pages": max_pages,
                "page_pause": page_pause,
                "start_time": start_iso,
                "end_time": end_iso,
            },
        )

        aggregated_results = SearchResults(
            tweets=sorted_tweets,
            users=aggregated_users,
            media=aggregated_media,
            next_token=final_next_token,
            result_count=len(sorted_tweets),
            total_count=approximate_total,
            metadata=metadata,
        )

        logger.success(
            "📚 历史抓取完成: %s | 推文 %s 条 | 分页 %s",
            label or prepared_query,
            len(sorted_tweets),
            page_count,
        )

        return aggregated_results
    
    async def get_tweet(self, tweet_id: str) -> Tweet:
        """
        获取单条推文详情（包含完整的引用/评论关系）
        
        Args:
            tweet_id: 推文 ID
        
        Returns:
            Tweet 对象
        
        Example:
            >>> tweet = await crawler.get_tweet("1234567890")
            >>> print(f"内容: {tweet.text}")
            >>> print(f"点赞: {tweet.like_count}, 转发: {tweet.retweet_count}")
        """
        logger.info(f"📡 获取推文详情: tweet_id={tweet_id}")
        
        response = await self._client.get_tweet(
            id=tweet_id,
            tweet_fields=[
                "id", "text", "created_at", "author_id",
                "public_metrics", "lang", "possibly_sensitive",
                "source", "referenced_tweets", "attachments"
            ],
            expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
            user_fields=["id", "username", "name", "verified"],
            media_fields=["media_key", "type", "url", "preview_image_url"]
        )
        
        if not response.data:
            raise ValueError(f"推文不存在 (ID: {tweet_id})")
        
        tweet_data = self._parse_tweet_data(response.data)
        tweet = Tweet(**tweet_data)
        
        logger.success(f"✅ 获取推文成功: {tweet.id}")
        return tweet
    
    async def get_tweets(self, tweet_ids: list[str]) -> SearchResults:
        """
        批量获取推文详情（最多 100 条）
        
        Args:
            tweet_ids: 推文 ID 列表（最多 100 个）
        
        Returns:
            SearchResults 对象（包含推文、用户、媒体映射）
        
        Example:
            >>> # 批量获取热门推文的详情
            >>> results = await crawler.get_tweets([
            ...     "1234567890",
            ...     "0987654321",
            ...     "1122334455"
            ... ])
            >>> for tweet in results.tweets:
            ...     print(f"{tweet.text} - 点赞: {tweet.like_count}")
        
        Note:
            适用于获取搜索结果中提到的引用推文或评论
        """
        logger.info(f"📡 批量获取推文: count={len(tweet_ids)}")
        
        if len(tweet_ids) > 100:
            logger.warning("⚠️ 推文 ID 数量超过 100，截取前 100 个")
            tweet_ids = tweet_ids[:100]
        
        response = await self._client.get_tweets(
            ids=tweet_ids,
            tweet_fields=[
                "id", "text", "created_at", "author_id",
                "public_metrics", "lang", "possibly_sensitive",
                "source", "referenced_tweets", "attachments"
            ],
            expansions=["author_id", "attachments.media_keys"],
            user_fields=["id", "username", "name", "verified", "public_metrics"],
            media_fields=["media_key", "type", "url", "preview_image_url"]
        )
        
        if not response.data:
            logger.warning("⚠️ 未找到任何推文")
            return SearchResults(
                tweets=[],
                users={},
                media={},
                result_count=0
            )
        
        # 解析推文
        tweets = [self._parse_tweet_data(tweet) for tweet in response.data]
        
        # 解析用户
        users = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                user_data = self._parse_user_data(user)
                users[user_data["id"]] = User(**user_data)
        
        # 解析媒体
        media = {}
        if response.includes and "media" in response.includes:
            for m in response.includes["media"]:
                media_data = self._parse_media_data(m)
                media[media_data["media_key"]] = media_data
        
        results = SearchResults(
            tweets=[Tweet(**t) for t in tweets],
            users=users,
            media=media,
            result_count=len(tweets)
        )
        
        logger.success(f"✅ 批量获取成功: {results.result_count} 条推文")
        return results
    
    async def fetch_user_by_id(self, user_id: str) -> User:
        """
        根据用户 ID 获取用户信息
        
        Args:
            user_id: Twitter 用户 ID
        
        Returns:
            User 对象
        
        Example:
            >>> user = await crawler.fetch_user_by_id("12")
            >>> print(f"@{user.username}: {user.followers_count:,} 粉丝")
        """
        logger.info(f"📡 获取用户信息 (ID: {user_id})")
        
        response = await self._client.get_user(
            id=user_id,
            user_fields=[
                "id", "username", "name", "created_at",
                "description", "location", "verified",
                "profile_image_url", "public_metrics"
            ]
        )
        
        if not response.data:
            raise ValueError(f"用户不存在 (ID: {user_id})")
        
        user_data = self._parse_user_data(response.data)
        user = User(**user_data)
        
        logger.success(f"✅ 获取用户成功: @{user.username}")
        return user
    
    # ============================================
    # 数据解析器（API 响应 -> dict）
    # ============================================
    
    def _parse_user_data(self, user: Any) -> dict[str, Any]:
        """将 tweepy User 对象转换为 dict"""
        public_metrics = getattr(user, "public_metrics", None) or {}
        
        return {
            "id": str(user.id),
            "username": user.username,
            "name": user.name,
            "created_at": getattr(user, "created_at", None),
            "description": getattr(user, "description", None),
            "location": getattr(user, "location", None),
            "verified": getattr(user, "verified", None),
            "profile_image_url": getattr(user, "profile_image_url", None),
            "followers_count": public_metrics.get("followers_count"),
            "following_count": public_metrics.get("following_count"),
            "tweet_count": public_metrics.get("tweet_count"),
            "listed_count": public_metrics.get("listed_count"),
        }
    
    def _parse_tweet_data(self, tweet: Any) -> dict[str, Any]:
        """将 tweepy Tweet 对象转换为 dict"""
        public_metrics = getattr(tweet, "public_metrics", None) or {}
        
        return {
            "id": str(tweet.id),
            "text": tweet.text,
            "created_at": tweet.created_at,
            "author_id": str(tweet.author_id),
            "retweet_count": public_metrics.get("retweet_count"),
            "reply_count": public_metrics.get("reply_count"),
            "like_count": public_metrics.get("like_count"),
            "quote_count": public_metrics.get("quote_count"),
            "impression_count": public_metrics.get("impression_count"),
            "lang": getattr(tweet, "lang", None),
            "possibly_sensitive": getattr(tweet, "possibly_sensitive", None),
            "source": getattr(tweet, "source", None),
            "referenced_tweets": getattr(tweet, "referenced_tweets", None),
            "attachments": getattr(tweet, "attachments", None),
            "in_reply_to_user_id": getattr(tweet, "in_reply_to_user_id", None),
            "conversation_id": getattr(tweet, "conversation_id", None),
            "context_annotations": getattr(tweet, "context_annotations", None),
            "entities": getattr(tweet, "entities", None),
            "geo": getattr(tweet, "geo", None),
        }
    
    def _parse_media_data(self, media: Any) -> dict[str, Any]:
        """将 tweepy Media 对象转换为 dict"""
        return {
            "media_key": media.media_key,
            "type": media.type,
            "url": getattr(media, "url", None),
            "preview_image_url": getattr(media, "preview_image_url", None),
            "width": getattr(media, "width", None),
            "height": getattr(media, "height", None),
            "duration_ms": getattr(media, "duration_ms", None),
        }


# ============================================
# 便捷函数
# ============================================

async def create_crawler() -> TwitterCrawler:
    """创建并返回 TwitterCrawler 实例"""
    return TwitterCrawler()
