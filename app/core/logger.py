"""
============================================
日志配置管理
============================================
基于 loguru 的日志配置
"""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """
    配置日志系统

    功能：
    - 控制台日志输出
    - 文件日志输出（按日期轮转）
    - JSON 格式日志（生产环境）
    - 彩色日志（开发环境）
    """
    # 移除默认的日志处理器
    logger.remove()

    # 控制台日志
    if settings.DEBUG:
        # 开发环境：彩色格式化输出
        logger.add(
            sys.stdout,
            format=settings.LOG_FORMAT,
            level=settings.LOG_LEVEL,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # 生产环境：JSON 格式输出
        logger.add(
            sys.stdout,
            serialize=True,  # JSON 格式
            level=settings.LOG_LEVEL,
        )

    # 文件日志（按日期轮转）
    logger.add(
        "logs/tnega_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留 30 天
        compression="zip",  # 压缩旧日志
        format=settings.LOG_FORMAT,
        level=settings.LOG_LEVEL,
        encoding="utf-8",
        enqueue=True,  # 多进程安全
    )

    # 错误日志文件（单独记录 ERROR 及以上级别）
    logger.add(
        "logs/tnega_errors_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        format=settings.LOG_FORMAT,
        level="ERROR",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info("日志系统初始化完成")


def get_logger(name: str = None):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称（通常是模块名）

    Returns:
        配置好的日志记录器实例
    """
    if name:
        return logger.bind(name=name)
    return logger