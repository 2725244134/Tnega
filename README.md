# Tnega: 基于 FastAPI + Redis 的社交内容分析服务

## 🎯 项目概述

Tnega 是一个现代化的社交内容分析平台，采用 **FastAPI + Redis + Celery + PostgreSQL** 架构重构，专为阿拉伯地区对中国"93阅兵"等主题的舆情分析而设计。

### ✨ 核心特性

- **🚀 异步高性能**: 基于 FastAPI 和异步编程，支持高并发处理
- **📊 智能数据采集**: AI 驱动的 Twitter 数据采集，自动优化搜索策略
- **🔄 异步任务处理**: Celery + Redis 实现分布式任务队列，支持重试和监控
- **💾 数据库持久化**: PostgreSQL 存储分析结果，支持复杂查询和统计
- **⚡ 智能缓存**: Redis 缓存层大幅提升重复查询性能
- **🔍 完整讨论追踪**: 自动获取推文回复和 Thread 上下文
- **📈 多维度分析**: 情感分析、趋势分析、摘要生成
- **🐳 容器化部署**: Docker + Docker Compose 一键部署

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    前端层 (Frontend)                        │
├─────────────────────────────────────────────────────────────┤
│                    FastAPI 应用层                           │
│  ┌─────────────┬──────────────┬─────────────┬────────────┐ │
│  │  分析任务API │  任务管理API  │  健康检查API │  缓存管理   │ │
│  └─────────────┴──────────────┴─────────────┴────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    服务层 (Services)                        │
│  ┌──────────────┬────────────────────────────────────────┐ │
│  │ 任务服务层    │ 工作流管理器 (采集 -> 分析 -> 存储)      │ │
│  └──────────────┴────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    任务层 (Tasks)                           │
│  ┌─────────────┬──────────────┬──────────────────────────┐ │
│  │ 采集任务队列 │  分析任务队列  │  定时清理任务            │ │
│  │ (Celery Q1) │ (Celery Q2)   │  (Celery Beat)           │ │
│  └─────────────┴──────────────┴──────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    数据层 (Data)                            │
│  ┌──────────────┬─────────────────┬───────────────────────┐ │
│  │ PostgreSQL   │     Redis       │   文件存储            │ │
│  │  (分析结果)   │   (缓存/队列)    │   (日志/导出)         │ │
│  └──────────────┴─────────────────┴───────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📦 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 后端框架 | FastAPI | 高性能异步 API 框架 |
| 数据库 | PostgreSQL + SQLAlchemy | 数据持久化和 ORM |
| 缓存 | Redis | 高速缓存和消息队列 |
| 任务队列 | Celery | 分布式异步任务处理 |
| AI 框架 | pydantic-ai | 智能分析和决策 |
| 数据采集 | tweepy + twitterapi.io | Twitter 数据采集 |
| 容器化 | Docker + Docker Compose | 容器化部署 |
| 监控 | Prometheus + Grafana | 性能监控和可视化 |

## 🚀 快速开始

### 1. 环境要求

- Python 3.14+
- Docker & Docker Compose
- Twitter API 密钥
- Google Gemini API 密钥

### 2. 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd tnega

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 API 密钥

# 一键启动
./start.sh start
```

### 3. 访问服务

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **任务管理**: http://localhost:8000/api/v1/tasks
- **监控面板**: http://localhost:3000 (Grafana)

## 📋 核心 API 端点

### 分析任务管理

```bash
# 创建分析任务
POST /api/v1/analysis/tasks
{
  "title": "阿拉伯地区对93阅兵的讨论分析",
  "description": "分析阿拉伯语用户对中国93阅兵的态度和讨论热度",
  "search_query": "(China parade OR 93阅兵) lang:ar",
  "target_count": 2000
}

# 获取任务列表
GET /api/v1/analysis/tasks?page=1&page_size=20

# 获取任务状态
GET /api/v1/analysis/tasks/{task_id}/status

