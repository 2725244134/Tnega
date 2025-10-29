"""
============================================
存储功能测试（使用 Mock 数据）
============================================
测试推文数据的保存和加载，不依赖真实 API
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.x_crawl import (
    Tweet,
    User,
    SearchResults,
    save_tweets_json,
    save_tweets_jsonl,
    save_search_results_json,
    save_results,
    load_tweets_json,
    load_tweets_jsonl,
    load_search_results_json,
)
from src.x_crawl.models import SearchMetadata


def create_mock_tweet(tweet_id: str, text: str) -> Tweet:
    """创建 mock 推文"""
    return Tweet(
        id=tweet_id,
        text=text,
        created_at=datetime.now(),
        author_id="12345",
        like_count=100,
        retweet_count=50,
        reply_count=10,
        quote_count=5
    )


def create_mock_user(user_id: str, username: str) -> User:
    """创建 mock 用户"""
    return User(
        id=user_id,
        username=username,
        name=f"Test User {username}",
        created_at=datetime.now(),
        followers_count=10000,
        following_count=500,
        tweet_count=1000
    )


def test_json_storage():
    """测试 JSON 存储"""
    print("\n" + "=" * 60)
    print("🧪 测试：JSON 存储")
    print("=" * 60)
    
    # 创建 mock 数据
    tweets = [
        create_mock_tweet("1", "这是第一条推文"),
        create_mock_tweet("2", "这是第二条推文"),
        create_mock_tweet("3", "这是第三条推文"),
    ]
    
    # 保存
    print("\n▶️ 步骤 1：保存推文为 JSON")
    path = save_tweets_json(tweets, "mock_tweets.json")
    print(f"✅ 保存成功: {path}")
    
    # 加载
    print("\n▶️ 步骤 2：从 JSON 加载")
    loaded = load_tweets_json(path)
    print(f"✅ 加载成功: {len(loaded)} 条推文")
    
    # 验证
    print("\n▶️ 步骤 3：验证数据一致性")
    assert len(loaded) == len(tweets)
    assert loaded[0].id == tweets[0].id
    assert loaded[0].text == tweets[0].text
    assert loaded[1].like_count == tweets[1].like_count
    print("✅ 数据一致性检查通过")
    
    print("\n" + "=" * 60)


def test_jsonl_storage():
    """测试 JSONL 存储"""
    print("\n" + "=" * 60)
    print("🧪 测试：JSONL 存储")
    print("=" * 60)
    
    # 创建 mock 数据
    batch1 = [
        create_mock_tweet("10", "批次 1 - 推文 A"),
        create_mock_tweet("11", "批次 1 - 推文 B"),
    ]
    batch2 = [
        create_mock_tweet("20", "批次 2 - 推文 C"),
        create_mock_tweet("21", "批次 2 - 推文 D"),
    ]
    
    # 保存第一批
    print("\n▶️ 步骤 1：保存第一批推文")
    path = save_tweets_jsonl(batch1, "mock_tweets.jsonl", append=False)
    print(f"✅ 保存成功: {path}")
    
    # 追加第二批
    print("\n▶️ 步骤 2：追加第二批推文")
    save_tweets_jsonl(batch2, "mock_tweets.jsonl", append=True)
    print("✅ 追加成功")
    
    # 加载全部
    print("\n▶️ 步骤 3：加载全部推文")
    loaded = load_tweets_jsonl(path)
    print(f"✅ 加载成功: {len(loaded)} 条推文")
    
    # 验证
    print("\n▶️ 步骤 4：验证追加模式")
    assert len(loaded) == 4
    assert loaded[0].id == "10"
    assert loaded[2].id == "20"
    print("✅ 追加模式验证通过")
    
    print("\n" + "=" * 60)


def test_search_results_storage():
    """测试完整搜索结果存储"""
    print("\n" + "=" * 60)
    print("🧪 测试：搜索结果存储")
    print("=" * 60)
    
    # 创建 mock 搜索结果
    tweets = [
        create_mock_tweet("100", "AI 相关推文 1"),
        create_mock_tweet("101", "AI 相关推文 2"),
    ]
    users = {
        "12345": create_mock_user("12345", "alice"),
        "67890": create_mock_user("67890", "bob"),
    }
    
    metadata = SearchMetadata(
        query="AI agents",
        source="search_all",
        page_count=1,
        total_collected=len(tweets),
    )

    results = SearchResults(
        tweets=tweets,
        users=users,
        media={},
        result_count=2,
        total_count=2,
        next_token="abc123",
        metadata=metadata,
    )
    
    # 保存
    print("\n▶️ 步骤 1：保存搜索结果")
    path = save_search_results_json(results, "mock_results.json")
    print(f"✅ 保存成功: {path}")
    
    # 加载
    print("\n▶️ 步骤 2：加载搜索结果")
    loaded = load_search_results_json(path)
    print(f"✅ 加载成功: {loaded.result_count} 条推文")
    
    # 验证
    print("\n▶️ 步骤 3：验证完整数据")
    assert len(loaded.tweets) == 2
    assert len(loaded.users) == 2
    assert loaded.next_token == "abc123"
    assert "12345" in loaded.users
    assert loaded.users["12345"].username == "alice"
    assert loaded.metadata and loaded.metadata.query == "AI agents"
    print("✅ 完整数据验证通过")
    
    print("\n" + "=" * 60)


def test_convenience_function():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("🧪 测试：便捷保存函数")
    print("=" * 60)
    
    # 创建数据
    tweets = [create_mock_tweet("200", "测试查询结果")]
    results = SearchResults(
        tweets=tweets,
        users={},
        media={},
        result_count=1
    )
    
    # 测试自动命名 - JSON
    print("\n▶️ 步骤 1：自动命名保存 (JSON)")
    path1 = save_results(results, "AI agents 2024", format="json")
    print(f"✅ JSON 文件: {path1.name}")
    
    # 测试自动命名 - JSONL
    print("\n▶️ 步骤 2：自动命名保存 (JSONL)")
    path2 = save_results(results, "Web3 developer", format="jsonl")
    print(f"✅ JSONL 文件: {path2.name}")
    
    # 验证文件名清理
    print("\n▶️ 步骤 3：验证文件名清理")
    assert "AI_agents_2024" in path1.name
    assert "Web3_developer" in path2.name
    print("✅ 文件名清理正确")
    
    print("\n" + "=" * 60)


def test_data_persistence():
    """测试数据持久化"""
    print("\n" + "=" * 60)
    print("🧪 测试：数据持久化")
    print("=" * 60)
    
    # 创建复杂数据
    tweet = create_mock_tweet("999", "包含特殊字符: 😀 #AI @user https://example.com")
    
    print("\n▶️ 步骤 1：保存特殊字符推文")
    path = save_tweets_json([tweet], "special_chars.json")
    
    print("\n▶️ 步骤 2：加载并验证")
    loaded = load_tweets_json(path)
    
    assert loaded[0].text == tweet.text
    print(f"✅ 原文: {tweet.text}")
    print(f"✅ 加载: {loaded[0].text}")
    print("✅ 特殊字符保留完整")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("📦 存储模块完整测试")
    print("=" * 60)
    
    try:
        test_json_storage()
        test_jsonl_storage()
        test_search_results_storage()
        test_convenience_function()
        test_data_persistence()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        print("\n📁 测试文件保存在: data/ 目录")
        print("\n🎯 存储功能就绪，可以开始使用！")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
