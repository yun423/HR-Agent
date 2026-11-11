"""
评分标准管理相关的API接口
    - 创建、更新、删除评分标准记录
    - 保存和管理评分标准内容
    - 查询评分标准列表和详情
    - 数据库操作和持久化

负责评分标准管理，调用ScoringCriteriaService
用于保存 AI生成的评分标准、更新评分标准、查看详情、分页查询列表、删除评分标准。

"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import User as UserSchema
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringCriteriaUpdate,
    ScoringCriteriaResponse,
    ScoringCriteriaListResponse
)
from app.services.scoring_criteria_service import ScoringCriteriaService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/save", response_model=ScoringCriteriaResponse)
async def save_scoring_criteria(
    criteria_data: ScoringCriteriaCreate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    保存生成的评分标准到数据库
    """
    try:
        service = ScoringCriteriaService(db)
        result = await service.save_scoring_criteria(criteria_data, current_user.id)
        return result
    except Exception as e:
        logger.error(f"保存评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存评分标准失败: {str(e)}"
        )


@router.put("/{criteria_id}", response_model=ScoringCriteriaResponse)
async def update_scoring_criteria(
    criteria_id: str,
    criteria_data: ScoringCriteriaUpdate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    更新已保存的评分标准
    """
    try:
        service = ScoringCriteriaService(db)
        result = await service.update_scoring_criteria(criteria_id, criteria_data, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新评分标准失败: {str(e)}"
        )


@router.get("/{criteria_id}", response_model=ScoringCriteriaResponse)
async def get_scoring_criteria(
    criteria_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取单个评分标准详情
    """
    try:
        service = ScoringCriteriaService(db)
        result = await service.get_scoring_criteria(criteria_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评分标准失败: {str(e)}"
        )


@router.get("/", response_model=ScoringCriteriaListResponse)
async def get_scoring_criteria_list(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    job_description_id: Optional[str] = Query(None, description="关联的JD ID"),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取评分标准列表
    """
    try:
        service = ScoringCriteriaService(db)
        result = await service.get_scoring_criteria_list(
            user_id=current_user.id,
            page=page,
            size=size,
            job_description_id=job_description_id
        )
        return result
    except Exception as e:
        logger.error(f"获取评分标准列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评分标准列表失败: {str(e)}"
        )


@router.delete("/{criteria_id}")
async def delete_scoring_criteria(
    criteria_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除评分标准（软删除）
    """
    try:
        service = ScoringCriteriaService(db)
        result = await service.delete_scoring_criteria(criteria_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除评分标准失败: {str(e)}"
        )