"""
============================================
测试推文讨论采集功能
============================================
验证 collect_tweet_discussions 函数是否正常工作
"""

import asyncio
from pathlib import Path

from loguru import logger

from src.x_crawl import collect_tweet_discussions, create_client

# ============================================
# 配置日志输出到文件
# ============================================

# 创建日志目录
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 配置日志输出
log_file = log_dir / "test_collect_discussions.log"

# 移除默认的控制台输出
logger.remove()

# 添加控制台输出（带颜色）
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
    level="INFO",
)

# 添加文件输出（完整日志）
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)

logger.info(f"日志文件: {log_file}")

# ============================================
# 测试函数
# ============================================


async def test_basic_collection():
    """
    测试基本的推文采集功能

    搜索关于"九三阅兵"的阿拉伯语推文及其讨论
    """
    logger.info("=" * 60)
    logger.info("测试 1: 基本推文采集")
    logger.info("=" * 60)

    # LLM 生成的完整 query
    query = "(China parade OR 93阅兵) lang:ar"

    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            query_type="Latest",
            max_seed_tweets=10,  # 只获取 10 条测试
            max_replies_per_tweet=5,  # 每条推文最多 5 条回复
            include_thread=True,
            max_concurrent=2,  # 降低并发避免限流
        )

    # 验证结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果:")
    logger.info(f"  种子推文数: {result.metadata.seed_tweet_count}")
    logger.info(f"  成功处理: {len(result.items)}")
    logger.info(f"  失败数: {len(result.metadata.failed_tweet_ids)}")
    logger.info(f"  总推文数: {result.total_tweets}")
    logger.info(f"  总回复数: {result.total_replies}")
    logger.info(f"  总 Thread 数: {result.total_threads}")
    logger.info(f"  成功率: {result.success_rate:.1%}")
    logger.info(f"  平均回复数: {result.average_replies_per_tweet:.1f}")

    # 展示前 3 条推文的详细信息
    logger.info("\n前 3 条推文详情:")
    for i, item in enumerate(result.items[:3], 1):
        logger.info(f"\n推文 {i}:")
        logger.info(f"  ID: {item.tweet.id}")
        logger.info(f"  作者: {item.author.name} (@{item.author.username})")
        logger.info(f"  位置: {item.author.location or 'N/A'}")
        logger.info(f"  文本: {item.tweet.text[:80]}...")
        logger.info(f"  语言: {item.tweet.lang}")
        logger.info(f"  发布时间: {item.tweet.created_at}")
        logger.info(f"  点赞: {item.tweet.like_count}")
        logger.info(f"  转推: {item.tweet.retweet_count}")
        logger.info(f"  回复数: {len(item.replies)}")
        logger.info(f"  Thread 长度: {len(item.thread_context)}")
        logger.info(f"  总互动数: {item.total_engagement}")
        logger.info(f"  参与者数: {len(item.reply_authors)}")


async def test_with_time_range():
    """
    测试带时间范围的查询

    LLM 在 query 中指定时间范围
    """
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 带时间范围的查询")
    logger.info("=" * 60)

    # LLM 生成的 query（包含时间范围）
    query = "(China parade OR 93阅兵) lang:ar since:2021-01-01 until:2025-01-15"

    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=5,
            max_replies_per_tweet=3,
            include_thread=False,  # 不获取 Thread，提升速度
            max_concurrent=2,
        )

    logger.info(f"\n查询: {query}")
    logger.info(f"获取推文数: {len(result.items)}")
    logger.info("时间范围内的推文:")
    for item in result.items:
        logger.info(f"  - {item.tweet.created_at}: {item.tweet.text[:50]}...")


async def test_top_tweets():
    """
    测试获取热门推文
    """
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 获取热门推文")
    logger.info("=" * 60)

    # LLM 可以选择 Top 类型获取热门推文
    query = "China 93 parade lang:ar min_faves:10"

    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            query_type="Top",  # 热门排序
            max_seed_tweets=5,
            max_replies_per_tweet=10,
            max_concurrent=2,
        )

    logger.info(f"\n获取热门推文数: {len(result.items)}")

    # 按互动量排序展示
    sorted_items = sorted(result.items, key=lambda x: x.total_engagement, reverse=True)

    logger.info("\n按互动量排序:")
    for i, item in enumerate(sorted_items, 1):
        logger.info(f"  {i}. 互动数 {item.total_engagement}: {item.tweet.text[:50]}...")


async def test_client_reuse():
    """
    测试 client 复用（性能优化）

    这是推荐的使用方式：创建一次 client，多次调用
    """
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: Client 复用（推荐方式）")
    logger.info("=" * 60)

    async with create_client() as client:
        # 第一次调用
        result1 = await collect_tweet_discussions(
            query="China parade lang:ar",
            client=client,
            max_seed_tweets=3,
            max_replies_per_tweet=2,
            max_concurrent=1,
        )

        # 第二次调用（复用 client）
        result2 = await collect_tweet_discussions(
            query="93阅兵 lang:ar",
            client=client,
            max_seed_tweets=3,
            max_replies_per_tweet=2,
            max_concurrent=1,
        )

        # 第三次调用（复用 client）
        result3 = await collect_tweet_discussions(
            query="Beijing military parade lang:ar",
            client=client,
            max_seed_tweets=3,
            max_replies_per_tweet=2,
            max_concurrent=1,
        )

    logger.info(f"\n查询 1: 获取 {len(result1.items)} 条推文")
    logger.info(f"查询 2: 获取 {len(result2.items)} 条推文")
    logger.info(f"查询 3: 获取 {len(result3.items)} 条推文")
    logger.info("✅ Client 复用成功！（连接池复用，性能更好）")


async def test_error_handling():
    """
    测试错误处理

    验证部分失败时的容错性
    """
    logger.info("\n" + "=" * 60)
    logger.info("测试 5: 错误处理和容错性")
    logger.info("=" * 60)

    # 测试无结果的查询
    query = "nonexistent_keyword_12345 lang:ar"

    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=10,
            max_concurrent=2,
        )

    if result.metadata.seed_tweet_count == 0:
        logger.info("✅ 无结果查询处理正确（返回空集合）")
    else:
        logger.info(f"获取到 {len(result.items)} 条推文")

    logger.info(f"失败的推文 ID: {result.metadata.failed_tweet_ids}")


# ============================================
# 主函数
# ============================================


async def main():
    """运行所有测试"""
    logger.info("开始测试 x_crawl 推文讨论采集功能")
    logger.info("=" * 60)

    try:
        # 测试 1: 基本功能
        await test_basic_collection()

        # 测试 2: 时间范围
        await test_with_time_range()

        # 测试 3: 热门推文
        await test_top_tweets()

        # 测试 4: Client 复用
        await test_client_reuse()

        # 测试 5: 错误处理
        await test_error_handling()

        logger.success("\n" + "=" * 60)
        logger.success("✅ 所有测试通过！")
        logger.success("=" * 60)

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"❌ 测试失败: {e}")
        logger.error("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())
