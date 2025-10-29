# Tnega

异步 Twitter/X 抓取工具集，聚焦中国 93 阅兵等专题数据采集。

## 快速开始

```bash
uv sync
uv run python scripts/backfill_parade_2025_ar.py --start 2024-12-01 --end 2025-12-31
```

> 请在 `.env` 或环境变量中配置 `BEARER_TOKEN`（不区分大小写）。
