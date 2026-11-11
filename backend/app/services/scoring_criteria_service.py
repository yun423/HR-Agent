"""
评分标准服务：处理评分标准的业务逻辑
    负责保存、更新、获取、分页列表、删除评分标准，底层通过remote_service_client请求远程服务。
    业务上对应“根据JD生成/维护简历筛选评分规则”。
"""
from typing import Any, Optional, Dict, List
from uuid import UUID
import logging
from datetime import datetime, timezone
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringCriteriaUpdate,
    ScoringCriteriaListResponse,
    ScoringCriteriaResponse
)
from app.services.remote_service_client import remote_service_client

logger = logging.getLogger(__name__)


class ScoringCriteriaService:
    """评分标准服务类"""

    def __init__(self, db=None):
        # 不再需要数据库会话，但保留参数以保持接口兼容
        self.db = db

    async def save_scoring_criteria(
        self,
        criteria_data: ScoringCriteriaCreate,
        user_id: UUID
    ) -> ScoringCriteriaResponse:
        """
        保存生成的评分标准到数据库

        Args:
            criteria_data: 评分标准创建数据
            user_id: 用户ID

        Returns:
            保存的评分标准对象
        """
        try:
            # 准备请求数据，使用mode='json'确保UUID等类型被正确序列化
            request_data = criteria_data.model_dump(mode='json')
            
            # 发送POST请求到远程服务
            result_data = await remote_service_client.post(
                endpoint="/scoring-criteria/save",
                data=request_data,
                user_id=user_id
            )
            
            return self._build_scoring_criteria_response(result_data, request_data, user_id)

        except Exception as e:
            logger.error(f"保存评分标准失败: {str(e)}")
            raise

    async def update_scoring_criteria(
        self,
        criteria_id: str,
        criteria_data: ScoringCriteriaUpdate,
        user_id: UUID
    ) -> ScoringCriteriaResponse:
        """
        更新已保存的评分标准

        Args:
            criteria_id: 评分标准ID
            criteria_data: 评分标准更新数据
            user_id: 用户ID

        Returns:
            更新后的评分标准对象
        """
        try:
            # 准备请求数据，使用mode='json'确保UUID等类型被正确序列化
            request_data = criteria_data.model_dump(mode='json', exclude_unset=True)
            
            # 发送PUT请求到远程服务
            result_data = await remote_service_client.put(
                endpoint=f"/scoring-criteria/{criteria_id}",
                data=request_data,
                user_id=user_id
            )
            
            return self._build_scoring_criteria_response(result_data, request_data, user_id, criteria_id=criteria_id)

        except Exception as e:
            logger.error(f"更新评分标准失败: {str(e)}")
            raise

    def _build_scoring_criteria_response(
        self,
        result_data: Dict[str, Any],
        request_data: Dict[str, Any],
        user_id: UUID,
        criteria_id: Optional[str] = None,
    ) -> ScoringCriteriaResponse:
        payload = result_data.get("data") if isinstance(result_data.get("data"), dict) else result_data
        merged_data = {
            **request_data,
            **payload,
        }
        now = datetime.now(timezone.utc).isoformat()
        if criteria_id:
            merged_data.setdefault("id", criteria_id)
        merged_data.setdefault("user_id", str(user_id))
        merged_data.setdefault("workflow_type", request_data.get("workflow_type") or "scoring_criteria_generation")
        merged_data.setdefault("created_at", now)
        merged_data.setdefault("updated_at", now)
        merged_data.setdefault("is_active", True)
        return ScoringCriteriaResponse(**merged_data)

    async def get_scoring_criteria(
        self,
        criteria_id: str,
        user_id: UUID
    ) -> ScoringCriteriaResponse:
        """
        获取单个评分标准详情

        Args:
            criteria_id: 评分标准ID
            user_id: 用户ID

        Returns:
            评分标准对象
        """
        try:
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint=f"/scoring-criteria/{criteria_id}",
                user_id=user_id
            )
            
            return ScoringCriteriaResponse(**result_data)

        except Exception as e:
            logger.error(f"获取评分标准失败: {str(e)}")
            raise

    async def get_scoring_criteria_list(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        job_description_id: Optional[str] = None
    ) -> ScoringCriteriaListResponse:
        """
        获取评分标准列表

        Args:
            user_id: 用户ID
            page: 页码
            size: 每页数量
            job_description_id: 关联的JD ID

        Returns:
            评分标准列表响应对象
        """
        try:
            # 准备查询参数
            additional_params = {
                "page": page,
                "size": size
            }
            if job_description_id:
                additional_params["job_description_id"] = job_description_id
            
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint="/scoring-criteria/",
                user_id=user_id,
                additional_params=additional_params
            )
            
            return ScoringCriteriaListResponse(**result_data)

        except Exception as e:
            logger.error(f"获取评分标准列表失败: {str(e)}")
            raise

    async def delete_scoring_criteria(
        self,
        criteria_id: str,
        user_id: UUID
    ) -> Dict[str, str]:
        """
        删除评分标准（软删除）

        Args:
            criteria_id: 评分标准ID
            user_id: 用户ID

        Returns:
            删除结果信息
        """
        try:
            # 发送DELETE请求到远程服务
            result_data = await remote_service_client.delete(
                endpoint=f"/scoring-criteria/{criteria_id}",
                user_id=user_id
            )
            
            return result_data

        except Exception as e:
            logger.error(f"删除评分标准失败: {str(e)}")
            raise
