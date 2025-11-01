
import asyncio
from pydantic_ai import RunContext, RunUsage
from src.agent.models import CollectorState
from src.agent.collector_tool import collect_tweets_tool

SYSTEM_PROMPT = """
你是一个 Twitter 数据采集专家。你的任务是根据用户需求，自动设计和优化 Twitter 搜索 query，调用工具采集推文，直到找到足够多的相关推文（默认 2000 条）。

终止条件：
- 总推文数 >= 2000
- 连续 3 次新增 < 10 条
- 尝试超过 10 次（报错）

工具: collect_tweets_tool(query, max_tweets) → {new_tweet_count, total_tweet_count, sample_texts}

策略:
- 推文少 → 扩展关键词/放宽时间
- 重复多 → 换角度搜索
- 不相关 → 缩小范围/精确匹配

Twitter 语法: (A OR B) lang:ar since:2020-01-01 min_faves:10 -RT
"""

async def run_agent(user_request: str, target_count: int = 2000, max_attempts: int = 10):
    state = CollectorState()
    result = None
    for attempt in range(max_attempts):
        # Agent 设计 query 并调用工具
        ctx = RunContext[CollectorState](model=state, usage="agent", deps=state)
        result = await collect_tweets_tool(ctx, user_request, max_tweets=500)
        print(f"第 {attempt+1} 次: 新增 {result.new_tweet_count} 条，累计 {result.total_tweet_count} 条")
        if result.total_tweet_count >= target_count:
            print(f"✅ 达到目标，采集完成！总计 {result.total_tweet_count} 条推文")
            print(f"保存路径: {result.output_path}")
            return result
        if attempt >= 2 and result.new_tweet_count < 10:
            print(f"⚠️ 连续 3 次新增 < 10 条，终止采集。当前累计 {result.total_tweet_count} 条")
            break
    if result is not None:
        raise ValueError(f"已尝试 {max_attempts} 次，仍未达到目标 {target_count} 条。当前累计 {result.total_tweet_count} 条")
    else:
        raise ValueError("采集失败，未获得任何推文。")

if __name__ == "__main__":
    # 示例测试
    asyncio.run(run_agent("找阿拉伯地区对中国 93 阅兵的讨论"))
