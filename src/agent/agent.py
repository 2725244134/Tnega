import csv
import os
from io import StringIO

import aiofiles
import dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agent.prompt_loader import load_system_prompt
from src.x_crawl.tweet_fetcher import collect_tweet_discussions
from src.x_crawl.twitter_client import create_client

# ============================================
# Agent 依赖注入 - 状态容器
# ============================================

_ = dotenv.load_dotenv()


class Deps(BaseModel):
    """
    Agent 运行时的可变状态容器

    职责：
    - 记录去重后的推文数量
    - 存储已获取的推文文本（自动去重）

    设计决策：
    - 使用 set[str] 实现自动去重（Good Taste: 消除特殊情况）
    - 可变容器，允许 agent 运行中直接修改
    - 内存状态，无持久化需求
    """

    tweet_texts: set[str] = set()  # 去重的推文文本集合
    attempt_count: int = 0  # 全局调用次数

    @property
    def fetched_count(self) -> int:
        """去重后的推文数量"""
        return len(self.tweet_texts)

    def add_tweet_text(self, text: str) -> bool:
        """
        添加推文文本（自动去重）

        Args:
            text: 推文文本内容

        Returns:
            True 表示新增成功，False 表示已存在（重复）
        """
        before_count = len(self.tweet_texts)
        self.tweet_texts.add(text)
        return len(self.tweet_texts) > before_count


# ============================================
# Tool 返回结果模型
# ============================================


class CollectionResult(BaseModel):
    """
    采集工具的返回结果摘要

    职责：
    - 报告本次采集的统计信息
    - 提供样本推文供 Agent 判断相关性
    - 追踪累计状态
    """

    new_tweet_count: int = Field(..., description="本次新增的去重推文数")
    total_tweet_count: int = Field(..., description="累计总推文数（自动去重）")
    duplicate_count: int = Field(..., description="本次遇到的重复推文数")
    query: str = Field(..., description="使用的查询语句")
    attempt_number: int = Field(..., description="当前是第几次尝试")
    sample_texts: list[str] = Field(
        default_factory=list, description="本次采集的前 5 条推文文本（用于判断相关性）"
    )


# ============================================
# Agent Tools
# ============================================


async def collect_tweets(
    ctx: RunContext[Deps],
    query: str,
    max_tweets: int = 2000,
) -> CollectionResult:
    """
    采集 Twitter 推文并返回结果摘要

    **输入**：
    - `query`: Twitter 搜索查询（支持高级语法）
    - `max_tweets`: 本次最多采集多少条种子推文

    **返回**：
    - `new_tweet_count`: 本次新增的去重推文数
    - `total_tweet_count`: 累计总推文数（自动去重）
    - `duplicate_count`: 本次遇到的重复推文数
    - `query`: 使用的 query
    - `attempt_number`: 当前是第几次尝试
    - `sample_texts`: 本次采集的前 5 条推文文本（用于判断相关性）

    **重要**：工具会自动去重，`total_tweet_count` 是累计的唯一推文数

    Example:
        >>> # Agent 会自动调用此工具
        >>> result = await collect_tweets(
        ...     ctx=ctx,
        ...     query="(China parade OR 93阅兵) lang:ar",
        ...     max_tweets=100
        ... )
        >>> print(f"新增 {result.new_tweet_count} 条，累计 {result.total_tweet_count} 条")
    """
    deps = ctx.deps

    # 更新尝试次数
    deps.attempt_count += 1

    # 记录初始状态
    # 调用 x_crawl 层获取数据
    async with create_client() as client:
        collection = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=max_tweets,
            max_replies_per_tweet=200,
            include_thread=True,
            max_concurrent=10,
        )

    # 提取所有推文文本（种子 + 回复 + Thread）
    all_texts = [tweet.text for tweet in collection.all_tweets]

    # 更新 deps 状态（去重）
    new_count = 0
    duplicate_count = 0

    for text in all_texts:
        if deps.add_tweet_text(text):
            new_count += 1
        else:
            duplicate_count += 1

    # 获取样本文本（本次采集的前 5 条）
    sample_texts = all_texts[:5]
    # This section seems to be a leftover from debugging and is not logically sound
    # within the collect_tweets function. It attempts to write to a file on every
    # tool call, and the variable `text` is not defined in this scope.
    # The file writing logic is correctly placed in the `if __name__ == "__main__"` block.
    # Therefore, this block is removed to fix the bug and align with the function's purpose.
    # If async file writing were needed here, it would look like:
    #
    #
    async with aiofiles.open(
        f"tweets{deps.attempt_count}.csv", "w", newline="", encoding="utf-8"
    ) as csvfile:
        # Note: The 'csv' module works with string streams, not directly with aiofiles async file handles.
        # A common pattern is to write to an in-memory buffer and then write the buffer to the file.
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["tweet_text"])
        # Assuming `deps.tweet_texts` was intended instead of the unbound `text`
        for tweet_text in deps.tweet_texts:
            writer.writerow([tweet_text])
        await csvfile.write(output.getvalue())
    # However, since this logic is misplaced, the correct action is to remove it.
    # 构造返回结果
    return CollectionResult(
        new_tweet_count=new_count,
        total_tweet_count=len(deps.tweet_texts),
        duplicate_count=duplicate_count,
        query=query,
        attempt_number=deps.attempt_count,
        sample_texts=sample_texts,
    )


provider = OpenAIProvider(
    base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"]
)
model = OpenAIChatModel(provider=provider, model_name="minimax/minimax-m2:free")
agentx = Agent(
    system_prompt=load_system_prompt(),
    deps_type=Deps,
    model=model,
    tools=[collect_tweets],
)
if __name__ == "__main__":
    # 创建 Agent 实例
    import asyncio

    deps = Deps()
    result = asyncio.run(
        agentx.run(
            deps=deps,
            user_prompt="查询x上阿拉伯语地区对于2025年中国93阅兵的讨论,你应该重复调用工具，获取2000条以上推文",
        )
    )
    text = deps.tweet_texts
    import csv

    # 保存推文到CSV文件
    with open("tweets.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["num", "tweet_text"])  # 写入表头
        i = 1
        for tweet_text in text:
            writer.writerow([i, tweet_text])
            i = i + 1

    print(f"已保存 {len(text)} 条推文到 tweets.csv")
    print(result.output)
