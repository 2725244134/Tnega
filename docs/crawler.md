# Twitter Crawler 使用指南

## 🚀 快速开始

```python
import asyncio
from src.x_crawl import TwitterCrawler

async def main():
    # 初始化 crawler（自动从 .env 加载 bearer_token）
    crawler = TwitterCrawler()
    
    try:
        # 获取用户信息
        user = await crawler.fetch_user_by_username("jack")
        print(f"用户：@{user.username}")
        print(f"粉丝数：{user.followers_count:,}")
        
        # 获取用户时间线
        timeline = await crawler.fetch_user_timeline(user.id, max_results=10)
        print(f"\n最近推文数：{timeline.result_count}")
        
        for tweet in timeline.tweets[:3]:
            print(f"- {tweet.text[:60]}...")
        
        # 搜索推文
        results = await crawler.search_recent_tweets("python AI", max_results=10)
        print(f"\n搜索到 {results.result_count} 条推文")
        
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 API 方法

### 用户相关

```python
# 根据用户名获取用户
user = await crawler.fetch_user_by_username("jack")

# 根据 ID 获取用户
user = await crawler.fetch_user_by_id("12")
```

### 推文相关

```python
# 获取单条推文
tweet = await crawler.fetch_tweet_by_id("20")

# 获取用户时间线
timeline = await crawler.fetch_user_timeline("12", max_results=20)

# 搜索推文
results = await crawler.search_recent_tweets("python", max_results=50)
```

## 🎯 返回类型

所有方法都返回类型安全的 Pydantic 模型：

- `User` - 用户信息（包含粉丝数、认证状态等）
- `Tweet` - 推文对象（文本、互动数据、时间等）
- `Timeline` - 时间线容器（推文列表 + 用户映射 + 分页信息）
- `SearchResults` - 搜索结果容器（推文列表 + 分页令牌）

## ⚙️ 配置

在项目根目录创建 `.env` 文件：

```properties
"bearer_token" = "你的 Twitter Bearer Token"
```

或在代码中直接传入：

```python
crawler = TwitterCrawler(bearer_token="YOUR_TOKEN_HERE")
```

## 🧪 运行测试

```bash
# 运行集成测试（需要有效的 API 凭证）
uv run python tests/test_crawler.py

# 或使用 pytest
uv run pytest tests/test_crawler.py -v
```

## 📊 测试结果示例

```
✅ 通过：5 | ❌ 失败：0

测试内容：
- 获取用户信息（用户名）✅
- 获取用户信息（ID）✅
- 获取单条推文 ✅
- 获取用户时间线 ✅
- 搜索推文 ✅
```

## 🎨 设计原则

- **全异步**：所有 API 调用都是异步的
- **类型安全**：使用 Pydantic 模型确保数据结构正确
- **日志友好**：使用 loguru 记录所有关键操作
- **简洁优雅**：API 设计直观，符合 Python 习惯
