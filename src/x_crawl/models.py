"""
============================================
Twitter API 数据模型定义
============================================
基于 Twitter API v2 响应结构的 Pydantic 模型
所有模型严格遵循类型安全原则
"""


from datetime import datetime
from typing import Literal, Any

from pydantic import BaseModel, Field


# ============================================
# 用户实体 (User Entity)
# ============================================

class User(BaseModel):
    """
    Twitter 用户对象
    
    对应 API 响应中的 User Object
    参考: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/user
    """
    id: str = Field(
        ...,
        description="用户唯一标识符（数字型字符串）",
        examples=["1234567890"]
    )
    
    username: str = Field(
        ...,
        description="用户名（@handle，不含 @ 符号）",
        min_length=1,
        max_length=15,
        examples=["jack"]
    )
    
    name: str = Field(
        ...,
        description="用户显示名称",
        max_length=50,
        examples=["Jack Dorsey"]
    )
    
    created_at: datetime | None = Field(
        default=None,
        description="账户创建时间（UTC）"
    )
    
    description: str | None = Field(
        default=None,
        description="用户简介（bio）",
        max_length=160
    )

    location: str | None = Field(
        default=None,
        description="用户填写的位置信息",
        max_length=30
    )
    
    verified: bool | None = Field(
        default=None,
        description="是否为认证账户（蓝V）"
    )
    
    profile_image_url: str | None = Field(
        default=None,
        description="头像 URL"
    )
    
    # ========== 统计数据 ==========
    followers_count: int | None = Field(
        default=None,
        description="粉丝数量",
        ge=0
    )
    
    following_count: int | None = Field(
        default=None,
        description="关注数量",
        ge=0
    )
    
    tweet_count: int | None = Field(
        default=None,
        description="推文总数",
        ge=0
    )
    
    listed_count: int | None = Field(
        default=None,
        description="被列表收录次数",
        ge=0
    )


# ============================================
# 媒体实体 (Media Entity)
# ============================================

class Media(BaseModel):
    """
    推文附带的媒体对象（图片、视频、GIF）
    
    参考: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/media
    """
    media_key: str = Field(
        ...,
        description="媒体唯一标识符",
        examples=["3_1234567890"]
    )
    
    type: Literal["photo", "video", "animated_gif"] = Field(
        ...,
        description="媒体类型"
    )
    
    url: str | None = Field(
        default=None,
        description="图片直链（仅 photo 类型）"
    )
    
    preview_image_url: str | None = Field(
        default=None,
        description="视频预览图（video/animated_gif 类型）"
    )
    
    width: int | None = Field(
        default=None,
        description="媒体宽度（像素）",
        gt=0
    )
    
    height: int | None = Field(
        default=None,
        description="媒体高度（像素）",
        gt=0
    )
    
    duration_ms: int | None = Field(
        default=None,
        description="视频时长（毫秒，仅 video 类型）",
        ge=0
    )


# ============================================
# 推文实体 (Tweet Entity)
# ============================================

class Tweet(BaseModel):
    """
    Twitter 推文对象（核心数据结构）
    
    参考: https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet
    """
    id: str = Field(
        ...,
        description="推文唯一标识符（数字型字符串）",
        examples=["1234567890123456789"]
    )
    
    text: str = Field(
        ...,
        description="推文文本内容",
        max_length=4096  # Twitter 长推文上限
    )
    
    created_at: datetime = Field(
        ...,
        description="推文发布时间（UTC）"
    )
    
    author_id: str = Field(
        ...,
        description="作者用户 ID（关联 User.id）"
    )
    
    # ========== 互动数据 ==========
    retweet_count: int | None = Field(
        default=None,
        description="转推数量",
        ge=0
    )
    
    reply_count: int | None = Field(
        default=None,
        description="回复数量",
        ge=0
    )
    
    like_count: int | None = Field(
        default=None,
        description="点赞数量",
        ge=0
    )
    
    quote_count: int | None = Field(
        default=None,
        description="引用推文数量",
        ge=0
    )
    
    impression_count: int | None = Field(
        default=None,
        description="展示次数（需要高级权限）",
        ge=0
    )
    
    # ========== 关系数据 ==========
    in_reply_to_user_id: str | None = Field(
        default=None,
        description="回复的目标用户 ID"
    )
    
    referenced_tweets: list[dict[str, Any]] | None = Field(
        default=None,
        description="引用的推文列表（转推/引用/回复）"
    )
    
    # ========== 附件数据 ==========
    attachments: dict[str, Any] | None = Field(
        default=None,
        description="附件信息（media_keys, poll_ids 等）"
    )
    
    # ========== 元数据 ==========
    lang: str | None = Field(
        default=None,
        description="推文语言代码（ISO 639-1）",
        examples=["en", "zh", "ja"]
    )
    
    possibly_sensitive: bool | None = Field(
        default=None,
        description="是否可能包含敏感内容"
    )
    
    source: str | None = Field(
        default=None,
        description="发推工具/来源",
        examples=["Twitter for iPhone", "Twitter Web App"]
    )


