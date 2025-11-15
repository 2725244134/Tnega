#!/bin/bash
# ============================================
# Docker 入口脚本
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# 等待数据库启动
wait_for_db() {
    log_info "等待数据库启动..."

    while ! pg_isready -h "${TNEGA_DB_HOST:-db}" -p "${TNEGA_DB_PORT:-5432}" -U "${TNEGA_DB_USER:-postgres}"; do
        log_warn "数据库未就绪，等待 2 秒..."
        sleep 2
    done

    log_info "数据库已就绪"
}

# 等待 Redis 启动
wait_for_redis() {
    log_info "等待 Redis 启动..."

    while ! redis-cli -h "${TNEGA_REDIS_HOST:-redis}" -p "${TNEGA_REDIS_PORT:-6379}" ping; do
        log_warn "Redis 未就绪，等待 2 秒..."
        sleep 2
    done

    log_info "Redis 已就绪"
}

# 运行数据库迁移
run_migrations() {
    if [ "${TNEGA_RUN_MIGRATIONS:-true}" = "true" ]; then
        log_info "运行数据库迁移..."

        cd /app
        uv run alembic upgrade head

        log_info "数据库迁移完成"
    else
        log_info "跳过数据库迁移"
    fi
}

# 创建日志目录
create_log_dirs() {
    log_info "创建日志目录..."
    mkdir -p logs
    chmod 755 logs
}

# 设置环境变量默认值
set_default_env() {
    export TNEGA_DB_HOST="${TNEGA_DB_HOST:-db}"
    export TNEGA_DB_PORT="${TNEGA_DB_PORT:-5432}"
    export TNEGA_DB_USER="${TNEGA_DB_USER:-postgres}"
    export TNEGA_DB_NAME="${TNEGA_DB_NAME:-tnega}"
    export TNEGA_REDIS_HOST="${TNEGA_REDIS_HOST:-redis}"
    export TNEGA_REDIS_PORT="${TNEGA_REDIS_PORT:-6379}"

    # 构建数据库 URL
    if [ -z "$TNEGA_DATABASE_URL" ]; then
        export TNEGA_DATABASE_URL="postgresql+asyncpg://${TNEGA_DB_USER}:${TNEGA_DB_PASSWORD}@${TNEGA_DB_HOST}:${TNEGA_DB_PORT}/${TNEGA_DB_NAME}"
    fi

    # 构建 Redis URL
    if [ -z "$TNEGA_REDIS_URL" ]; then
        export TNEGA_REDIS_URL="redis://${TNEGA_REDIS_HOST}:${TNEGA_REDIS_PORT}/0"
    fi

    # 构建 Celery URL
    if [ -z "$TNEGA_CELERY_BROKER_URL" ]; then
        export TNEGA_CELERY_BROKER_URL="redis://${TNEGA_REDIS_HOST}:${TNEGA_REDIS_PORT}/1"
    fi

    if [ -z "$TNEGA_CELERY_RESULT_BACKEND" ]; then
        export TNEGA_CELERY_RESULT_BACKEND="redis://${TNEGA_REDIS_HOST}:${TNEGA_REDIS_PORT}/2"
    fi
}

# 检查必需的环境变量
check_required_env() {
    local required_vars=("TNEGA_TWITTER_API_KEY" "TNEGA_GOOGLE_API_KEY")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "缺少必需的环境变量: ${missing_vars[*]}"
        log_error "请设置以下环境变量:"
        log_error "  TNEGA_TWITTER_API_KEY - Twitter API 密钥"
        log_error "  TNEGA_GOOGLE_API_KEY - Google Gemini API 密钥"
        exit 1
    fi
}

# 主函数
main() {
    log_info "启动 Tnega 服务..."

    # 设置环境变量
    set_default_env

    # 检查必需的环境变量
    check_required_env

    # 创建日志目录
    create_log_dirs

    # 等待依赖服务
    wait_for_db
    wait_for_redis

    # 运行数据库迁移
    run_migrations

    log_info "服务初始化完成"

    # 执行传入的命令
    exec "$@"
}

# 运行主函数
main "$@"