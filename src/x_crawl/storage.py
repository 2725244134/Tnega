"""
============================================
数据存储模块
============================================
将爬取的推文数据保存到文件
支持 JSON 和 JSONL 格式
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from .models import Tweet, User, SearchResults, SearchMetadata


# ============================================
# 存储路径配置
# ============================================

DEFAULT_DATA_DIR = Path("data")


def _ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


# ============================================
# JSON 存储（适合小批量数据）
# ============================================

def save_tweets_json(
    tweets: list[Tweet],
    filename: str | None = None,
    data_dir: Path = DEFAULT_DATA_DIR
) -> Path:
    """
    保存推文列表为 JSON 文件
    
    Args:
        tweets: 推文列表
        filename: 文件名（不提供则自动生成时间戳）
        data_dir: 数据目录
    
    Returns:
        保存的文件路径
    
    Example:
        >>> tweets = [tweet1, tweet2, tweet3]
        >>> path = save_tweets_json(tweets)
        >>> print(f"保存到: {path}")
    """
    _ensure_dir(data_dir)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tweets_{timestamp}.json"
    
    filepath = data_dir / filename
    
    # 转换为 dict 列表
    data = [tweet.model_dump(mode="json") for tweet in tweets]
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.success(f"💾 保存 {len(tweets)} 条推文 → {filepath}")
    return filepath


def save_search_results_json(
    results: SearchResults,
    filename: str | None = None,
    data_dir: Path = DEFAULT_DATA_DIR
) -> Path:
    """
    保存搜索结果为 JSON 文件（包含推文、用户、媒体）
    
    Args:
        results: SearchResults 对象
        filename: 文件名
        data_dir: 数据目录
    
    Returns:
        保存的文件路径
    """
    _ensure_dir(data_dir)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_results_{timestamp}.json"
    
    filepath = data_dir / filename
    
    # 转换为完整的数据结构
    metadata_payload: dict[str, Any] = {
        "result_count": results.result_count,
        "total_count": results.total_count,
        "next_token": results.next_token,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    if results.metadata:
        metadata_payload["search"] = results.metadata.model_dump(mode="json")

    data = {
        "tweets": [t.model_dump(mode="json") for t in results.tweets],
        "users": {uid: u.model_dump(mode="json") for uid, u in results.users.items()},
        "media": results.media,  # media 已经是 dict，可以直接序列化
        "metadata": metadata_payload,
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.success(f"💾 保存搜索结果 → {filepath} ({results.result_count} 条推文)")
    return filepath


# ============================================
# JSONL 存储（适合大批量数据）
# ============================================

def save_tweets_jsonl(
    tweets: list[Tweet],
    filename: str | None = None,
    data_dir: Path = DEFAULT_DATA_DIR,
    append: bool = False
) -> Path:
    """
    保存推文为 JSONL 文件（每行一条推文）
    
    Args:
        tweets: 推文列表
        filename: 文件名
        data_dir: 数据目录
        append: 是否追加到已有文件（适合分批抓取）
    
    Returns:
        保存的文件路径
    
    Example:
        >>> # 第一批
        >>> save_tweets_jsonl(batch1, "ai_tweets.jsonl")
        >>> # 第二批（追加）
        >>> save_tweets_jsonl(batch2, "ai_tweets.jsonl", append=True)
    
    Note:
        JSONL 格式适合流式处理和增量写入
    """
    _ensure_dir(data_dir)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tweets_{timestamp}.jsonl"
    
    filepath = data_dir / filename
    mode = "a" if append else "w"
    
    with open(filepath, mode, encoding="utf-8") as f:
        for tweet in tweets:
            line = json.dumps(tweet.model_dump(mode="json"), ensure_ascii=False)
            f.write(line + "\n")
    
    action = "追加" if append else "保存"
    logger.success(f"💾 {action} {len(tweets)} 条推文 → {filepath}")
    return filepath


def append_tweet_jsonl(
    tweet: Tweet,
    filename: str,
    data_dir: Path = DEFAULT_DATA_DIR
) -> Path:
    """
    追加单条推文到 JSONL 文件（流式写入）
    
    Args:
        tweet: 单条推文
        filename: 文件名
        data_dir: 数据目录
    
    Returns:
        文件路径
    
    Example:
        >>> async for tweet in stream_tweets():
        ...     append_tweet_jsonl(tweet, "stream.jsonl")
    """
    return save_tweets_jsonl([tweet], filename, data_dir, append=True)


# ============================================
# 数据加载
# ============================================

def load_tweets_json(filepath: Path) -> list[Tweet]:
    """
    从 JSON 文件加载推文列表
    
    Args:
        filepath: 文件路径
    
    Returns:
        推文列表
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    tweets = [Tweet(**item) for item in data]
    logger.info(f"📂 加载 {len(tweets)} 条推文 ← {filepath}")
    return tweets


def load_tweets_jsonl(filepath: Path) -> list[Tweet]:
    """
    从 JSONL 文件加载推文列表
    
    Args:
        filepath: 文件路径
    
    Returns:
        推文列表
    """
    tweets = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                tweets.append(Tweet(**data))
    
    logger.info(f"📂 加载 {len(tweets)} 条推文 ← {filepath}")
    return tweets


def load_search_results_json(filepath: Path) -> SearchResults:
    """
    从 JSON 文件加载搜索结果
    
    Args:
        filepath: 文件路径
    
    Returns:
        SearchResults 对象
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    metadata_blob = data.get("metadata", {})
    search_metadata_blob = metadata_blob.get("search")
    search_metadata = SearchMetadata(**search_metadata_blob) if search_metadata_blob else None

    results = SearchResults(
        tweets=[Tweet(**t) for t in data["tweets"]],
        users={uid: User(**u) for uid, u in data["users"].items()},
        media=data.get("media", {}),
        result_count=metadata_blob.get("result_count", len(data.get("tweets", []))),
        total_count=metadata_blob.get("total_count"),
        next_token=metadata_blob.get("next_token"),
        metadata=search_metadata,
    )
    
    logger.info(f"📂 加载搜索结果 ← {filepath} ({results.result_count} 条推文)")
    return results


# ============================================
# 便捷函数
# ============================================

def save_results(
    results: SearchResults,
    query: str,
    format: str = "json",
    data_dir: Path = DEFAULT_DATA_DIR
) -> Path:
    """
    自动保存搜索结果（根据查询生成文件名）
    
    Args:
        results: 搜索结果
        query: 搜索查询（用于生成文件名）
        format: 文件格式（"json" 或 "jsonl"）
        data_dir: 数据目录
    
    Returns:
        保存的文件路径
    
    Example:
        >>> results = await crawler.search_all_tweets("AI agents")
        >>> save_results(results, "AI agents")
    """
    # 清理查询字符串作为文件名
    safe_query = "".join(c if c.isalnum() or c in (" ", "_") else "_" for c in query)
    safe_query = safe_query.strip().replace(" ", "_")[:50]  # 限制长度

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if results.metadata:
        results.metadata.label = results.metadata.label or safe_query
        results.metadata.total_collected = results.result_count

    if format == "jsonl":
        filename = f"{safe_query}_{timestamp}.jsonl"
        return save_tweets_jsonl(results.tweets, filename, data_dir)
    else:
        filename = f"{safe_query}_{timestamp}.json"
        return save_search_results_json(results, filename, data_dir)
