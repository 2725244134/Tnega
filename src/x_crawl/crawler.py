"""
============================================
Twitter 数据采集核心模块
============================================
基于 tweepy 的异步 API 封装
所有方法返回类型安全的 Pydantic 模型
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from tweepy.asynchronous import AsyncClient #pyright:ignore[reportMissingTypeStubs]

from .models import User, Tweet, SearchResults


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
                "referenced_tweets", "attachments"
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
        
        results = SearchResults(
            tweets=[Tweet(**t) for t in tweets],
            users=users,
            media=media,
            next_token=meta.get("next_token"),
            result_count=meta.get("result_count", len(tweets))
        )
        
        logger.success(f"✅ 搜索成功: {results.result_count} 条推文")
        return results
    
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
            "in_reply_to_user_id": None,  # 需要从 referenced_tweets 解析
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
