"""
============================================
存储功能测试
============================================
测试推文数据的保存和加载
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.x_crawl import (
    TwitterCrawler,
    save_tweets_json,
    save_tweets_jsonl,
    save_search_results_json,
    save_results,
    load_tweets_json,
    load_tweets_jsonl,
)


async def test_save_and_load():
    """测试保存和加载推文"""
    print("\n" + "=" * 60)
    print("🧪 测试：存储功能")
    print("=" * 60)
    
    crawler = TwitterCrawler()
    
    try:
        # 1. 获取一些推文
        print("\n▶️ 步骤 1：获取推文数据")
        results = await crawler.get_tweets(["20", "21"])
        print(f"✅ 获取到 {len(results.tweets)} 条推文")
        
        # 2. 测试 JSON 格式保存
        print("\n▶️ 步骤 2：保存为 JSON 格式")
        json_path = save_tweets_json(results.tweets, "test_tweets.json")
        print(f"✅ JSON 文件: {json_path}")
        
        # 3. 测试 JSONL 格式保存
        print("\n▶️ 步骤 3：保存为 JSONL 格式")
        jsonl_path = save_tweets_jsonl(results.tweets, "test_tweets.jsonl")
        print(f"✅ JSONL 文件: {jsonl_path}")
        
        # 4. 测试完整搜索结果保存
        print("\n▶️ 步骤 4：保存完整搜索结果")
        full_path = save_search_results_json(results, "test_results.json")
        print(f"✅ 完整结果: {full_path}")
        
        # 5. 测试便捷保存函数
        print("\n▶️ 步骤 5：使用便捷函数保存")
        auto_path = save_results(results, "test query", format="json")
        print(f"✅ 自动命名: {auto_path}")
        
        # 6. 测试加载
        print("\n▶️ 步骤 6：加载数据验证")
        loaded_tweets = load_tweets_json(json_path)
        print(f"✅ 从 JSON 加载: {len(loaded_tweets)} 条推文")
        
        loaded_jsonl = load_tweets_jsonl(jsonl_path)
        print(f"✅ 从 JSONL 加载: {len(loaded_jsonl)} 条推文")
        
        # 7. 验证数据一致性
        print("\n▶️ 步骤 7：验证数据一致性")
        assert loaded_tweets[0].id == results.tweets[0].id
        assert loaded_tweets[0].text == results.tweets[0].text
        print("✅ 数据一致性检查通过")
        
        # 8. 测试追加模式
        print("\n▶️ 步骤 8：测试 JSONL 追加模式")
        save_tweets_jsonl([results.tweets[0]], "test_append.jsonl", append=False)
        save_tweets_jsonl([results.tweets[1]], "test_append.jsonl", append=True)
        appended = load_tweets_jsonl(Path("data/test_append.jsonl"))
        print(f"✅ 追加后共 {len(appended)} 条推文")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await crawler.close()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    print(f"\n📁 所有文件保存在: data/ 目录")


async def demo_workflow():
    """演示完整工作流"""
    print("\n" + "=" * 60)
    print("📝 演示：主题抓取 → 存储工作流")
    print("=" * 60)
    
    crawler = TwitterCrawler()
    
    try:
        print("\n▶️ 场景：抓取推文并保存")
        
        # 获取推文
        results = await crawler.get_tweets(["20"])
        print(f"✅ 抓取: {len(results.tweets)} 条推文")
        
        # 自动保存
        path = save_results(results, "Twitter 第一条推文", format="json")
        print(f"✅ 保存: {path}")
        
        # 展示推文内容
        for tweet in results.tweets:
            print(f"\n📄 推文内容:")
            print(f"   ID: {tweet.id}")
            print(f"   文本: {tweet.text}")
            print(f"   点赞: {tweet.like_count:,}")
            print(f"   转发: {tweet.retweet_count:,}")
        
    finally:
        await crawler.close()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_save_and_load())
    
    # 运行演示
    asyncio.run(demo_workflow())
