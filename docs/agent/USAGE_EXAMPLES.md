# 使用示例与最佳实践

> **目标**：展示 Agent 的实际使用方法和常见场景

---

## 🚀 快速开始

### 最简单的使用

```python
from src.agent import TweetCollectorAgent

# 创建 Agent
agent = TweetCollectorAgent()

# 运行（自然语言输入）
result = await agent.run("找阿拉伯地区对中国 93 阅兵的讨论")

# 查看结果
print(f"找到 {result.total_tweets} 条推文")
print(f"保存路径: {result.output_path}")
```

---

## 📖 基础示例

### 示例 1: 基础主题搜索

```python
import asyncio
from src.agent import TweetCollectorAgent

async def main():
    agent = TweetCollectorAgent()
    
    # 用户需求：找关于中国 93 阅兵的阿拉伯语讨论
    result = await agent.run(
        "找阿拉伯地区对中国 93 阅兵的讨论，越多越好"
    )
    
    print(f"✅ 采集完成")
    print(f"   总推文数: {result.total_tweets}")
    print(f"   尝试次数: {result.attempts}")
    print(f"   保存路径: {result.output_path}")
    print(f"   耗时: {result.duration_seconds:.1f} 秒")

if __name__ == "__main__":
    asyncio.run(main())
```

**预期输出**：
```
✅ 采集完成
   总推文数: 2155
   尝试次数: 4
   保存路径: data/collections/93阅兵_2025-11-01_143022.csv
   耗时: 185.3 秒
```

---

### 示例 2: 带时间范围的搜索

```python
result = await agent.run(
    "找 2020-2023 年阿拉伯地区对中国军事阅兵的讨论"
)
```

**Agent 会自动识别**：
- 时间范围: `since:2020-01-01 until:2023-12-31`
- 主题: 军事阅兵
- 语言: 阿拉伯语 (`lang:ar`)

---

### 示例 3: 指定目标数量

```python
result = await agent.run(
    "找阿拉伯地区对中国的讨论，至少 5000 条",
    target_count=5000,  # 明确目标
)
```

---

### 示例 4: 高互动推文

```python
result = await agent.run(
    "找阿拉伯地区对中国的高互动讨论（点赞数至少 50）"
)
```

**Agent 会自动添加**: `min_faves:50`

---

## 🎛️ 高级配置

### 自定义参数

```python
from src.agent import TweetCollectorAgent, CollectorConfig

# 创建配置
config = CollectorConfig(
    target_count=5000,           # 目标推文数
    max_attempts=15,             # 最大尝试次数
    max_tweets_per_attempt=1000, # 每次最多采集
    include_replies=True,        # 包含回复
    include_threads=True,        # 包含 Thread
    output_dir="data/my_collections",  # 自定义输出目录
)

# 创建 Agent
agent = TweetCollectorAgent(config=config)

# 运行
result = await agent.run("找关于中国的讨论")
```

---

### 指定 LLM 模型

```python
from src.agent import TweetCollectorAgent

# 使用 Gemini 1.5 Pro（更强的推理能力，但更贵）
agent = TweetCollectorAgent(model="gemini-1.5-pro")

# 或使用 Flash（更快，更便宜）
agent = TweetCollectorAgent(model="gemini-1.5-flash")
```

---

## 🎯 典型场景

### 场景 1: 舆情分析准备

```python
"""
需求：收集阿拉伯地区对中国某事件的所有讨论
目的：后续进行情感分析、主题提取
"""

async def collect_for_sentiment_analysis():
    agent = TweetCollectorAgent()
    
    # 第一步：收集推文
    result = await agent.run(
        "找阿拉伯地区对中国 93 阅兵的所有讨论，"
        "时间范围 2015-2025，包含回复和转发"
    )
    
    print(f"收集了 {result.total_tweets} 条推文")
    print(f"CSV 路径: {result.output_path}")
    
    # 第二步：可以用其他工具分析这个 CSV
    # analyze_sentiment(result.output_path)
    # extract_topics(result.output_path)
```

---

### 场景 2: 对比研究

