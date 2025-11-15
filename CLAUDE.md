# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 项目概述

Tnega 是一个基于 **FastAPI + Redis + Celery + PostgreSQL** 的现代化社交内容分析服务，专注于阿拉伯地区对中国"93阅兵"等主题的舆情分析。重构后的架构采用微服务设计理念，支持高并发、分布式处理和企业级部署。

## 🏗️ 新架构设计

```
app/
├── api/           # FastAPI 路由层
│   ├── endpoints/ # API 端点（分析、任务、健康检查）
│   └── router.py  # 路由注册
├── core/          # 核心配置和基础设施
│   ├── config.py  # 环境配置（数据库、Redis、Celery）
│   ├── database.py # PostgreSQL 连接管理
│   ├── redis.py   # Redis 缓存管理
│   └── logger.py  # 日志配置
├── models/        # 数据模型
│   ├── base.py    # SQLAlchemy 基础模型
│   ├── analysis.py # 分析任务、结果、推文数据模型
│   └── schemas.py # Pydantic 请求/响应模式
├── services/      # 业务逻辑层
│   └── task_service.py # 任务管理和工作流服务
├── tasks/         # Celery 异步任务
│   ├── celery_app.py   # Celery 配置
│   ├── analysis.py     # 分析任务（情感、趋势、摘要）
│   ├── collection.py   # 数据采集任务
│   └── twitter_client.py # Twitter 客户端适配器
└── main.py        # FastAPI 应用入口
```

## 🔧 开发命令（重构后）

### 环境设置
```bash
# 安装依赖（使用 uv）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件填入 API 密钥
```

### 本地开发
```bash
# 运行数据库迁移
uv run alembic upgrade head

# 启动 FastAPI 开发服务器
uv run python app/main.py

# 启动 Celery Worker（分析任务）
uv run celery -A app.tasks.celery_app worker -Q analysis --loglevel=info

# 启动 Celery Worker（采集任务）
uv run celery -A app.tasks.celery_app worker -Q collection --loglevel=info

# 启动 Celery Beat（定时任务）
uv run celery -A app.tasks.celery_app beat --loglevel=info
```

### Docker 部署
```bash
# 一键启动所有服务
./start.sh start

# 查看服务状态
./start.sh status

# 查看日志
./start.sh logs --service api

# 停止服务
./start.sh stop
```

## 📋 API 端点（新）

### 分析任务管理
```bash
# 创建分析任务
POST /api/v1/analysis/tasks
{
  "title": "阿拉伯地区对93阅兵的讨论分析",
  "description": "分析阿拉伯语用户对中国93阅兵的态度",
  "search_query": "(China parade OR 93阅兵) lang:ar",
  "target_count": 2000
}

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
GET /health/database
GET /health/redis

# 任务队列管理
GET /api/v1/tasks/queue/status
GET /api/v1/tasks/workers/status

# 缓存管理
GET /api/v1/tasks/cache/info
DELETE /api/v1/tasks/cache
```

## 🗄️ 数据库模型（新）

### 核心表结构
- **analysis_tasks**: 分析任务表（状态、进度、参数）
- **analysis_results**: 分析结果表（情感、趋势、摘要）
- **tweet_data**: 推文数据表（原始数据、元数据、分析状态）
- **analysis_cache**: 分析缓存表（缓存键、过期时间、访问统计）

### 索引优化
- 任务状态索引 (`idx_analysis_tasks_status`)
- 时间范围索引 (`idx_tweet_data_created_at`)
- 语言过滤索引 (`idx_tweet_data_lang`)
- 缓存过期索引 (`idx_analysis_cache_expires_at`)

## ⚡ 异步任务系统

### Celery 队列配置
- **analysis 队列**: 处理推文分析任务（情感、趋势、摘要）
- **collection 队列**: 处理数据采集任务（Twitter API 调用）
- **定时任务**: 清理过期数据、验证数据完整性

### 任务状态管理
- **PENDING**: 等待执行
- **RUNNING**: 执行中
- **COMPLETED**: 完成
- **FAILED**: 失败（支持重试）
- **CANCELLED**: 已取消

## 💾 缓存策略

### Redis 缓存键命名
```python
CacheKey.analysis_result(task_id)     # 分析结果缓存
CacheKey.task_status(task_id)         # 任务状态缓存
CacheKey.tweet_data(tweet_id)         # 推文数据缓存
CacheKey.search_results(query_hash)   # 搜索结果缓存
```

### 缓存过期时间
- 任务状态: 5 分钟
- 搜索结果: 24 小时
- 分析结果: 24 小时

## 🔧 关键配置

### 环境变量（前缀：TNEGA_）
```bash
# 数据库
TNEGA_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Redis
TNEGA_REDIS_URL=redis://host:port/db
TNEGA_CELERY_BROKER_URL=redis://host:port/1
TNEGA_CELERY_RESULT_BACKEND=redis://host:port/2

# API 密钥
TNEGA_TWITTER_API_KEY=your_twitter_api_key
TNEGA_GOOGLE_API_KEY=your_google_api_key
```

## 🚫 关键约束（保持原有）

### 代码规范
- **类型安全**: 所有公开函数必须标注类型
- **异步优先**: 所有 I/O 操作必须异步
- **文件限制**: 每个文件不超过 800 行
- **目录限制**: 每层目录不超过 8 个文件
- **命名规则**: snake_case（模块）、PascalCase（类）

### 架构原则
- **解耦设计**: x_crawl（数据采集）与 agent（智能分析）分离
- **类型安全**: 强制 Pydantic 模型验证
- **错误传播**: 异常传播优于捕获
- **中文注释**: 面向中文开发者

## 🚀 部署和运维

### 性能优化
- **连接池**: 数据库和 Redis 连接池配置
- **并发控制**: 最大并发任务数限制
- **内存管理**: Worker 最大任务数后重启
- **监控指标**: Prometheus + Grafana 集成

### 扩展性
- **水平扩展**: 支持多个 Worker 实例
- **队列分离**: 不同类型任务使用不同队列
- **数据库分片**: 支持读写分离和分片
- **缓存集群**: Redis 集群支持

## 🎯 开发建议

1. **优先使用异步**: 所有数据库和外部 API 调用都使用 async/await
2. **缓存优先**: 重复查询优先考虑 Redis 缓存
3. **任务拆分**: 大任务拆分为多个小任务，提高并发性
4. **错误重试**: 外部 API 调用必须实现重试机制
5. **监控日志**: 关键操作添加结构化日志，便于排查问题

## 📊 性能指标

- **API 响应时间**: < 100ms（缓存命中）
- **任务处理速度**: 1000+ 推文/分钟
- **并发任务数**: 支持 100+ 并发任务
- **缓存命中率**: > 80%
- **系统可用性**: > 99.9%