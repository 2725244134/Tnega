# Tnega

基于 `pydantic-ai` + `tweepy` 的 Twitter 数据智能分析系统，专注于阿拉伯地区对"93阅兵"等中国主题的舆情分析。

## ✨ 核心特性

- 🔍 **智能数据采集**：基于 twitterapi.io 的异步推文采集
- 📊 **完整讨论追踪**：自动获取推文回复和 Thread 上下文
- 🧹 **文本清洗**：去除 URL、@提及、Emoji，适合分析
- 📁 **Excel 友好导出**：CSV 格式，包含作者、时间、互动数据
- 🎯 **类型安全**：基于 Pydantic 的端到端类型标注

## 🚀 快速开始

### 安装依赖

```bash
uv sync
```

### 配置 API Key

在 `.env` 文件中配置：
```bash
TWITTER_API_KEY=your_api_key_here
```

### 采集推文并导出 CSV

```python
from src.x_crawl import create_client, collect_tweet_discussions, export_texts_from_collection

# 搜索阿拉伯语推文
query = "(China parade OR 93阅兵) lang:ar"

async with create_client() as client:
    result = await collect_tweet_discussions(
        query=query,
        client=client,
        max_seed_tweets=100,
        max_replies_per_tweet=50,
    )

# 导出为 Excel 友好的 CSV
export_texts_from_collection(
    collection=result,
    output_path="data/93阅兵_讨论.csv",
    file_format="csv",
    csv_mode="full",  # 包含作者、时间、互动数据
    clean=True,        # 清洗文本
)
```

### 运行测试

```bash
# 测试数据采集
uv run python -m examples.test_collect_discussions

# 测试 CSV 导出
uv run python -m examples.test_csv_export
```
