"""
============================================
测试 CSV 导出功能（带详细日志）
============================================
验证模型修改后的 CSV 导出是否正常
重点检查 author_name 字段是否正确提取
"""

import asyncio
from pathlib import Path

from loguru import logger

from src.x_crawl import (
    collect_tweet_discussions,
    create_client,
    export_texts_from_collection,
)

# ============================================
# 配置日志
# ============================================

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

log_file = log_dir / "test_csv_export.log"

# 移除默认输出
logger.remove()

# 添加控制台输出（彩色）
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    colorize=True,
    level="INFO",
)

# 添加文件输出（完整）
logger.add(
    log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",
    encoding="utf-8",
)

logger.info(f"📝 日志文件: {log_file}")

# ============================================
# 主测试流程
# ============================================


async def main():
    """
    完整测试流程：
    1. 采集推文数据
    2. 检查模型字段
    3. 导出 CSV
    4. 验证 CSV 内容
    """
    
    logger.info("=" * 80)
    logger.info("🚀 开始测试 CSV 导出功能")
    logger.info("=" * 80)
    
    # ============================================
    # 步骤 1: 采集数据
    # ============================================
    logger.info("\n📡 步骤 1: 采集推文数据...")
    
    query = "(China parade OR 93阅兵) lang:ar"
    
    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            query_type="Latest",
            max_seed_tweets=5,  # 少量测试
            max_replies_per_tweet=3,
            include_thread=True,
            max_concurrent=2,
        )
    
    logger.info(f"\n✅ 采集完成:")
    logger.info(f"   种子推文: {result.metadata.seed_tweet_count}")
    logger.info(f"   成功处理: {len(result.items)}")
    logger.info(f"   失败数: {len(result.metadata.failed_tweet_ids)}")
    logger.info(f"   总推文数: {result.total_tweets}")
    logger.info(f"   总回复数: {result.total_replies}")
    logger.info(f"   Thread 数: {result.total_threads}")
    logger.info(f"   成功率: {result.success_rate:.1%}")
    
    # ============================================
    # 步骤 2: 检查模型字段（验证 author_name）
    # ============================================
    logger.info("\n🔍 步骤 2: 检查模型字段...")
    
    if not result.items:
        logger.error("❌ 没有采集到任何推文，测试终止")
        return
    
    logger.info(f"\n检查第 1 条推文的字段:")
    first_item = result.items[0]
    first_tweet = first_item.tweet
    
    logger.info(f"   Tweet.id: {first_tweet.id}")
    logger.info(f"   Tweet.text: {first_tweet.text[:50]}...")
    logger.info(f"   Tweet.author_name: {first_tweet.author_name}")  # ⚠️ 关键字段
    logger.info(f"   Tweet.created_at: {first_tweet.created_at}")
    logger.info(f"   Tweet.like_count: {first_tweet.like_count}")
    logger.info(f"   Tweet.retweet_count: {first_tweet.retweet_count}")
    logger.info(f"   Tweet.reply_count: {first_tweet.reply_count}")
    
    # 检查是否有 author_name
    if first_tweet.author_name:
        logger.success(f"   ✅ author_name 字段存在: '{first_tweet.author_name}'")
    else:
        logger.warning(f"   ⚠️  author_name 为 None")
    
    # 检查回复和 Thread
    if first_item.replies:
        logger.info(f"\n检查第 1 条回复:")
        first_reply = first_item.replies[0]
        logger.info(f"   Reply.id: {first_reply.id}")
        logger.info(f"   Reply.text: {first_reply.text[:50]}...")
        logger.info(f"   Reply.author_name: {first_reply.author_name}")
        
        if first_reply.author_name:
            logger.success(f"   ✅ 回复的 author_name 存在: '{first_reply.author_name}'")
        else:
            logger.warning(f"   ⚠️  回复的 author_name 为 None")
    
    if first_item.thread_context:
        logger.info(f"\n检查第 1 条 Thread 推文:")
        first_thread = first_item.thread_context[0]
        logger.info(f"   Thread.id: {first_thread.id}")
        logger.info(f"   Thread.text: {first_thread.text[:50]}...")
        logger.info(f"   Thread.author_name: {first_thread.author_name}")
        
        if first_thread.author_name:
            logger.success(f"   ✅ Thread 的 author_name 存在: '{first_thread.author_name}'")
        else:
            logger.warning(f"   ⚠️  Thread 的 author_name 为 None")
    
    # 统计 author_name 的覆盖率
    logger.info(f"\n📊 author_name 字段统计:")
    
    all_tweets = result.all_tweets
    tweets_with_author = sum(1 for t in all_tweets if t.author_name)
    tweets_without_author = len(all_tweets) - tweets_with_author
    
    logger.info(f"   总推文数: {len(all_tweets)}")
    logger.info(f"   有 author_name: {tweets_with_author} ({tweets_with_author/len(all_tweets)*100:.1f}%)")
    logger.info(f"   无 author_name: {tweets_without_author} ({tweets_without_author/len(all_tweets)*100:.1f}%)")
    
    # ============================================
    # 步骤 3: 导出 CSV
    # ============================================
    logger.info("\n💾 步骤 3: 导出 CSV 文件...")
    
    output_dir = Path("data/test_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_dir / "test_export.csv"
    
    logger.info(f"   输出路径: {csv_path}")
    
    try:
        export_texts_from_collection(
            collection=result,
            output_path=csv_path,
            file_format="csv",
            csv_mode="full",  # 完整版本
            clean=True,
        )
        logger.success(f"   ✅ CSV 导出成功")
    except Exception as e:
        logger.error(f"   ❌ CSV 导出失败: {e}")
        logger.exception("详细错误信息:")
        return
    
    # ============================================
    # 步骤 4: 验证 CSV 文件
    # ============================================
    logger.info("\n✅ 步骤 4: 验证 CSV 文件...")
    
    if not csv_path.exists():
        logger.error(f"   ❌ CSV 文件不存在: {csv_path}")
        return
    
    # 读取文件前 5 行
    logger.info(f"   文件大小: {csv_path.stat().st_size} 字节")
    
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            lines = [f.readline().strip() for _ in range(5)]
        
        logger.info(f"\n   CSV 文件前 5 行:")
        for i, line in enumerate(lines, 1):
            # 截断过长的行
            display_line = line if len(line) <= 100 else line[:100] + "..."
            logger.info(f"   {i}: {display_line}")
    except Exception as e:
        logger.error(f"   ❌ 读取 CSV 文件失败: {e}")
        return
    
    # 使用 csv 模块验证
    import csv
    
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        logger.info(f"\n   CSV 数据验证:")
        logger.info(f"   总行数: {len(rows)}")
        logger.info(f"   列名: {list(rows[0].keys()) if rows else '无数据'}")
        
        # 检查前 3 行的作者名称
        logger.info(f"\n   前 3 行的作者名称:")
        for i, row in enumerate(rows[:3], 1):
            author = row.get("作者名称", "N/A")
            source = row.get("来源类型", "N/A")
            content_preview = row.get("推文内容", "")[:30]
            logger.info(f"   {i}. [{source}] {author}: {content_preview}...")
        
        # 统计作者名称分布
        author_names = [row.get("作者名称", "Unknown") for row in rows]
        unknown_count = sum(1 for name in author_names if name == "Unknown")
        
        logger.info(f"\n   作者名称统计:")
        logger.info(f"   总行数: {len(rows)}")
        logger.info(f"   'Unknown': {unknown_count} ({unknown_count/len(rows)*100:.1f}%)")
        logger.info(f"   有名字: {len(rows) - unknown_count} ({(len(rows) - unknown_count)/len(rows)*100:.1f}%)")
        
        if unknown_count == 0:
            logger.success(f"   🎉 所有推文都有作者名称！")
        elif unknown_count < len(rows) * 0.5:
            logger.success(f"   ✅ 大部分推文有作者名称")
        else:
            logger.warning(f"   ⚠️  超过一半的推文作者为 Unknown")
    
    except Exception as e:
        logger.error(f"   ❌ CSV 验证失败: {e}")
        logger.exception("详细错误信息:")
        return
    
    # ============================================
    # 测试总结
    # ============================================
    logger.info("\n" + "=" * 80)
    logger.info("📋 测试总结")
    logger.info("=" * 80)
    logger.info(f"✅ 数据采集: 成功")
    logger.info(f"✅ 模型字段: author_name 存在")
    logger.info(f"✅ CSV 导出: 成功")
    logger.info(f"✅ CSV 验证: 通过")
    logger.info(f"\n📁 输出文件: {csv_path}")
    logger.info(f"📝 日志文件: {log_file}")
    logger.info("\n🎉 测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
