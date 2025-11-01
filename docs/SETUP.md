# x_crawl 安装和设置指南

## 📋 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [配置说明](#配置说明)
- [验证安装](#验证安装)
- [常见问题](#常见问题)

---

## 环境要求

### 系统要求
- **Python**: 3.14+
- **包管理器**: `uv` (推荐) 或 `pip`
- **操作系统**: Linux / macOS / Windows

### API 要求
- **Twitter API Key**: 从 [twitterapi.io](https://twitterapi.io) 获取
- **QPS 限制**: 
  - 免费用户: 0.2 QPS (每 5 秒 1 次请求)
  - 充值用户: 20 QPS

---

## 安装步骤

### 1. 克隆项目（如果需要）

```bash
git clone <repository_url>
cd Tnega
```

### 2. 安装依赖

#### 使用 uv（推荐）

```bash
# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync

# 添加缺失的依赖
uv add pydantic-settings httpx
```

#### 使用 pip

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 手动安装缺失的依赖
pip install pydantic-settings httpx
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

在 `.env` 文件中填入你的 API Key：

```env
TWITTER_API_KEY=your_api_key_here
```

---

## 配置说明

### 环境变量详解

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `TWITTER_API_KEY` | ✅ | - | Twitter API Key (从 twitterapi.io 获取) |
| `TWITTER_API_BASE_URL` | ❌ | `https://api.twitterapi.io` | API 基础 URL |
| `HTTP_TIMEOUT` | ❌ | `30.0` | HTTP 请求超时时间（秒） |
| `MAX_CONCURRENT_REQUESTS` | ❌ | `20` | 连接池大小 |

### 获取 API Key

1. 访问 [twitterapi.io](https://twitterapi.io)
2. 注册账户
3. 在控制台创建 API Key
4. 复制 Key 到 `.env` 文件

### QPS 配置建议

根据你的账户类型调整并发参数：

**免费用户**：
```python
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client,
        max_concurrent=1  # 串行执行
    )
```

**充值用户**：
```python
async with create_client() as client:
    result = await collect_tweet_discussions(
        query="...",
        client=client,
        max_concurrent=10  # 并发执行
    )
```

---

## 验证安装

### 快速测试

创建测试文件 `test_installation.py`：

```python
"""验证 x_crawl 安装是否正确"""
import asyncio
from src.x_crawl import create_client, collect_tweet_discussions

async def test():
    print("测试 x_crawl 安装...")
    
    try:
        async with create_client() as client:
            result = await collect_tweet_discussions(
                query="test lang:en",
                client=client,
                max_seed_tweets=1,
                max_replies_per_tweet=1,
                max_concurrent=1
            )
        
        print(f"✅ 安装成功！获取到 {len(result.items)} 条推文")
        
    except Exception as e:
        print(f"❌ 安装失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test())
```

运行测试：

```bash
uv run python test_installation.py
```

### 运行完整测试

```bash
uv run python examples/test_collect_discussions.py
```

预期输出：

```
开始测试 x_crawl 推文讨论采集功能
============================================================
测试 1: 基本推文采集
============================================================
开始采集推文讨论
...
✅ 所有测试通过！
```

---

## 常见问题

### 1. 导入错误

**问题**：`ModuleNotFoundError: No module named 'pydantic_settings'`

**解决方案**：
```bash
uv add pydantic-settings
# 或
pip install pydantic-settings
```

---

### 2. API Key 错误

**问题**：`httpx.HTTPStatusError: 401 Unauthorized`

**解决方案**：
1. 检查 `.env` 文件是否存在
2. 确认 `TWITTER_API_KEY` 拼写正确
3. 验证 API Key 是否有效（登录 twitterapi.io 查看）

---

### 3. 限流错误

**问题**：`httpx.HTTPStatusError: 429 Too Many Requests`

**解决方案**：
1. 降低并发数：`max_concurrent=1`
2. 减少请求量：`max_seed_tweets=10`
3. 考虑充值账户提升 QPS 限额

---

### 4. 超时错误

**问题**：`asyncio.TimeoutError`

**解决方案**：
```python
# 增加超时时间
# 在 .env 中设置：
HTTP_TIMEOUT=60.0
```

---

### 5. 环境变量未加载

**问题**：`ValidationError: TWITTER_API_KEY field required`

**解决方案**：
1. 确认 `.env` 文件在项目根目录
2. 确认文件名是 `.env` 而不是 `.env.example`
3. 重启 Python 解释器

---

### 6. Python 版本不兼容

**问题**：`SyntaxError: invalid syntax` (使用了新语法如 `str | None`)

**解决方案**：
```bash
# 检查 Python 版本
python --version

# 应该是 3.14 或更高
# 如果版本过低，升级 Python：
# (具体方法取决于你的操作系统)
```

---

## 下一步

安装成功后，你可以：

1. **阅读 API 文档**: [docs/x_crawl_api.md](./x_crawl_api.md)
2. **查看使用示例**: [examples/test_collect_discussions.py](../examples/test_collect_discussions.py)
3. **设计 Agent 接口**: 将 `collect_tweet_discussions` 作为 pydantic-ai Tool

---

## 更新依赖

### 使用 uv

```bash
# 更新所有依赖到最新版本
uv sync --upgrade

# 更新特定依赖
uv add pydantic-ai@latest
```

### 使用 pip

```bash
pip install --upgrade -r requirements.txt
```

---

## 卸载

```bash
# 删除虚拟环境
rm -rf .venv

# 删除配置文件（注意备份）
rm .env

# 删除缓存
rm -rf __pycache__ src/**/__pycache__
```

---

**文档版本**: v0.1.0  
**最后更新**: 2025-01-15  
**维护者**: x_crawl 团队