# 获取分析结果
GET /api/v1/analysis/tasks/{task_id}/results

# 获取分析汇总
GET /api/v1/analysis/tasks/{task_id}/summary
```

### 系统管理

```bash
# 健康检查
GET /health
GET /health/detailed

# 缓存管理
GET /api/v1/tasks/cache/info
DELETE /api/v1/tasks/cache

# 任务队列管理
GET /api/v1/tasks/queue/status
GET /api/v1/tasks/workers/status
```

## 🔧 开发指南

### 本地开发

```bash
# 安装依赖
uv sync

# 运行数据库迁移
uv run alembic upgrade head

# 启动开发服务器
uv run python app/main.py

# 启动 Celery Worker
uv run celery -A app.tasks.celery_app worker --loglevel=info
```

### 项目结构

```
tnega/
├── app/                    # FastAPI 应用
│   ├── api/               # API 路由
│   ├── core/              # 核心配置和工具
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑服务
│   ├── tasks/             # Celery 任务
│   └── main.py            # 应用入口
├── migrations/            # 数据库迁移
├── docker/                # Docker 配置
├── src/                   # 原始数据采集代码
├── tests/                 # 测试代码
└── start.sh              # 一键启动脚本
```

## 📊 性能优化

### 缓存策略

- **任务状态缓存**: Redis 缓存任务状态，减少数据库查询
- **搜索结果缓存**: 24 小时缓存相同查询的采集结果
- **分析结果缓存**: 分析结果缓存一天，避免重复计算

### 异步处理

- **异步 API**: FastAPI 原生异步支持，高并发处理
- **任务队列**: Celery 分布式处理，支持任务重试和监控
- **数据库连接池**: SQLAlchemy 异步连接池，优化数据库性能

### 数据库优化

- **索引优化**: 针对查询场景创建复合索引
- **分区策略**: 大表分区，提升查询性能
- **读写分离**: 支持读写分离架构

## 🔍 监控和运维

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed

# 数据库健康检查
curl http://localhost:8000/health/database

# Redis 健康检查
curl http://localhost:8000/health/redis
```

### 日志管理

- **结构化日志**: 使用 loguru 输出 JSON 格式日志
- **日志轮转**: 自动按日期分割日志文件
- **错误追踪**: 单独的错误日志文件，便于排查问题

### 性能监控

- **Prometheus 指标**: 自动采集应用性能指标
- **Grafana 仪表板**: 可视化监控面板
- **Celery 监控**: 任务队列状态和性能监控

## 🔐 安全配置

### API 安全

- **输入验证**: Pydantic 模型严格验证输入数据
- **错误处理**: 统一的错误响应，不暴露系统细节
- **限流保护**: 支持 API 限流，防止滥用

### 数据安全

- **敏感信息脱敏**: 日志中自动脱敏敏感信息
- **数据库连接加密**: 支持 SSL/TLS 数据库连接
- **API 密钥管理**: 环境变量管理，不硬编码在代码中

## 📈 扩展功能

### 多语言支持

- **阿拉伯语优化**: 专门针对阿拉伯语文本分析
- **中文支持**: 支持中文内容分析和处理
- **扩展性**: 易于添加新的语言支持

### 数据源扩展

- **多平台支持**: 架构支持扩展到其他社交平台
- **API 适配器**: 统一的数据采集接口，易于添加新数据源
- **插件化设计**: 支持自定义分析插件

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如遇到问题，请：

1. 查看 [FAQ](docs/FAQ.md) 文档
2. 检查 [Issues](https://github.com/your-repo/issues) 页面
3. 创建新的 Issue 描述问题

## 🎉 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [Celery](https://docs.celeryproject.org/) - 分布式任务队列
- [Redis](https://redis.io/) - 高性能内存数据库
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [pydantic-ai](https://ai.pydantic.dev/) - AI 智能体框架
- [twitterapi.io](https://twitterapi.io/) - Twitter API 服务

---

**Tnega** - 让社交内容分析更简单、更智能！ 🚀