"""
    面试方案相关的API接口：面试方案管理功能
    - 创建、更新、删除面试方案记录
    - 保存和管理面试方案内容
    - 查询面试方案列表和详情

    负责面试方案管理，挂载前缀是 /interview-plans。
    主要接口：
        POST   /interview-plans/save-generated
        PUT    /interview-plans/{plan_id}
        GET    /interview-plans/{plan_id}
        GET    /interview-plans/
        DELETE /interview-plans/{plan_id}

    调用 InterviewPlanService
    用于保存生成后的面试方案、更新方案、获取方案详情、分页获取列表、删除方案。
    所有接口都需要当前登录用户，确保用户只能操作自己的数据。

"""
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.schemas.user import User as UserSchema
from app.schemas.interview_plan import (
    InterviewPlanCreate,
    InterviewPlanUpdate,
    InterviewPlanResponse,
    InterviewPlanListResponse,
    InterviewPlanSaveRequest,
    InterviewPlanGenerateRequest
)
from app.services.interview_plan_service import InterviewPlanService

router = APIRouter()


@router.post("/save-generated", response_model=InterviewPlanResponse)
async def create_interview_plan(
    plan_data: InterviewPlanCreate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    创建面试方案
    """
    try:
        service = InterviewPlanService(db)
        interview_plan = await service.create_interview_plan(
            user_id=current_user.id,
            plan_data=plan_data
        )
        return interview_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建面试方案失败: {str(e)}"
        )


@router.put("/{plan_id}", response_model=InterviewPlanResponse)
async def update_interview_plan(
    plan_id: UUID,
    plan_data: InterviewPlanUpdate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
        更新面试方案
    """
    try:
        service = InterviewPlanService(db)
        interview_plan = await service.update_interview_plan(
            plan_id=plan_id,
            user_id=current_user.id,
            plan_data=plan_data
        )
        return interview_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新面试方案失败: {str(e)}"
        )


@router.get("/{plan_id}", response_model=InterviewPlanResponse)
async def get_interview_plan(
    plan_id: UUID,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取面试方案详情
    """
    try:
        service = InterviewPlanService(db)
        interview_plan = await service.get_interview_plan(
            plan_id=plan_id,
            user_id=current_user.id
        )
        return interview_plan
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取面试方案失败: {str(e)}"
        )


@router.get("/", response_model=InterviewPlanListResponse)
async def list_interview_plans(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    resume_evaluation_id: Optional[UUID] = Query(None, description="简历评价ID"),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取面试方案列表
    """
    try:
        service = InterviewPlanService(db)
        result = await service.list_interview_plans(
            user_id=current_user.id,
            page=page,
            size=size,
            resume_evaluation_id=resume_evaluation_id
        )
        
        return InterviewPlanListResponse(
            items=result["items"],
            total=result["total"],
            page=result["page"],
            size=result["size"],
            pages=result["pages"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取面试方案列表失败: {str(e)}"
        )

# todo：删除面试方案不是软删除，前端未实现
@router.delete("/{plan_id}")
async def delete_interview_plan(
    plan_id: UUID,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除面试方案
    """
    try:
        service = InterviewPlanService(db)
        result = await service.delete_interview_plan(
            plan_id=plan_id,
            user_id=current_user.id
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除面试方案失败: {str(e)}"
        )
