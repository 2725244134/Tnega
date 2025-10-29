"""
============================================
抓取 93 阅兵相关推文（真实数据）
============================================
使用英语查询词搜索中国 2025 年纪念抗战胜利 70 周年阅兵相关内容
注意：由于 search_all_tweets 需要 Academic Research 权限，
     我们改用其他可用的 API 方法
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.x_crawl import TwitterCrawler, save_results, save_tweets_jsonl


async def crawl_recent_parade_topics():
    """抓取 93 阅兵相关推文（使用 search_recent_tweets，搜索最近的相关内容）"""
    print("\n" + "=" * 60)
    print("🎯 任务：搜索中国阅兵相关推文（最近 7 天）")
    print("=" * 60)
    print("⚠️  注意：使用 search_recent_tweets 只能搜索最近 7 天的推文")
    print("💡 提示：如果需要 2015 年的历史数据，需要 Academic Research 权限")
    
    # 英语查询词组合（搜索当前相关话题）
    queries = [
        "China military parade",
        "China Victory Day",
        "Beijing parade",
    ]
    
    crawler = TwitterCrawler()
    
    try:
        for query in queries:
            print(f"\n▶️ 查询: {query}")
            print("-" * 60)
            
            try:
                # 使用 search_recent_tweets（最近 7 天，不需要特殊权限）
                results = await crawler.search_recent_tweets(
                    query=query,
                    max_results=50  # 先获取 50 条看看效果
                )
                
                if results.result_count == 0:
                    print(f"⚠️ 没有找到匹配的推文（可能最近 7 天没有相关内容）")
                    continue
                
                print(f"✅ 找到 {results.result_count} 条推文")
                
                # 输出前 5 条推文概览
                print("\n📋 推文预览（前 5 条）：")
                for i, tweet in enumerate(results.tweets[:5], 1):
                    author = results.users.get(tweet.author_id)
                    author_name = f"@{author.username}" if author else "未知用户"
                    
                    # 截断长文本
                    text_preview = tweet.text[:80] + "..." if len(tweet.text) > 80 else tweet.text
                    
                    print(f"\n{i}. {author_name}")
                    print(f"   {text_preview}")
                    print(f"   ❤️ {tweet.like_count:,} | 🔄 {tweet.retweet_count:,} | 💬 {tweet.reply_count:,}")
                    print(f"   🕒 {tweet.created_at}")
                
                # 统计数据
                total_likes = sum(t.like_count or 0 for t in results.tweets)
                total_retweets = sum(t.retweet_count or 0 for t in results.tweets)
                total_replies = sum(t.reply_count or 0 for t in results.tweets)
                
                print(f"\n📊 统计数据：")
                print(f"   推文数: {results.result_count}")
                print(f"   用户数: {len(results.users)}")
                print(f"   总点赞: {total_likes:,}")
                print(f"   总转发: {total_retweets:,}")
                print(f"   总回复: {total_replies:,}")
                
                # 保存数据
                json_path = save_results(results, f"China_parade_{query.replace(' ', '_')}")
                jsonl_path = save_tweets_jsonl(results.tweets, f"parade_{query.replace(' ', '_')}.jsonl")
                
                print(f"\n💾 数据已保存：")
                print(f"   JSON:  {json_path}")
                print(f"   JSONL: {jsonl_path}")
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    print("❌ 速率限制（429）：API 调用过于频繁")
                    print("💡 建议：等待 15 分钟后重试")
                    break
                elif "403" in error_msg:
                    print("❌ 权限不足（403）")
                    print("💡 建议：检查 API 密钥权限")
                    break
                else:
                    print(f"❌ 错误: {error_msg}")
    
    finally:
        await crawler.close()


async def demonstrate_with_known_tweets():
    """
    演示如何使用已知推文 ID 获取真实数据
    （这种方法可以获取历史推文，不受 7 天限制）
    """
    print("\n" + "=" * 60)
    print("🎯 方案 2：使用已知推文 ID 获取数据")
    print("=" * 60)
    
    crawler = TwitterCrawler()
    
    try:
        # 获取 Twitter 历史著名推文演示 API 功能
        print("\n▶️ 获取 Twitter 历史推文（演示 API 功能）...")
        
        # Jack Dorsey 第一条推文
        demo_ids = ["20"]
        
        results = await crawler.get_tweets(demo_ids)
        
        if results.result_count > 0:
            print(f"✅ API 工作正常！成功获取 {results.result_count} 条推文")
            
            for tweet in results.tweets:
                author = results.users.get(tweet.author_id)
                print(f"\n📄 推文内容: {tweet.text}")
                print(f"   创建时间: {tweet.created_at}")
                print(f"   点赞数: {tweet.like_count:,}")
                print(f"   转发数: {tweet.retweet_count:,}")
                if author:
                    print(f"   作者: @{author.username} ({author.name})")
            
            # 保存示例数据
            save_path = save_tweets_jsonl(results.tweets, "api_demo.jsonl")
            print(f"\n💾 演示数据已保存: {save_path}")
            
            print("\n✅ API 功能验证通过！")
        
    except Exception as e:
        if "429" in str(e):
            print("❌ 速率限制：请等待 15 分钟后重试")
        else:
            print(f"❌ 错误: {e}")
    
    finally:
        await crawler.close()


async def main():
    """主函数"""
    print("\n🚀 开始真实数据抓取")
    print("=" * 60)
    
    # 方案 1：搜索最近 7 天的相关话题
    await crawl_recent_parade_topics()
    
    # 方案 2：演示使用已知 ID 获取历史数据
    print("\n" + "=" * 60)
    await demonstrate_with_known_tweets()
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    print("\n要获取 93 阅兵（2015年）的真实推文数据，你需要：")
    print("\n选项 A - 使用已知推文 ID：")
    print("  1. 在 Twitter 网页搜索 'China military parade 2015'")
    print("  2. 找到相关推文，从 URL 复制推文 ID")
    print("     例如：twitter.com/user/status/123456 → ID 是 123456")
    print("  3. 添加到脚本中使用 get_tweets(ids) 获取")
    print("\n选项 B - 申请 Academic Research 权限：")
    print("  1. 访问 https://developer.twitter.com/en/portal/petition/academic/is-it-right-for-you")
    print("  2. 申请 Academic Research 权限（需要学术/研究用途）")
    print("  3. 获得权限后使用 search_all_tweets() 搜索历史数据")
    print("\n选项 C - 搜索最近 7 天的类似话题：")
    print("  1. 使用 search_recent_tweets()（已在上面演示）")
    print("  2. 可以找到最近的相关讨论和话题")
    print("\n选项 C - 使用现有数据集：")
    print("  1. 寻找已有的 93 阅兵推文数据集")
    print("  2. 导入到我们的系统中进行分析")


if __name__ == "__main__":
    asyncio.run(main())

