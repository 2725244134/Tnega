# Agent 架构设计

> **项目目标**：让 AI Agent 学会优化 Twitter 搜索 query，自动采集大量相关推文

---

## 🎯 核心理念

### 问题定义

如何让 Agent 自动找到**尽可能多**的相关推文？

**挑战**：
- Twitter 高级搜索语法复杂（关键词、时间、语言、互动数等）
- 初始 query 往往效果不佳（太宽泛 or 太狭窄）
- 需要**迭代优化** query 才能找到最优结果

**解决方案**：
- Agent 设计初始 query → 调用工具 → 看到结果 → 调整 query → 再次尝试
- 循环直到：找到足够多推文（≥2000条）OR 连续多次都是重复推文

---

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────────────┐
│  用户输入（自然语言）                          │
│  "找阿拉伯地区对 93 阅兵的讨论"                │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  Agent (pydantic-ai + Gemini)               │
│  - 理解用户需求                              │
│  - 设计初始 query                            │
│  - 迭代优化 query                            │
│  - 判断何时停止                              │
└────────────────┬────────────────────────────┘
                 │
                 │ (多次调用)
                 ▼
┌─────────────────────────────────────────────┐
│  Tool: collect_tweets                       │
│  - 调用 x_crawl 采集推文                     │
│  - 返回：推文数量 + 示例文本                  │
│  - 自动去重（跨多次调用）                     │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│  输出：合并后的 CSV 文件                      │
│  - 所有尝试的推文合并                        │
│  - 自动去重（基于 tweet.id）                 │
│  - 包含完整元数据                            │
└─────────────────────────────────────────────┘
```

---

## 🔄 工作流程

### 单次运行的完整流程

```python
用户: "找阿拉伯地区关于中国 93 阅兵的讨论，至少 2000 条"

Agent 内部对话（单次运行，多轮迭代）：

【第 1 轮】
Agent 思考: "用户要找阿拉伯语推文，关于 93 阅兵"
Agent 设计: query = "(93阅兵 OR China parade) lang:ar"
Agent 调用: collect_tweets(query, max=500)
Tool 返回: 找到 45 条推文
Agent 判断: "太少了！只有 45 条，需要扩展关键词"

【第 2 轮】
Agent 思考: "扩展中文和英文关键词，增加相关词"
Agent 设计: query = "(China OR 中国 OR parade OR 阅兵 OR military OR 军事) lang:ar"
Agent 调用: collect_tweets(query, max=500)
Tool 返回: 找到 320 条推文（其中 40 条重复）
Agent 判断: "好多了！但还不够 2000 条，继续扩展时间范围"

【第 3 轮】
Agent 思考: "放宽时间限制，从 2015 年开始搜索"
Agent 设计: query = "(China OR 中国 OR parade OR 阅兵) lang:ar since:2015-01-01"
Agent 调用: collect_tweets(query, max=1000)
Tool 返回: 找到 1580 条推文（其中 300 条重复）
Agent 判断: "接近了！再降低互动数要求"

【第 4 轮】
Agent 思考: "去掉 min_faves 限制，包含所有推文"
Agent 设计: query = "(China OR 中国) lang:ar since:2015-01-01"
Agent 调用: collect_tweets(query, max=1500)
Tool 返回: 找到 2150 条推文（其中 500 条重复）
Agent 判断: "成功！总共 2150 条去重后的推文，达到目标"

【输出】
Agent: "✅ 采集完成！共尝试 4 种 query，找到 2150 条去重推文"
      "保存路径: data/collections/93阅兵_2025-11-01.csv"
```

---

## 🛑 终止条件

Agent 何时停止迭代？满足以下**任一条件**：

### 条件 1: 达到目标数量
```python
total_unique_tweets >= 2000
```

### 条件 2: 连续重复
```python
# 连续 3 次调用，新推文数 < 10
if last_3_attempts_all_had_less_than_10_new_tweets:
    stop()
```

### 条件 3: 最大尝试次数
```python
# 防止无限循环
if attempt_count >= 10:
    raise ValueError("尝试了 10 次仍未达到目标")
```

---

## 📊 数据去重策略

### 问题
Agent 多次调用工具，不同 query 可能返回相同的推文。

### 解决方案

**方案 A：工具层去重（推荐）**
```python
# Tool 内部维护一个全局 seen_tweet_ids 集合
# 每次调用自动过滤已见过的推文
class TweetCollectorContext:
    seen_tweet_ids: set[str] = set()
    all_tweets: list[Tweet] = []
```

**方案 B：Agent 层去重**
```python
# Agent 自己记录已获取的推文 ID
# 但这样会增加 Agent 的复杂度（不推荐）
```

**最终选择**：方案 A（工具层去重）

---

## 🎛️ 可配置参数

### 用户可控参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `target_count` | `int` | `2000` | 目标推文数量 |
| `max_attempts` | `int` | `10` | 最大尝试次数 |
| `max_tweets_per_attempt` | `int` | `500` | 每次调用最多获取推文数 |
| `include_replies` | `bool` | `True` | 是否包含回复 |
| `include_threads` | `bool` | `True` | 是否包含 Thread |

### 示例

```python
result = await agent.run(
    "找阿拉伯地区对中国的讨论",
    target_count=5000,      # 目标 5000 条
    max_attempts=15,        # 最多尝试 15 次
)
```

---

## 🧠 Agent System Prompt 设计要点

### 核心能力要求

1. **理解 Twitter 高级搜索语法**
   - 关键词组合：`(A OR B) AND C`
   - 语言过滤：`lang:ar`
   - 时间范围：`since:2020-01-01 until:2025-12-31`
   - 互动数：`min_faves:10 min_retweets:5`
   - 排除：`-RT`（排除转发）

2. **迭代优化策略**
   - 推文太少 → 扩展关键词 / 放宽时间 / 降低互动数要求
   - 推文太多但不相关 → 缩小关键词 / 添加排除词
   - 重复率高 → 换一个角度搜索（地理、账号类型等）

3. **判断力**
   - 何时停止（达到目标 or 无法再优化）
   - 如何平衡相关性和数量

### Prompt 结构

```
你是 Twitter 数据采集专家。

