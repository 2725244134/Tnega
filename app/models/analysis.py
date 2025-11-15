"""
============================================
分析任务相关模型
============================================
分析任务、结果等模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"    # 重试中


class AnalysisTask(Base, TimestampMixin, SoftDeleteMixin):
    """
    分析任务模型

    记录用户提交的分析任务信息
    """

    __tablename__ = "analysis_tasks"

    # 任务ID（主键）
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="任务UUID"
    )

    # 用户ID（可选，用于多用户系统）
    user_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="用户ID"
    )

    # 任务标题
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="任务标题"
    )

    # 分析需求描述
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="分析需求描述"
    )

    # 搜索查询
    search_query: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="搜索查询语句"
    )

    # 目标推文数量
    target_count: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
        comment="目标推文数量"
    )

    # 任务状态
    status: Mapped[TaskStatus] = mapped_column(
        String(20),
        default=TaskStatus.PENDING,
        nullable=False,
        comment="任务状态"
    )

    # 进度（0-100）
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="任务进度百分比"
    )

    # 开始时间
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="任务开始时间"
    )

    # 完成时间
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="任务完成时间"
    )

    # 失败原因
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="失败原因"
    )

    # 重试次数
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="重试次数"
    )

    # 最大重试次数
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        comment="最大重试次数"
    )

    # 任务参数
    parameters: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="任务参数（JSON）"
    )

    # 关联关系
    results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="task",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_analysis_tasks_status", "status"),
        Index("idx_analysis_tasks_user_id", "user_id"),
        Index("idx_analysis_tasks_created_at", "created_at"),
    )

    @property
    def duration(self) -> Optional[float]:
        """
        任务耗时（秒）

        Returns:
            任务耗时，如果未完成返回 None
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_finished(self) -> bool:
        """是否已完成（成功或失败）"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries


class AnalysisResult(Base, TimestampMixin):
    """
    分析结果模型

    存储分析任务的详细结果
    """

    __tablename__ = "analysis_results"

    # 结果ID（主键）
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="结果UUID"
    )

    # 关联的任务ID
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("analysis_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联任务ID"
    )

    # 结果类型
    result_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="结果类型（summary, sentiment, trend, etc.）"
    )

    # 结果标题
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="结果标题"
    )

    # 结果描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="结果描述"
    )

    # 结果数据
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="结果数据（JSON）"
    )

    # 结果质量分数（0-100）
    quality_score: Mapped[Optional[float]] = mapped_column(
        Integer,
        nullable=True,
        comment="结果质量分数（0-100）"
    )

    # 关联关系
    task: Mapped["AnalysisTask"] = relationship(
        "AnalysisTask",
        back_populates="results"
    )

    # 索引
    __table_args__ = (
        Index("idx_analysis_results_task_id", "task_id"),
        Index("idx_analysis_results_result_type", "result_type"),
    )


class TweetData(Base, TimestampMixin):
    """
    推文数据模型

    存储采集的推文原始数据
    """

    __tablename__ = "tweet_data"

    # 推文ID（主键）
    tweet_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="推文ID"
    )

    # 推文文本
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="推文文本"
    )

    # 作者信息
    author_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="作者ID"
    )

    author_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="作者名称"
    )

    author_username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="作者用户名"
    )

    # 推文元数据
    lang: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="语言代码"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="推文创建时间"
    )

    # 互动数据
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="点赞数"
    )

    retweet_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="转推数"
    )

    reply_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="回复数"
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="浏览数"
    )

    # 关系数据
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="会话ID"
    )

    is_reply: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="是否为回复"
    )

    in_reply_to_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="回复的目标推文ID"
    )

    # 原始数据
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="原始推文数据"
    )

    # 分析状态
    is_analyzed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="是否已分析"
    )

    # 索引
    __table_args__ = (
        Index("idx_tweet_data_author_id", "author_id"),
        Index("idx_tweet_data_created_at", "created_at"),
        Index("idx_tweet_data_lang", "lang"),
        Index("idx_tweet_data_conversation_id", "conversation_id"),
        Index("idx_tweet_data_is_analyzed", "is_analyzed"),
    )

    @property
    def total_engagement(self) -> int:
        """总互动数"""
        return self.like_count + self.retweet_count + self.reply_count

    @property
    def engagement_rate(self) -> float:
        """互动率（基于浏览数）"""
        if self.view_count > 0:
            return self.total_engagement / self.view_count
        return 0.0


class AnalysisCache(Base, TimestampMixin):
    """
    分析缓存模型

    缓存分析结果，提高重复查询性能
    """

    __tablename__ = "analysis_cache"

    # 缓存键（主键）
    cache_key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="缓存键"
    )

    # 缓存类型
    cache_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="缓存类型"
    )

    # 缓存数据
    data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="缓存数据"
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="过期时间"
    )

    # 访问次数
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="访问次数"
    )

    # 最后访问时间
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后访问时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_analysis_cache_cache_type", "cache_type"),
        Index("idx_analysis_cache_expires_at", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return datetime.utcnow() > self.expires_at

    def touch(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()