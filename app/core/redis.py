"""
============================================
Redis 连接管理
============================================
基于 redis-py 的异步 Redis 连接管理
"""

import json
from typing import Any, Optional
import redis.asyncio as redis
from loguru import logger

from app.core.config import settings

# Redis 连接池
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """
    初始化 Redis 连接

    功能：
    - 创建 Redis 连接池
    - 测试连接
    """
    global redis_client

    try:
        # 创建 Redis 连接池
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=30,  # 健康检查间隔（秒）
        )

        # 测试连接
        await redis_client.ping()
        logger.info("✅ Redis 连接成功")

    except Exception as e:
        logger.error(f"❌ Redis 连接失败: {e}")
        redis_client = None
        raise


async def close_redis():
    """
    关闭 Redis 连接

    在应用关闭时调用
    """
    global redis_client

    if redis_client:
        try:
            await redis_client.close()
            logger.info("🔄 Redis 连接已关闭")
        except Exception as e:
            logger.error(f"关闭 Redis 连接失败: {e}")
        finally:
            redis_client = None


# 缓存工具类
class RedisCache:
    """Redis 缓存工具类"""

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回 None
        """
        if not redis_client:
            return None

        try:
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET 错误: {e}")
            return None

    @staticmethod
    async def set(
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值（支持 JSON 序列化）
            ttl: 过期时间（秒）

        Returns:
            是否成功
        """
        if not redis_client:
            return False

        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)

            # 设置缓存
            if ttl:
                return await redis_client.setex(key, ttl, value)
            else:
                return await redis_client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET 错误: {e}")
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        if not redis_client:
            return False

        try:
            return bool(await redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE 错误: {e}")
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        if not redis_client:
            return False

        try:
            return bool(await redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS 错误: {e}")
            return False

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        """
        获取 JSON 格式的缓存值

        Args:
            key: 缓存键

        Returns:
            解析后的 JSON 对象，如果不存在或解析失败返回 None
        """
        value = await RedisCache.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"缓存值不是有效的 JSON: {key}")
        return None

    @staticmethod
    async def set_json(
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置 JSON 格式的缓存值

        Args:
            key: 缓存键
            value: JSON 可序列化的值
            ttl: 过期时间（秒）

        Returns:
            是否成功
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return await RedisCache.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON 序列化失败: {e}")
            return False

    @staticmethod
    async def get_connection_info() -> dict:
        """
        获取 Redis 连接信息

        Returns:
            连接信息
        """
        if not redis_client:
            return {"status": "disconnected"}

        try:
            info = await redis_client.info()
            return {
                "status": "connected",
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except Exception as e:
            logger.error(f"获取 Redis 信息失败: {e}")
            return {"status": "error", "error": str(e)}


# 缓存装饰器
class CacheKey:
    """缓存键命名空间"""

    @staticmethod
    def analysis_result(task_id: str) -> str:
        """分析结果缓存键"""
        return f"analysis:result:{task_id}"

    @staticmethod
    def task_status(task_id: str) -> str:
        """任务状态缓存键"""
        return f"task:status:{task_id}"

    @staticmethod
    def tweet_data(tweet_id: str) -> str:
        """推文数据缓存键"""
        return f"tweet:data:{tweet_id}"

    @staticmethod
    def user_data(user_id: str) -> str:
        """用户数据缓存键"""
        return f"user:data:{user_id}"

    @staticmethod
    def search_results(query_hash: str) -> str:
        """搜索结果缓存键"""
        return f"search:results:{query_hash}"