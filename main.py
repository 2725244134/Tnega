#!/usr/bin/env python3
# ============================================
# Tnega 主程序 - 生产级推文采集
# ============================================
# 使用 Gemini 2.5 Pro 智能采集阿拉伯地区推文数据

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, Field

from src.agent.agent_runner import run_collector_agent
from src.agent.config import AgentConfig

# ============================================
# 加载 .env 文件
# ============================================
_ = load_dotenv()


# ============================================
# 运行参数配置
# ============================================
class RunConfig(BaseModel):
    """主程序运行配置"""

    user_request: str = Field(
        default="找阿拉伯地区对中国 93 阅兵的讨论",
        description="用户需求（自然语言）",
    )

    target_tweet_count: int = Field(
        default=2000,
        description="目标采集推文数量",
    )

    max_attempts: int = Field(
        default=10,
        description="最大尝试次数",
    )

    model_name: str = Field(
        default="gemini-2.0-flash-exp",
        description="使用的 LLM 模型名称",
    )

    output_dir: str = Field(
        default="data/output",
        description="输出目录",
    )


# ============================================
# 环境检查
# ============================================
def check_environment() -> dict[str, bool]:
    """
    检查必需的环境变量

    Returns:
        环境检查结果字典
    """
    checks = {
        "TWITTER_API_KEY": bool(os.getenv("TWITTER_API_KEY")),
        "GOOGLE_API_KEY": bool(
            os.getenv("OPENROUTER_API_KEY") or os.getenv("GOOGLE_API_KEY")
        ),
        "LOGFIRE_TOKEN": bool(os.getenv("LOGFIRE_TOKEN")),
    }

    return checks


def print_environment_status(checks: dict[str, bool]):
    """打印环境状态"""
    print("\n" + "=" * 60)
    print("🔧 环境检查")
    print("=" * 60)

    for key, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {key}: {'已配置' if status else '未配置'}")

    print("=" * 60 + "\n")


# ============================================


# ============================================
# 主采集逻辑
# ============================================
async def run_collection(config: RunConfig):
    """
    运行推文采集任务

    Args:
        config: 运行配置
    """
    start_time = datetime.now()

    print("\n" + "🔥" * 30)
    print("Tnega - AI-Powered Twitter Data Intelligence")
    print("🔥" * 30 + "\n")

    # ============================================
    # 打印配置信息
    # ============================================
    print("📋 任务配置:")
    print(f"  - 用户需求: {config.user_request}")
    print(f"  - 目标数量: {config.target_tweet_count} 条推文")
    print(f"  - 最大尝试: {config.max_attempts} 次")
    print(f"  - LLM 模型: {config.model_name}")
    print(f"  - 输出目录: {config.output_dir}")
    print()

    # ============================================
    # 创建 Agent 配置
    # ============================================
    agent_config = AgentConfig(
        target_tweet_count=config.target_tweet_count,
        max_total_attempts=config.max_attempts,
        model_name=config.model_name,
        output_dir=config.output_dir,
        output_format="csv",
    )

    logger.info(f"开始采集任务 | 用户需求: {config.user_request}")

    # ============================================
    # 运行 Agent
    # ============================================
    try:
        result = await run_collector_agent(
            user_request=config.user_request,
            config=agent_config,
        )

        # ============================================
        # 打印结果
        # ============================================
        duration = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        if result.success:
            print("✅ 采集成功！")
        else:
            print("⚠️  采集未完全达标（但有部分数据）")
        print("=" * 60)

        print(f"\n{result.summary}\n")

        print("📊 详细统计:")
        print(f"  - 总推文数: {result.total_tweets} 条")
        print(f"  - 尝试次数: {result.total_attempts} 次")
        print(f"  - 总耗时: {duration:.1f} 秒")
        print(f"  - Agent 耗时: {result.duration_seconds:.1f} 秒")
        print(f"  - 平均速度: {result.total_tweets / duration:.1f} 条/秒")

        print("\n💾 输出文件:")
        print(f"  {result.output_path}")

        # 检查文件是否存在
        if Path(result.output_path).exists():
            file_size = Path(result.output_path).stat().st_size
            print(f"  文件大小: {file_size / 1024:.1f} KB")
        else:
            print("  ⚠️  文件不存在（可能尚未保存）")

        print("\n🎯 终止原因:")
        print(f"  {result.termination_reason}")

        print(f"\n🔍 使用的查询 ({len(result.queries_used)} 个):")
        for i, query in enumerate(result.queries_used, 1):
            print(f"  {i}. {query}")

        print()

        # ============================================
        # Logfire 提示
        # ============================================

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断采集")
        logger.warning("用户中断采集")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ 采集失败: {e}")
        logger.exception("采集任务失败")
        sys.exit(1)


# ============================================
# 命令行参数解析
# ============================================
def parse_args() -> RunConfig:
    """
    解析命令行参数

    Returns:
        运行配置
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Tnega - AI-Powered Twitter Data Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置（采集阿拉伯地区93阅兵讨论）
  python main.py

  # 自定义需求
  python main.py --request "找美国对中国太空站的讨论"

  # 指定目标数量和模型
  python main.py --target 5000 --model gemini-2.0-flash-exp

  # 禁用 Logfire
  python main.py --no-logfire

环境变量（必需）:
  TWITTER_API_KEY   - Twitter API 密钥
  GOOGLE_API_KEY    - Google Gemini API 密钥
  LOGFIRE_TOKEN     - Logfire 监控 Token（可选）
        """,
    )

    parser.add_argument(
        "--request",
        type=str,
        default="找阿拉伯地区对中国 93 阅兵的讨论",
        help="用户需求（自然语言）",
    )

    parser.add_argument(
        "--target",
        type=int,
        default=2000,
        help="目标采集推文数量（默认: 2000）",
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=10,
        help="最大尝试次数（默认: 10）",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.5-pro",
        help="LLM 模型名称（默认: gemini-2.5-pro）",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/output",
        help="输出目录（默认: data/output）",
    )

    args = parser.parse_args()

    return RunConfig(
        user_request=args.request,
        target_tweet_count=args.target,
        max_attempts=args.max_attempts,
        model_name=args.model,
        output_dir=args.output_dir,
    )


# ============================================
# 主入口
# ============================================
async def async_main():
    """异步主入口"""
    # 解析参数
    config = parse_args()

    # 检查环境
    env_checks = check_environment()
    print_environment_status(env_checks)

    # 验证必需的环境变量
    if not env_checks["TWITTER_API_KEY"]:
        print("❌ 错误: 未设置 TWITTER_API_KEY 环境变量")
        print("   请设置: export TWITTER_API_KEY='your_twitter_api_key'")
        sys.exit(1)

    if not env_checks["GOOGLE_API_KEY"]:
        print("❌ 错误: 未设置 GOOGLE_API_KEY 环境变量")
        print("   请设置: export GOOGLE_API_KEY='your_gemini_api_key'")
        sys.exit(1)

    # 运行采集
    await run_collection(config)


def main():
    """同步主入口（供 setuptools entry point 使用）"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)


# ============================================
# 程序入口
# ============================================
if __name__ == "__main__":
    main()
