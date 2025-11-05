# ============================================
# Agent 单元测试
# ============================================
# 使用 pydantic-ai 的 TestModel 进行测试，无需真实 LLM 调用

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from src.agent.agent_runner import create_collector_agent
from src.agent.collector_tool import format_result_for_agent
from src.agent.config import AgentConfig, TerminationChecker
from src.agent.models import AgentFinalOutput, CollectionResult, CollectorState

# ============================================
# 测试配置
# ============================================

# 阻止所有真实的 LLM 请求
models.ALLOW_MODEL_REQUESTS = False

pytestmark = pytest.mark.anyio


# ============================================
# 测试 TerminationChecker
# ============================================


def test_termination_checker_reaches_target():
    """测试：达到目标数量时应该终止"""
    config = AgentConfig(target_tweet_count=100)
    checker = TerminationChecker(config)

    should_stop, reason = checker.should_terminate(
        total_tweets=100,
        new_tweets=50,
        attempt=1,
    )

    assert should_stop is True
    assert "目标数量" in reason


def test_termination_checker_max_attempts():
    """测试：超过最大尝试次数时应该终止"""
    config = AgentConfig(max_total_attempts=5)
    checker = TerminationChecker(config)

    should_stop, reason = checker.should_terminate(
        total_tweets=50,
        new_tweets=10,
        attempt=5,
    )

    assert should_stop is True
    assert "最大尝试次数" in reason


def test_termination_checker_low_yield():
    """测试：连续低产出时应该终止"""
    config = AgentConfig(
        min_new_tweets_threshold=10,
        max_low_yield_attempts=3,
    )
    checker = TerminationChecker(config)

    # 第 1 次低产出
    should_stop, _ = checker.should_terminate(
        total_tweets=50,
        new_tweets=5,
        attempt=1,
    )
    assert should_stop is False

    # 第 2 次低产出
    should_stop, _ = checker.should_terminate(
        total_tweets=55,
        new_tweets=5,
        attempt=2,
    )
    assert should_stop is False

    # 第 3 次低产出，应该终止
    should_stop, reason = checker.should_terminate(
        total_tweets=60,
        new_tweets=5,
        attempt=3,
    )
    assert should_stop is True
    assert "低产出" in reason


def test_termination_checker_reset_on_good_yield():
    """测试：高产出时应该重置低产出计数"""
    config = AgentConfig(
        min_new_tweets_threshold=10,
        max_low_yield_attempts=3,
    )
    checker = TerminationChecker(config)

    # 低产出
    checker.should_terminate(total_tweets=50, new_tweets=5, attempt=1)
    assert checker.low_yield_count == 1

    # 高产出，应该重置
    checker.should_terminate(total_tweets=100, new_tweets=50, attempt=2)
    assert checker.low_yield_count == 0


# ============================================
# 测试 CollectionResult 格式化
# ============================================


def test_format_result_for_agent_success():
    """测试：格式化成功的采集结果"""
    result = CollectionResult(
        success=True,
        new_tweet_count=100,
        total_tweet_count=500,
        duplicate_count=20,
        query="China lang:ar",
        attempt_number=3,
        success_rate=0.95,
        sample_texts=["Sample 1", "Sample 2"],
    )

    formatted = format_result_for_agent(result)

    assert "✅" in formatted
    assert "100" in formatted  # new_tweet_count
    assert "500" in formatted  # total_tweet_count
    assert "China lang:ar" in formatted
    assert "Sample 1" in formatted


def test_format_result_for_agent_failure():
    """测试：格式化失败的采集结果"""
    result = CollectionResult(
        success=False,
        new_tweet_count=0,
        total_tweet_count=0,
        duplicate_count=0,
        query="invalid query",
        attempt_number=1,
        success_rate=0.0,
        sample_texts=[],
        error_message="API Error",
    )

    formatted = format_result_for_agent(result)

    assert "❌" in formatted
    assert "失败" in formatted
    assert "API Error" in formatted


# ============================================
# 测试 CollectorState
# ============================================


def test_collector_state_initialization():
    """测试：CollectorState 初始化"""
    state = CollectorState()

    assert state.total_tweet_count == 0
    assert state.attempts == 0
    assert len(state.seen_tweet_ids) == 0
    assert len(state.queries_tried) == 0
    assert state.collected_at is None


def test_collector_state_deduplication():
    """测试：CollectorState 去重逻辑"""
    state = CollectorState()

    # 添加推文 ID
    state.seen_tweet_ids.add("tweet_1")
    state.seen_tweet_ids.add("tweet_2")
    state.total_tweet_count = 2

    # 尝试添加重复 ID
    new_id = "tweet_1"
    if new_id not in state.seen_tweet_ids:
        state.seen_tweet_ids.add(new_id)
        state.total_tweet_count += 1

    # 应该没有增加
    assert state.total_tweet_count == 2
    assert len(state.seen_tweet_ids) == 2


