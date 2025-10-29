# 主题抓取 API 精简版

## ✅ 核心能力

TwitterCrawler 面向主题抓取，提供异步 API 和类型安全模型，支持历史回填与实时监控。

---

## 🎯 核心 API

### 1. `search_all_tweets()` - 完整历史搜索 🔥

**用途**：搜索指定主题的完整推文历史（从 2006 年开始）

```python
results = await crawler.search_all_tweets(
    query="AI agents",
    max_results=500,
    start_time="2023-01-01T00:00:00Z",
    end_time="2023-12-31T23:59:59Z"
)

# 支持分页
next_page = await crawler.search_all_tweets(
    query="AI agents",
    max_results=500,
    next_token=results.next_token  # 获取下一页
)
```

**限制**：
- 需要 **Academic Research** 权限
- 单次最多 500 条
- 默认返回最近 30 天（如不指定 `start_time`）

---

### 1.1 `search_all_tweets_paginated()` - 自动分页回填 🗂️

**用途**：自动处理 `next_token`，带速率限制退避，汇总多页结果并补充搜索元数据。

```python
results = await crawler.search_all_tweets_paginated(
    query='(الصين OR بكين) "العرض العسكري"',
    start_time="2025-01-01T00:00:00Z",
    end_time="2025-01-31T23:59:59Z",
    max_results=400,
    page_pause=3.5,
    label="parade2025_ar_window",
    language="ar",
)

print(results.metadata.page_count)      # 分页次数
print(results.metadata.total_collected) # 合并后的推文量
```

**特点**：
- ✅ 自动追加 `lang:<code>` 过滤（如提供 `language="ar"`）
- ✅ 指数退避处理 `TooManyRequests`
- ✅ 元数据包含时间窗口、分页次数、保存标签

---

### 2. `get_tweet()` - 获取单条推文详情

**用途**：查看特定推文的完整信息（包含引用/评论关系）

```python
tweet = await crawler.get_tweet("1234567890")

print(f"内容: {tweet.text}")
print(f"点赞: {tweet.like_count:,}")
print(f"转发: {tweet.retweet_count:,}")

# 检查是否是回复
if tweet.referenced_tweets:
    print(f"引用了其他推文")
```

**适用场景**：
- 深挖热门推文
- 获取搜索结果中引用的推文详情

---

### 3. `search_recent_tweets()` - 最近 7 天搜索

```python
results = await crawler.search_recent_tweets(
    query="China military parade lang:ar",
    max_results=50,
)

print(results.metadata.source)  # "search_recent"
```

**适用场景**：快速验证查询词或监控最新动态。

---

### 3. `get_tweets()` - 批量获取推文

**用途**：一次性获取多条推文（最多 100 条）

```python
# 批量获取
results = await crawler.get_tweets([
    "1234567890",
    "0987654321",
    "5555555555"
])

# 返回 SearchResults（包含推文 + 用户映射）
for tweet in results.tweets:
    author = results.users.get(tweet.author_id)
    print(f"@{author.username}: {tweet.text[:50]}...")
```

**适用场景**：
- 获取搜索结果中提到的所有引用推文
- 批量查看热门评论

---

### 4. `fetch_user_by_id()` - 获取用户信息

**用途**：获取推文作者的详细资料

```python
user = await crawler.fetch_user_by_id("12")

print(f"用户: @{user.username}")
print(f"粉丝: {user.followers_count:,}")
print(f"简介: {user.description}")
```

**适用场景**：
- 补全搜索结果中的用户信息
- 分析推文作者的影响力

---

## 🔄 典型工作流

### 场景 1：深度主题分析

```python
# 1. 搜索主题
results = await crawler.search_all_tweets(
    "Web3 developer",
    max_results=500,
    start_time="2024-01-01T00:00:00Z"
)

# 2. 获取高互动推文的详情
hot_tweets = [t for t in results.tweets if t.like_count > 1000]
details = await crawler.get_tweets([t.id for t in hot_tweets])

# 3. 分析作者
for tweet in details.tweets:
    author = await crawler.fetch_user_by_id(tweet.author_id)
    print(f"KOL: @{author.username}, 粉丝 {author.followers_count:,}")
```

### 场景 2：持续监控

```python
# 搜索最新讨论
results = await crawler.search_all_tweets(
    "GPT-5 release",
    max_results=100
)

# 检查是否有新内容
if results.next_token:
    # 保存 token，下次从这里继续
    save_checkpoint(results.next_token)
```

---

## ⚠️ 已知限制

1. **速率限制（429 错误）**
   - Twitter API 有严格的速率限制
   - `search_all_tweets_paginated()` 已内建指数退避，可根据需要调整 `page_pause`

2. **Academic Research 权限**
   - `search_all_tweets()` 需要特殊权限
   - 普通账号无法访问完整历史

3. **数据完整性**
   - 某些字段可能为 `None`（取决于 API 返回）
   - 需要在使用前检查

---

## 📝 测试状态

```bash
$ uv run python tests/test_topic_crawler.py

✅ get_tweet() - 成功获取推文详情
✅ get_tweets() - 批量获取 2 条推文
⚠️ fetch_user_by_id() - 达到速率限制（429）
⚠️ search_all_tweets() - 需要 Academic Research 权限
```

**结论**：核心功能正常，需要处理速率限制和权限问题。