```python
"""
需求：对比不同时间段的讨论量
"""

async def compare_time_periods():
    agent = TweetCollectorAgent()
    
    # 2015-2019
    result1 = await agent.run(
        "找 2015-2019 年阿拉伯地区对中国阅兵的讨论"
    )
    
    # 2020-2024
    result2 = await agent.run(
        "找 2020-2024 年阿拉伯地区对中国阅兵的讨论"
    )
    
    print(f"2015-2019: {result1.total_tweets} 条")
    print(f"2020-2024: {result2.total_tweets} 条")
    print(f"增长: {(result2.total_tweets / result1.total_tweets - 1) * 100:.1f}%")
```

---

### 场景 3: 批量采集

```python
"""
需求：采集多个相关主题
"""

async def batch_collection():
    agent = TweetCollectorAgent()
    
    topics = [
        "中国 93 阅兵",
        "中国军事演习",
        "中国一带一路",
        "中国空间站",
    ]
    
    results = []
    for topic in topics:
        result = await agent.run(
            f"找阿拉伯地区对{topic}的讨论"
        )
        results.append({
            "topic": topic,
            "tweet_count": result.total_tweets,
            "file": result.output_path,
        })
    
    # 汇总结果
    for r in results:
        print(f"{r['topic']}: {r['tweet_count']} 条 → {r['file']}")
```

---

## 🔍 结果分析

### 查看采集统计

```python
result = await agent.run("找关于中国的讨论")

# 基础统计
print(f"总推文数: {result.total_tweets}")
print(f"尝试次数: {result.attempts}")
print(f"成功率: {result.success_rate:.1%}")

# 查看使用的 query
for i, query in enumerate(result.queries_tried, 1):
    print(f"第 {i} 次: {query}")

# 时间信息
print(f"采集时间: {result.collected_at}")
print(f"耗时: {result.duration_seconds:.1f} 秒")
```

---

### 读取 CSV 结果

```python
import pandas as pd

# 读取 CSV
df = pd.read_csv(result.output_path, encoding="utf-8-sig")

print(f"CSV 行数: {len(df)}")
print(f"CSV 列: {df.columns.tolist()}")

# 统计分析
print(f"\n来源类型分布:")
print(df['来源类型'].value_counts())

print(f"\n作者分布（前 10）:")
print(df['作者名称'].value_counts().head(10))

print(f"\n平均互动数:")
print(f"  点赞: {df['点赞数'].mean():.1f}")
print(f"  转发: {df['转发数'].mean():.1f}")
print(f"  回复: {df['回复数'].mean():.1f}")
```

---

## ⚠️ 常见问题

### Q1: Agent 尝试太多次仍未达到目标

**问题**：
```python
ValueError: 已尝试 10 次，仍未达到目标 2000 条
```

**原因**：
- 主题太小众，相关推文确实不多
- 搜索条件过于严格（时间范围太窄、互动数太高）

**解决方案**：
```python
# 方案 1: 降低目标数量
result = await agent.run(
    "找阿拉伯地区对某小众事件的讨论",
    target_count=500,  # 降低到 500
)

# 方案 2: 放宽搜索条件
result = await agent.run(
    "找阿拉伯地区对某事件的讨论，"
    "包含所有时间段，包含转发"
)

# 方案 3: 增加最大尝试次数
config = CollectorConfig(max_attempts=20)
agent = TweetCollectorAgent(config=config)
```

---

### Q2: 采集速度慢

**问题**：
```
耗时: 600 秒（10 分钟）
```

**原因**：
- API QPS 限制（免费用户 0.2 QPS）
- 网络延迟
- 包含大量回复和 Thread

**解决方案**：
```python
# 方案 1: 升级到付费 API（QPS 20）
# 在 .env 中配置付费 API Key

# 方案 2: 减少回复和 Thread
config = CollectorConfig(
    include_replies=False,  # 不要回复
    include_threads=False,  # 不要 Thread
)
agent = TweetCollectorAgent(config=config)

# 方案 3: 分批采集
# 第一次：种子推文
result1 = await agent.run("...", max_tweets_per_attempt=100)

# 第二次：继续采集
result2 = await agent.run("...", max_tweets_per_attempt=500)
```

---

### Q3: 推文不相关

**问题**：
```
采集了 2000 条推文，但很多与主题无关
```

**原因**：
- 关键词过于宽泛
- 没有使用精确匹配

**解决方案**：
```python
# 更精确的描述
result = await agent.run(
    "找阿拉伯地区对中国 93 年阅兵仪式的讨论，"
    "必须包含阅兵、军事等关键词，"
    "排除旅游、商业话题"
)

# 或者手动检查后，给 Agent 反馈
# （未来版本可能支持）
```

