"""
============================================
93 阅兵（2025）阿语推文历史回填脚本
============================================
针对阿拉伯语用户的讨论，批量抓取并保存到 data/ 目录
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from loguru import logger

from src.x_crawl import TwitterCrawler, save_results


@dataclass(frozen=True)
class QuerySpec:
    """描述一次搜索任务"""

    label: str
    query: str


DEFAULT_QUERIES: tuple[QuerySpec, ...] = (
    QuerySpec(
        label="parade2025_ar_signature",
        query='(الصين OR بكين) ("العرض العسكري" OR "استعراض عسكري") (2025 OR "ذكرى النصر")',
    ),
    QuerySpec(
        label="parade2025_ar_victory",
        query='("يوم النصر" OR "ذكرى النصر") (الصين OR بكين) (العرض)',
    ),
    QuerySpec(
        label="parade2025_ar_hashtags",
        query='(#الصين OR #العرض_العسكري OR #بكين) (2025 OR "ذكرى")',
    ),
    QuerySpec(
        label="parade2025_ar_coalition",
        query='(الصين OR بكين) (العرض OR الاحتفال) (العالم العربي OR الخليج OR السعودية OR الامارات)',
    ),
)


def parse_date(value: str) -> datetime:
    """Parse YYYY-MM-DD string to aware datetime at start of day UTC."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iter_windows(start: datetime, end: datetime, window_days: int) -> Iterable[tuple[datetime, datetime]]:
    """Yield sliding windows within [start, end)."""
    cursor = start
    delta = timedelta(days=window_days)

    while cursor < end:
        window_end = min(cursor + delta, end)
        yield cursor, window_end
        cursor = window_end


async def backfill_window(
    crawler: TwitterCrawler,
    spec: QuerySpec,
    window_start: datetime,
    window_end: datetime,
    *,
    max_pages: int | None,
    max_results: int,
    page_pause: float,
    output_format: str,
) -> None:
    iso_start = window_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    iso_end = window_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    window_label = f"{spec.label}_{window_start:%Y%m%d}_{window_end:%Y%m%d}"
    logger.info(
        "🛰️ 开始抓取: %s | %s → %s", spec.label, iso_start, iso_end
    )

    results = await crawler.search_all_tweets_paginated(
        spec.query,
        start_time=iso_start,
        end_time=iso_end,
        max_results=max_results,
        max_pages=max_pages,
        page_pause=page_pause,
        label=window_label,
        language="ar",
    )

    if not results.tweets:
        logger.warning("⚠️ 无结果: %s (%s → %s)", spec.label, iso_start, iso_end)
        return

    if results.metadata:
        results.metadata.label = window_label
        results.metadata.total_collected = results.result_count
        results.metadata.language = results.metadata.language or "ar"

    output_path = save_results(results, window_label, format=output_format)
    logger.success(
        "💾 保存完成: %s | 推文 %s 条 → %s",
        window_label,
        results.result_count,
        output_path,
    )


async def async_main(args: argparse.Namespace) -> None:
    start = parse_date(args.start)
    # include the entire end date until 23:59:59 by adding one day and treating window as [start, end)
    end = parse_date(args.end) + timedelta(days=1)

    selected_specs = [
        spec
        for spec in DEFAULT_QUERIES
        if not args.queries or spec.label in args.queries
    ]

    if not selected_specs:
        raise SystemExit("未匹配到任何查询标签，请检查 --queries 参数")

    crawler = TwitterCrawler()

    try:
        for window_start, window_end in iter_windows(start, end, args.window_days):
            for spec in selected_specs:
                await backfill_window(
                    crawler,
                    spec,
                    window_start,
                    window_end,
                    max_pages=args.max_pages,
                    max_results=args.max_results,
                    page_pause=args.page_pause,
                    output_format=args.format,
                )
    finally:
        await crawler.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取 2025 中国 93 阅兵相关的阿语推文",
    )
    parser.add_argument("--start", default="2024-12-01", help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-12-31", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--window-days", type=int, default=14, help="分割时间窗口的天数")
    parser.add_argument("--max-pages", type=int, default=None, help="每个窗口最大分页次数")
    parser.add_argument("--max-results", type=int, default=400, help="每页抓取数量 (≤500)")
    parser.add_argument("--page-pause", type=float, default=3.5, help="分页间隔秒数")
    parser.add_argument(
        "--format",
        choices=("json", "jsonl"),
        default="json",
        help="保存格式",
    )
    parser.add_argument(
        "--queries",
        nargs="*",
        help="仅运行指定标签的查询 (默认运行全部)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logger.info("🚀 启动阿语历史回填任务")
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
