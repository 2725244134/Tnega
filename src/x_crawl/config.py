"""
============================================
Twitter API 配置管理
============================================
使用 pydantic-settings 管理环境变量
所有敏感信息从 .env 加载
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================
# Twitter API 配置
# ============================================


class TwitterAPIConfig(BaseSettings):
    """
    Twitter API 访问配置

    从环境变量或 .env 文件加载
    所有字段都有合理的默认值（除了 twitter_api_key）
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    twitter_api_key: str = Field(
        "new1_2d3ec9c7e1104ca1a6a062f6a87869ea",
        description="Twitter API Key (从 twitterapi.io 获取)",
    )

    twitter_api_base_url: str = Field(
        default="https://api.twitterapi.io",
        description="Twitter API 基础 URL",
    )

    # ========== HTTP 配置 ==========
    http_timeout: float = Field(
        default=30.0,
        description="HTTP 请求超时时间（秒）",
        gt=0,
    )

    max_concurrent_requests: int = Field(
        default=20,
        description="HTTP 客户端连接池大小",
        gt=0,
    )


# ============================================
# 全局配置实例（单例模式）
# ============================================

_config_instance: TwitterAPIConfig | None = None


def get_config() -> TwitterAPIConfig:
    """
    获取全局配置单例

    首次调用时从环境变量加载
    后续调用返回缓存的配置对象

    Returns:
        TwitterAPIConfig: 配置对象

    Raises:
        ValidationError: 环境变量缺失或格式错误

    Example:
        >>> config = get_config()
        >>> print(config.twitter_api_key)
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = TwitterAPIConfig()

    return _config_instance
