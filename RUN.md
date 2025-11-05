# 🚀 快速运行指南

> 5 分钟从零到采集推文数据

---

## 📋 前置要求

### 1. 安装依赖

```bash
# 克隆仓库（如果还没有）
cd Tnega

# 安装依赖
uv sync
```

### 2. 获取 API Keys

你需要两个 API Key：

#### Twitter API Key
1. 访问 [twitterapi.io](https://twitterapi.io/)
2. 注册并获取 API Key
3. 记录你的 `TWITTERAPI_KEY`

#### Google Gemini API Key
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建 API Key
3. 记录你的 `GOOGLE_API_KEY`

#### Logfire Token（可选，用于监控）
1. 访问 [logfire.pydantic.dev](https://logfire.pydantic.dev/)
2. 注册并创建项目
3. 获取 Write Token

---

## ⚙️ 配置环境变量

### 方式 1: 使用 .env 文件（推荐）

```bash
# 复制模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

添加以下内容：

```bash
# Twitter API（必需）
TWITTERAPI_KEY=your_twitter_api_key_here

# Google Gemini API（必需）
GOOGLE_API_KEY=your_gemini_api_key_here

# Logfire 监控（可选）
LOGFIRE_TOKEN=your_logfire_token_here

# 环境标识
ENV=production
```

### 方式 2: 直接设置环境变量

```bash
export TWITTERAPI_KEY="your_twitter_api_key_here"
export GOOGLE_API_KEY="your_gemini_api_key_here"
export LOGFIRE_TOKEN="your_logfire_token_here"  # 可选
```

---

## 🎯 运行采集任务

### 快速开始（使用默认配置）

```bash
uv run python main.py
```

**默认配置**:
- 需求: 找阿拉伯地区对中国 93 阅兵的讨论
- 目标: 2000 条推文
- 模型: gemini-2.0-flash-exp
- 输出: `data/output/agent_YYYYMMDD_HHMMSS_final.csv`

---

## 🔧 自定义运行

### 1. 自定义采集需求

```bash
uv run python main.py --request "找美国对中国太空站的讨论"
```

### 2. 指定目标数量

```bash
# 采集 5000 条推文
uv run python main.py --target 5000
```

### 3. 使用不同的 Gemini 模型

```bash
# 使用 Gemini 2.0 Flash（更快）
uv run python main.py --model gemini-2.0-flash-exp

# 使用 Gemini 1.5 Pro（更强）
uv run python main.py --model gemini-1.5-pro

# 使用 Gemini 2.5 Pro（最强，如果可用）
uv run python main.py --model gemini-2.5-pro
```

### 4. 组合使用

```bash
uv run python main.py \
  --request "找日本对中国新能源汽车的讨论" \
  --target 3000 \
  --model gemini-2.0-flash-exp \
  --max-attempts 15
```

### 5. 禁用 Logfire 监控

```bash
uv run python main.py --no-logfire
```

---

## 📊 查看结果

### 运行时输出

程序会实时显示：

```
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
Tnega - AI-Powered Twitter Data Intelligence
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

📋 任务配置:
  - 用户需求: 找阿拉伯地区对中国 93 阅兵的讨论
  - 目标数量: 2000 条推文
  - 最大尝试: 10 次
  - LLM 模型: gemini-2.0-flash-exp
  - 输出目录: data/output

... (采集进度) ...

============================================================
✅ 采集成功！
============================================================

成功采集 2134 条推文，共尝试 7 次。已达到目标 2000 条。

📊 详细统计:
  - 总推文数: 2134 条
  - 尝试次数: 7 次
  - 总耗时: 245.3 秒
  - 平均速度: 8.7 条/秒

💾 输出文件:
  data/output/agent_20251104_153045_final.csv
  文件大小: 456.2 KB

🎯 终止原因:
  已达到目标数量 2000 条

🔍 使用的查询 (7 个):
  1. China 93 parade lang:ar since:2015-09-01
  2. 中国阅兵 lang:ar since:2015-08-01
  3. ...
```

### 输出文件格式

生成的 CSV 文件包含以下字段：

| 字段 | 说明 |
|------|------|
| `tweet_id` | 推文唯一 ID |
| `text` | 推文文本内容 |
| `created_at` | 发布时间 |
| `author_name` | 作者名称 |
| `lang` | 语言代码 |
| `like_count` | 点赞数 |
| `retweet_count` | 转推数 |
| `reply_count` | 回复数 |
| `view_count` | 浏览数 |
| `location` | 用户位置 |
| `is_reply` | 是否为回复 |
| `conversation_id` | 会话 ID |

### 打开 CSV 文件

```bash
# 使用命令行查看前 10 行
head -n 10 data/output/agent_YYYYMMDD_HHMMSS_final.csv

# 使用 Python 分析
python -c "
import pandas as pd
df = pd.read_csv('data/output/agent_YYYYMMDD_HHMMSS_final.csv')
print(df.head())
print(f'\n总推文数: {len(df)}')
print(f'语言分布:\n{df[\"lang\"].value_counts()}')
"

# 或使用 Excel/LibreOffice 打开
```

---

## 🐛 故障排查

### 问题 1: `TWITTERAPI_KEY not set`

**原因**: 环境变量未配置

**解决**:
```bash
export TWITTERAPI_KEY="your_key_here"
# 或编辑 .env 文件
```

### 问题 2: `GOOGLE_API_KEY not set`

**原因**: Gemini API Key 未配置

**解决**:
```bash
export GOOGLE_API_KEY="your_key_here"
# 或编辑 .env 文件
```

### 问题 3: `API Rate Limit Exceeded`

**原因**: Twitter API 限流

**解决**:
- 等待一段时间（通常 15 分钟）
- 或降低并发度（修改 `src/agent/config.py` 中的 `default_max_tweets_per_attempt`）

### 问题 4: 采集速度很慢

**原因**: 网络延迟或 API 响应慢

**建议**:
- 使用更快的网络
- 切换到 `gemini-2.0-flash-exp`（更快的模型）
- 减小目标数量

### 问题 5: 采集结果与需求不符

**原因**: Agent 理解偏差

**解决**:
- 使用更明确的需求描述
- 尝试更强的模型（如 `gemini-1.5-pro`）
- 查看 Logfire Trace 分析 Agent 的决策过程

---

## 📈 监控与调试

### 启用详细日志

```bash
# 设置日志级别
export LOGURU_LEVEL=DEBUG

uv run python main.py
```

### 查看 Logfire Trace

如果配置了 `LOGFIRE_TOKEN`:

1. 访问 https://logfire.pydantic.dev/
2. 选择你的项目
3. 查看最新的 Trace
4. 分析 Agent 的：
   - LLM 调用次数
   - Tool 调用情况
   - 决策逻辑
   - 性能瓶颈

### 本地调试模式

如果想快速测试而不调用真实 API：

```bash
# 使用 TestModel（模拟模式）
uv run python demo_agent.py
```

---

## 🎓 进阶用法

### 1. 批量采集多个需求

创建 `tasks.txt`:
```
找阿拉伯地区对中国 93 阅兵的讨论
找美国对中国太空站的讨论
找欧洲对中国一带一路的讨论
```

运行脚本：
```bash
while IFS= read -r request; do
  uv run python main.py --request "$request" --target 1000
done < tasks.txt
```

### 2. 定时采集（Cron）

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点采集
0 2 * * * cd /path/to/Tnega && /path/to/uv run python main.py >> logs/cron.log 2>&1
```

### 3. Docker 部署

```dockerfile
FROM python:3.14-slim

WORKDIR /app
COPY . .

RUN pip install uv && uv sync

CMD ["uv", "run", "python", "main.py"]
```

```bash
docker build -t tnega .
docker run -e TWITTERAPI_KEY=$TWITTERAPI_KEY \
           -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
           -v $(pwd)/data:/app/data \
           tnega
```

---

## 📚 相关文档

- [快速开始指南](docs/QUICKSTART.md) - 完整的环境配置
- [架构说明](.github/copilot-instructions.md) - 系统设计理念
- [测试指南](docs/testing-guide.md) - 如何编写测试
- [监控指南](docs/monitoring-guide.md) - Logfire 深度使用

---

## 💡 最佳实践

1. **首次运行**: 先用 `--target 100` 测试，确保一切正常
2. **成本控制**: 使用 `gemini-2.0-flash-exp` 而非 Pro 版本（更便宜）
3. **数据备份**: 定期备份 `data/output/` 目录
4. **监控**: 生产环境务必启用 Logfire
5. **速率限制**: 避免短时间内多次运行（Twitter API 限流）

---

## 🎉 完成！

现在你已经可以：
- ✅ 使用 Gemini 2.5 Pro 智能采集推文
- ✅ 自定义采集需求和参数
- ✅ 获取高质量的结构化数据
- ✅ 监控和调试采集过程

**祝你采集顺利！** 🚀