---

### Q4: 重复率高

**问题**：
```
Agent 连续 3 次采集，都是重复推文
```

**原因**：
- 这个角度的推文已经搜尽了
- Agent 应该自动换角度，但可能卡住了

**解决方案**：
```python
# 通常 Agent 会自动处理
# 如果真的卡住了，可以给更明确的指示

result = await agent.run(
    "找阿拉伯地区对中国的讨论，"
    "尝试不同的关键词组合和时间段"
)
```

---

## 🎓 最佳实践

### 1. 清晰描述需求

```python
# ❌ 不好：模糊
"找关于中国的推文"

# ✅ 好：具体
"找 2020-2024 年阿拉伯地区对中国 93 阅兵的讨论，包含回复"
```

---

### 2. 合理设置目标

```python
# ❌ 不好：目标过高
target_count=100000  # 可能无法达到

# ✅ 好：根据主题设置
target_count=2000   # 一般主题
target_count=5000   # 热门主题
target_count=500    # 小众主题
```

---

### 3. 检查结果质量

```python
result = await agent.run("...")

# 检查采集效率
if result.attempts > 8:
    print("⚠️ 尝试次数较多，可能主题太小众")

# 检查数据量
if result.total_tweets < 1000:
    print("⚠️ 推文较少，考虑扩展搜索范围")

# 抽查推文内容
df = pd.read_csv(result.output_path)
print(df['推文内容'].sample(10))  # 随机查看 10 条
```

---

### 4. 保存元信息

```python
# 保存采集的元信息，便于后续分析
metadata = {
    "user_request": "找阿拉伯地区对中国的讨论",
    "target_count": 2000,
    "total_tweets": result.total_tweets,
    "attempts": result.attempts,
    "queries_tried": result.queries_tried,
    "collected_at": str(result.collected_at),
    "duration_seconds": result.duration_seconds,
}

import json
meta_path = result.output_path.replace(".csv", "_meta.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
```

---

## 📊 性能优化

### 并行采集（未来版本）

```python
# 未来可能支持
async def parallel_collection():
    agent = TweetCollectorAgent()
    
    # 同时采集多个主题
    tasks = [
        agent.run("找关于中国阅兵的讨论"),
        agent.run("找关于中国军事的讨论"),
        agent.run("找关于中国外交的讨论"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    for r in results:
        print(f"{r.total_tweets} 条 → {r.output_path}")
```

---

### 缓存机制（未来版本）

```python
# 未来可能支持
# 避免重复采集相同的推文

agent = TweetCollectorAgent(
    cache_enabled=True,
    cache_dir="data/cache",
)

# 第一次：从 API 采集
result1 = await agent.run("找关于中国的讨论")

# 第二次：如果 query 相同，直接从缓存读取
result2 = await agent.run("找关于中国的讨论")  # 秒级返回
```

---

## 🧪 测试和调试

### 启用详细日志

```python
from loguru import logger

# 配置详细日志
logger.add(
    "logs/agent_debug.log",
    level="DEBUG",
    format="{time} | {level} | {message}",
)

agent = TweetCollectorAgent()
result = await agent.run("...")

# 查看日志
# logs/agent_debug.log 会包含每次 Tool 调用的详细信息
```

---

### 模拟运行（不调用 API）

```python
# 未来可能支持
agent = TweetCollectorAgent(dry_run=True)

result = await agent.run("找关于中国的讨论")

# dry_run 模式下：
# - Agent 会设计 query
# - 不会真正调用 API
# - 返回模拟结果
# 用于测试 Agent 的策略是否合理
```

---

## 📚 相关文档

- [Agent 架构设计](./AGENT_DESIGN.md)
- [Tool 接口文档](./TOOL_REFERENCE.md)
- [System Prompt](./SYSTEM_PROMPT.md)
- [x_crawl API](../x_crawl_api.md)

---

## 🔗 扩展阅读

### Twitter 高级搜索

- [Twitter Advanced Search Guide](https://github.com/igorbrigadir/twitter-advanced-search)
- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)

### pydantic-ai

- [pydantic-ai Documentation](https://ai.pydantic.dev/)
- [pydantic-ai Examples](https://ai.pydantic.dev/examples/)

---

**最后更新**: 2025-11-01  
**版本**: v0.1.0

**问题反馈**: 如有使用问题，请查看常见问题章节或提交 Issue
