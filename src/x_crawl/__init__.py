"""
============================================
x_crawl - Twitter 数据采集层
============================================
提供类型安全的数据模型和 API 封装
"""

from .models import (
    # 核心实体
    User,
    Tweet,
    Media,
    
    # 扩展类型
    TweetWithIncludes,
    
    # API 响应容器
    TwitterAPIResponse,
    
    # 业务容器
    Timeline,
    SearchResults,
    UserProfile,
)

from .crawler import TwitterCrawler, create_crawler
from .storage import (
    save_tweets_json,
    save_tweets_jsonl,
    save_search_results_json,
    save_results,
    load_tweets_json,
    load_tweets_jsonl,
    load_search_results_json,
)

__all__ = [
    # 核心实体
    "User",
    "Tweet",
    "Media",
    
    # 扩展类型
    "TweetWithIncludes",
    
    # API 响应容器
    "TwitterAPIResponse",
    
    # 业务容器
    "Timeline",
    "SearchResults",
    "UserProfile",
    
    # API 客户端
    "TwitterCrawler",
    "create_crawler",
    
    # 存储功能
    "save_tweets_json",
    "save_tweets_jsonl",
    "save_search_results_json",
    "save_results",
    "load_tweets_json",
    "load_tweets_jsonl",
    "load_search_results_json",
]
