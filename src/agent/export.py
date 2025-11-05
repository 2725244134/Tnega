"""
============================================
推文数据导出工具
============================================
职责：将 Deps 中的推文文本导出为 CSV 文件
"""

from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from src.agent.agent import Deps

# ============================================
# 导出结果模型
# ============================================


class ExportResult(BaseModel):
    """
    CSV 导出结果摘要

    职责：
    - 报告导出的文件路径和统计信息
    - 用于 Agent 反馈和日志记录
    """

    success: bool = Field(..., description="是否导出成功")
    file_path: str = Field(..., description="导出文件的完整路径")
    tweet_count: int = Field(..., description="导出的推文数量")
    file_size_bytes: int = Field(default=0, description="文件大小（字节）")
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="导出时间（UTC）",
    )
    error_message: str | None = Field(default=None, description="错误信息（如果失败）")


# ============================================
# 核心导出函数
# ============================================


async def export_tweets_to_csv(
    deps: Deps,
    filename: str = "tweets.csv",
    output_dir: str = "output",
) -> ExportResult:
    """
    将 Deps 中的推文文本导出为 CSV 文件（异步 I/O）

    CSV 格式：
    - 列 1: tweet_id（自动生成的序号，从 1 开始）
    - 列 2: text（推文文本内容）

    Args:
        deps: Agent 依赖注入容器（包含推文文本集合）
        filename: 文件名（默认 tweets.csv）
        output_dir: 输出目录（默认 output/）

    Returns:
        ExportResult: 导出结果摘要

    Example:
        >>> deps = Deps()
        >>> deps.add_tweet_text("Hello World")
        >>> deps.add_tweet_text("AI is amazing")
        >>> result = await export_tweets_to_csv(deps, "my_tweets.csv")
        >>> print(f"导出 {result.tweet_count} 条推文到 {result.file_path}")
    """
    try:
        # ========== 准备输出路径 ==========
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / filename
        absolute_path = file_path.resolve()

        logger.info(f"开始导出推文到: {absolute_path}")

        # ========== 检查数据 ==========
        if not deps.tweet_texts:
            logger.warning("没有推文数据可导出")
            return ExportResult(
                success=False,
                file_path=str(absolute_path),
                tweet_count=0,
                error_message="没有推文数据",
            )

        # ========== 写入 CSV（异步 I/O）==========
        # 先在内存中构建 CSV 内容（set 转 list 排序，确保可复现）
        sorted_texts = sorted(deps.tweet_texts)

        # 构建 CSV 内容
        csv_lines = []
        csv_lines.append("tweet_id,text")  # Header

        for idx, text in enumerate(sorted_texts, start=1):
            # 转义引号和换行符（CSV 标准）
            escaped_text = text.replace('"', '""')
            csv_lines.append(f'{idx},"{escaped_text}"')

        csv_content = "\n".join(csv_lines)

        # 异步写入文件
        async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
            await f.write(csv_content)

        # ========== 获取文件大小 ==========
        file_size = file_path.stat().st_size

        logger.info(
            f"导出成功: {len(sorted_texts)} 条推文, "
            f"文件大小: {file_size} 字节, "
            f"路径: {absolute_path}"
        )

        return ExportResult(
            success=True,
            file_path=str(absolute_path),
            tweet_count=len(sorted_texts),
            file_size_bytes=file_size,
        )

    except Exception as e:
        logger.error(f"导出失败: {e}")
        return ExportResult(
            success=False,
            file_path=str(absolute_path) if "absolute_path" in locals() else filename,
            tweet_count=0,
            error_message=str(e),
        )


# ============================================
# Agent Tool 包装
# ============================================


async def export_tweets_tool(
    ctx: RunContext[Deps],
    filename: str = "tweets.csv",
    output_dir: str = "output",
) -> ExportResult:
    """
    Agent 工具：导出推文到 CSV

    **输入**：
    - `filename`: CSV 文件名（默认 tweets.csv）
    - `output_dir`: 输出目录（默认 output/）

    **返回**：
    - `success`: 是否成功
    - `file_path`: 文件完整路径
    - `tweet_count`: 导出的推文数量
    - `file_size_bytes`: 文件大小
    - `exported_at`: 导出时间
    - `error_message`: 错误信息（如果失败）

    Example:
        >>> # Agent 自动调用
        >>> result = await agentx.run(
        ...     "采集完成后保存为 tweets.csv",
        ...     deps=deps
        ... )
    """
    return await export_tweets_to_csv(
        deps=ctx.deps,
        filename=filename,
        output_dir=output_dir,
    )
