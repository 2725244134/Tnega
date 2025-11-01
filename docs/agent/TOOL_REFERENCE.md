# Tool 接口文档

> **工具定义**：Agent 可调用的函数，用于与外部系统交互

---

## 🔧 Tool: `collect_tweets`

### 功能描述

采集 Twitter 推文并返回结果摘要。

- 调用 `x_crawl` 模块进行数据采集
- 自动去重（基于 tweet.id）
- 更新全局状态（seen_tweet_ids, all_tweets）
- 返回本次采集的统计信息

---

## 📝 函数签名

```python
async def collect_tweets(
    ctx: RunContext[CollectorState],
    query: str,
    max_tweets: int = 500,
) -> CollectionResult:
    """
    采集 Twitter 推文
    
    Args:
        ctx: pydantic-ai 运行上下文（包含状态）
        query: Twitter 搜索查询语句（支持高级语法）
        max_tweets: 本次最多采集多少条种子推文
    
    Returns:
        CollectionResult: 采集结果摘要
    
    Raises:
        ValueError: 如果 query 为空或无效
        httpx.HTTPStatusError: 如果 API 调用失败
    """
```

---

## 📊 返回数据结构

### `CollectionResult`

```python
from pydantic import BaseModel

class CollectionResult(BaseModel):
    """采集结果摘要"""
    
    # 核心统计
    new_tweet_count: int
    """本次新增的去重推文数量"""
    
    total_tweet_count: int
    """当前总推文数（累计，去重后）"""
    
    duplicate_count: int
    """本次遇到的重复推文数量"""
    
    # Query 信息
    query: str
    """使用的搜索 query"""
    
    attempt_number: int
    """当前是第几次尝试"""
    
    # 质量指标
    success_rate: float
    """API 调用成功率（0-1）"""
    
    # 示例数据（供 Agent 判断相关性）
    sample_texts: list[str]
    """本次采集的前 5 条推文文本"""
    
    # 可选：额外信息
    has_replies: bool = True
    """是否包含回复"""
    
    has_threads: bool = True
    """是否包含 Thread"""
```

### 示例返回值

```json
{
  "new_tweet_count": 45,
  "total_tweet_count": 245,
  "duplicate_count": 5,
  "query": "(China parade OR 93阅兵) lang:ar",
  "attempt_number": 2,
  "success_rate": 1.0,
  "sample_texts": [
    "بحضور صيني روسي رفيع.. عرض لـ«أقوى الأسلحة» في بيونغ يانغ...",
    "China victory day parade وشوفو غير حديث الرئيس الصيني...",
    "..."
  ],
  "has_replies": true,
  "has_threads": true
}
```

---

## 🔄 工作流程

### 内部实现逻辑

```python
async def collect_tweets(
    ctx: RunContext[CollectorState],
    query: str,
    max_tweets: int = 500,
) -> CollectionResult:
    
    # 1. 获取状态
    state = ctx.deps
    state.attempts += 1
    state.queries_tried.append(query)
    
    # 2. 调用 x_crawl 采集
    async with create_client() as client:
        collection = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=max_tweets,
            max_replies_per_tweet=10,
            include_thread=True,
            max_concurrent=10,
        )
    
    # 3. 去重
    all_tweets = collection.all_tweets
    new_tweets = [
        t for t in all_tweets 
        if t.id not in state.seen_tweet_ids
    ]
    duplicate_count = len(all_tweets) - len(new_tweets)
    
    # 4. 更新状态
    state.seen_tweet_ids.update(t.id for t in new_tweets)
    state.all_tweets.extend(new_tweets)
    
    # 5. 提取示例
    samples = [t.text[:100] for t in new_tweets[:5]]
    
    # 6. 返回结果
    return CollectionResult(
        new_tweet_count=len(new_tweets),
        total_tweet_count=len(state.all_tweets),
        duplicate_count=duplicate_count,
        query=query,
        attempt_number=state.attempts,
        success_rate=collection.success_rate,
        sample_texts=samples,
        has_replies=collection.total_replies > 0,
        has_threads=collection.total_threads > 0,
    )
```

