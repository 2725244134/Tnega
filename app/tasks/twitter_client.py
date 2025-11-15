"""
============================================
Twitter 客户端适配器
============================================
适配现有的 Twitter 客户端代码到新的架构
"""

import asyncio
from typing import Optional
from loguru import logger

from src.x_crawl.twitter_client import create_client as original_create_client
from src.x_crawl.models import TweetDiscussionCollection
from app.core.config import settings


class TwitterClient:
    """Twitter 客户端适配器"""

    def __init__(self):
        self._client = None
        self._initialized = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def initialize(self):
        """初始化客户端"""
        if not self._initialized:
            try:
                self._client = await original_create_client()
                self._initialized = True
                logger.info("Twitter 客户端初始化成功")
            except Exception as e:
                logger.error(f"Twitter 客户端初始化失败: {e}")
                raise

    async def close(self):
        """关闭客户端"""
        if self._client:
            try:
                await self._client.close()
                self._initialized = False
                logger.info("Twitter 客户端已关闭")
            except Exception as e:
                logger.error(f"关闭 Twitter 客户端失败: {e}")

    async def collect_tweet_discussions(
        self,
        query: str,
        max_seed_tweets: int = 100,
        max_replies_per_tweet: int = 50
    ) -> TweetDiscussionCollection:
        """
        采集推文讨论

        Args:
            query: 搜索查询
            max_seed_tweets: 最大种子推文数
            max_replies_per_tweet: 每条推文最大回复数

        Returns:
            推文讨论集合
        """
        if not self._initialized:
            raise RuntimeError("Twitter 客户端未初始化")

        try:
            # 使用原始的采集函数
            from src.x_crawl.tweet_fetcher import collect_tweet_discussions as original_collect

            result = await original_collect(
                query=query,
                client=self._client,
                max_seed_tweets=max_seed_tweets,
                max_replies_per_tweet=max_replies_per_tweet
            )

            logger.info(f"采集推文讨论完成: {len(result.items)} 个讨论")
            return result

        except Exception as e:
            logger.error(f"采集推文讨论失败: {e}")
            raise

    async def get_tweet_by_id(self, tweet_id: str) -> Optional[dict]:
        """
        根据ID获取推文

        Args:
            tweet_id: 推文ID

        Returns:
            推文数据
        """
        if not self._initialized:
            raise RuntimeError("Twitter 客户端未初始化")

        try:
            # 这里可以实现获取单条推文的逻辑
            # 目前使用现有的客户端功能
            logger.info(f"获取推文: {tweet_id}")
            # 返回模拟数据或实现真实逻辑
            return None

        except Exception as e:
            logger.error(f"获取推文失败: {tweet_id}, 错误: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        根据ID获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            用户数据
        """
        if not self._initialized:
            raise RuntimeError("Twitter 客户端未初始化")

        try:
            logger.info(f"获取用户信息: {user_id}")
            # 返回模拟数据或实现真实逻辑
            return None

        except Exception as e:
            logger.error(f"获取用户信息失败: {user_id}, 错误: {e}")
            return None


# 客户端工厂函数
async def create_twitter_client() -> TwitterClient:
    """
    创建 Twitter 客户端

    Returns:
        TwitterClient 实例
    """
    client = TwitterClient()
    await client.initialize()
    return client


# 全局客户端实例（可选）
_twitter_client: Optional[TwitterClient] = None


async def get_twitter_client() -> TwitterClient:
    """
    获取全局 Twitter 客户端

    Returns:
        TwitterClient 实例
    """
    global _twitter_client

    if _twitter_client is None:
        _twitter_client = await create_twitter_client()

    return _twitter_client


async def close_twitter_client():
    """关闭全局 Twitter 客户端"""
    global _twitter_client

    if _twitter_client:
        await _twitter_client.close()
        _twitter_client = None
        logger.info("全局 Twitter 客户端已关闭")


# 向后兼容的客户端创建函数
async def create_client():
    """
    向后兼容的客户端创建函数

    Returns:
        原始的 Twitter 客户端
    """
    return await original_create_client()