# ============================================
# Tnega FastAPI 应用 Docker 镜像
# ============================================

# 使用 Python 3.14 作为基础镜像
FROM python:3.14-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gcc \
        g++ \
        postgresql-client \
        redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器（更快的 Python 包管理）
RUN pip install uv

# 复制依赖文件
COPY pyproject.toml ./
COPY uv.lock ./

# 安装 Python 依赖
RUN uv sync --frozen --no-dev

# 复制应用代码
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/entrypoint.sh

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 入口脚本
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# 默认命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]