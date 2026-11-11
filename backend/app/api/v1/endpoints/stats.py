"""
统计相关的API端点，负责仪表盘统计接口
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import User as UserSchema
from app.services.stats_service import StatsService

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取仪表板统计数据
    """
    try:
        stats_service = StatsService(db)
        stats = await stats_service.get_dashboard_stats(str(current_user.id))
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计数据失败: {str(e)}"
        )


@router.get("/recruitment-trend")
async def get_recruitment_trend(
    days: int = 30,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取招聘趋势数据
    """
    try:
        stats_service = StatsService(db)
        trend_data = await stats_service.get_recruitment_trend_data(str(current_user.id), days)
        return trend_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取招聘趋势数据失败: {str(e)}"
        )


@router.get("/training-completion")
async def get_training_completion_stats(
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取简历评价分布统计
    """
    try:
        stats_service = StatsService(db)
        completion_stats = await stats_service.get_training_completion_stats(str(current_user.id))
        return completion_stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取简历评价分布统计失败: {str(e)}"
        )


@router.get("/recent-activities")
async def get_recent_activities(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取最近活动记录（支持分页）
    """
    try:
        stats_service = StatsService(db)
        activities = await stats_service.get_recent_activities(str(current_user.id), limit, offset)
        return activities
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近活动记录失败: {str(e)}"
        )