# ============================================
# 扩展推文（包含关联数据）
# ============================================

class TweetWithIncludes(BaseModel):
    """
    包含 includes 扩展数据的推文
    
    当 API 请求带 expansions 参数时，会返回额外的关联对象
    如 author（用户）、media（媒体）、referenced_tweets（引用推文）等
    """
    tweet: Tweet = Field(
        ...,
        description="核心推文数据"
    )
    
    author: User | None = Field(
        default=None,
        description="推文作者完整信息"
    )
    
    media: list[Media] | None = Field(
        default=None,
        description="推文附带的媒体列表"
    )
    
    referenced_tweets: list[Tweet] | None = Field(
        default=None,
        description="被引用/转推/回复的原始推文列表"
    )


# ============================================
# API 响应容器
# ============================================

class TwitterAPIResponse(BaseModel):
    """
    Twitter API 通用响应结构
    
    包含数据主体（data）+ 扩展对象（includes）+ 元信息（meta）
    """
    data: list[Tweet] | Tweet | None = Field(
        default=None,
        description="响应主体（单个或多个推文）"
    )
    
    includes: dict[str, Any] | None = Field(
        default=None,
        description="扩展对象（users, media, places 等）"
    )
    
    meta: dict[str, Any] | None = Field(
        default=None,
        description="元信息（分页、结果统计等）"
    )
    
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description="错误列表（部分失败场景）"
    )


# ============================================
# 时间线与集合容器
# ============================================

class Timeline(BaseModel):
    """
    用户时间线（推文列表 + 元信息）
    
    用于 GET /2/users/:id/tweets 等 timeline 接口
    """
    tweets: list[Tweet] = Field(
        default_factory=list[Tweet],
        description="推文列表（按时间倒序）"
    )
    
    users: dict[str, User] = Field(
        default_factory=dict[str, User],
        description="用户映射表（user_id -> User）"
    )
    
    media: dict[str, Media] = Field(
        default_factory=dict[str, Media],
        description="媒体映射表（media_key -> Media）"
    )
    
    oldest_id: str | None = Field(
        default=None,
        description="最旧推文 ID（用于分页）"
    )
    
    newest_id: str | None = Field(
        default=None,
        description="最新推文 ID（用于分页）"
    )
    
    result_count: int = Field(
        0,
        description="本次返回的推文数量",
        ge=0
    )


class SearchResults(BaseModel):
    """
    搜索结果容器
    
    用于 GET /2/tweets/search/recent 等搜索接口
    """
    tweets: list[Tweet] = Field(
        default_factory=list[Tweet],
        description="匹配的推文列表"
    )
    
    users: dict[str, User] = Field(
        default_factory=dict[str, User],
        description="关联用户映射表"
    )
    
    media: dict[str, Media] = Field(
        default_factory=dict[str, Media],
        description="关联媒体映射表"
    )
    
    next_token: str | None = Field(
        default=None,
        description="下一页分页令牌"
    )
    
    result_count: int = Field(
        default=0,
        description="本次返回结果数",
        ge=0
    )
    
    total_count: int | None = Field(
        default=None,
        description="总匹配数（非精确，仅估算）",
        ge=0
    )


class UserProfile(BaseModel):
    """
    用户完整档案（用户信息 + 最近推文）
    
    组合数据结构，用于展示用户主页
    """
    user: User = Field(
        ...,
        description="用户基本信息"
    )
    
    recent_tweets: list[Tweet] = Field(
        default_factory=list[Tweet],
        description="用户最近推文（默认最多 10 条）"
    )
    
    pinned_tweet: Tweet | None = Field(
        default=None,
        description="置顶推文"
    )

