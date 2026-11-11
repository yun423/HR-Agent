"""
面试方案服务：处理面试方案相关的核心业务逻辑
    通过 remote_service_client 保存、更新、获取、列表查询和删除面试方案。
    代码里有部分直接数据库模型操作被注释，当前主要是把面试方案数据代理到远程服务。
"""
import logging
from typing import Any, List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from app.models.resume_evaluation import ResumeEvaluation
from app.schemas.interview_plan import (
    InterviewPlanCreate,
    InterviewPlanUpdate,
    InterviewPlanResponse,
    InterviewPlanSaveRequest
)
from app.services.remote_service_client import remote_service_client

logger = logging.getLogger(__name__)
class InterviewPlanService:
    """面试方案服务类"""

    def __init__(self, db=None):
        # 不再需要数据库会话，但保留参数以保持接口兼容
        self.db = db

    # 对应前端保存方案
    async def create_interview_plan(
        self,
        user_id: UUID,
        plan_data: InterviewPlanCreate
    ) -> InterviewPlanResponse:
        """
        创建面试方案

        Args:
            user_id: 用户ID
            plan_data: 面试方案创建数据

        Returns:
            创建的面试方案对象

        Raises:
            HTTPException: 简历评价未找到或无权限访问时抛出
        """
        # 验证简历评价是否存在且属于当前用户
        result = await self.db.execute(
            select(ResumeEvaluation).where(
                and_(
                    ResumeEvaluation.id == plan_data.resume_evaluation_id,
                    ResumeEvaluation.user_id == user_id
                )
            )
        )
        resume_evaluation = result.scalar_one_or_none()

        if not resume_evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="简历评价记录未找到或无权限访问"
            )
        try:
            # 准备请求数据，使用mode='json'确保UUID等类型被正确序列化
            request_data = plan_data.model_dump(mode='json')
            
            # 发送POST请求到远程服务
            result_data = await remote_service_client.post(
                endpoint="/interview-plans/save-generated",
                data=request_data,
                user_id=user_id
            )
            
            logger.info(f"成功创建面试方案: {result_data.get('id')}")
            return InterviewPlanResponse(**result_data)
            
        except ValueError as e:
            # 远程服务返回404时抛出ValueError，转换为HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"创建面试方案失败: {str(e)}")
            raise

    # 对应前端编辑后再保存方案
    async def update_interview_plan(
        self,
        plan_id: UUID,
        user_id: UUID,
        plan_data: InterviewPlanUpdate
    ) -> InterviewPlanResponse:
        """
        更新面试方案

        Args:
            plan_id: 面试方案ID
            user_id: 用户ID
            plan_data: 面试方案更新数据

        Returns:
            更新后的面试方案对象

        Raises:
            HTTPException: 面试方案未找到或无权限访问时抛出
        """
        try:
            # 准备请求数据，使用mode='json'确保UUID等类型被正确序列化
            request_data = plan_data.model_dump(mode='json', exclude_unset=True)
            
            # 发送PUT请求到远程服务
            result_data = await remote_service_client.put(
                endpoint=f"/interview-plans/{plan_id}",
                data=request_data,
                user_id=user_id
            )
            
            logger.info(f"成功更新面试方案: {plan_id}")
            return InterviewPlanResponse(**result_data)
            
        except ValueError as e:
            # 远程服务返回404时抛出ValueError，转换为HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"更新面试方案失败: {str(e)}")
            raise

    # async def save_interview_plan_content(
    #     self,
    #     plan_id: UUID,
    #     user_id: UUID,
    #     save_data: InterviewPlanSaveRequest
    # ) -> InterviewPlan:
    #     """
    #     保存面试方案内容（用于前端编辑后保存）

    #     Args:
    #         plan_id: 面试方案ID
    #         user_id: 用户ID
    #         save_data: 保存数据

    #     Returns:
    #         保存后的面试方案对象

    #     Raises:
    #         HTTPException: 面试方案未找到或无权限访问时抛出
    #     """
    #     # 查询面试方案
    #     result = await self.db.execute(
    #         select(InterviewPlan).where(
    #             and_(
    #                 InterviewPlan.id == plan_id,
    #                 InterviewPlan.user_id == user_id
    #             )
    #         )
    #     )
    #     interview_plan = result.scalar_one_or_none()
        
    #     if not interview_plan:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="面试方案未找到或无权限访问"
    #         )
        
    #     # 更新内容
    #     interview_plan.content = save_data.content
    #     if save_data.candidate_name:
    #         interview_plan.candidate_name = save_data.candidate_name
    #     if save_data.candidate_position:
    #         interview_plan.candidate_position = save_data.candidate_position
        
    #     await self.db.commit()
    #     await self.db.refresh(interview_plan)
    #     logger.info(f"成功保存面试方案内容: {interview_plan.id}")
    #     return interview_plan

    async def get_interview_plan(
        self,
        plan_id: UUID,
        user_id: UUID
    ) -> InterviewPlanResponse:
        """
        获取面试方案详情

        Args:
            plan_id: 面试方案ID
            user_id: 用户ID

        Returns:
            面试方案对象

        Raises:
            HTTPException: 面试方案未找到或无权限访问时抛出
        """
        try:
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint=f"/interview-plans/{plan_id}",
                user_id=user_id
            )
            
            logger.info(f"成功获取面试方案详情: {plan_id}")
            return InterviewPlanResponse(**result_data)
            
        except ValueError as e:
            # 远程服务返回404时抛出ValueError，转换为HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"获取面试方案失败: {str(e)}")
            raise

    async def list_interview_plans(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        resume_evaluation_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        获取面试方案列表

        Args:
            user_id: 用户ID
            page: 页码
            size: 每页数量
            resume_evaluation_id: 简历评价ID筛选

        Returns:
            包含面试方案列表和分页信息的字典
        """
        try:
            # 准备查询参数
            additional_params = {
                "page": page,
                "size": size
            }
            if resume_evaluation_id:
                additional_params["resume_evaluation_id"] = str(resume_evaluation_id)
            
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint="/interview-plans/",
                user_id=user_id,
                additional_params=additional_params
            )
            
            logger.info(f"成功获取面试方案列表，第 {page} 页，共 {result_data.get('total', 0)} 条结果")
            return result_data
            
        except Exception as e:
            logger.error(f"获取面试方案列表失败: {str(e)}")
            raise

    async def delete_interview_plan(
        self,
        plan_id: UUID,
        user_id: UUID
    ) -> Dict[str, str]:
        """
        删除面试方案

        Args:
            plan_id: 面试方案ID
            user_id: 用户ID

        Returns:
            删除成功消息

        Raises:
            HTTPException: 面试方案未找到或无权限访问时抛出
        """
        try:
            # 发送DELETE请求到远程服务
            result_data = await remote_service_client.delete(
                endpoint=f"/interview-plans/{plan_id}",
                user_id=user_id
            )
            
            logger.info(f"成功删除面试方案: {plan_id}")
            return result_data
            
        except ValueError as e:
            # 远程服务返回404时抛出ValueError，转换为HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"删除面试方案失败: {str(e)}")
            raise

    # async def save_generated_interview_plan(
    #     self,
    #     user_id: UUID,
    #     plan_data: InterviewPlanCreate
    # ) -> InterviewPlan:
    #     """
    #     保存生成的面试方案内容

    #     Args:
    #         user_id: 用户ID
    #         plan_data: 面试方案创建数据

    #     Returns:
    #         创建的面试方案对象

    #     Raises:
    #         HTTPException: 简历评价未找到或无权限访问时抛出
    #     """
    #     # 验证简历评价是否存在且属于当前用户
    #     result = await self.db.execute(
    #         select(ResumeEvaluation).where(
    #             and_(
    #                 ResumeEvaluation.id == plan_data.resume_evaluation_id,
    #                 ResumeEvaluation.user_id == user_id
    #             )
    #         )
    #     )
    #     resume_evaluation = result.scalar_one_or_none()
        
    #     if not resume_evaluation:
    #         raise HTTPException(
    #             status_code=status.HTTP_404_NOT_FOUND,
    #             detail="简历评价记录未找到或无权限访问"
    #         )
        
    #     # 检查是否已存在面试方案
    #     existing_result = await self.db.execute(
    #         select(InterviewPlan).where(
    #             and_(
    #                 InterviewPlan.resume_evaluation_id == plan_data.resume_evaluation_id,
    #                 InterviewPlan.user_id == user_id
    #             )
    #         )
    #     )
    #     existing_plan = existing_result.scalar_one_or_none()
        
    #     if existing_plan:
    #         # 如果已存在，则更新现有方案
    #         existing_plan.candidate_name = plan_data.candidate_name
    #         existing_plan.candidate_position = plan_data.candidate_position
    #         existing_plan.content = plan_data.content
            
    #         await self.db.commit()
    #         await self.db.refresh(existing_plan)
    #         logger.info(f"成功更新面试方案2: {existing_plan.id}")
    #         return existing_plan
    #     else:
    #         # 如果不存在，则创建新方案
    #         return await self.create_interview_plan(user_id, plan_data)