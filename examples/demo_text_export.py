"""
============================================
示例：提取推文文本并导出
============================================
演示如何从采集结果中提取所有文本并导出为文件
"""

import asyncio
from pathlib import Path

from loguru import logger

from src.x_crawl import (
    collect_tweet_discussions,
    create_client,
    export_texts_from_collection,
)


async def main():
    """提取推文文本示例"""
    
    # ============================================
    # 步骤 1: 采集推文
    # ============================================
    logger.info("开始采集推文...")
    
    query = "(China parade OR 93阅兵) lang:ar"
    
    async with create_client() as client:
        result = await collect_tweet_discussions(
            query=query,
            client=client,
            max_seed_tweets=10,
            max_replies_per_tweet=5,
            include_thread=True,
            max_concurrent=2,
        )
    
    logger.info(f"✅ 采集完成: {len(result.items)} 条种子推文")
    logger.info(f"   总推文数: {result.total_tweets}")
    logger.info(f"   总回复数: {result.total_replies}")
    logger.info(f"   Thread 数: {result.total_threads}")
    
    # ============================================
    # 步骤 2: 提取并导出文本
    # ============================================
    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 方案 A: 导出为带编号的 TXT（推荐给非技术人员）
    logger.info("\n导出为带编号的 TXT...")
    texts = export_texts_from_collection(
        collection=result,
        output_path=output_dir / "93阅兵_推文_带编号.txt",
        file_format="txt",
        txt_style="numbered",  # [1] text...
        clean=True,
    )
    
    # 方案 B: 导出为分隔线格式的 TXT
    logger.info("\n导出为分隔线格式的 TXT...")
    export_texts_from_collection(
        collection=result,
        output_path=output_dir / "93阅兵_推文_分隔线.txt",
        file_format="txt",
        txt_style="separated",  # === 推文 1 ===
        clean=True,
    )
    
    # 方案 C: 导出为纯文本（每行一条）
    logger.info("\n导出为纯文本...")
    export_texts_from_collection(
        collection=result,
        output_path=output_dir / "93阅兵_推文_纯文本.txt",
        file_format="txt",
        txt_style="plain",
        clean=True,
    )
    
    # 方案 D: 导出为完整 CSV（推荐！包含元数据）
    logger.info("\n导出为完整 CSV（包含来源、作者、时间、互动数据）...")
    export_texts_from_collection(
        collection=result,
        output_path=output_dir / "93阅兵_推文_完整版.csv",
        file_format="csv",
        csv_mode="full",  # 完整版
        clean=True,
    )
    
    # 方案 E: 导出为简单 CSV（仅文本）
    logger.info("\n导出为简单 CSV（仅文本内容）...")
    export_texts_from_collection(
        collection=result,
        output_path=output_dir / "93阅兵_推文_简单版.csv",
        file_format="csv",
        csv_mode="simple",  # 简单版
        clean=True,
    )
    
    # ============================================
    # 步骤 3: 查看导出结果
    # ============================================
    logger.info("\n" + "=" * 60)
    logger.success("✅ 所有格式导出完成！")
    logger.info("=" * 60)
    logger.info(f"导出文件位置: {output_dir.absolute()}")
    logger.info(f"共导出 {len(texts)} 条唯一推文")
    logger.info("\n生成的文件：")
    for file in sorted(output_dir.glob("93阅兵_推文*")):
        size_kb = file.stat().st_size / 1024
        logger.info(f"  - {file.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
