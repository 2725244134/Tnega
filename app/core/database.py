"""
============================================
数据库连接管理
============================================
基于 SQLAlchemy 2.0 的异步数据库连接管理
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from loguru import logger

from app.core.config import settings

# 创建异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.database_echo,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # 连接前检查连接是否有效
    pool_recycle=3600,  # 连接回收时间（秒）
    future=True,  # SQLAlchemy 2.0 风格
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 防止异步操作时对象过期
)


async def init_db():
    """
    初始化数据库连接

    功能：
    - 测试数据库连接
    - 创建表（如果不存在）
    """
    try:
        # 测试连接
        async with engine.begin() as conn:
            # 执行一个简单的查询测试连接
            await conn.execute("SELECT 1")
            logger.info("✅ 数据库连接成功")

        # 创建表（使用 Alembic 进行迁移管理）
        # 这里可以添加基础数据的初始化
        logger.info("📊 数据库初始化完成")

    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    依赖注入用，确保会话正确关闭

    Yields:
        AsyncSession: 异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话错误: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """
    关闭数据库连接

    在应用关闭时调用
    """
    try:
        await engine.dispose()
        logger.info("📊 数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


# 数据库工具函数
class DatabaseUtils:
    """数据库工具类"""

    @staticmethod
    async def check_connection() -> bool:
        """
        检查数据库连接状态

        Returns:
            bool: 连接是否正常
        """
        try:
            async with engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接检查失败: {e}")
            return False

    @staticmethod
    async def get_connection_info() -> dict:
        """
        获取数据库连接信息

        Returns:
            dict: 连接信息
        """
        return {
            "url": settings.DATABASE_URL.split("@")[-1],  # 隐藏敏感信息
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "echo": settings.database_echo,
        }