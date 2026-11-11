"""
仪表盘统计服务：用于聚合各种业务数据，提供仪表板统计数据
    聚合招聘、培训考试、面试、AI助手等数据，返回dashboard统计、招聘趋势、培训完成情况和最近活动。
    部分统计来自本地数据库，部分通过远程服务补充。
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from uuid import UUID

# from app.models.job_description import JobDescription
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.resume_evaluation import ResumeEvaluation, ResumeStatus
from app.models.conversation import Conversation
from app.services.remote_service_client import remote_service_client

logger = logging.getLogger(__name__)


class StatsService:
    """统计服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取仪表板统计数据

        Args:
            user_id: 用户ID

        Returns:
            包含各类统计数据的字典
        """
        try:
            # 获取招聘统计数据
            recruitment_stats = await self._get_recruitment_stats(user_id)

            # 获取简历统计数据
            training_stats = await self._get_training_stats(user_id)

            # 获取面试统计数据
            interview_stats = await self._get_interview_stats(user_id)

            # 获取AI助手统计数据
            assistant_stats = await self._get_assistant_stats(user_id)

            return {
                "recruitment": recruitment_stats,
                "training": training_stats,
                "interview": interview_stats,
                "assistant": assistant_stats
            }

        except Exception as e:
            logger.error(f"获取仪表板统计数据失败: {e}")
            raise

    async def _get_recruitment_stats(self, user_id: str) -> Dict[str, Any]:
        """获取招聘统计数据"""
        try:
            # 调用远程服务获取招聘统计数据
            result_data = await remote_service_client.get(
                endpoint="/jd-stats/jd_dashboard",
                user_id=UUID(user_id)
            )
            
            return result_data

        except Exception as e:
            logger.error(f"获取招聘统计数据失败: {e}")
            return {"total": 0, "change": 0}

    async def _get_training_stats(self, user_id: str) -> Dict[str, Any]:
        """获取简历统计数据"""
        try:
            # 获取简历评价总数
            total_query = select(func.count(ResumeEvaluation.id)).where(
                ResumeEvaluation.user_id == user_id
            )
            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar() or 0

            # 获取最近7天新增的简历评价数
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(ResumeEvaluation.id)).where(
                and_(
                    ResumeEvaluation.user_id == user_id,
                    ResumeEvaluation.created_at >= week_ago
                )
            )
            recent_result = await self.db.execute(recent_query)
            recent_count = recent_result.scalar() or 0

            # 计算增长率
            growth_rate = 0
            if total_count > 0:
                growth_rate = round((recent_count / total_count) * 100, 2)

            return {
                "total": total_count,
                "change": growth_rate
            }

        except Exception as e:
            logger.error(f"获取简历统计数据失败: {e}")
            return {"total": 0, "change": 0}

    async def _get_interview_stats(self, user_id: str) -> Dict[str, Any]:
        """获取面试统计数据"""
        try:
            # 获取待面试的简历数量
            pending_query = select(func.count(ResumeEvaluation.id)).where(
                and_(
                    ResumeEvaluation.user_id == user_id,
                    ResumeEvaluation.status == ResumeStatus.INTERVIEW,
                    ResumeEvaluation.is_active == True
                )
            )
            pending_result = await self.db.execute(pending_query)
            pending_count = pending_result.scalar() or 0

            # 获取最近7天新增的待面试简历数
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(ResumeEvaluation.id)).where(
                and_(
                    ResumeEvaluation.user_id == user_id,
                    ResumeEvaluation.status == ResumeStatus.INTERVIEW,
                    ResumeEvaluation.is_active == True,
                    ResumeEvaluation.created_at >= week_ago
                )
            )
            recent_result = await self.db.execute(recent_query)
            recent_count = recent_result.scalar() or 0

            # 计算变化率（负数表示减少）
            change_rate = 0
            if pending_count > 0:
                change_rate = round((recent_count / pending_count) * 100, 2)

            return {
                "total": pending_count,
                "change": -change_rate  # 负数表示需要处理的面试减少
            }

        except Exception as e:
            logger.error(f"获取面试统计数据失败: {e}")
            return {"total": 0, "change": 0}

    async def _get_assistant_stats(self, user_id: str) -> Dict[str, Any]:
        """获取AI助手统计数据"""
        try:
            # 获取对话总数
            total_query = select(func.count(Conversation.id)).where(
                Conversation.user_id == user_id
            )
            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar() or 0

            # 获取最近7天新增的对话数
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(Conversation.id)).where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.created_at >= week_ago
                )
            )
            recent_result = await self.db.execute(recent_query)
            recent_count = recent_result.scalar() or 0

            # 计算增长率
            growth_rate = 0
            if total_count > 0:
                growth_rate = round((recent_count / total_count) * 100, 2)

            return {
                "total": total_count,
                "change": growth_rate
            }

        except Exception as e:
            logger.error(f"获取AI助手统计数据失败: {e}")
            return {"total": 0, "change": 0}

    async def get_recruitment_trend_data(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取招聘趋势数据

        Args:
            user_id: 用户ID
            days: 天数范围

        Returns:
            包含趋势数据的字典
        """
        try:
            # 调用远程服务获取招聘趋势数据
            result_data = await remote_service_client.get(
                endpoint="/jd-stats/jd-recruitment-trend",
                user_id=UUID(user_id),
                additional_params={"days": days}
            )
            
            return result_data

        except Exception as e:
            logger.error(f"获取招聘趋势数据失败: {e}")
            return {"dates": [], "counts": []}

    async def get_training_completion_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取简历评价分布统计

        Args:
            user_id: 用户ID

        Returns:
            包含简历评价分布统计数据的字典
        """
        try:
            # 获取简历评价总数
            total_query = select(func.count(ResumeEvaluation.id)).where(
                ResumeEvaluation.user_id == user_id
            )
            total_result = await self.db.execute(total_query)
            total_count = total_result.scalar() or 0

            # 获取高分简历数（80分以上）
            high_score_query = select(func.count(ResumeEvaluation.id)).where(
                and_(
                    ResumeEvaluation.user_id == user_id,
                    ResumeEvaluation.total_score >= 80
                )
            )
            high_score_result = await self.db.execute(high_score_query)
            high_score_count = high_score_result.scalar() or 0

            # 获取中等分数简历数（60-80分）
            medium_score_query = select(func.count(ResumeEvaluation.id)).where(
                and_(
                    ResumeEvaluation.user_id == user_id,
                    ResumeEvaluation.total_score >= 60,
                    ResumeEvaluation.total_score < 80
                )
            )
            medium_score_result = await self.db.execute(medium_score_query)
            medium_score_count = medium_score_result.scalar() or 0

            # 计算各部分占比
            high_percentage = round((high_score_count / total_count) * 100, 2) if total_count > 0 else 0
            medium_percentage = round((medium_score_count / total_count) * 100, 2) if total_count > 0 else 0
            low_percentage = round(100 - high_percentage - medium_percentage, 2)

            return {
                "high_score": high_percentage,
                "medium_score": medium_percentage,
                "low_score": low_percentage
            }

        except Exception as e:
            logger.error(f"获取简历评价分布统计失败: {e}")
            # 返回默认数据
            return {
                "high_score": 25,
                "medium_score": 50,
                "low_score": 25
            }

    async def get_recent_activities(self, user_id: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        获取最近活动记录（支持分页）

        Args:
            user_id: 用户ID
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            包含活动记录和分页信息的字典
        """
        try:
            activities = []

            # 获取职位描述创建记录（从远程服务）
            try:
                jd_activities = await remote_service_client.get(
                    endpoint="/jd-stats/jd-recent-activities",
                    user_id=UUID(user_id)
                )
                            
                # 将远程服务返回的活动记录添加到列表中，并转换created_at为datetime
                for activity in jd_activities:
                    if isinstance(activity.get('created_at'), str):
                        try:
                            # 将ISO格式字符串转换为datetime对象
                            activity['created_at'] = datetime.fromisoformat(activity['created_at'])
                        except (ValueError, TypeError):
                            # 如果转换失败，使用当前时间作为备选
                            activity['created_at'] = datetime.utcnow()
                    activities.append(activity)
            except Exception as e:
                logger.warning(f"获取职位描述记录失败: {e}")

            # 获取简历评价记录
            try:
                resume_query = select(ResumeEvaluation).where(
                    ResumeEvaluation.user_id == user_id
                ).order_by(ResumeEvaluation.created_at.desc())

                resume_result = await self.db.execute(resume_query)
                resume_records = resume_result.scalars().all()

                for record in resume_records:
                    candidate_name = record.candidate_name or "未知候选人"
                    activities.append({
                        "id": str(record.id),
                        "type": "training",
                        "icon": "Reading",
                        "title": f"评价了{candidate_name}的简历",
                        "time": self._format_time_diff(record.created_at),
                        "created_at": record.created_at
                    })
            except Exception as e:
                logger.warning(f"获取简历评价记录失败: {e}")

            # 获取对话记录
            try:
                conversation_query = select(Conversation).where(
                    Conversation.user_id == user_id
                ).order_by(Conversation.created_at.desc())

                conversation_result = await self.db.execute(conversation_query)
                conversation_records = conversation_result.scalars().all()

                for record in conversation_records:
                    # 简化处理，直接使用固定标题
                    title = "与AI助手进行了对话"

                    activities.append({
                        "id": str(record.id),
                        "type": "assistant",
                        "icon": "ChatDotRound",
                        "title": title,
                        "time": self._format_time_diff(record.created_at),
                        "created_at": record.created_at
                    })
            except Exception as e:
                logger.warning(f"获取对话记录失败: {e}")

            # 按时间排序
            activities.sort(key=lambda x: x['created_at'], reverse=True)

            # 获取总数
            total = len(activities)

            # 应用分页
            paginated_activities = activities[offset:offset + limit]

            return {
                "items": paginated_activities,
                "total": total,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "size": limit
            }

        except Exception as e:
            logger.exception(f"获取最近活动记录失败: {e}")
            # 返回默认活动记录以确保前端有数据显示
            default_activities = [
                {
                    "id": "1",
                    "type": "recruitment",
                    "icon": "Document",
                    "title": "欢迎使用HR助手系统",
                    "time": "刚刚"
                },
                {
                    "id": "2",
                    "type": "training",
                    "icon": "Reading",
                    "title": "开始创建您的第一个职位描述",
                    "time": "刚刚"
                },
                {
                    "id": "3",
                    "type": "assistant",
                    "icon": "ChatDotRound",
                    "title": "与AI助手进行首次对话",
                    "time": "刚刚"
                }
            ]

            return {
                "items": default_activities[:limit],
                "total": len(default_activities),
                "page": 1,
                "size": limit
            }

    def _format_time_diff(self, created_at) -> str:
        """格式化时间差显示"""
        if not created_at:
            return "未知时间"

        now = datetime.utcnow()
        diff = now - created_at.replace(tzinfo=None)

        minutes = diff.total_seconds() // 60
        hours = minutes // 60
        days = hours // 24

        if days > 0:
            return f"{int(days)}天前"
        elif hours > 0:
            return f"{int(hours)}小时前"
        elif minutes > 0:
            return f"{int(minutes)}分钟前"
        else:
            return "刚刚"