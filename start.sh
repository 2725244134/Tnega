#!/bin/bash
# ============================================
# Tnega FastAPI 服务启动脚本
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_blue() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f ".env" ]; then
        log_warn "未找到 .env 文件，使用 .env.example 作为模板"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_info "已创建 .env 文件，请编辑配置后再运行"
            log_warn "必需配置：TNEGA_TWITTER_API_KEY 和 TNEGA_GOOGLE_API_KEY"
            exit 1
        else
            log_error "未找到 .env.example 文件"
            exit 1
        fi
    fi
}

# 检查依赖
 check_dependencies() {
    local missing_deps=()

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "缺少必需的依赖: ${missing_deps[*]}"
        log_info "请安装 Docker 和 Docker Compose"
        exit 1
    fi
}

# 检查 API 密钥
check_api_keys() {
    local missing_keys=()

    # 从 .env 文件中读取配置
    if [ -f ".env" ]; then
        source .env
    fi

    if [ -z "$TNEGA_TWITTER_API_KEY" ] || [ "$TNEGA_TWITTER_API_KEY" = "your_twitter_api_key_here" ]; then
        missing_keys+=("TNEGA_TWITTER_API_KEY")
    fi

    if [ -z "$TNEGA_GOOGLE_API_KEY" ] || [ "$TNEGA_GOOGLE_API_KEY" = "your_google_api_key_here" ]; then
        missing_keys+=("TNEGA_GOOGLE_API_KEY")
    fi

    if [ ${#missing_keys[@]} -gt 0 ]; then
        log_error "缺少必需的 API 密钥: ${missing_keys[*]}"
        log_info "请编辑 .env 文件，设置正确的 API 密钥"
        log_info "- TNEGA_TWITTER_API_KEY: 从 https://twitterapi.io/ 获取"
        log_info "- TNEGA_GOOGLE_API_KEY: 从 https://makersuite.google.com/app/apikey 获取"
        exit 1
    fi
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    docker-compose build --no-cache
}

# 启动服务
start_services() {
    log_info "启动 Tnega 服务..."

    # 创建必要的目录
    mkdir -p logs

    # 启动服务
    docker-compose up -d

    log_info "服务启动中，请等待..."
    sleep 10
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."

    # 检查数据库
    if docker-compose exec -T db pg_isready -U postgres; then
        log_info "✅ 数据库服务正常"
    else
        log_error "❌ 数据库服务异常"
        return 1
    fi

    # 检查 Redis
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_info "✅ Redis 服务正常"
    else
        log_error "❌ Redis 服务异常"
        return 1
    fi

    # 检查 API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "✅ API 服务正常"
    else
        log_warn "⚠️  API 服务可能还在启动中"
    fi
}

# 显示服务信息
show_service_info() {
    log_blue "========================================"
    log_blue "Tnega 服务已成功启动！"
    log_blue "========================================"
    echo
    log_info "服务访问地址："
    echo "  📊 API 文档: http://localhost:8000/docs"
    echo "  🔍 API 端点: http://localhost:8000/api/v1"
    echo "  ❤️  健康检查: http://localhost:8000/health"
    echo
    log_info "监控面板（如果启用）："
    echo "  📈 Grafana: http://localhost:3000 (admin/admin)"
    echo "  🔍 Prometheus: http://localhost:9090"
    echo
    log_info "常用命令："
    echo "  # 查看服务状态"
    echo "  docker-compose ps"
    echo
    echo "  # 查看日志"
    echo "  docker-compose logs -f api"
    echo
    echo "  # 停止服务"
    echo "  docker-compose down"
    echo
    echo "  # 重启服务"
    echo "  docker-compose restart"
    echo
    log_blue "========================================"
}

# 停止服务
stop_services() {
    log_info "停止 Tnega 服务..."
    docker-compose down
    log_info "服务已停止"
}

# 重启服务
restart_services() {
    log_info "重启 Tnega 服务..."
    docker-compose restart
    log_info "服务重启完成"
}

# 查看日志
show_logs() {
    local service=${1:-api}
    log_info "查看 $service 服务日志..."
    docker-compose logs -f "$service"
}

# 显示帮助信息
show_help() {
    echo "Tnega FastAPI 服务启动脚本"
    echo
    echo "用法: $0 [命令] [选项]"
    echo
    echo "命令："
    echo "  start     启动服务（默认）"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  logs      查看日志"
    echo "  build     构建镜像"
    echo "  status    查看服务状态"
    echo "  help      显示帮助信息"
    echo
    echo "选项："
    echo "  --no-build    跳过镜像构建（仅用于 start 命令）"
    echo "  --service     指定服务名称（仅用于 logs 命令）"
    echo
    echo "示例："
    echo "  $0 start              # 启动服务"
    echo "  $0 start --no-build   # 启动服务（跳过构建）"
    echo "  $0 stop               # 停止服务"
    echo "  $0 logs               # 查看 API 日志"
    echo "  $0 logs --service db  # 查看数据库日志"
    echo "  $0 status             # 查看服务状态"
}

# 查看服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
    echo
    log_info "服务统计："
    echo "  运行中的容器: $(docker-compose ps -q | wc -l)"
    echo "  总容器数: $(docker-compose config --services | wc -l)"
}

# 主函数
main() {
    local command=${1:-start}
    local skip_build=false
    local service="api"

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-build)
                skip_build=true
                shift
                ;;
            --service)
                service="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    case $command in
        start)
            log_blue "========================================"
            log_blue "启动 Tnega FastAPI 服务"
            log_blue "========================================"

            check_env_file
            check_dependencies
            check_api_keys

            if [ "$skip_build" = false ]; then
                build_images
            fi

            start_services

            if check_services; then
                show_service_info
            else
                log_error "服务启动失败，请查看日志："
                echo "docker-compose logs"
                exit 1
            fi
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs "$service"
            ;;
        build)
            build_images
            ;;
        status)
            show_status
            ;;
        help)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"