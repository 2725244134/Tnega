"""
============================================
应用配置管理
============================================
基于 pydantic-settings 的配置管理
"""

from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类

    环境变量前缀：TNEGA_
    例如：TNEGA_DEBUG=true, TNEGA_PORT=8000
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TNEGA_",
        case_sensitive=False,
    )

    # ============================================
    # 基础配置
    # ============================================

    DEBUG: bool = Field(default=False, description="调试模式")
    HOST: str = Field(default="0.0.0.0", description="服务绑定地址")
    PORT: int = Field(default=8000, description="服务端口")

    # ============================================
    # 数据库配置
    # ============================================

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost/tnega",
        description="PostgreSQL 数据库连接字符串"
    )

    DB_POOL_SIZE: int = Field(default=20, description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(default=40, description="数据库连接池最大溢出")

    # ============================================
    # Redis 配置
    # ============================================

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis 连接字符串"
    )

    REDIS_POOL_SIZE: int = Field(default=20, description="Redis 连接池大小")
    REDIS_TIMEOUT: int = Field(default=5, description="Redis 连接超时时间（秒）")

    # ============================================
    # Celery 配置
    # ============================================

    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery 消息代理 URL"
    )

    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery 结果后端 URL"
    )

    CELERY_TASK_TIMEOUT: int = Field(
        default=3600,  # 1 小时
        description="任务超时时间（秒）"
    )

    # ============================================
    # API 配置
    # ============================================

    API_TITLE: str = Field(default="Tnega API", description="API 标题")
    API_VERSION: str = Field(default="v1", description="API 版本")
    API_DESCRIPTION: str = Field(
        default="基于 FastAPI + Redis 的社交内容分析服务",
        description="API 描述"
    )

    # CORS 配置
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="允许的 CORS 来源"
    )

    # ============================================
    # Twitter API 配置
    # ============================================

    TWITTER_API_KEY: str = Field(description="Twitter API Key")
    TWITTER_API_BASE_URL: str = Field(
        default="https://api.twitterapi.io",
        description="Twitter API 基础 URL"
    )

    # ============================================
    # Google Gemini API 配置
    # ============================================

    GOOGLE_API_KEY: str = Field(description="Google Gemini API Key")

    # ============================================
    # 日志配置
    # ============================================

    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="日志格式"
    )

    # ============================================
    # 缓存配置
    # ============================================

    CACHE_TTL: int = Field(
        default=3600,  # 1 小时
        description="缓存过期时间（秒）"
    )

    ANALYSIS_CACHE_TTL: int = Field(
        default=86400,  # 24 小时
        description="分析结果缓存时间（秒）"
    )

    # ============================================
    # 任务配置
    # ============================================

    MAX_CONCURRENT_TASKS: int = Field(
        default=10,
        description="最大并发任务数"
    )

    TASK_RETRY_TIMES: int = Field(
        default=3,
        description="任务重试次数"
    )

    TASK_RETRY_DELAY: int = Field(
        default=60,  # 1 分钟
        description="任务重试延迟（秒）"
    )

    # ============================================
    # 验证器
    # ============================================

    @validator("DATABASE_URL", "REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")
    def validate_urls(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v:
            raise ValueError("URL 不能为空")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日志级别必须是 {valid_levels} 之一")
        return v.upper()

    # ============================================
    # 便捷属性
    # ============================================

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return not self.DEBUG

    @property
    def database_echo(self) -> bool:
        """是否打印数据库 SQL 语句"""
        return self.DEBUG

    @property
    def celery_task_routes(self) -> dict:
        """Celery 任务路由配置"""
        return {
            "app.tasks.analysis.analyze_tweets": {"queue": "analysis"},
            "app.tasks.collection.collect_tweets": {"queue": "collection"},
        }


# 全局配置实例
settings = Settings()