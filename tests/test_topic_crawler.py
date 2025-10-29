"""
============================================
主题抓取 API 测试
============================================
测试面向主题抓取的核心 API
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.x_crawl import TwitterCrawler


async def test_search_all_tweets():
    """测试完整历史搜索（需要 Academic Research 权限）"""
    print("\n▶️ 测试：搜索完整历史推文")
    
    crawler = TwitterCrawler()
    
    try:
        # 搜索关于 "python" 的推文（过去 30 天）
        results = await crawler.search_all_tweets(
            query="python",
            max_results=10
        )
        
        print(f"✅ 搜索结果：{results.result_count} 条推文")
        
        if results.tweets:
            first = results.tweets[0]
            print(f"   示例推文: {first.text[:60]}...")
            
        if results.next_token:
            print(f"   下一页令牌: {results.next_token[:30]}...")
        
    except Exception as e:
        print(f"⚠️ 搜索失败（可能需要 Academic Research 权限）: {e}")
    
    finally:
        await crawler.close()


async def test_get_tweet():
    """测试获取单条推文详情"""
    print("\n▶️ 测试：获取推文详情")
    
    crawler = TwitterCrawler()
    
    try:
        # 获取 Twitter 第一条推文
        tweet = await crawler.get_tweet("20")
        
        print(f"✅ 推文内容: {tweet.text}")
        print(f"   点赞: {tweet.like_count:,}, 转发: {tweet.retweet_count:,}")
        
    finally:
        await crawler.close()


async def test_get_tweets_batch():
    """测试批量获取推文"""
    print("\n▶️ 测试：批量获取推文")
    
    crawler = TwitterCrawler()
    
    try:
        # 批量获取多条推文
        results = await crawler.get_tweets([
            "20",  # Twitter 第一条推文
            "21",  # 第二条推文
        ])
        
        print(f"✅ 获取到 {results.result_count} 条推文")
        
        for tweet in results.tweets:
            print(f"   - {tweet.text[:50]}...")
        
    finally:
        await crawler.close()


async def test_fetch_user_by_id():
    """测试获取用户信息"""
    print("\n▶️ 测试：获取用户信息")
    
    crawler = TwitterCrawler()
    
    try:
        # 获取 Jack Dorsey 的用户信息
        user = await crawler.fetch_user_by_id("12")
        
        print(f"✅ 用户: @{user.username}")
        print(f"   粉丝数: {user.followers_count:,}")
        
    except Exception as e:
        print(f"⚠️ 获取失败（可能达到速率限制）: {e}")
        
    finally:
        await crawler.close()


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 主题抓取 API 测试")
    print("=" * 60)
    
    # 测试核心 API
    await test_get_tweet()
    await test_get_tweets_batch()
    await test_fetch_user_by_id()
    await test_search_all_tweets()  # 可能失败（需要特殊权限）
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
