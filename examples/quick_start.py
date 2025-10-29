"""
============================================
快速开始：主题抓取 + 存储
============================================
演示完整的抓取和存储流程
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.x_crawl import TwitterCrawler, save_results


async def quick_start():
    """快速开始示例"""
    print("\n" + "=" * 60)
    print("🚀 快速开始：主题抓取 + 自动存储")
    print("=" * 60)
    
    crawler = TwitterCrawler()
    
    try:
        # 步骤 1：搜索主题
        print("\n▶️ 步骤 1：搜索推文")
        query = "python programming"
        print(f"   查询: {query}")
        
        try:
            results = await crawler.search_all_tweets(
                query=query,
                max_results=10
            )
            print(f"   ✅ 找到 {results.result_count} 条推文")
            
            # 步骤 2：自动保存
            print("\n▶️ 步骤 2：保存数据")
            path = save_results(results, query, format="json")
            print(f"   ✅ 文件: {path}")
            
            # 步骤 3：展示内容
            print("\n▶️ 步骤 3：预览内容")
            for i, tweet in enumerate(results.tweets[:3], 1):
                print(f"\n   {i}. {tweet.text[:80]}...")
                print(f"      👍 {tweet.like_count or 0:,} | 🔄 {tweet.retweet_count or 0:,}")
            
            if results.next_token:
                print(f"\n   💡 提示：有更多结果可用 (next_token 已保存)")
            
        except Exception as e:
            if "429" in str(e):
                print(f"   ⚠️ 速率限制：请稍后再试")
            elif "Academic Research" in str(e):
                print(f"   ⚠️ 需要 Academic Research 权限")
                print(f"   💡 尝试使用其他 API（如 get_tweets）")
            else:
                print(f"   ❌ 错误: {e}")
        
    finally:
        await crawler.close()
    
    print("\n" + "=" * 60)
    print("✅ 完成！数据已保存到 data/ 目录")
    print("=" * 60)


async def alternative_demo():
    """备用演示（使用不需要特殊权限的 API）"""
    print("\n" + "=" * 60)
    print("🎯 备用方案：批量获取推文")
    print("=" * 60)
    
    crawler = TwitterCrawler()
    
    try:
        # 使用 get_tweets（不需要特殊权限）
        print("\n▶️ 获取特定推文")
        tweet_ids = ["20", "21", "22"]  # Twitter 早期推文
        
        try:
            results = await crawler.get_tweets(tweet_ids)
            print(f"   ✅ 获取到 {len(results.tweets)} 条推文")
            
            # 保存
            from src.x_crawl import save_tweets_json
            path = save_tweets_json(results.tweets, "early_tweets.json")
            print(f"   ✅ 保存到: {path}")
            
            # 展示
            for tweet in results.tweets:
                print(f"\n   📄 {tweet.text}")
                print(f"      点赞: {tweet.like_count:,} | 时间: {tweet.created_at}")
            
        except Exception as e:
            if "429" in str(e):
                print(f"   ⚠️ 速率限制：请等待 15 分钟后重试")
            else:
                print(f"   ❌ 错误: {e}")
        
    finally:
        await crawler.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 尝试主要方法
    asyncio.run(quick_start())
    
    # 如果主要方法失败，运行备用方案
    print("\n" + "-" * 60)
    asyncio.run(alternative_demo())
