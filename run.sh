#!/bin/bash
# ============================================
# Tnega 一键启动脚本
# ============================================
# 自动检查环境、配置并运行采集任务

set -e  # 遇到错误立即退出

# ============================================
# 颜色定义
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# 打印函数
# ============================================
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================
# 检查依赖
# ============================================
check_dependencies() {
    print_header "检查依赖"

    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python 已安装: $PYTHON_VERSION"
    else
        print_error "Python 3 未安装"
        exit 1
    fi

    # 检查 uv
    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version)
        print_success "uv 已安装: $UV_VERSION"
    else
        print_warning "uv 未安装，将使用 python 直接运行"
    fi

    echo ""
}

# ============================================
# 检查环境变量
# ============================================
check_env_vars() {
    print_header "检查环境变量"

    # 加载 .env 文件（如果存在）
    if [ -f .env ]; then
        print_info "加载 .env 文件"
        export $(cat .env | grep -v '^#' | xargs)
    fi

    # 检查 TWITTER_API_KEY
    if [ -z "$TWITTER_API_KEY" ]; then
        print_error "TWITTER_API_KEY 未设置"
        echo ""
        echo "请执行以下操作之一："
        echo "  1. 设置环境变量: export TWITTER_API_KEY='your_key'"
        echo "  2. 创建 .env 文件并添加: TWITTER_API_KEY=your_key"
        echo ""
        exit 1
    else
        print_success "TWITTER_API_KEY 已配置"
    fi

    # 检查 GOOGLE_API_KEY
    if [ -z "$GOOGLE_API_KEY" ]; then
        print_error "GOOGLE_API_KEY 未设置"
        echo ""
        echo "请执行以下操作之一："
        echo "  1. 设置环境变量: export GOOGLE_API_KEY='your_key'"
        echo "  2. 创建 .env 文件并添加: GOOGLE_API_KEY=your_key"
        echo ""
        exit 1
    else
        print_success "GOOGLE_API_KEY 已配置"
    fi

    # 检查 LOGFIRE_TOKEN（可选）
    if [ -z "$LOGFIRE_TOKEN" ]; then
        print_warning "LOGFIRE_TOKEN 未设置（监控将禁用）"
    else
        print_success "LOGFIRE_TOKEN 已配置（监控已启用）"
    fi

    echo ""
}

# ============================================
# 创建输出目录
# ============================================
prepare_output_dir() {
    print_header "准备输出目录"

    OUTPUT_DIR="data/output"

    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR"
        print_success "创建输出目录: $OUTPUT_DIR"
    else
        print_info "输出目录已存在: $OUTPUT_DIR"
    fi

    echo ""
}

# ============================================
# 运行采集任务
# ============================================
run_collection() {
    print_header "运行采集任务"

    # 解析命令行参数
    REQUEST="${1:-找阿拉伯地区对中国 93 阅兵的讨论}"
    TARGET="${2:-2000}"
    MODEL="${3:-gemini-2.0-flash-exp}"

    print_info "用户需求: $REQUEST"
    print_info "目标数量: $TARGET 条推文"
    print_info "LLM 模型: $MODEL"
    echo ""

    # 决定使用 uv 还是 python
    if command -v uv &> /dev/null; then
        RUN_CMD="uv run python"
    else
        RUN_CMD="python3"
    fi

    # 运行 main.py
    $RUN_CMD main.py \
        --request "$REQUEST" \
        --target "$TARGET" \
        --model "$MODEL"
}

# ============================================
# 主函数
# ============================================
main() {
    clear

    echo ""
    echo "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥"
    echo "  Tnega - AI-Powered Twitter Data Intelligence"
    echo "  一键启动脚本"
    echo "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥"
    echo ""

    # 步骤 1: 检查依赖
    check_dependencies

    # 步骤 2: 检查环境变量
    check_env_vars

    # 步骤 3: 准备输出目录
    prepare_output_dir

    # 步骤 4: 运行采集任务
    run_collection "$@"
}

# ============================================
# 帮助信息
# ============================================
show_help() {
    cat << EOF
Tnega 一键启动脚本

用法:
  ./run.sh [需求] [目标数量] [模型名称]

参数:
  需求        - 用户需求（自然语言），默认: "找阿拉伯地区对中国 93 阅兵的讨论"
  目标数量    - 目标采集推文数，默认: 2000
  模型名称    - LLM 模型名称，默认: gemini-2.0-flash-exp

示例:
  # 使用默认配置
  ./run.sh

  # 自定义需求
  ./run.sh "找美国对中国太空站的讨论"

  # 自定义需求和目标数量
  ./run.sh "找欧洲对中国电动车的讨论" 3000

  # 完整自定义
  ./run.sh "找日本对中国高铁的讨论" 5000 gemini-1.5-pro

环境变量（必需）:
  TWITTER_API_KEY   - Twitter API 密钥
  GOOGLE_API_KEY    - Google Gemini API 密钥
  LOGFIRE_TOKEN     - Logfire 监控 Token（可选）

更多信息:
  查看 RUN.md 获取完整文档
EOF
}

# ============================================
# 入口
# ============================================
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

main "$@"
