"""
============================================
x_crawl - Twitter 数据采集层
============================================
提供类型安全的数据模型和 API 封装
"""

from .config import TwitterAPIConfig, get_config
from .models import (
    CollectionMetadata,
    SearchResults,
    Tweet,
    TweetDiscussionCollection,
    TweetWithContext,
    User,
)
from .tweet_fetcher import collect_tweet_discussions
from .twitter_client import create_client

__all__ = [
    # 核心数据模型
    "User",
    "Tweet",
    "TweetWithContext",
    "CollectionMetadata",
    "TweetDiscussionCollection",
    "SearchResults",
    # 配置
    "TwitterAPIConfig",
    "get_config",
    # HTTP 客户端
    "create_client",
    # 核心功能
    "collect_tweet_discussions",
]
