"""
============================================
任务服务层
============================================
分析任务的业务逻辑服务
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.redis import RedisCache, CacheKey
from app.models.analysis import AnalysisTask, TaskStatus
from app.tasks.collection import collect_tweets
from app.tasks.analysis import analyze_tweets


class TaskService:
    """任务服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger

    async def create_task(
        self,
        title: str,
        description: str,
        search_query: Optional[str] = None,
        target_count: int = 1000,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> AnalysisTask:
        """
        创建分析任务

        Args:
            title: 任务标题
            description: 任务描述
            search_query: 搜索查询
            target_count: 目标推文数量
            parameters: 任务参数
            user_id: 用户ID

        Returns:
            创建的任务
        """
        try:
            # 这里可以添加业务逻辑验证
            # 例如：检查用户配额、验证查询语法等

            # 创建任务（实际创建逻辑在 API 层）
            # 这里只是服务层的示例

            self.logger.info(f"创建任务: {title}")
            return None  # 实际实现需要返回任务对象

        except Exception as e:
            self.logger.error(f"创建任务失败: {e}")
            raise

    async def get_task_by_id(self, task_id: str) -> Optional[AnalysisTask]:
        """
        根据ID获取任务

        Args:
            task_id: 任务ID

        Returns:
            任务对象，如果不存在返回 None
        """
        try:
            result = await self.db.execute(
                "SELECT * FROM analysis_tasks WHERE id = :task_id AND deleted_at IS NULL",
                {"task_id": task_id}
            )
            task = result.first()

            if task:
                self.logger.debug(f"获取任务: {task_id}")
            else:
                self.logger.warning(f"任务不存在: {task_id}")

            return task

        except Exception as e:
            self.logger.error(f"获取任务失败: {task_id}, 错误: {e}")
            raise

    async def get_task_status_with_cache(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态（带缓存）

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        try:
            # 先检查缓存
            cached_status = await RedisCache.get_json(CacheKey.task_status(task_id))
            if cached_status:
                self.logger.debug(f"从缓存获取任务状态: {task_id}")
                return cached_status

            # 从数据库获取
            task = await self.get_task_by_id(task_id)
            if not task:
                return {"error": "任务不存在"}

            status_info = {
                "status": task.status,
                "progress": task.progress,
                "current_step": getattr(task, 'current_step', None),
                "updated_at": task.updated_at.isoformat()
            }

            # 缓存状态信息（5分钟）
            await RedisCache.set_json(
                CacheKey.task_status(task_id),
                status_info,
                ttl=300
            )

            return status_info

        except Exception as e:
            self.logger.error(f"获取任务状态失败: {task_id}, 错误: {e}")
            return {"error": str(e)}

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        status: TaskStatus,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新任务进度

        Args:
            task_id: 任务ID
            progress: 进度百分比
            status: 任务状态
            current_step: 当前步骤
            error_message: 错误信息

        Returns:
            是否更新成功
        """
        try:
            # 构建更新数据
            update_data = {
                "progress": progress,
                "status": status,
                "updated_at": datetime.utcnow()
            }

            if status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.utcnow()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                update_data["completed_at"] = datetime.utcnow()

            if current_step:
                update_data["current_step"] = current_step

            if error_message:
                update_data["error_message"] = error_message

            # 执行更新
            result = await self.db.execute(
                """
                UPDATE analysis_tasks
                SET progress = :progress,
                    status = :status,
                    updated_at = :updated_at,
                    started_at = COALESCE(:started_at, started_at),
                    completed_at = COALESCE(:completed_at, completed_at),
                    current_step = COALESCE(:current_step, current_step),
                    error_message = COALESCE(:error_message, error_message)
                WHERE id = :task_id
                """,
                {**update_data, "task_id": task_id}
            )

            await self.db.commit()

            if result.rowcount > 0:
                self.logger.info(f"更新任务进度: {task_id} - {status} - {progress}%")

                # 更新缓存
                status_info = {
                    "status": status,
                    "progress": progress,
                    "current_step": current_step,
                    "updated_at": datetime.utcnow().isoformat()
                }

                await RedisCache.set_json(
                    CacheKey.task_status(task_id),
                    status_info,
                    ttl=300
                )

                return True
            else:
                self.logger.warning(f"任务不存在或更新失败: {task_id}")
                return False

        except Exception as e:
            self.logger.error(f"更新任务进度失败: {task_id}, 错误: {e}")
            await self.db.rollback()
            return False

    async def get_task_results(self, task_id: str, result_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取任务分析结果

        Args:
            task_id: 任务ID
            result_type: 结果类型过滤

        Returns:
            分析结果列表
        """
        try:
            # 构建查询条件
            where_conditions = ["task_id = :task_id"]
            params = {"task_id": task_id}

            if result_type:
                where_conditions.append("result_type = :result_type")
                params["result_type"] = result_type

            where_clause = " AND ".join(where_conditions)

            result = await self.db.execute(
                f"SELECT * FROM analysis_results WHERE {where_clause} ORDER BY created_at DESC",
                params
            )

            results = result.fetchall()

            self.logger.info(f"获取任务结果: {task_id}, 结果数量: {len(results)}")

            return [dict(result._mapping) for result in results]

        except Exception as e:
            self.logger.error(f"获取任务结果失败: {task_id}, 错误: {e}")
            raise

    async def retry_task(self, task_id: str) -> bool:
        """
        重试失败的任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功启动重试
        """
        try:
            # 获取任务信息
            task = await self.get_task_by_id(task_id)
            if not task:
                self.logger.warning(f"重试任务不存在: {task_id}")
                return False

            if task.status != TaskStatus.FAILED:
                self.logger.warning(f"任务状态不是失败，无法重试: {task_id} - {task.status}")
                return False

            if task.retry_count >= task.max_retries:
                self.logger.warning(f"已达到最大重试次数: {task_id}")
                return False

            # 更新任务状态为待重试
            success = await self.update_task_progress(
                task_id=task_id,
                progress=0,
                status=TaskStatus.PENDING,
                current_step="等待重试"
            )

            if success:
                # 启动重试（这里可以调用后台任务）
                self.logger.info(f"任务重试已启动: {task_id}")
                # 实际的重试逻辑应该在后台任务中执行
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"重试任务失败: {task_id}, 错误: {e}")
            return False

    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务（软删除）

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        try:
            # 检查任务是否存在
            task = await self.get_task_by_id(task_id)
            if not task:
                self.logger.warning(f"删除任务不存在: {task_id}")
                return False

            # 软删除任务
            result = await self.db.execute(
                "UPDATE analysis_tasks SET deleted_at = NOW() WHERE id = :task_id",
                {"task_id": task_id}
            )

            await self.db.commit()

            if result.rowcount > 0:
                self.logger.info(f"删除任务: {task_id}")

                # 清除相关缓存
                await RedisCache.delete(CacheKey.task_status(task_id))
                await RedisCache.delete(CacheKey.analysis_result(task_id))

                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"删除任务失败: {task_id}, 错误: {e}")
            await self.db.rollback()
            return False

    async def get_task_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[TaskStatus] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取任务列表

        Args:
            page: 页码
            page_size: 每页大小
            status: 状态过滤
            user_id: 用户ID过滤

        Returns:
            任务列表和分页信息
        """
        try:
            # 构建查询条件
            where_conditions = ["deleted_at IS NULL"]
            params = {}

            if status:
                where_conditions.append("status = :status")
                params["status"] = status

            if user_id:
                where_conditions.append("user_id = :user_id")
                params["user_id"] = user_id

            where_clause = " AND ".join(where_conditions)

            # 获取总数
            count_result = await self.db.execute(
                f"SELECT COUNT(*) FROM analysis_tasks WHERE {where_clause}",
                params
            )
            total = count_result.scalar()

            # 获取任务列表
            offset = (page - 1) * page_size
            params.update({
                "offset": offset,
                "limit": page_size
            })

            result = await self.db.execute(
                f"""
                SELECT * FROM analysis_tasks
                WHERE {where_clause}
                ORDER BY created_at DESC
                OFFSET :offset LIMIT :limit
                """,
                params
            )

            tasks = result.fetchall()

            # 构建分页信息
            pages = (total + page_size - 1) // page_size

            return {
                "items": [dict(task._mapping) for task in tasks],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "pages": pages,
                    "has_prev": page > 1,
                    "has_next": page < pages
                }
            }

        except Exception as e:
            self.logger.error(f"获取任务列表失败: {e}")
            raise

    async def start_analysis_workflow(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """
        启动分析工作流

        Args:
            task_id: 任务ID
            task_data: 任务数据

        Returns:
            是否成功启动
        """
        try:
            self.logger.info(f"启动分析工作流: {task_id}")

            # 第一步：采集推文
            collection_task = collect_tweets.delay(
                task_id=task_id,
                parameters=task_data
            )

            self.logger.info(f"采集任务已启动: {collection_task.id}")

            # 可以在这里添加等待采集完成的逻辑
            # 或者直接返回，让前端轮询状态

            return True

        except Exception as e:
            self.logger.error(f"启动分析工作流失败: {task_id}, 错误: {e}")
            return False

    async def get_task_statistics(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务统计信息

        Args:
            task_id: 任务ID

        Returns:
            统计信息
        """
        try:
            # 获取推文统计
            tweets_result = await self.db.execute(
                """
                SELECT
                    COUNT(*) as total_tweets,
                    COUNT(DISTINCT author_id) as unique_authors,
                    AVG(like_count) as avg_likes,
                    AVG(retweet_count) as avg_retweets,
                    AVG(reply_count) as avg_replies,
                    MIN(created_at) as earliest_tweet,
                    MAX(created_at) as latest_tweet
                FROM tweet_data
                WHERE tweet_id IN (
                    SELECT tweet_id FROM analysis_results
                    WHERE task_id = :task_id
                )
                """,
                {"task_id": task_id}
            )
            tweet_stats = tweets_result.first()

            # 获取结果统计
            results_result = await self.db.execute(
                """
                SELECT
                    result_type,
                    COUNT(*) as count,
                    AVG(quality_score) as avg_quality
                FROM analysis_results
                WHERE task_id = :task_id
                GROUP BY result_type
                """,
                {"task_id": task_id}
            )
            result_stats = results_result.fetchall()

            # 获取任务时间统计
            task_result = await self.db.execute(
                """
                SELECT
                    created_at,
                    started_at,
                    completed_at,
                    duration
                FROM analysis_tasks
                WHERE id = :task_id
                """,
                {"task_id": task_id}
            )
            task_info = task_result.first()

            statistics = {
                "tweets": {
                    "total": tweet_stats.total_tweets if tweet_stats else 0,
                    "unique_authors": tweet_stats.unique_authors if tweet_stats else 0,
                    "avg_likes": float(tweet_stats.avg_likes) if tweet_stats and tweet_stats.avg_likes else 0,
                    "avg_retweets": float(tweet_stats.avg_retweets) if tweet_stats and tweet_stats.avg_retweets else 0,
                    "avg_replies": float(tweet_stats.avg_replies) if tweet_stats and tweet_stats.avg_replies else 0,
                    "time_range": {
                        "start": tweet_stats.earliest_tweet.isoformat() if tweet_stats and tweet_stats.earliest_tweet else None,
                        "end": tweet_stats.latest_tweet.isoformat() if tweet_stats and tweet_stats.latest_tweet else None,
                    }
                },
                "results": {
                    stat.result_type: {
                        "count": stat.count,
                        "avg_quality": float(stat.avg_quality) if stat.avg_quality else 0
                    }
                    for stat in result_stats
                },
                "task": {
                    "created_at": task_info.created_at.isoformat() if task_info else None,
                    "started_at": task_info.started_at.isoformat() if task_info and task_info.started_at else None,
                    "completed_at": task_info.completed_at.isoformat() if task_info and task_info.completed_at else None,
                    "duration": task_info.duration if task_info else None,
                }
            }

            return statistics

        except Exception as e:
            self.logger.error(f"获取任务统计失败: {task_id}, 错误: {e}")
            return {"error": str(e)}

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        try:
            # 这里应该调用 Celery 的取消任务功能
            # 目前只是更新状态
            success = await self.update_task_progress(
                task_id=task_id,
                progress=100,
                status=TaskStatus.CANCELLED,
                current_step="任务已取消"
            )

            if success:
                self.logger.info(f"取消任务: {task_id}")

            return success

        except Exception as e:
            self.logger.error(f"取消任务失败: {task_id}, 错误: {e}")
            return False

    async def get_running_tasks_count(self, user_id: Optional[str] = None) -> int:
        """
        获取运行中的任务数量

        Args:
            user_id: 用户ID（可选）

        Returns:
            运行中的任务数量
        """
        try:
            params = {}
            where_conditions = ["status IN :running_statuses"]
            params["running_statuses"] = [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING]

            if user_id:
                where_conditions.append("user_id = :user_id")
                params["user_id"] = user_id

            where_clause = " AND ".join(where_conditions)

            result = await self.db.execute(
                f"SELECT COUNT(*) FROM analysis_tasks WHERE {where_clause}",
                params
            )

            count = result.scalar()
            return count or 0

        except Exception as e:
            self.logger.error(f"获取运行中任务数量失败: {e}")
            return 0

    async def get_user_task_quota(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户任务配额信息

        Args:
            user_id: 用户ID

        Returns:
            配额信息
        """
        try:
            # 获取用户今日创建的任务数量
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            result = await self.db.execute(
                """
                SELECT COUNT(*) as count
                FROM analysis_tasks
                WHERE user_id = :user_id
                AND created_at >= :today_start
                """,
                {
                    "user_id": user_id,
                    "today_start": today_start
                }
            )

            today_count = result.scalar() or 0

            # 获取用户运行中的任务数量
            running_count = await self.get_running_tasks_count(user_id)

            # 配额配置（可以从配置中读取）
            daily_limit = 100  # 每日限制
            concurrent_limit = 5  # 并发限制

            return {
                "user_id": user_id,
                "today_created": today_count,
                "today_limit": daily_limit,
                "today_remaining": max(0, daily_limit - today_count),
                "running_tasks": running_count,
                "concurrent_limit": concurrent_limit,
                "can_create": today_count < daily_limit and running_count < concurrent_limit
            }

        except Exception as e:
            self.logger.error(f"获取用户配额失败: {user_id}, 错误: {e}")
            return {"error": str(e), "can_create": False}


# 任务工作流管理器
class TaskWorkflowManager:
    """任务工作流管理器"""

    def __init__(self):
        self.logger = logger

    async def execute_analysis_workflow(
        self,
        task_id: str,
        task_data: Dict[str, Any]
    ) -> bool:
        """
        执行分析工作流

        Args:
            task_id: 任务ID
            task_data: 任务数据

        Returns:
            是否成功执行
        """
        try:
            self.logger.info(f"执行分析工作流: {task_id}")

            # 第一步：采集推文数据
            collection_task = collect_tweets.delay(
                task_id=task_id,
                parameters=task_data
            )

            self.logger.info(f"采集任务已启动: {collection_task.id}")

            # 可以在这里添加等待采集完成的逻辑
            # 或者直接返回，让前端轮询状态

            return True

        except Exception as e:
            self.logger.error(f"执行分析工作流失败: {task_id}, 错误: {e}")
            return False

    async def execute_collection_workflow(
        self,
        task_id: str,
        collection_params: Dict[str, Any]
    ) -> str:
        """
        执行采集工作流

        Args:
            task_id: 任务ID
            collection_params: 采集参数

        Returns:
            Celery 任务ID
        """
        try:
            self.logger.info(f"执行采集工作流: {task_id}")

            # 启动采集任务
            task = collect_tweets.delay(
                task_id=task_id,
                parameters=collection_params
            )

            self.logger.info(f"采集任务已启动: {task.id}")

            return task.id

        except Exception as e:
            self.logger.error(f"执行采集工作流失败: {task_id}, 错误: {e}")
            raise

    async def execute_analysis_only_workflow(
        self,
        task_id: str,
        analysis_params: Dict[str, Any]
    ) -> str:
        """
        执行纯分析工作流

        Args:
            task_id: 任务ID
            analysis_params: 分析参数

        Returns:
            Celery 任务ID
        """
        try:
            self.logger.info(f"执行纯分析工作流: {task_id}")

            # 启动分析任务
            task = analyze_tweets.delay(
                task_id=task_id,
                parameters=analysis_params
            )

            self.logger.info(f"分析任务已启动: {task.id}")

            return task.id

        except Exception as e:
            self.logger.error(f"执行纯分析工作流失败: {task_id}, 错误: {e}")
            raise