# x_crawl API 接口文档

## 📋 目录

- [概述](#概述)
- [核心数据模型](#核心数据模型)
- [API 函数](#api-函数)
- [使用示例](#使用示例)
- [错误处理](#错误处理)
- [性能优化](#性能优化)

---

## 概述

`x_crawl` 是基于 [twitterapi.io](https://twitterapi.io) 构建的 Twitter 数据采集层，提供类型安全的异步 API 接口。

### 设计原则

1. **异步优先** - 所有 I/O 操作使用 `async/await`
2. **类型安全** - 基于 Pydantic 模型，全面类型标注
3. **高级封装** - 一次调用完成"搜索 → 获取回复 → 获取 Thread"的完整流程
4. **容错设计** - 部分失败不影响整体，记录错误信息供后续处理

### 核心功能

```
搜索阿拉伯地区对"九三阅兵"的讨论
    ↓
collect_tweet_discussions(query="(China parade OR 93阅兵) lang:ar")
    ↓
返回 TweetDiscussionCollection
    ├─ 种子推文列表
    ├─ 每条推文的所有回复
    ├─ 每条推文的 Thread 上下文
    └─ 采集元信息（统计、失败记录等）
```

---

## 核心数据模型

### User - 用户对象

```python
class User(BaseModel):
    """Twitter 用户对象（精简版）"""
    
    id: str                          # 用户唯一标识符
    username: str                    # 用户名（@handle）
    name: str                        # 显示名称
    location: str | None = None      # 地理位置（用于判断地区）
    verified: bool = False           # 是否认证账户
    followers_count: int = 0         # 粉丝数（影响力指标）
    created_at: datetime | None      # 账户创建时间
```

**字段说明**：
- `location` - 用于判断阿拉伯地区（如 "Riyadh, Saudi Arabia"）
- `verified` / `followers_count` - 评估用户影响力
- 删除字段：`description`, `profile_image_url`, `following_count`, `tweet_count` 等冗余信息

---

### Tweet - 推文对象

```python
class Tweet(BaseModel):
    """Twitter 推文对象（精简版）"""
    
    # ========== 基础信息 ==========
    id: str                          # 推文 ID（用于 API 调用）
    text: str                        # 推文文本（核心目标数据）
    created_at: datetime             # 发布时间（用于时间过滤）
    author_id: str                   # 作者用户 ID
    lang: str | None = None          # 语言代码（如 "ar", "en", "zh"）
    
    # ========== 互动数据（热度指标）==========
    like_count: int = 0              # 点赞数
    retweet_count: int = 0           # 转推数
    reply_count: int = 0             # 回复数
    view_count: int = 0              # 浏览数
    
    # ========== 关系数据 ==========
    conversation_id: str | None      # 会话 ID（追踪讨论线程）
    is_reply: bool = False           # 是否为回复推文
    in_reply_to_id: str | None       # 回复的目标推文 ID
```

**字段说明**：
- `text` - 核心目标，所有分析基于此
- `lang` - 判断阿拉伯地区的关键字段（`lang:ar`）
- 互动数据 - 评估推文热度和传播力
- 删除字段：`referenced_tweets`, `attachments`, `entities`, `geo`, `context_annotations` 等

---

### TweetWithContext - 推文及其讨论上下文

```python
class TweetWithContext(BaseModel):
    """推文及其完整讨论上下文"""
    
    tweet: Tweet                     # 种子推文
    author: User                     # 推文作者信息
    replies: list[Tweet] = []        # 该推文的所有回复（平铺列表）
    thread_context: list[Tweet] = [] # Thread 上下文（父推文链）
    
    # ========== 派生属性 ==========
    @property
    def total_engagement(self) -> int:
        """总互动数（点赞 + 转推 + 回复）"""
        return (
            self.tweet.like_count + 
            self.tweet.retweet_count + 
            self.tweet.reply_count
        )
    
    @property
    def reply_authors(self) -> set[str]:
        """回复者 ID 集合（去重，用于统计参与者数量）"""
        return {reply.author_id for reply in self.replies}
    
    @property
    def has_discussion(self) -> bool:
        """是否有讨论（回复数 > 0）"""
        return len(self.replies) > 0
    
    @property
    def has_thread(self) -> bool:
        """是否属于 Thread（上下文推文数 > 0）"""
        return len(self.thread_context) > 0
```

**设计说明**：
- `replies` - 平铺列表，不构建树状结构（交给 Agent 层处理）
- `thread_context` - 包含该推文所在 Thread 的所有推文（含父推文链）
- 派生属性 - 提供常用计算，避免重复代码

---

### CollectionMetadata - 采集元信息

```python
class CollectionMetadata(BaseModel):
    """数据采集的元信息"""
    
    # ========== 查询参数 ==========
    query: str                                # 原始搜索查询
    query_type: Literal["Latest", "Top"]      # 查询类型
    collected_at: datetime                    # 采集时间（UTC）
    
    # ========== 统计数据 ==========
    seed_tweet_count: int = 0                 # 种子推文数量
    total_reply_count: int = 0                # 总回复数
    total_thread_count: int = 0               # 总 Thread 推文数
    failed_tweet_ids: list[str] = []          # 获取失败的推文 ID 列表
    
    # ========== 时间范围 ==========
    since_timestamp: int | None = None        # 起始时间戳（Unix 秒）
    until_timestamp: int | None = None        # 结束时间戳（Unix 秒）
    
    # ========== 其他参数 ==========
    max_seed_tweets: int = 0                  # 最大种子推文数限制
    max_replies_per_tweet: int = 0            # 每条推文最大回复数限制
    max_concurrent: int = 0                   # 最大并发请求数
```

**字段说明**：
- `failed_tweet_ids` - 记录哪些推文处理失败，Agent 可据此决定是否重试
- 时间戳 - Unix 秒格式，方便与 API 参数对接
- 统计数据 - 用于评估采集质量和完整性

---

### TweetDiscussionCollection - 讨论采集结果

```python
class TweetDiscussionCollection(BaseModel):
    """推文讨论采集结果（高级组合操作的返回值）"""
    
    items: list[TweetWithContext] = []  # 推文及其讨论上下文列表
    metadata: CollectionMetadata        # 采集元信息
    
    # ========== 便捷访问属性 ==========
    @property
    def all_tweets(self) -> list[Tweet]:
        """所有推文（种子 + 回复 + Thread，去重）"""
        ...
    
    @property
    def all_users(self) -> dict[str, User]:
        """所有涉及的用户（user_id -> User）"""
        ...
    
    @property
    def total_tweets(self) -> int:
        """推文总数（去重后）"""
        ...
    
    @property
    def total_replies(self) -> int:
        """总回复数"""
        ...
    
    @property
    def total_threads(self) -> int:
        """总 Thread 推文数"""
        ...
    
    @property
    def success_rate(self) -> float:
        """成功率（未失败推文数 / 总推文数）"""
        ...
    
    @property
    def average_replies_per_tweet(self) -> float:
        """平均每条推文的回复数"""
        ...
```

**设计说明**：
- `items` - 核心数据，保留推文与回复/Thread 的关联关系
- 便捷属性 - 提供全局统计和分析视图
- `all_tweets` - 自动去重，适合做语言分布、时间分布等全局分析

---

## API 函数

### collect_tweet_discussions - 核心函数

```python
async def collect_tweet_discussions(
    query: str,
    client: httpx.AsyncClient,
    *,
    query_type: Literal["Latest", "Top"] = "Latest",
    max_seed_tweets: int = 500,
    max_replies_per_tweet: int = 200,
    include_thread: bool = True,
    max_concurrent: int = 10,
) -> TweetDiscussionCollection:
    """
    一站式采集推文讨论数据（高级组合操作）
    
    工作流程：
    1. 通过 advanced_search 搜索种子推文
    2. 并发获取每条种子推文的 replies
    3. 并发获取每条种子推文的 thread_context（如果 include_thread=True）
    4. 返回结构化的讨论数据
    
    Args:
        query: 搜索查询语句（完整的 query，由 LLM 生成）
               支持 Twitter 高级语法，例如：
               - "(China parade OR 93阅兵) lang:ar"
               - "九三阅兵 lang:ar since:2021-01-01 until:2025-01-15"
               - "China military parade lang:ar min_faves:10 since:2021-01-01"
               
               **重要**: 所有搜索条件（时间、语言、互动数等）都应该在 query 字符串中指定
               完整语法参考：https://github.com/igorbrigadir/twitter-advanced-search
        
        client: httpx.AsyncClient 实例（使用 create_client() 创建）
        
        query_type: 查询类型
                   - "Latest": 最新推文（按时间倒序）
                   - "Top": 热门推文（按互动量排序）
                   默认 "Latest"
        
        max_seed_tweets: 最多获取多少条种子推文
                        默认 500
                        建议根据 API 配额调整（免费用户可能需要减少）
        
        max_replies_per_tweet: 每条推文最多获取多少回复
                              默认 200
                              热门推文可能有数千条回复，此参数限制获取量
        
        include_thread: 是否获取 thread context
                       默认 True
                       如果只关心回复，可设为 False 提升性能
        
        max_concurrent: 最大并发请求数
                       根据 API QPS 限制调整
                       twitterapi.io 充值后 QPS = 20，建议设为 10（留余量）
                       免费用户 QPS = 0.2，建议设为 1
    
    Returns:
        TweetDiscussionCollection: 包含所有推文及其讨论上下文
    
    Raises:
        ValueError: query 为空或无效
        httpx.HTTPStatusError: API 请求失败（4xx/5xx）
        asyncio.TimeoutError: 请求超时
    
    Example:
        >>> from src.x_crawl import create_client, collect_tweet_discussions
        >>> 
        >>> # 搜索阿拉伯语推文及其讨论（LLM 生成完整 query）
        >>> async with create_client() as client:
        ...     result = await collect_tweet_discussions(
        ...         query="(China parade OR 93阅兵) lang:ar since:2021-01-01 until:2025-01-15",
        ...         client=client,
        ...         query_type="Latest",
        ...         max_seed_tweets=100,
        ...         max_replies_per_tweet=50
        ...     )
        >>> 
        >>> print(f"采集了 {len(result.items)} 条推文的讨论")
        >>> print(f"总推文数: {result.total_tweets}")
        >>> print(f"总回复数: {result.total_replies}")
        >>> print(f"成功率: {result.success_rate:.1%}")
        >>> print(f"失败的推文: {result.metadata.failed_tweet_ids}")
        >>> 
        >>> # 分析每条推文的讨论热度
        >>> for item in result.items:
        ...     print(f"推文 {item.tweet.id}:")
        ...     print(f"  文本: {item.tweet.text[:50]}...")
        ...     print(f"  回复数: {len(item.replies)}")
        ...     print(f"  参与者: {len(item.reply_authors)}")
        ...     print(f"  总互动: {item.total_engagement}")
    """
```

---

## 使用示例

### 示例 1：基本用法

```python
from src.x_crawl import create_client, collect_tweet_discussions

# 搜索阿拉伯语推文
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="China 93 parade lang:ar",
        client=client,
        max_seed_tweets=50,
        max_replies_per_tweet=20
    )

# 查看结果
print(f"采集了 {len(result.items)} 条推文")
print(f"总回复数: {result.total_replies}")

# 遍历每条推文
for item in result.items:
    print(f"\n推文 ID: {item.tweet.id}")
    print(f"作者: {item.author.name} (@{item.author.username})")
    print(f"内容: {item.tweet.text}")
    print(f"回复数: {len(item.replies)}")
```

### 示例 2：时间范围过滤

```python
# 获取 2021-2025 年的讨论（LLM 在 query 中指定时间）
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="九三阅兵 lang:ar since:2021-01-01 until:2025-01-15",
        client=client,
        max_seed_tweets=100
    )

# 按时间分析
from collections import defaultdict

tweets_by_year = defaultdict(int)
for tweet in result.all_tweets:
    year = tweet.created_at.year
    tweets_by_year[year] += 1

print("推文时间分布:")
for year, count in sorted(tweets_by_year.items()):
    print(f"  {year}: {count} 条")
```

### 示例 3：热度分析

```python
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="China military parade lang:ar min_faves:10",
        client=client,
        query_type="Top",  # 获取热门推文
        max_seed_tweets=20
    )

# 按互动量排序
sorted_items = sorted(
    result.items,
    key=lambda x: x.total_engagement,
    reverse=True
)

print("最热门的 5 条推文:")
for i, item in enumerate(sorted_items[:5], 1):
    print(f"\n{i}. 推文 {item.tweet.id}")
    print(f"   点赞: {item.tweet.like_count}")
    print(f"   转推: {item.tweet.retweet_count}")
    print(f"   回复: {len(item.replies)}")
    print(f"   总互动: {item.total_engagement}")
```

### 示例 4：地区分析

```python
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="93阅兵 lang:ar",
        client=client,
        max_seed_tweets=100
    )

# 统计用户位置分布
from collections import Counter

locations = [
    user.location 
    for user in result.all_users.values() 
    if user.location
]

location_dist = Counter(locations)

print("用户地理位置分布:")
for location, count in location_dist.most_common(10):
    print(f"  {location}: {count}")
```

### 示例 5：失败处理

```python
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="China parade lang:ar",
        client=client,
        max_seed_tweets=200
    )

# 检查失败情况
if result.metadata.failed_tweet_ids:
    print(f"警告: {len(result.metadata.failed_tweet_ids)} 条推文处理失败")
    print(f"成功率: {result.success_rate:.1%}")
    
    # 重试失败的推文（如果需要）
    for failed_id in result.metadata.failed_tweet_ids:
        print(f"失败的推文 ID: {failed_id}")
        # TODO: 实现重试逻辑
```

### 示例 6：并发控制

```python
async with create_client() as client:
    # 免费用户（QPS = 0.2）
    result = await collect_tweet_discussions(
        query="China parade lang:ar",
        client=client,
        max_seed_tweets=10,
        max_concurrent=1  # 串行执行，避免限流
    )

    # 充值用户（QPS = 20）
    result = await collect_tweet_discussions(
        query="China parade lang:ar",
        client=client,
        max_seed_tweets=200,
        max_concurrent=10  # 并发执行，提升速度
    )
```

---

## 错误处理

### 常见错误类型

#### 1. API Key 无效

```python
# 错误信息
httpx.HTTPStatusError: 401 Unauthorized

# 解决方案
# 检查 .env 文件中的 TWITTER_API_KEY 是否正确
# 或使用自定义 API Key 创建 client
async with create_client(api_key="your_valid_key_here") as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client
    )
```

#### 2. 限流（Rate Limit）

```python
# 错误信息
httpx.HTTPStatusError: 429 Too Many Requests

# 解决方案
# 1. 减少 max_concurrent（降低并发）
# 2. 减少 max_seed_tweets（减少请求数）
# 3. 充值账户（提升 QPS 限额）
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client,
        max_concurrent=1,  # 降低并发
        max_seed_tweets=10  # 减少数量
    )
```

#### 3. 查询语法错误

```python
# 错误信息
httpx.HTTPStatusError: 400 Bad Request

# 解决方案
# 检查 query 语法是否正确
# 参考：https://github.com/igorbrigadir/twitter-advanced-search
async with create_client() as client:
    result = await collect_tweet_discussions(
        query='(China parade OR "93阅兵") lang:ar',  # 注意引号使用
        client=client
    )
```

#### 4. 部分推文获取失败

```python
# 不会抛异常，但 metadata.failed_tweet_ids 会记录失败的 ID
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client
    )

if result.metadata.failed_tweet_ids:
    logger.warning(
        f"{len(result.metadata.failed_tweet_ids)} 条推文处理失败"
    )
    # 可选：重试失败的推文
```

### 错误处理最佳实践

```python
from loguru import logger
import asyncio

async def safe_collect(query: str, **kwargs):
    """带重试和错误处理的采集函数"""
    max_retries = 3
    retry_delay = 5  # 秒
    
    async with create_client() as client:
        for attempt in range(max_retries):
            try:
                result = await collect_tweet_discussions(query, client, **kwargs)
            
            # 检查成功率
            if result.success_rate < 0.8:
                logger.warning(
                    f"成功率较低: {result.success_rate:.1%}, "
                    f"失败 {len(result.metadata.failed_tweet_ids)} 条"
                )
            
            return result
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # 限流，等待后重试
                logger.warning(f"限流，等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                # 其他错误，直接抛出
                raise
        
        except Exception as e:
            logger.error(f"采集失败: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(retry_delay)
    
        raise RuntimeError(f"采集失败，已重试 {max_retries} 次")

# 使用
result = await safe_collect(
    query="China parade lang:ar",
    max_seed_tweets=100
)
```

---

## 性能优化

### 1. 并发控制

```python
# 根据 API QPS 限制调整
# QPS = 20 → max_concurrent = 10（留 50% 余量）
# QPS = 0.2 → max_concurrent = 1（串行）

async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client,
        max_concurrent=10  # 根据账户类型调整
    )
```

### 2. 结果数量限制

```python
# 只获取最热门的 50 条推文及其讨论
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="China parade lang:ar min_faves:10",
        client=client,
        query_type="Top",  # 热门排序
        max_seed_tweets=50,
        max_replies_per_tweet=30  # 每条推文最多 30 回复
    )
```

### 3. 跳过 Thread Context

```python
# 如果不需要 Thread 上下文，可以跳过以提升速度
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client,
        include_thread=False  # 跳过 thread_context 获取
    )
```

### 4. 批量处理

```python
# 分批处理大量推文
async def collect_in_batches(query: str, total: int, batch_size: int = 100):
    results = []
    
    async with create_client() as client:
        for offset in range(0, total, batch_size):
            logger.info(f"处理第 {offset}-{offset+batch_size} 条...")
            
            result = await collect_tweet_discussions(
                query=query,
                client=client,
                max_seed_tweets=batch_size,
                # TODO: 添加分页逻辑（需要支持 cursor 参数）
            )
            
            results.append(result)
            
            # 避免限流，批次间等待
            await asyncio.sleep(2)
    
    return results
```

### 5. 缓存策略

```python
import json
from pathlib import Path

async def collect_with_cache(query: str, cache_dir: Path, **kwargs):
    """带文件缓存的采集函数"""
    
    # 生成缓存文件名
    cache_file = cache_dir / f"{hash(query)}.json"
    
    # 检查缓存
    if cache_file.exists():
        logger.info(f"从缓存加载: {cache_file}")
        data = json.loads(cache_file.read_text())
        return TweetDiscussionCollection(**data)
    
    # 采集数据
    async with create_client() as client:
        result = await collect_tweet_discussions(query, client, **kwargs)
    
    # 保存缓存
    cache_file.write_text(result.model_dump_json(indent=2))
    logger.info(f"已缓存到: {cache_file}")
    
    return result
```

---

## 附录

### A. Twitter 高级搜索语法

完整语法参考：https://github.com/igorbrigadir/twitter-advanced-search

常用示例：

```python
# 关键词组合
"(China parade OR 93阅兵 OR Beijing 2015)"

# 语言过滤
"China parade lang:ar"  # 阿拉伯语

# 时间范围
"China parade since:2021-01-01 until:2025-01-15"

# 用户过滤
"China parade from:username"  # 指定用户
"China parade -from:username"  # 排除用户

# 互动数过滤
"China parade min_faves:100"  # 至少 100 点赞
"China parade min_retweets:50"  # 至少 50 转推

# 组合使用
"(China parade OR 93阅兵) lang:ar since:2021-01-01 min_faves:10"
```

### B. 数据模型字段映射表

| twitterapi.io 字段 | models.py 字段 | 类型 | 说明 |
|-------------------|---------------|------|------|
| `id` | `Tweet.id` | str | 推文 ID |
| `text` | `Tweet.text` | str | 推文文本 |
| `createdAt` | `Tweet.created_at` | datetime | 发布时间（需解析） |
| `author.id` | `Tweet.author_id` | str | 作者 ID |
| `lang` | `Tweet.lang` | str | 语言代码 |
| `likeCount` | `Tweet.like_count` | int | 点赞数 |
| `retweetCount` | `Tweet.retweet_count` | int | 转推数 |
| `replyCount` | `Tweet.reply_count` | int | 回复数 |
| `viewCount` | `Tweet.view_count` | int | 浏览数 |
| `conversationId` | `Tweet.conversation_id` | str | 会话 ID |
| `isReply` | `Tweet.is_reply` | bool | 是否回复 |
| `inReplyToId` | `Tweet.in_reply_to_id` | str | 回复目标 ID |
| `author.userName` | `User.username` | str | 用户名 |
| `author.name` | `User.name` | str | 显示名称 |
| `author.location` | `User.location` | str | 地理位置 |
| `author.isBlueVerified` | `User.verified` | bool | 认证状态 |
| `author.followers` | `User.followers_count` | int | 粉丝数 |

### C. API 端点映射

| 函数 | 底层 API 端点 | 说明 |
|------|--------------|------|
| `collect_tweet_discussions` | `/twitter/tweet/advanced_search` | 搜索种子推文 |
| ↓ | `/twitter/tweet/reply` | 获取每条推文的回复 |
| ↓ | `/twitter/tweet/thread_context` | 获取每条推文的 Thread |

---

## 更新日志

### v0.1.0 (2025-01-15)

- ✅ 初始版本
- ✅ 实现 `collect_tweet_discussions` 核心函数
- ✅ 精简数据模型（删除冗余字段）
- ✅ 支持并发控制和失败处理
- ✅ 完整的类型标注和文档

---

**文档编写**: 2025-01-15  
**最后更新**: 2025-01-15  
**维护者**: x_crawl 团队