# 🚀 Tnega 生产环境使用指南

> AI 驱动的 Twitter 数据智能采集系统 - 使用 Gemini 2.0 Flash Exp

---

## 📖 快速开始

### 1. 安装依赖

```bash
cd Tnega
uv sync
```

### 2. 配置 API Keys

创建 `.env` 文件：

```bash
# Twitter API（必需）
TWITTERAPI_KEY=your_twitter_api_key_here

# Google Gemini API（必需）
GOOGLE_API_KEY=your_gemini_api_key_here

# Logfire 监控（可选）
LOGFIRE_TOKEN=your_logfire_token_here
```

### 3. 运行采集

```bash
# 方式 1: 使用脚本（推荐）
./run.sh

# 方式 2: 直接运行 Python
uv run python main.py
```

---

## 🎯 核心功能

- ✅ **智能查询生成**: Gemini 2.0 自动生成最优 Twitter 搜索查询
- ✅ **自动去重**: 智能去除重复推文
- ✅ **进度监控**: 实时显示采集进度和统计
- ✅ **多轮迭代**: 自动调整策略直到达成目标
- ✅ **结构化输出**: CSV 格式，包含完整元数据

---

## 📋 使用示例

### 默认配置（采集阿拉伯地区93阅兵讨论）

```bash
uv run python main.py
```

### 自定义需求

```bash
# 采集美国对中国太空站的讨论
uv run python main.py --request "找美国对中国太空站的讨论"

# 采集 5000 条推文
uv run python main.py --target 5000

# 使用 Gemini 1.5 Pro
uv run python main.py --model gemini-1.5-pro

# 组合使用
uv run python main.py \
  --request "找欧洲对中国电动车的讨论" \
  --target 3000 \
  --model gemini-2.0-flash-exp
```

---

## 📊 输出格式

生成的 CSV 文件位于 `data/output/`，包含字段：

| 字段 | 说明 |
|------|------|
| `tweet_id` | 推文唯一标识符 |
| `text` | 推文完整文本 |
| `created_at` | 发布时间（UTC） |
| `author_name` | 作者显示名称 |
| `lang` | 语言代码（如 ar, en） |
| `like_count` | 点赞数 |
| `retweet_count` | 转推数 |
| `reply_count` | 回复数 |
| `view_count` | 浏览数 |
| `location` | 用户位置信息 |
| `is_reply` | 是否为回复 |
| `conversation_id` | 会话线程 ID |

---

## ⚙️ 参数说明

```bash
uv run python main.py --help
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--request` | "找阿拉伯地区对中国 93 阅兵的讨论" | 采集需求（自然语言） |
| `--target` | 2000 | 目标推文数量 |
| `--max-attempts` | 10 | 最大尝试次数 |
| `--model` | gemini-2.0-flash-exp | LLM 模型名称 |
| `--output-dir` | data/output | 输出目录 |
| `--no-logfire` | - | 禁用 Logfire 监控 |

---

## 🔧 常见问题

### Q: 如何获取 Twitter API Key？

访问 [twitterapi.io](https://twitterapi.io/) 注册并获取。

### Q: 如何获取 Gemini API Key？

访问 [Google AI Studio](https://makersuite.google.com/app/apikey) 创建。

### Q: 支持哪些 Gemini 模型？

- `gemini-2.0-flash-exp` - 最快，推荐生产使用
- `gemini-1.5-flash` - 平衡性能
- `gemini-1.5-pro` - 最强理解能力
- `gemini-2.5-pro` - 如果可用（需确认 API 访问权限）

### Q: 采集速度有多快？

通常 5-15 条/秒，取决于：
- 网络延迟
- Twitter API 响应速度
- Gemini 模型选择
- 查询复杂度

### Q: 如何监控采集过程？

配置 `LOGFIRE_TOKEN` 后访问 [logfire.pydantic.dev](https://logfire.pydantic.dev/) 查看完整 Trace。

---

## 🎓 高级用法

### 批量采集多个需求

```bash
# 创建任务列表
cat > tasks.txt << EOF
找阿拉伯地区对中国 93 阅兵的讨论
找美国对中国太空站的讨论
找欧洲对中国一带一路的讨论
EOF

# 批量执行
while IFS= read -r request; do
  uv run python main.py --request "$request"
done < tasks.txt
```

### 定时采集（Cron）

```bash
# 每天凌晨 2 点运行
0 2 * * * cd /path/to/Tnega && /path/to/uv run python main.py >> logs/cron.log 2>&1
```

### Docker 部署

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
ENV TWITTERAPI_KEY=""
ENV GOOGLE_API_KEY=""
CMD ["uv", "run", "python", "main.py"]
```

---

## 📚 文档导航

- [完整文档](docs/README.md) - 文档索引
- [快速开始](docs/QUICKSTART.md) - 详细配置说明
- [运行指南](RUN.md) - 完整运行文档
- [架构说明](.github/copilot-instructions.md) - 系统设计
- [测试指南](docs/testing-guide.md) - 开发测试
- [重构总结](REFACTOR_SUMMARY.md) - 最新改动

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────┐
│  main.py (用户入口)                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  Agent 层 (pydantic-ai + Gemini 2.0)            │
│  - 理解用户需求                                 │
│  - 生成搜索查询                                 │
│  - 决策采集策略                                 │
│  - 判断终止条件                                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  x_crawl 层 (Twitter API v2)                    │
│  - 执行推文搜索                                 │
│  - 采集回复和线程                               │
│  - 数据清洗与去重                               │
│  - CSV 导出                                     │
└─────────────────────────────────────────────────┘
```

---

## 💡 最佳实践

1. **首次运行**: 先用 `--target 100` 测试
2. **成本控制**: 优先使用 `gemini-2.0-flash-exp`
3. **数据备份**: 定期备份 `data/output/`
4. **监控启用**: 生产环境必须配置 Logfire
5. **限流遵守**: 避免短时间内频繁调用

---

## 🐛 故障排查

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `TWITTERAPI_KEY not set` | 环境变量未配置 | 设置 `export TWITTERAPI_KEY=...` 或编辑 `.env` |
| `GOOGLE_API_KEY not set` | Gemini API Key 未配置 | 设置 `export GOOGLE_API_KEY=...` 或编辑 `.env` |
| `Rate Limit Exceeded` | Twitter API 限流 | 等待 15 分钟或降低并发度 |
| 采集结果不符预期 | Agent 理解偏差 | 使用更明确的需求描述或更强的模型 |

---

## 📞 支持

- 🐛 [报告 Bug](https://github.com/your-org/Tnega/issues)
- 💬 [讨论交流](https://github.com/your-org/Tnega/discussions)
- 📧 联系维护者

---

## 📄 许可证

本项目遵循 MIT 许可证。

---

**Tnega** - 让数据采集变得智能 🚀