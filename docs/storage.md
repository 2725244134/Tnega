# 数据存储功能

## ✅ 已实现

完整的文件存储系统，支持 JSON 和 JSONL 两种格式。

---

## 📦 核心功能

### 1. JSON 存储（适合小批量数据）

```python
from src.x_crawl import save_tweets_json, load_tweets_json

# 保存推文
tweets = [tweet1, tweet2, tweet3]
path = save_tweets_json(tweets, "my_tweets.json")
# 输出: 💾 保存 3 条推文 → data/my_tweets.json

# 加载推文
loaded = load_tweets_json(path)
# 输出: 📂 加载 3 条推文 ← data/my_tweets.json
```

**特点**：
- ✅ 可读性好（格式化缩进）
- ✅ 适合手动查看和编辑
- ✅ 文件大小较大

---

### 2. JSONL 存储（适合大批量数据）

```python
from src.x_crawl import save_tweets_jsonl, load_tweets_jsonl

# 第一批数据
save_tweets_jsonl(batch1, "stream.jsonl", append=False)

# 追加第二批
save_tweets_jsonl(batch2, "stream.jsonl", append=True)

# 追加第三批
save_tweets_jsonl(batch3, "stream.jsonl", append=True)

# 加载全部
all_tweets = load_tweets_jsonl(Path("data/stream.jsonl"))
```

**特点**：
- ✅ 支持流式追加（分批抓取场景）
- ✅ 文件大小更小
- ✅ 逐行处理大文件

---

### 3. 完整搜索结果存储

```python
from src.x_crawl import save_search_results_json, load_search_results_json

# 保存完整结果（包含推文、用户、媒体）
results = await crawler.search_all_tweets("AI agents")
path = save_search_results_json(results, "ai_agents_results.json")

# 加载
loaded_results = load_search_results_json(path)

# 访问数据
for tweet in loaded_results.tweets:
    author = loaded_results.users[tweet.author_id]
    print(f"@{author.username}: {tweet.text}")
```

**包含内容**：
- ✅ 推文列表
- ✅ 用户映射（id → User）
- ✅ 媒体数据
- ✅ 分页信息（next_token）
- ✅ 元数据（result_count, total_count, saved_at, search metadata）

`search metadata` 会记录查询语句、时间窗口、分页次数等信息，便于在后续分析中追溯抓取参数。

---

### 4. 便捷保存函数（自动命名）

```python
from src.x_crawl import save_results

# 自动生成文件名
results = await crawler.search_all_tweets("Web3 developer")
path = save_results(results, "Web3 developer", format="json")
# 生成: data/Web3_developer_20251029_173530.json

# JSONL 格式
path = save_results(results, "AI agents 2024", format="jsonl")
# 生成: data/AI_agents_2024_20251029_173530.jsonl
```

**自动处理**：
- ✅ 清理文件名（移除特殊字符）
- ✅ 添加时间戳
- ✅ 统一保存在 `data/` 目录

---

## 🎯 典型使用场景

### 场景 1：批量抓取并保存

```python
import asyncio
from src.x_crawl import TwitterCrawler, save_results

async def crawl_topic(query: str):
    """抓取主题并自动保存"""
    crawler = TwitterCrawler()
    
    try:
        # 搜索推文
        results = await crawler.search_all_tweets(
            query=query,
            max_results=500
        )
        
        # 自动保存
        path = save_results(results, query, format="json")
        print(f"✅ 抓取完成，保存到: {path}")
        
        return results
        
    finally:
        await crawler.close()

# 使用
asyncio.run(crawl_topic("AI agents 2024"))
```

---

### 场景 2：分批抓取（增量追加）

```python
from src.x_crawl import TwitterCrawler, save_tweets_jsonl

async def crawl_with_pagination(query: str, total: int = 5000):
    """分批抓取大量数据"""
    crawler = TwitterCrawler()
    filename = "large_dataset.jsonl"
    next_token = None
    count = 0
    
    try:
        while count < total:
            # 每次获取 500 条
            results = await crawler.search_all_tweets(
                query=query,
                max_results=500,
                next_token=next_token
            )
            
            # 追加到文件
            save_tweets_jsonl(
                results.tweets,
                filename,
                append=(count > 0)  # 第一次不追加，后续追加
            )
            
            count += len(results.tweets)
            next_token = results.next_token
            
            print(f"进度: {count}/{total}")
            
            # 没有下一页了
            if not next_token:
                break
                
    finally:
        await crawler.close()
    
    print(f"✅ 总共抓取 {count} 条推文")
```

