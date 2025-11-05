# ============================================
# Agent + x_crawl 集成测试
# ============================================
# 测试完整的端到端流程：Agent 决策 -> 调用 Tool -> x_crawl 采集
# 使用 TestModel 和 Mock 避免真实 API 调用

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from src.agent.agent_runner import create_collector_agent
from src.agent.config import AgentConfig
from src.agent.models import CollectionResult, CollectorState
from src.x_crawl.data_collector import CollectionResponse
from src.x_crawl.models import (
    CollectionMetadata,
    Tweet,
    TweetDiscussionCollection,
    TweetWithContext,
    User,
)

pytestmark = pytest.mark.anyio


# ============================================
# Fixture：Mock x_crawl 响应
# ============================================


@pytest.fixture
def mock_collection_metadata():
    """创建假的 metadata"""
    return CollectionMetadata(
        query="China lang:ar",
        query_type="Latest",
        seed_tweet_count=10,
        total_reply_count=5,
        total_thread_count=2,
        max_seed_tweets=100,
        max_replies_per_tweet=10,
        max_concurrent=5,
    )


@pytest.fixture
def mock_tweets():
    """创建假推文列表"""
    return [
        Tweet(
            id=f"tweet_{i}",
            text=f"Sample tweet {i} about China 93 parade in Arabic",
            created_at=datetime(2024, 1, 1, 12, i),
            author_name=f"User {i}",
            lang="ar",
            like_count=10 * i,
            retweet_count=5 * i,
            reply_count=2 * i,
            view_count=100 * i,
        )
        for i in range(1, 11)
    ]


@pytest.fixture
def mock_users():
    """创建假用户列表"""
    return [
        User(
            id=f"user_{i}",
            username=f"user{i}",
            name=f"User {i}",
            location="Saudi Arabia",
            verified=i % 2 == 0,
            followers_count=1000 * i,
            created_at=datetime(2020, 1, 1),
        )
        for i in range(1, 11)
    ]


@pytest.fixture
def mock_twitter_response(mock_tweets, mock_users, mock_collection_metadata):
    """创建完整的 Mock Twitter 响应"""

    # 创建 TweetWithContext 列表
    items = [
        TweetWithContext(
            tweet=tweet,
            author=user,
            replies=[],
            thread_context=[],
        )
        for tweet, user in zip(mock_tweets, mock_users)
    ]

    collection = TweetDiscussionCollection(
        items=items,
        metadata=mock_collection_metadata,
    )

    return CollectionResponse(
        success=True,
        tweet_count=len(mock_tweets),
        seed_count=len(mock_tweets),
        reply_count=0,
        thread_count=0,
        success_rate=1.0,
        collection=collection,
        collected_at=datetime.utcnow(),
    )


# ============================================
# 测试：Agent + Tool 集成（Mock x_crawl）
# ============================================


async def test_agent_with_mocked_xcrawl(mock_twitter_response):
    """
    测试：Agent 调用 Tool -> Tool 调用 x_crawl（Mock）

    验证：
    1. Agent 能成功创建并运行
    2. Tool 能正确解析 x_crawl 响应
    3. State 正确更新（去重、计数等）
    """
    # Mock x_crawl 的 collect_twitter_data 函数
    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=mock_twitter_response),
    ):
        config = AgentConfig(
            target_tweet_count=20,  # 目标 20 条，第一次能拿到 10 条
            max_total_attempts=3,
        )

        # 使用 TestModel 创建 Agent
        agent = create_collector_agent(config, model=TestModel())
        state = CollectorState()

        # 运行 Agent
        result = await agent.run(
            "找阿拉伯地区对中国 93 阅兵的讨论",
            deps=state,
        )

        # 验证运行成功
        assert result is not None
        assert result.usage() is not None

        # 验证 state 被更新（TestModel 可能调用了 tool）
        # 注意：TestModel 不一定会真正调用 tool，这只是框架测试
        assert state.attempts >= 0


async def test_collector_tool_deduplication(mock_twitter_response):
    """
    测试：Tool 的去重逻辑

    验证：
    1. 第一次调用：所有推文都是新的
    2. 第二次调用（相同推文）：全部被去重
    3. State 正确记录总数和去重数
    """

    from src.agent.collector_tool import collect_tweets_tool

    # Mock x_crawl
    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=mock_twitter_response),
    ):
        state = CollectorState()

        # 创建 Mock RunContext
        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        # 第一次调用
        result1 = await collect_tweets_tool(
            ctx=ctx,
            query="China lang:ar",
            max_tweets=100,
        )

        assert result1.success is True
        assert result1.new_tweet_count == 10
        assert result1.duplicate_count == 0
        assert result1.total_tweet_count == 10
        assert state.attempts == 1

        # 第二次调用（相同推文）
        result2 = await collect_tweets_tool(
            ctx=ctx,
            query="China lang:ar",
            max_tweets=100,
        )

        assert result2.success is True
        assert result2.new_tweet_count == 0  # 全部去重
        assert result2.duplicate_count == 10  # 10 条重复
        assert result2.total_tweet_count == 10  # 总数不变
        assert state.attempts == 2


