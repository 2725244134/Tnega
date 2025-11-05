import argparse
from pathlib import Path

import pandas as pd


# ============================================
# 脚本参数解析
# ============================================
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="合并指定目录下的所有 CSV 文件，并添加序号列。"
    )
    parser.add_argument("input_dir", type=str, help="包含源 CSV 文件的目录路径。")
    parser.add_argument("output_file", type=str, help="合并后输出的 CSV 文件路径。")
    return parser.parse_args()


# ============================================
# 核心合并逻辑
# ============================================
def merge_and_number_csvs(input_dir: str, output_file: str):
    """
    查找、合并并编号 CSV 文件。

    Args:
        input_dir: 输入目录路径。
        output_file: 输出文件路径。
    """
    source_path = Path(input_dir)
    if not source_path.is_dir():
        print(f"错误: 目录 '{input_dir}' 不存在。")
        return

    # 1. 查找所有 CSV 文件，消除“10个”这个特殊情况
    csv_files = list(source_path.glob("*.csv"))
    if not csv_files:
        print(f"在目录 '{input_dir}' 中没有找到任何 CSV 文件。")
        return

    print(f"找到 {len(csv_files)} 个 CSV 文件，准备合并...")

    # 2. 读入并合并
    # 使用列表推导式，简洁高效
    df_list = [pd.read_csv(file) for file in csv_files]
    merged_df = pd.concat(df_list, ignore_index=True)

    # 3. 添加序号列 (从 1 开始)
    # 这比循环高效得多，是 pandas 的正确用法
    merged_df.insert(0, "序号", range(1, len(merged_df) + 1))

    # 4. 保存到新文件，不修改原始数据
    merged_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"合并完成！结果已保存到 '{output_file}'。")
    print(f"总共处理了 {len(merged_df)} 行数据。")


if __name__ == "__main__":
    args = parse_arguments()
    merge_and_number_csvs(args.input_dir, args.output_file)
