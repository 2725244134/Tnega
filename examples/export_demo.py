"""
============================================
推文导出功能示例（方案 B：手动调用）
============================================
演示如何：
1. 初始化 Agent 和 Deps
2. 采集推文数据
3. 手动导出到 CSV 文件
"""

import asyncio

from loguru import logger

from src.agent.agent import Deps, agentx
from src.agent.export import export_tweets_to_csv


async def main():
    """主函数：采集 + 导出工作流"""

    logger.info("=" * 60)
    logger.info("开始推文采集与导出流程")
    logger.info("=" * 60)

    # ========== 步骤 1: 初始化 Deps ==========
    deps = Deps()
    logger.info("✓ Deps 初始化完成")

    # ========== 步骤 2: 使用 Agent 采集推文 ==========
    logger.info("\n开始采集推文...")

    try:
        # 示例 1: 采集关于"93阅兵"的阿拉伯语推文
        result = await agentx.run(
            user_prompt='采集关于 "93阅兵" 或 "China parade" 的阿拉伯语推文，最多 100 条',
            deps=deps,
        )

        logger.info("✓ 第一次采集完成")
        logger.info(f"  - 尝试次数: {deps.attempt_count}")
        logger.info(f"  - 累计推文: {deps.fetched_count}")

        # 示例 2: 再次采集（可选，测试去重）
        result2 = await agentx.run(
            user_prompt="再采集一次相同的查询，测试去重",
            deps=deps,
        )

        logger.info("✓ 第二次采集完成")
        logger.info(f"  - 尝试次数: {deps.attempt_count}")
        logger.info(f"  - 累计推文: {deps.fetched_count}")

    except Exception as e:
        logger.error(f"✗ 采集失败: {e}")
        return

    # ========== 步骤 3: 手动导出到 CSV ==========
    if deps.fetched_count == 0:
        logger.warning("没有采集到推文，跳过导出")
        return

    logger.info(f"\n开始导出 {deps.fetched_count} 条推文...")

    export_result = await export_tweets_to_csv(
        deps=deps,
        filename="tweets_93_parade.csv",
        output_dir="output",
    )

    # ========== 步骤 4: 检查导出结果 ==========
    if export_result.success:
        logger.info("=" * 60)
        logger.info("✓ 导出成功！")
        logger.info(f"  - 文件路径: {export_result.file_path}")
        logger.info(f"  - 推文数量: {export_result.tweet_count}")
        logger.info(f"  - 文件大小: {export_result.file_size_bytes} 字节")
        logger.info(f"  - 导出时间: {export_result.exported_at}")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error("✗ 导出失败！")
        logger.error(f"  - 错误信息: {export_result.error_message}")
        logger.error("=" * 60)


# ============================================
# 进阶示例：批量导出不同查询
# ============================================


async def batch_export_demo():
    """演示批量采集和分别导出"""

    queries = [
        ("93阅兵 lang:ar", "tweets_parade_ar.csv"),
        ("China military lang:ar", "tweets_military_ar.csv"),
        ("中国阅兵 lang:zh", "tweets_parade_zh.csv"),
    ]

    for query, filename in queries:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"处理查询: {query}")
        logger.info(f"{'=' * 60}")

        # 每个查询使用独立的 Deps
        deps = Deps()

        try:
            # 采集
            await agentx.run(
                user_prompt=f"采集推文: {query}",
                deps=deps,
            )

            # 导出
            if deps.fetched_count > 0:
                result = await export_tweets_to_csv(
                    deps=deps,
                    filename=filename,
                    output_dir="output/batch",
                )

                if result.success:
                    logger.info(f"✓ {filename}: {result.tweet_count} 条推文")
                else:
                    logger.error(f"✗ {filename}: {result.error_message}")
            else:
                logger.warning(f"⚠ {query}: 没有采集到推文")

        except Exception as e:
            logger.error(f"✗ 处理失败: {e}")


# ============================================
# 运行示例
# ============================================

if __name__ == "__main__":
    # 运行基础示例
    asyncio.run(main())

    # 取消注释以运行批量示例
    # asyncio.run(batch_export_demo())