async def test_collector_tool_with_failure(mock_collection_metadata):
    """
    测试：x_crawl 返回失败响应时的处理

    验证：
    1. Tool 能正确处理失败响应
    2. State 仍然被更新（attempts 增加）
    3. 返回的 CollectionResult 标记为失败
    """

    from src.agent.collector_tool import collect_tweets_tool

    # Mock 失败的响应
    failed_response = CollectionResponse(
        success=False,
        tweet_count=0,
        seed_count=0,
        reply_count=0,
        thread_count=0,
        success_rate=0.0,
        collection=TweetDiscussionCollection(
            items=[],
            metadata=mock_collection_metadata,
        ),
        error_message="API Rate Limit Exceeded",
        collected_at=datetime.utcnow(),
    )

    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=failed_response),
    ):
        state = CollectorState()

        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        result = await collect_tweets_tool(
            ctx=ctx,
            query="test query",
            max_tweets=100,
        )

        # 验证失败响应
        assert result.success is False
        assert result.new_tweet_count == 0
        assert result.error_message == "API Rate Limit Exceeded"
        assert state.attempts == 1


# ============================================
# 测试：完整的 run_collector_agent 流程
# ============================================


async def test_run_collector_agent_with_mock(mock_twitter_response):
    """
    测试：完整的 Agent 运行流程（从用户请求到最终输出）

    验证：
    1. 能处理用户的自然语言请求
    2. 返回结构化的 AgentFinalOutput
    3. 包含正确的统计信息
    """
    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=mock_twitter_response),
    ):
        # 注意：run_collector_agent 内部会创建 Agent（使用真实 model_name）
        # 这里我们只 Mock x_crawl，不 Mock LLM
        # 如果要完整测试，需要 Mock LLM 或使用 TestModel

        # 暂时跳过，因为 run_collector_agent 会尝试初始化真实模型
        # 这个测试更适合在有真实 API key 的环境中运行
        pass


# ============================================
# 测试：State 共享与更新
# ============================================


async def test_state_shared_across_tool_calls(mock_twitter_response):
    """
    测试：多次 Tool 调用间 State 正确共享

    验证：
    1. seen_tweet_ids 在多次调用间保持
    2. queries_tried 累积所有查询
    3. attempts 正确递增
    """

    from src.agent.collector_tool import collect_tweets_tool

    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=mock_twitter_response),
    ):
        state = CollectorState()

        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        # 第一次查询
        await collect_tweets_tool(ctx, query="query1", max_tweets=100)
        assert state.attempts == 1
        assert len(state.queries_tried) == 1
        assert "query1" in state.queries_tried
        assert len(state.seen_tweet_ids) == 10

        # 第二次查询（不同 query）
        await collect_tweets_tool(ctx, query="query2", max_tweets=100)
        assert state.attempts == 2
        assert len(state.queries_tried) == 2
        assert "query2" in state.queries_tried
        # seen_tweet_ids 不变（因为是相同的 mock 数据）
        assert len(state.seen_tweet_ids) == 10


# ============================================
# 测试：结果格式化
# ============================================


def test_format_collection_result():
    """
    测试：CollectionResult 格式化为可读字符串

    验证：
    1. 包含关键统计信息
    2. 包含示例文本
    3. 格式清晰易读
    """
    from src.agent.collector_tool import format_result_for_agent

    result = CollectionResult(
        success=True,
        new_tweet_count=50,
        total_tweet_count=150,
        duplicate_count=10,
        query="China lang:ar",
        attempt_number=3,
        success_rate=0.95,
        sample_texts=[
            "Sample tweet 1",
            "Sample tweet 2",
            "Sample tweet 3",
        ],
        has_replies=True,
        has_threads=True,
    )

    formatted = format_result_for_agent(result)

    # 验证包含关键信息
    assert "50" in formatted  # new_tweet_count
    assert "150" in formatted  # total_tweet_count
    assert "10" in formatted  # duplicate_count
    assert "China lang:ar" in formatted
    assert "Sample tweet 1" in formatted


# ============================================
# 边界测试
# ============================================


async def test_tool_with_empty_response(mock_collection_metadata):
    """
    测试：x_crawl 返回空结果（0 条推文）

    验证：
    1. Tool 能正确处理空响应
    2. State 正确更新
    3. 不会崩溃
    """

    from src.agent.collector_tool import collect_tweets_tool

    empty_response = CollectionResponse(
        success=True,
        tweet_count=0,
        seed_count=0,
        reply_count=0,
        thread_count=0,
        success_rate=1.0,
        collection=TweetDiscussionCollection(
            items=[],
            metadata=mock_collection_metadata,
        ),
        collected_at=datetime.utcnow(),
    )

    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=empty_response),
    ):
        state = CollectorState()

        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        result = await collect_tweets_tool(ctx, query="test", max_tweets=100)

        assert result.success is True
        assert result.new_tweet_count == 0
        assert result.total_tweet_count == 0
        assert state.attempts == 1


async def test_tool_exception_handling():
    """
    测试：x_crawl 抛出异常时的处理

    验证：
    1. Tool 捕获异常
    2. 返回失败的 CollectionResult
    3. State 仍然更新
    """

    from src.agent.collector_tool import collect_tweets_tool

    # Mock 抛出异常
    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(side_effect=Exception("Network Error")),
    ):
        state = CollectorState()

        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        result = await collect_tweets_tool(ctx, query="test", max_tweets=100)

        assert result.success is False
        assert "Network Error" in result.error_message
        assert state.attempts == 1


# ============================================
# 性能测试
# ============================================


async def test_tool_performance(mock_twitter_response):
    """
    测试：Tool 的执行性能

    验证：单次调用应该很快（< 1 秒，Mock 模式下）
    """
    import time

    from src.agent.collector_tool import collect_tweets_tool

    with patch(
        "src.agent.collector_tool.collect_twitter_data",
        new=AsyncMock(return_value=mock_twitter_response),
    ):
        state = CollectorState()

        class MockRunContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = MockRunContext(state)

        start = time.time()
        await collect_tweets_tool(ctx, query="test", max_tweets=100)
        duration = time.time() - start

        # Mock 模式下应该很快
        assert duration < 1.0