---

## 🧠 Agent 如何使用此 Tool

### 典型调用流程

```python
# Agent 内部思考过程（伪代码）

def agent_logic(user_request):
    # 1. 理解需求
    topic = extract_topic(user_request)  # "93阅兵"
    language = extract_language(user_request)  # "ar"
    
    # 2. 设计初始 query
    query = f"({topic} OR China parade) lang:{language}"
    
    # 3. 第一次尝试
    result1 = await collect_tweets(query, max_tweets=500)
    
    if result1.new_tweet_count < 100:
        # 推文太少，扩展关键词
        query = f"(China OR 中国 OR parade OR 阅兵) lang:{language}"
        result2 = await collect_tweets(query, max_tweets=500)
    
    if result2.total_tweet_count < 2000:
        # 还不够，放宽时间范围
        query += " since:2015-01-01"
        result3 = await collect_tweets(query, max_tweets=1000)
    
    # 检查是否达到目标
    if result3.total_tweet_count >= 2000:
        return success()
    
    # 继续优化...
```

### Agent Prompt 中的使用示例

```
你可以使用工具 collect_tweets(query, max_tweets) 来采集推文。

示例：
1. 初始尝试
   query = "(93阅兵 OR China parade) lang:ar"
   result = collect_tweets(query, 500)
   
   返回：
   {
     "new_tweet_count": 45,
     "total_tweet_count": 45,
     "sample_texts": ["..."]
   }
   
2. 如果推文太少，扩展关键词
   query = "(China OR 中国 OR military OR 军事) lang:ar"
   result = collect_tweets(query, 500)
   
   返回：
   {
     "new_tweet_count": 280,      # 新增 280 条
     "total_tweet_count": 325,    # 累计 325 条（45+280）
     "duplicate_count": 0,
     "sample_texts": ["..."]
   }

记住：
- total_tweet_count 是累计数量（自动去重）
- 如果 duplicate_count 很高，说明需要换个角度搜索
- 通过 sample_texts 可以判断相关性
```

---

## 🎛️ 参数说明

### `query` - 搜索查询

**类型**: `str`  
**必需**: 是  
**格式**: Twitter 高级搜索语法

**示例**:
```python
# 基础关键词
"China parade"

# 逻辑组合
"(China OR 中国) AND (parade OR 阅兵)"

# 语言过滤
"China lang:ar"

# 时间范围
"China since:2020-01-01 until:2025-12-31"

# 互动数限制
"China min_faves:10 min_retweets:5"

# 排除
"China -RT"  # 排除转发

# 复杂组合
"(China OR 中国) lang:ar since:2020-01-01 min_faves:5 -RT"
```

**完整语法参考**: https://github.com/igorbrigadir/twitter-advanced-search

---

### `max_tweets` - 最大采集数

**类型**: `int`  
**必需**: 否  
**默认值**: `500`  
**范围**: `1 - 5000`

**说明**:
- 这是单次调用最多采集的**种子推文**数量
- 实际返回数量可能少于此值（取决于搜索结果）
- 包含回复和 Thread 后，总推文数会更多

**建议值**:
- 初次尝试：`500`
- 后续优化：`500 - 1000`
- 最终收集：`1000 - 2000`

---

## 🔍 返回值解读

### `new_tweet_count` vs `total_tweet_count`

```python
# 第 1 次调用
result1 = collect_tweets("China lang:ar", 500)
# new_tweet_count = 45    (本次新增)
# total_tweet_count = 45  (累计)

# 第 2 次调用
result2 = collect_tweets("(China OR 中国) lang:ar", 500)
# new_tweet_count = 280   (本次新增，已去重)
# total_tweet_count = 325 (累计 = 45 + 280)
# duplicate_count = 5     (本次遇到 5 条重复)

# 第 3 次调用
result3 = collect_tweets("China lang:ar since:2015-01-01", 1000)
# new_tweet_count = 1200  (本次新增)
# total_tweet_count = 1525 (累计 = 325 + 1200)
# duplicate_count = 80    (本次遇到 80 条重复)
```