【任务】
根据用户需求，自动设计和优化 Twitter 搜索 query，找到尽可能多的相关推文。

【工具】
- collect_tweets(query, max_tweets): 采集推文，返回数量和示例

【策略】
1. 初始尝试：根据用户需求设计基础 query
2. 迭代优化：
   - 如果推文 < 100: 扩展关键词、放宽时间、降低互动数
   - 如果推文 > 1000 但不相关: 缩小范围、添加排除词
   - 如果重复率 > 80%: 尝试不同角度
3. 终止条件：
   - 总推文数 >= 2000
   - 连续 3 次新推文 < 10
   - 尝试次数 >= 10（抛出错误）

【Twitter 搜索语法】
... (详细语法说明)

【示例】
... (成功案例)
```

详细 Prompt 见 `SYSTEM_PROMPT.md`

---

## 🔧 技术实现细节

### pydantic-ai Agent 配置

```python
from pydantic_ai import Agent, RunContext

agent = Agent(
    model="gemini-1.5-flash",      # 快速、便宜
    # model="gemini-1.5-pro",      # 更强的推理能力
    
    tools=[collect_tweets_tool],
    
    system_prompt="...",  # 见 SYSTEM_PROMPT.md
    
    retries=2,            # API 失败重试
)
```

### 依赖状态管理

```python
from pydantic import BaseModel

class CollectorState(BaseModel):
    """Agent 运行时状态（单次运行内共享）"""
    seen_tweet_ids: set[str] = set()
    all_tweets: list[Tweet] = []
    attempts: int = 0
    queries_tried: list[str] = []
```

使用 `RunContext` 注入状态：
```python
async def collect_tweets_tool(
    ctx: RunContext[CollectorState],  # 注入状态
    query: str,
    max_tweets: int = 500,
) -> CollectionResult:
    state = ctx.deps  # 获取状态
    
    # 采集推文...
    
    # 更新状态
    state.seen_tweet_ids.update(...)
    state.all_tweets.extend(...)
    state.attempts += 1
```

---

## 📁 文件输出

### 目录结构

```
data/
├── collections/
│   ├── 93阅兵_2025-11-01_143022.csv      # 最终合并结果
│   └── 93阅兵_2025-11-01_143022.json     # 元信息（可选）
└── logs/
    └── agent_2025-11-01_143022.log       # Agent 运行日志
```

### CSV 格式

与 `x_crawl` 导出的格式一致：
```csv
序号,推文内容,来源类型,作者名称,发布时间,点赞数,转发数,回复数,字符数
```

### 元信息 JSON（可选）

```json
{
  "user_request": "找阿拉伯地区对中国的讨论",
  "target_count": 2000,
  "total_tweets": 2150,
  "attempts": 4,
  "queries_tried": [
    "(93阅兵 OR China parade) lang:ar",
    "(China OR 中国 OR parade) lang:ar",
    "..."
  ],
  "collected_at": "2025-11-01T14:30:22Z",
  "duration_seconds": 185.3
}
```

---

## 🚀 使用方式

### 命令行（推荐）

```bash
uv run python -m src.agent.run_collector \
  "找阿拉伯地区对中国 93 阅兵的讨论" \
  --target 5000 \
  --max-attempts 15
```

### Python API

```python
from src.agent import TweetCollectorAgent

agent = TweetCollectorAgent()

result = await agent.run(
    user_request="找阿拉伯地区对中国的讨论",
    target_count=2000,
    max_attempts=10,
)

print(f"找到 {result.total_tweets} 条推文")
print(f"保存路径: {result.output_path}")
```

---

## 🎯 成功指标

### 功能性指标

- ✅ 能够根据自然语言需求自动设计 query
- ✅ 能够迭代优化 query 找到更多推文
- ✅ 能够自动去重（跨多次调用）
- ✅ 能够在合理的尝试次数内达到目标

### 性能指标

- 平均尝试次数：3-5 次
- 达成率（≥2000 条）：> 80%
- 重复率：< 20%
- 运行时间：< 10 分钟（取决于 API 速度）

---

## 🔄 后续优化方向

### Phase 1: MVP（当前）
- 基础迭代优化
- 单次运行，多轮对话
- 简单终止条件

### Phase 2: 智能优化
- **学习历史成功模式**：记录哪些 query 效果好
- **A/B 测试**：同时尝试多个 query，选最好的
- **相关性评分**：不仅看数量，还判断推文相关性

### Phase 3: 高级功能
- **增量采集**：避免重复采集历史数据
- **多主题并行**：同时采集多个相关主题
- **自动分类**：采集时自动给推文打标签

---

## 📚 相关文档

- [Tool 接口文档](./TOOL_REFERENCE.md)
- [System Prompt 设计](./SYSTEM_PROMPT.md)
- [使用示例](./USAGE_EXAMPLES.md)
- [x_crawl API 文档](../x_crawl_api.md)

---

**最后更新**: 2025-11-01  
**版本**: v0.1.0 (设计阶段)
