"""
============================================
数据模型测试用例
============================================
验证 Pydantic 模型的类型安全和序列化能力
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from src.x_crawl.models import (
    User,
    Tweet,
    Media,
    Timeline,
    SearchResults,
    UserProfile,
    SearchMetadata,
)


def test_user_model():
    """测试 User 模型的基本功能"""
    user = User(
        id="1234567890",
        username="jack",
        name="Jack Dorsey",
        created_at=datetime(2006, 3, 21, tzinfo=timezone.utc),
        description="Block head",
        verified=True,
        followers_count=6_000_000,
        following_count=4500,
        tweet_count=28_000,
    )
    
    assert user.id == "1234567890"
    assert user.username == "jack"
    assert user.followers_count == 6_000_000
    
    # 测试序列化
    data = user.model_dump()
    assert data["username"] == "jack"
    
    # 测试 JSON 序列化
    json_str = user.model_dump_json()
    assert "jack" in json_str


def test_tweet_model():
    """测试 Tweet 模型的基本功能"""
    tweet = Tweet(
        id="1234567890123456789",
        text="just setting up my twttr",
        created_at=datetime(2006, 3, 21, 20, 50, 14, tzinfo=timezone.utc),
        author_id="12",
        retweet_count=150_000,
        like_count=250_000,
        reply_count=50_000,
        lang="en",
    )
    
    assert tweet.id == "1234567890123456789"
    assert tweet.text == "just setting up my twttr"
    assert tweet.like_count == 250_000
    assert tweet.conversation_id is None
    
    # 测试序列化
    data = tweet.model_dump()
    assert data["author_id"] == "12"


def test_media_model():
    """测试 Media 模型"""
    media = Media(
        media_key="3_1234567890",
        type="photo",
        url="https://pbs.twimg.com/media/example.jpg",
        width=1920,
        height=1080,
    )
    
    assert media.type == "photo"
    assert media.width == 1920
    
    # 测试视频类型
    video = Media(
        media_key="13_9876543210",
        type="video",
        preview_image_url="https://pbs.twimg.com/media/preview.jpg",
        duration_ms=30_000,
    )
    
    assert video.type == "video"
    assert video.duration_ms == 30_000


def test_timeline_model():
    """测试 Timeline 容器"""
    tweet1 = Tweet(
        id="111",
        text="First tweet",
        created_at=datetime.now(timezone.utc),
        author_id="100",
    )
    
    tweet2 = Tweet(
        id="222",
        text="Second tweet",
        created_at=datetime.now(timezone.utc),
        author_id="100",
    )
    
    user = User(
        id="100",
        username="testuser",
        name="Test User",
    )
    
    timeline = Timeline(
        tweets=[tweet1, tweet2],
        users={"100": user},
        oldest_id="111",
        newest_id="222",
        result_count=2,
    )
    
    assert len(timeline.tweets) == 2
    assert timeline.result_count == 2
    assert "100" in timeline.users


def test_search_results_model():
    """测试 SearchResults 容器"""
    metadata = SearchMetadata(
        query="python",
        source="search_recent",
        page_count=1,
    )
    results = SearchResults(
        tweets=[],
        next_token="abc123",
        result_count=0,
        total_count=1_000_000,
        metadata=metadata,
    )
    
    assert results.result_count == 0
    assert results.next_token == "abc123"
    assert results.total_count == 1_000_000
    assert results.metadata and results.metadata.source == "search_recent"


def test_search_metadata_defaults():
    """SearchMetadata 应该自动填充抓取时间"""
    metadata = SearchMetadata(source="search_all")
    assert metadata.source == "search_all"
    assert metadata.scraped_at is not None


def test_user_profile_model():
    """测试 UserProfile 组合模型"""
    user = User(
        id="100",
        username="linus",
        name="Linus Torvalds",
        verified=True,
    )
    
    tweet = Tweet(
        id="999",
        text="Talk is cheap. Show me the code.",
        created_at=datetime.now(timezone.utc),
        author_id="100",
    )
    
    profile = UserProfile(
        user=user,
        recent_tweets=[tweet],
        pinned_tweet=tweet,
    )
    
    assert profile.user.username == "linus"
    assert len(profile.recent_tweets) == 1
    assert profile.pinned_tweet is not None


if __name__ == "__main__":
    # 手动运行测试
    test_user_model()
    test_tweet_model()
    test_media_model()
    test_timeline_model()
    test_search_results_model()
    test_user_profile_model()
    print("✅ 所有数据模型测试通过")