### 如何判断是否需要继续

**情况 1: 推文太少**
```python
if result.new_tweet_count < 100:
    # 本次新增太少，需要扩展搜索范围
    → 扩展关键词 / 放宽时间 / 降低互动数
```

**情况 2: 重复率过高**
```python
if result.duplicate_count / (result.new_tweet_count + result.duplicate_count) > 0.8:
    # 80% 都是重复的，说明这个角度已经搜尽了
    → 换一个角度（不同关键词组合、时间段等）
```

**情况 3: 达到目标**
```python
if result.total_tweet_count >= 2000:
    # 达到目标，可以停止
    → 保存结果并返回
```

---

## ⚠️ 错误处理

### 常见错误

#### 1. 无效的 query
```python
# 空 query
collect_tweets("", 500)
# → ValueError: query 不能为空

# 语法错误
collect_tweets("China AND", 500)
# → API 返回错误（会自动重试）
```

#### 2. API 限流
```python
# 调用过于频繁
# → httpx.HTTPStatusError: 429 Too Many Requests
# → 工具内部会自动等待并重试
```

#### 3. 网络超时
```python
# 网络不稳定
# → asyncio.TimeoutError
# → 工具内部会自动重试（最多 3 次）
```

### 错误传播

工具遇到无法恢复的错误时，会向上传播给 Agent：
```python
try:
    result = await collect_tweets("invalid query", 500)
except ValueError as e:
    # Agent 会看到错误信息
    # 可以尝试修正 query 后重试
```

---

## 📈 性能考虑

### API 调用开销

每次调用 `collect_tweets` 的典型耗时：

| max_tweets | 预计耗时 | API 调用次数 |
|-----------|---------|-------------|
| 100       | 10-20s  | 5-10 次     |
| 500       | 30-60s  | 20-30 次    |
| 1000      | 60-120s | 40-60 次    |

**影响因素**：
- API QPS 限制（免费 0.2 QPS，付费 20 QPS）
- 网络延迟
- 回复和 Thread 的数量

### 优化建议

1. **逐步增加采集量**
   ```python
   # 不好：直接采集大量
   collect_tweets(query, 5000)  # 可能耗时很长
   
   # 好：先小量测试
   result = collect_tweets(query, 100)
   if result.new_tweet_count > 0:
       result = collect_tweets(query, 500)
   ```

2. **控制并发数**
   ```python
   # x_crawl 内部会控制并发
   # 付费用户：max_concurrent=10-20
   # 免费用户：max_concurrent=1
   ```

---

## 🧪 测试

### 单元测试示例

```python
import pytest
from src.agent.tools import collect_tweets
from src.agent.state import CollectorState

@pytest.mark.asyncio
async def test_collect_tweets_basic():
    """测试基础采集功能"""
    state = CollectorState()
    ctx = MockRunContext(deps=state)
    
    result = await collect_tweets(
        ctx,
        query="China lang:ar",
        max_tweets=10,
    )
    
    assert result.new_tweet_count > 0
    assert result.total_tweet_count == result.new_tweet_count
    assert len(result.sample_texts) <= 5

@pytest.mark.asyncio
async def test_collect_tweets_deduplication():
    """测试去重功能"""
    state = CollectorState()
    ctx = MockRunContext(deps=state)
    
    # 第一次调用
    result1 = await collect_tweets(ctx, "China lang:ar", 10)
    count1 = result1.total_tweet_count
    
    # 第二次调用（相同 query，应该有重复）
    result2 = await collect_tweets(ctx, "China lang:ar", 10)
    
    assert result2.total_tweet_count >= count1
    assert result2.duplicate_count > 0
```

---

## 📚 相关文档

- [Agent 架构设计](./AGENT_DESIGN.md)
- [System Prompt](./SYSTEM_PROMPT.md)
- [x_crawl API](../x_crawl_api.md)

---

**最后更新**: 2025-11-01  
**版本**: v0.1.0
