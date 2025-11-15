"""
============================================
Pydantic 数据模型（请求/响应）
============================================
API 请求和响应的数据模型定义
"""

from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models.analysis import TaskStatus


# ============================================
# 基础模型
# ============================================

class BaseSchema(BaseModel):
    """基础模式类"""

    class Config:
        # 允许字段填充
        populate_by_name = True
        # 验证赋值
        validate_assignment = True


class PaginationParams(BaseSchema):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class PaginationResponse(BaseSchema):
    """分页响应"""

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total: int = Field(description="总记录数")
    pages: int = Field(description="总页数")
    has_prev: bool = Field(description="是否有上一页")
    has_next: bool = Field(description="是否有下一页")


# ============================================
# 分析任务相关模型
# ============================================

class CreateAnalysisTaskRequest(BaseSchema):
    """创建分析任务请求"""

    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(..., min_length=1, description="分析需求描述")
    search_query: Optional[str] = Field(None, description="搜索查询语句")
    target_count: int = Field(default=1000, ge=10, le=10000, description="目标推文数量")
    parameters: Optional[dict[str, Any]] = Field(None, description="任务参数")


class AnalysisTaskResponse(BaseSchema):
    """分析任务响应"""

    id: str = Field(description="任务ID")
    title: str = Field(description="任务标题")
    description: str = Field(description="分析需求描述")
    search_query: Optional[str] = Field(None, description="搜索查询语句")
    target_count: int = Field(description="目标推文数量")
    status: TaskStatus = Field(description="任务状态")
    progress: int = Field(ge=0, le=100, description="任务进度百分比")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    retry_count: int = Field(ge=0, description="重试次数")
    error_message: Optional[str] = Field(None, description="错误信息")


class TaskListResponse(BaseSchema):
    """任务列表响应"""

    items: List[AnalysisTaskResponse] = Field(description="任务列表")
    pagination: PaginationResponse = Field(description="分页信息")


class TaskStatusResponse(BaseSchema):
    """任务状态响应"""

    id: str = Field(description="任务ID")
    status: TaskStatus = Field(description="任务状态")
    progress: int = Field(ge=0, le=100, description="任务进度百分比")
    current_step: Optional[str] = Field(None, description="当前步骤")
    estimated_remaining_time: Optional[int] = Field(None, description="预估剩余时间（秒）")


# ============================================
# 分析结果相关模型
# ============================================

class AnalysisResultResponse(BaseSchema):
    """分析结果响应"""

    id: str = Field(description="结果ID")
    task_id: str = Field(description="关联任务ID")
    result_type: str = Field(description="结果类型")
    title: str = Field(description="结果标题")
    description: Optional[str] = Field(None, description="结果描述")
    data: dict[str, Any] = Field(description="结果数据")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="质量分数")
    created_at: datetime = Field(description="创建时间")


class AnalysisSummaryResponse(BaseSchema):
    """分析汇总响应"""

    task: AnalysisTaskResponse = Field(description="任务信息")
    results: List[AnalysisResultResponse] = Field(description="分析结果列表")
    statistics: dict[str, Any] = Field(description="统计信息")


# ============================================
# 推文数据相关模型
# ============================================

class TweetDataResponse(BaseSchema):
    """推文数据响应"""

    tweet_id: str = Field(description="推文ID")
    text: str = Field(description="推文文本")
    author_id: str = Field(description="作者ID")
    author_name: str = Field(description="作者名称")
    author_username: str = Field(description="作者用户名")
    lang: Optional[str] = Field(None, description="语言代码")
    created_at: datetime = Field(description="创建时间")
    like_count: int = Field(ge=0, description="点赞数")
    retweet_count: int = Field(ge=0, description="转推数")
    reply_count: int = Field(ge=0, description="回复数")
    view_count: int = Field(ge=0, description="浏览数")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    is_reply: bool = Field(description="是否为回复")
    in_reply_to_id: Optional[str] = Field(None, description="回复的目标推文ID")
    total_engagement: int = Field(ge=0, description="总互动数")
    engagement_rate: float = Field(ge=0, description="互动率")


class TweetListResponse(BaseSchema):
    """推文列表响应"""

    items: List[TweetDataResponse] = Field(description="推文列表")
    pagination: PaginationResponse = Field(description="分页信息")


# ============================================
# 系统健康相关模型
# ============================================

class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceHealth(BaseSchema):
    """服务健康状态"""

    name: str = Field(description="服务名称")
    status: HealthStatus = Field(description="健康状态")
    message: Optional[str] = Field(None, description="状态信息")
    response_time: Optional[float] = Field(None, description="响应时间（毫秒）")


class HealthResponse(BaseSchema):
    """健康检查响应"""

    status: HealthStatus = Field(description="整体健康状态")
    version: str = Field(description="服务版本")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="检查时间")
    services: List[ServiceHealth] = Field(description="各服务健康状态")
    uptime: Optional[float] = Field(None, description="运行时间（秒）")


# ============================================
# 通用响应模型
# ============================================

class ErrorResponse(BaseSchema):
    """错误响应"""

    detail: str = Field(description="错误详情")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")
    path: Optional[str] = Field(None, description="请求路径")


class SuccessResponse(BaseSchema):
    """成功响应"""

    message: str = Field(description="成功消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间")


# ============================================
# 缓存相关模型
# ============================================

class CacheInfoResponse(BaseSchema):
    """缓存信息响应"""

    status: str = Field(description="缓存状态")
    version: Optional[str] = Field(None, description="Redis 版本")
    used_memory: Optional[str] = Field(None, description="使用内存")
    connected_clients: Optional[int] = Field(None, description="连接客户端数")
    total_commands_processed: Optional[int] = Field(None, description="处理命令数")


class CacheStatsResponse(BaseSchema):
    """缓存统计响应"""

    hit_rate: float = Field(description="缓存命中率")
    miss_rate: float = Field(description="缓存未命中率")
    total_requests: int = Field(description="总请求数")
    cache_hits: int = Field(description="缓存命中数")
    cache_misses: int = Field(description="缓存未命中数")