"""
============================================
Celery 应用配置
============================================
Celery 异步任务队列配置
"""

from celery import Celery
from loguru import logger
from app.core.config import settings


def create_celery_app():
    """
    创建 Celery 应用实例

    Returns:
        Celery: 配置好的 Celery 应用
    """
    # 创建 Celery 应用
    celery_app = Celery(
        "tnega",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["app.tasks.analysis", "app.tasks.collection"]
    )

    # 配置 Celery
    celery_app.conf.update(
        # 任务序列化
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        # 任务超时
        task_soft_time_limit=settings.CELERY_TASK_TIMEOUT,
        task_time_limit=settings.CELERY_TASK_TIMEOUT + 300,  # 硬超时比软超时多5分钟

        # 结果过期时间
        result_expires=3600,  # 1小时

        # 任务路由
        task_routes=settings.celery_task_routes,

        # 任务重试
        task_acks_late=True,  # 任务完成后才确认
        task_reject_on_worker_lost=True,  #  worker 丢失时拒绝任务
        worker_prefetch_multiplier=1,  # 每个 worker 一次只取一个任务

        # 监控和日志
        worker_send_task_events=True,
        task_send_sent_event=True,

        # 内存优化
        worker_max_tasks_per_child=1000,  # 每个 worker 最多处理1000个任务后重启
        worker_pool_restarts=True,

        # 任务结果
        result_backend_transport_options={
            'global_keyprefix': 'tnega_celery:',  # Redis key 前缀
        },
    )

    # 配置任务队列
    celery_app.conf.task_queues = {
        'analysis': {
            'exchange': 'analysis',
            'routing_key': 'analysis',
            'max_priority': 10,
        },
        'collection': {
            'exchange': 'collection',
            'routing_key': 'collection',
            'max_priority': 5,
        },
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        }
    }

    # 配置默认队列
    celery_app.conf.task_default_queue = 'default'
    celery_app.conf.task_default_exchange = 'default'
    celery_app.conf.task_default_routing_key = 'default'

    return celery_app


# 创建全局 Celery 实例
celery_app = create_celery_app()


# Celery 信号处理
@celery_app.task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务开始执行时的处理"""
    logger.info(f"🚀 任务开始执行: {task.name} (ID: {task_id})")


@celery_app.task_postrun.connect
def task_postrun_handler(task_id, task, *args, retval, state, **kwargs):
    """任务执行完成时的处理"""
    logger.info(f"✅ 任务执行完成: {task.name} (ID: {task_id}), 状态: {state}")


@celery_app.task_failure.connect
def task_failure_handler(task_id, exception, traceback, *args, **kwargs):
    """任务失败时的处理"""
    logger.error(f"❌ 任务执行失败: {kwargs.get('task')} (ID: {task_id})")
    logger.error(f"异常信息: {exception}")
    logger.error(f"错误追踪: {traceback}")


@celery_app.task_retry.connect
def task_retry_handler(request, reason, einfo, *args, **kwargs):
    """任务重试时的处理"""
    logger.warning(f"🔄 任务重试: {request.task} (ID: {request.id})")
    logger.warning(f"重试原因: {reason}")


# 任务基类
class BaseTask:
    """任务基类，提供通用功能"""

    def __init__(self):
        self.task_id = None
        self.logger = logger

    def update_state(self, state: str = None, meta: dict = None):
        """更新任务状态"""
        if self.task_id:
            self.logger.info(f"更新任务状态: {state}, 元数据: {meta}")
            # 这里可以添加状态更新逻辑

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        self.logger.info(f"任务成功完成: {task_id}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        self.logger.error(f"任务失败: {task_id}, 异常: {exc}")


def get_celery_app():
    """
    获取 Celery 应用实例

    Returns:
        Celery: Celery 应用实例
    """
    return celery_app


def get_task_info(task_id: str) -> dict:
    """
    获取任务信息

    Args:
        task_id: 任务ID

    Returns:
        dict: 任务信息
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
        "traceback": result.traceback,
    }