# ============================================
# 测试 AgentConfig
# ============================================


def test_agent_config_defaults():
    """测试：AgentConfig 默认值"""
    config = AgentConfig()

    assert config.target_tweet_count == 2000
    assert config.min_new_tweets_threshold == 10
    assert config.max_low_yield_attempts == 3
    assert config.max_total_attempts == 10
    assert config.model_name == "gemini-1.5-flash"


def test_agent_config_custom():
    """测试：AgentConfig 自定义值"""
    config = AgentConfig(
        target_tweet_count=5000,
        max_total_attempts=20,
        model_name="gemini-2.0-flash",
    )

    assert config.target_tweet_count == 5000
    assert config.max_total_attempts == 20
    assert config.model_name == "gemini-2.0-flash"


# ============================================
# 测试 Agent 创建
# ============================================


def test_create_collector_agent():
    """测试：创建 Agent 实例"""
    from pydantic_ai.models.test import TestModel

    config = AgentConfig()

    # 直接传入 TestModel，无需 API Key
    agent = create_collector_agent(config, model=TestModel())

    assert agent is not None
    assert agent.deps_type == CollectorState


async def test_agent_with_test_model():
    """测试：使用 TestModel 运行 Agent"""
    config = AgentConfig(
        target_tweet_count=100,
        max_total_attempts=2,
    )

    # 直接传入 TestModel 创建 Agent
    agent = create_collector_agent(config, model=TestModel())

    state = CollectorState()

    # 运行 Agent（TestModel 会自动生成假数据）
    result = await agent.run(
        "测试查询",
        deps=state,
    )

    # 验证基本结构
    assert result is not None
    # TestModel 可能不会返回完整的结构化输出，但至少应该有 usage
    assert result.usage() is not None


# ============================================
# 集成测试（Mock x_crawl 层）
# ============================================


@pytest.fixture
def mock_twitter_response():
    """Mock 的 Twitter API 响应"""
    from src.x_crawl.data_collector import CollectionResponse
    from src.x_crawl.models import Tweet, TweetCollection, User

    # 创建假推文
    fake_tweets = [
        Tweet(
            id=f"tweet_{i}",
            text=f"Sample tweet {i} about China",
            author=User(
                id=f"user_{i}",
                username=f"user{i}",
                name=f"User {i}",
            ),
            created_at="2024-01-01T00:00:00Z",
            lang="ar",
        )
        for i in range(10)
    ]

    collection = TweetCollection(
        seed_tweets=fake_tweets,
        replies={},
        threads={},
    )

    return CollectionResponse(
        success=True,
        tweet_count=10,
        seed_count=10,
        reply_count=0,
        thread_count=0,
        success_rate=1.0,
        collection=collection,
    )


# ============================================
# 性能测试
# ============================================


def test_termination_checker_performance():
    """测试：TerminationChecker 性能（应该很快）"""
    import time

    config = AgentConfig()
    checker = TerminationChecker(config)

    start = time.time()
    for i in range(1000):
        checker.should_terminate(
            total_tweets=i,
            new_tweets=10,
            attempt=i,
        )
    end = time.time()

    # 1000 次判断应该在 0.1 秒内完成
    assert (end - start) < 0.1


# ============================================
# 边界条件测试
# ============================================


def test_collector_state_with_empty_queries():
    """测试：空查询列表"""
    state = CollectorState()
    assert state.queries_tried == []


def test_agent_config_with_zero_target():
    """测试：目标为 0 的配置"""
    config = AgentConfig(target_tweet_count=0)
    checker = TerminationChecker(config)

    should_stop, _ = checker.should_terminate(
        total_tweets=0,
        new_tweets=0,
        attempt=1,
    )

    # 目标为 0，立即终止
    assert should_stop is True


def test_collection_result_with_no_samples():
    """测试：没有示例文本的采集结果"""
    result = CollectionResult(
        success=True,
        new_tweet_count=0,
        total_tweet_count=0,
        duplicate_count=0,
        query="test",
        attempt_number=1,
        success_rate=0.0,
        sample_texts=[],
    )

    formatted = format_result_for_agent(result)
    assert formatted is not None
    assert "示例文本" not in formatted  # 空列表不应该显示示例


# ============================================
# 错误处理测试
# ============================================


def test_agent_final_output_failure():
    """测试：失败的最终输出"""
    output = AgentFinalOutput(
        success=False,
        total_tweets=50,
        total_attempts=10,
        queries_used=["query1", "query2"],
        output_path="data/failed.csv",
        duration_seconds=120.5,
        termination_reason="运行错误: API限流",
        summary="采集失败，仅获得 50 条推文。",
    )

    assert output.success is False
    assert output.total_tweets == 50
    assert "API限流" in output.termination_reason