---

### 场景 3：数据处理流水线

```python
from pathlib import Path
from src.x_crawl import load_tweets_jsonl

def analyze_tweets(filepath: Path):
    """分析已保存的推文数据"""
    # 加载数据
    tweets = load_tweets_jsonl(filepath)
    
    # 统计分析
    total = len(tweets)
    total_likes = sum(t.like_count or 0 for t in tweets)
    avg_likes = total_likes / total if total > 0 else 0
    
    print(f"📊 分析结果:")
    print(f"   总推文数: {total:,}")
    print(f"   总点赞数: {total_likes:,}")
    print(f"   平均点赞: {avg_likes:.1f}")
    
    # 找出热门推文
    hot_tweets = sorted(tweets, key=lambda t: t.like_count or 0, reverse=True)[:10]
    
    print(f"\n🔥 热门推文 TOP 10:")
    for i, tweet in enumerate(hot_tweets, 1):
        print(f"   {i}. {tweet.text[:50]}... (👍 {tweet.like_count:,})")

# 使用
analyze_tweets(Path("data/AI_agents_2024_20251029_173530.json"))
```

---

### 场景 4：阿语历史回填与存储

```bash
uv run python scripts/backfill_parade_2025_ar.py \
  --start 2024-12-01 \
  --end 2025-12-31 \
  --window-days 14 \
  --format json
```

- 查询标签（例如 `--queries parade2025_ar_signature`）可筛选特定搜索语句
- 输出文件统一保存在 `data/`，文件名包含时间窗口与标签
- JSON 结果包含 `metadata.search` 字段，记录查询语句、时间窗口、分页次数等追溯信息

---

## 📂 文件结构

```
data/
├── AI_agents_2024_20251029_173530.json      # 完整搜索结果（JSON）
├── Web3_developer_20251029_173530.jsonl     # 推文列表（JSONL）
├── stream.jsonl                              # 流式追加数据
└── custom_filename.json                      # 自定义文件名
```

---

## 🎨 文件格式对比

### JSON 格式
```json
[
  {
    "id": "1234567890",
    "text": "推文内容",
    "created_at": "2024-01-01T12:00:00",
    "author_id": "12345",
    "like_count": 100,
    "retweet_count": 50
  },
  {
    "id": "0987654321",
    "text": "另一条推文",
    ...
  }
]
```

### JSONL 格式
```jsonl
{"id": "1234567890", "text": "推文内容", "created_at": "2024-01-01T12:00:00", ...}
{"id": "0987654321", "text": "另一条推文", "created_at": "2024-01-01T13:00:00", ...}
{"id": "1122334455", "text": "第三条推文", "created_at": "2024-01-01T14:00:00", ...}
```

---

## ⚙️ 配置

默认存储目录：`data/`

修改默认目录：
```python
from pathlib import Path
from src.x_crawl import save_tweets_json

# 使用自定义目录
save_tweets_json(tweets, "output.json", data_dir=Path("my_data"))
```

---

## ✅ 测试结果

```bash
$ uv run python tests/test_storage_mock.py

✅ JSON 存储测试通过
✅ JSONL 存储测试通过
✅ 搜索结果存储测试通过
✅ 便捷保存函数测试通过
✅ 数据持久化测试通过（特殊字符: 😀 #AI @user）

📁 6 个测试文件生成在 data/ 目录
```

---

## 🚀 下一步

存储功能已就绪，现在可以：

1. **开始大规模抓取** - 使用 JSONL 格式流式保存
2. **离线分析数据** - 加载已保存的数据进行统计
3. **构建数据集** - 积累主题相关的推文语料库

配合即将实现的 **错误重试机制**，可以实现稳定的长时间抓取任务。
