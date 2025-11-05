"""
============================================
数据解析器
============================================
将 twitterapi.io 的 JSON 响应转换为 Pydantic 模型
"""

from datetime import datetime
from typing import Any

from loguru import logger

from .models import Tweet, User

# ============================================
# 时间解析
# ============================================


def parse_twitter_time(time_str: str) -> datetime:
    """
    解析 Twitter API 时间格式

    格式: "Mon Oct 13 06:27:38 +0000 2025"
    标准: RFC 2822

    Args:
        time_str: 时间字符串

    Returns:
        datetime: 解析后的时间对象（带时区）

    Raises:
        ValueError: 时间格式无法解析

    Example:
        >>> parse_twitter_time("Mon Oct 13 06:27:38 +0000 2025")
        datetime.datetime(2025, 10, 13, 6, 27, 38, tzinfo=...)
    """
    try:
        return datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
    except ValueError as e:
        logger.error(f"无法解析时间格式: {time_str}, 错误: {e}")
        raise


# ============================================
# User 解析
# ============================================


def parse_user(raw: dict[str, Any]) -> User:
    """
    将原始 JSON 转换为 User 模型

    字段映射：
    - id → User.id
    - userName → User.username
    - name → User.name
    - location → User.location
    - isBlueVerified / isVerified → User.verified
    - followers → User.followers_count
    - createdAt → User.created_at

    Args:
        raw: twitterapi.io 返回的原始用户 JSON

    Returns:
        User: Pydantic 用户模型

    Example:
        >>> raw = {
        ...     "id": "1234567890",
        ...     "userName": "elonmusk",
        ...     "name": "Elon Musk",
        ...     "location": "Texas, USA",
        ...     "isBlueVerified": True,
        ...     "followers": 1000000
        ... }
        >>> user = parse_user(raw)
    """
    # 处理认证状态（优先使用 isBlueVerified）
    verified = raw.get("isBlueVerified", False) or raw.get("isVerified", False)

    # 处理空字符串的 location（转为 None）
    location = raw.get("location") or None
    if location and not location.strip():
        location = None

    # 解析创建时间
    created_at = None
    if raw.get("createdAt"):
        try:
            created_at = parse_twitter_time(raw["createdAt"])
        except ValueError:
            logger.warning(f"用户 {raw.get('id')} 的创建时间无法解析")

    return User(
        id=raw["id"],
        username=raw["userName"],
        name=raw["name"],
        location=location,
        verified=verified,
        followers_count=raw.get("followers", 0),
        created_at=created_at,
    )


# ============================================
# Tweet 解析
# ============================================


def parse_tweet(raw: dict[str, Any]) -> Tweet:
    """
    将原始 JSON 转换为 Tweet 模型

    字段映射：
    - id → Tweet.id
    - text → Tweet.text
    - createdAt → Tweet.created_at
    - author.name → Tweet.author_name
    - lang → Tweet.lang
    - likeCount → Tweet.like_count
    - retweetCount → Tweet.retweet_count
    - replyCount → Tweet.reply_count
    - viewCount → Tweet.view_count
    - conversationId → Tweet.conversation_id
    - isReply → Tweet.is_reply
    - inReplyToId → Tweet.in_reply_to_id

    Args:
        raw: twitterapi.io 返回的原始推文 JSON

    Returns:
        Tweet: Pydantic 推文模型

    Example:
        >>> raw = {
        ...     "id": "1234567890",
        ...     "text": "Hello World",
        ...     "createdAt": "Mon Oct 13 06:27:38 +0000 2025",
        ...     "author": {"name": "User Name"},
        ...     "lang": "en"
        ... }
        >>> tweet = parse_tweet(raw)
    """
    # 解析发布时间
    created_at = parse_twitter_time(raw["createdAt"])

    # 提取作者显示名称
    author_name = raw.get("author", {}).get("name") or None

    # 处理空字符串的 lang（转为 None）
    lang = raw.get("lang") or None

    # 处理空字符串的会话 ID 和回复 ID
    conversation_id = raw.get("conversationId") or None
    in_reply_to_id = raw.get("inReplyToId") or None

    return Tweet(
        id=raw["id"],
        text=raw["text"],
        created_at=created_at,
        author_name=author_name,
        lang=lang,
        like_count=raw.get("likeCount", 0),
        retweet_count=raw.get("retweetCount", 0),
        reply_count=raw.get("replyCount", 0),
        view_count=raw.get("viewCount", 0),
        conversation_id=conversation_id,
        is_reply=raw.get("isReply", False),
        in_reply_to_id=in_reply_to_id,
    )


# ============================================
# 批量解析
# ============================================


def parse_tweets_batch(
    raw_tweets: list[dict[str, Any]],
) -> tuple[list[Tweet], dict[str, User]]:
    """
    批量解析推文和用户

    同时提取推文和作者信息，自动去重用户

    Args:
        raw_tweets: 原始推文 JSON 列表

    Returns:
        tuple[list[Tweet], dict[str, User]]: (推文列表, 用户映射)

    Example:
        >>> tweets, users = parse_tweets_batch(raw_data)
        >>> print(f"解析了 {len(tweets)} 条推文")
        >>> print(f"涉及 {len(users)} 个用户")
    """
    logger.debug(f"parse_tweets_batch 收到 {len(raw_tweets)} 条原始推文")
    if len(raw_tweets) > 0:
        logger.debug(f"第一条原始推文: {raw_tweets[0]}")

    tweets = []
    users = {}

    for raw in raw_tweets:
        try:
            # 解析推文
            tweet = parse_tweet(raw)
            tweets.append(tweet)

            # 解析作者（去重）
            if "author" in raw:
                user = parse_user(raw["author"])
                if user.id not in users:
                    users[user.id] = user

        except Exception as e:
            logger.error(f"解析推文失败 (ID: {raw.get('id')}): {e}")
            logger.error(f"原始数据: {raw}")
            # 跳过无法解析的推文，继续处理其他推文
            continue

    logger.debug(f"parse_tweets_batch 返回 {len(tweets)} 条推文，{len(users)} 个用户")
    return tweets, users
