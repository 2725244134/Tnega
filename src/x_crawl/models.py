"""
============================================
Twitter API 数据模型定义
============================================
基于 twitterapi.io API 的精简数据模型
只保留核心字段，删除冗余数据
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

# ============================================
# 用户实体（精简版）
# ============================================


class User(BaseModel):
    """
    Twitter 用户对象

    只保留必要字段：
    - 身份识别（id, username, name）
    - 地理位置（location）- 用于判断阿拉伯地区
    - 影响力指标（verified, followers_count）
    - 账户时间（created_at）
    """

    id: str = Field(..., description="用户唯一标识符")

    username: str = Field(
        ..., description="用户名（@handle，不含 @ 符号）", examples=["elonmusk"]
    )

    name: str = Field(..., description="用户显示名称", examples=["Elon Musk"])

    location: str | None = Field(
        default=None, description="用户填写的位置信息（用于判断地区）"
    )

    verified: bool = Field(default=False, description="是否为认证账户")

    followers_count: int = Field(default=0, description="粉丝数量（影响力指标）", ge=0)

    created_at: datetime | None = Field(default=None, description="账户创建时间（UTC）")


# ============================================
# 推文实体（精简版）
# ============================================


class Tweet(BaseModel):
    """
    Twitter 推文对象

    只保留核心字段：
    - 基础信息（id, text, created_at, author_name, lang）
    - 互动数据（like/retweet/reply/view count）- 用于评估热度
    - 关系数据（conversation_id, is_reply, in_reply_to_id）- 用于追踪讨论
    """

    # ========== 基础信息 ==========
    id: str = Field(..., description="推文唯一标识符（用于 API 调用）")

    text: str = Field(..., description="推文文本内容（核心目标数据）")

    created_at: datetime = Field(..., description="推文发布时间（UTC，用于时间过滤）")

    author_name: str | None = Field(
        default=None, description="推文作者显示名称（用于 CSV 导出等）"
    )

    lang: str | None = Field(
        default=None,
        description="推文语言代码（ISO 639-1，用于判断地区）",
        examples=["en", "ar", "zh"],
    )

    # ========== 互动数据（热度指标）==========
    like_count: int = Field(default=0, description="点赞数量", ge=0)

    retweet_count: int = Field(default=0, description="转推数量", ge=0)

    reply_count: int = Field(default=0, description="回复数量", ge=0)

    view_count: int = Field(default=0, description="浏览数量", ge=0)

    # ========== 关系数据 ==========
    conversation_id: str | None = Field(
        default=None, description="所属会话 ID（用于追踪讨论线程）"
    )

    is_reply: bool = Field(default=False, description="是否为回复推文")

    in_reply_to_id: str | None = Field(default=None, description="回复的目标推文 ID")


# ============================================
# 推文与讨论上下文
# ============================================


class TweetWithContext(BaseModel):
    """
    推文及其完整讨论上下文

    包含：
    - 种子推文（tweet）
    - 作者信息（author）
    - 所有回复（replies）
    - Thread 上下文（thread_context）
    """

    tweet: Tweet = Field(..., description="种子推文")

    author: User = Field(..., description="推文作者信息")

    replies: list[Tweet] = Field(
        default_factory=list, description="该推文的所有回复（平铺列表）"
    )

    thread_context: list[Tweet] = Field(
        default_factory=list, description="该推文的 Thread 上下文（包含父推文链）"
    )

    # ========== 派生属性 ==========
    @property
    def total_engagement(self) -> int:
        """
        总互动数（点赞 + 转推 + 回复）

        用于评估推文的讨论热度
        """
        return self.tweet.like_count + self.tweet.retweet_count + self.tweet.reply_count

    @property
    def reply_authors(self) -> set[str | None]:
        """
        回复者名称集合（去重）

        用于统计参与讨论的独立用户数
        """
        return {reply.author_name for reply in self.replies}

    @property
    def has_discussion(self) -> bool:
        """是否有讨论（回复数 > 0）"""
        return len(self.replies) > 0

    @property
    def has_thread(self) -> bool:
        """是否属于 Thread（上下文推文数 > 0）"""
        return len(self.thread_context) > 0


# ============================================
# 采集元信息
# ============================================


class CollectionMetadata(BaseModel):
    """
    数据采集的元信息

    记录：
    - 查询参数（query, query_type）
    - 采集时间（collected_at）
    - 统计数据（推文数量、失败情况）
    - 时间范围（since/until timestamp）
    """

    # ========== 查询参数 ==========
    query: str = Field(..., description="原始搜索查询语句")

    query_type: Literal["Latest", "Top"] = Field(
        ..., description="查询类型（最新/热门）"
    )

    collected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="数据采集时间（UTC）",
    )

    # ========== 统计数据 ==========
    seed_tweet_count: int = Field(default=0, description="种子推文数量", ge=0)

    total_reply_count: int = Field(default=0, description="总回复数量", ge=0)

    total_thread_count: int = Field(default=0, description="总 Thread 推文数量", ge=0)

    failed_tweet_ids: list[str] = Field(
        default_factory=list, description="获取失败的推文 ID 列表"
    )

    # ========== 时间范围 ==========
    since_timestamp: int | None = Field(
        default=None, description="起始时间戳（Unix 秒）"
    )

    until_timestamp: int | None = Field(
        default=None, description="结束时间戳（Unix 秒）"
    )

    # ========== 其他参数 ==========
    max_seed_tweets: int = Field(default=0, description="最大种子推文数限制", ge=0)

    max_replies_per_tweet: int = Field(
        default=0, description="每条推文最大回复数限制", ge=0
    )

    max_concurrent: int = Field(default=0, description="最大并发请求数", ge=0)


# ============================================
# 推文讨论采集结果
# ============================================


class TweetDiscussionCollection(BaseModel):
    """
    推文讨论采集结果（高级组合操作的返回值）

    包含：
    - 推文及其讨论上下文列表（items）
    - 采集元信息（metadata）
    - 便捷访问属性（all_tweets, all_users 等）
    """

    items: list[TweetWithContext] = Field(
        default_factory=list, description="推文及其讨论上下文列表"
    )

    metadata: CollectionMetadata = Field(..., description="采集元信息")

    # ========== 便捷访问属性 ==========
    @property
    def all_tweets(self) -> list[Tweet]:
        """
        所有推文（种子 + 回复 + Thread，去重）

        用于全局分析（如语言分布、时间分布等）
        """
        seen = set()
        tweets = []

        for item in self.items:
            # 种子推文
            if item.tweet.id not in seen:
                seen.add(item.tweet.id)
                tweets.append(item.tweet)

            # 回复
            for reply in item.replies:
                if reply.id not in seen:
                    seen.add(reply.id)
                    tweets.append(reply)

            # Thread 上下文
            for thread_tweet in item.thread_context:
                if thread_tweet.id not in seen:
                    seen.add(thread_tweet.id)
                    tweets.append(thread_tweet)

        return tweets

    @property
    def all_users(self) -> dict[str, User]:
        """
        所有涉及的用户（user_id -> User）

        注意：只包含种子推文作者，不包含回复者
        （回复者信息需要单独获取）
        """
        return {item.author.id: item.author for item in self.items}

    @property
    def total_tweets(self) -> int:
        """推文总数（去重后）"""
        return len(self.all_tweets)

    @property
    def total_replies(self) -> int:
        """总回复数"""
        return sum(len(item.replies) for item in self.items)

    @property
    def total_threads(self) -> int:
        """总 Thread 推文数"""
        return sum(len(item.thread_context) for item in self.items)

    @property
    def success_rate(self) -> float:
        """
        成功率（未失败的推文数 / 总推文数）

        用于评估数据采集的完整性
        """
        total = self.metadata.seed_tweet_count
        failed = len(self.metadata.failed_tweet_ids)

        if total == 0:
            return 0.0

        return (total - failed) / total

    @property
    def average_replies_per_tweet(self) -> float:
        """平均每条推文的回复数"""
        if not self.items:
            return 0.0
        return self.total_replies / len(self.items)


# ============================================
# 简化的搜索结果（可选，用于向后兼容）
# ============================================


class SearchResults(BaseModel):
    """
    简化的搜索结果容器

    用于仅需要推文列表的场景
    （向后兼容旧代码）
    """

    tweets: list[Tweet] = Field(default_factory=list, description="推文列表")

    users: dict[str, User] = Field(
        default_factory=dict, description="用户映射表（user_id -> User）"
    )

    result_count: int = Field(default=0, description="结果数量", ge=0)

    query: str | None = Field(default=None, description="原始查询语句")
