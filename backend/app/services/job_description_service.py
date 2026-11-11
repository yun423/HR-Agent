"""
职位描述（JD）服务：
    负责创建、更新、获取、分页列表、删除 JD，底层通过 remote_service_client 调远程接口。
    _build_job_description_response 会把远程服务返回的数据整理成 JobDescriptionResponse 需要的结构。
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError

from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
    JobDescriptionResponse,
    JobDescriptionListResponse
)
from app.services.remote_service_client import remote_service_client

logger = logging.getLogger(__name__)


class JobDescriptionService:
    """职位描述服务类"""
    
    def __init__(self, db=None):
        # 不再需要数据库会话，但保留参数以保持接口兼容
        self.db = db
    
    async def create_job_description(
        self, 
        jd_data: JobDescriptionCreate, 
        user_id: UUID
    ) -> JobDescriptionResponse:
        """
        创建新的职位描述
        
        Args:
            jd_data: 职位描述创建数据
            user_id: 用户ID
            
        Returns:
            创建的职位描述对象
            
        Raises:
            Exception: 创建失败时抛出异常
        """
        try:
            # 准备请求数据，使用 mode='json' 确保 UUID/日期等类型可序列化
            request_data = jd_data.model_dump(mode="json")
            
            # 发送POST请求到远程服务
            result_data = await remote_service_client.post(
                endpoint="/job-descriptions/save",
                data=request_data,
                user_id=user_id
            )
            
            jd_response = self._build_job_description_response(result_data, request_data, user_id)
            logger.info(f"成功创建职位描述: {jd_response.id} - {jd_response.title}")
            return jd_response

        except Exception as e:
            logger.error(f"创建职位描述失败: {str(e)}", exc_info=True)
            raise

    def _build_job_description_response(
        self,
        result_data: Dict[str, Any],
        request_data: Dict[str, Any],
        user_id: UUID,
        jd_id: Optional[str] = None,
    ) -> JobDescriptionResponse:
        """兼容远程保存接口返回部分字段，避免已落库但本地响应校验误报失败。"""
        payload = result_data.get("data") if isinstance(result_data.get("data"), dict) else result_data
        merged_data = {
            **request_data,
            **payload,
        }
        now = datetime.now(timezone.utc).isoformat()
        if jd_id:
            merged_data.setdefault("id", jd_id)
        merged_data.setdefault("user_id", str(user_id))
        merged_data.setdefault("workflow_type", request_data.get("workflow_type") or "jd_generation")
        merged_data.setdefault("created_at", now)
        merged_data.setdefault("updated_at", now)
        merged_data.setdefault("is_active", True)

        try:
            return JobDescriptionResponse(**merged_data)
        except ValidationError as exc:
            logger.error(
                "远程 JD 已返回但无法组装响应，result_data=%s, request_title=%s",
                result_data,
                request_data.get("title"),
                exc_info=True,
            )
            raise exc
    
    async def update_job_description(
        self, 
        jd_id: str, 
        jd_data: JobDescriptionUpdate, 
        user_id: UUID
    ) -> JobDescriptionResponse:
        """
        更新职位描述
        
        Args:
            jd_id: 职位描述ID
            jd_data: 更新数据
            user_id: 用户ID
            
        Returns:
            更新后的职位描述对象
            
        Raises:
            ValueError: 职位描述不存在或无权限访问
            Exception: 更新失败时抛出异常
        """
        try:
            # 准备请求数据
            request_data = jd_data.model_dump(exclude_unset=True)
            
            # 发送PUT请求到远程服务
            result_data = await remote_service_client.put(
                endpoint=f"/job-descriptions/{jd_id}",
                data=request_data,
                user_id=user_id
            )
            
            logger.info(f"成功更新职位描述: {jd_id}")
            return self._build_job_description_response(result_data, request_data, user_id, jd_id=jd_id)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"更新职位描述失败: {str(e)}")
            raise
    
    async def get_job_description(
        self, 
        jd_id: str, 
        user_id: UUID
    ) -> JobDescriptionResponse:
        """
        获取指定的职位描述
        
        Args:
            jd_id: 职位描述ID
            user_id: 用户ID
            
        Returns:
            职位描述对象
            
        Raises:
            ValueError: 职位描述不存在或无权限访问
            Exception: 获取失败时抛出异常
        """
        try:
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint=f"/job-descriptions/{jd_id}",
                user_id=user_id
            )
            
            logger.debug(f"成功获取职位描述: {jd_id}")
            return JobDescriptionResponse(**result_data)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"获取职位描述失败: {str(e)}")
            raise
    
    async def list_job_descriptions(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户的职位描述列表
        
        Args:
            user_id: 用户ID
            page: 页码
            size: 每页数量
            status_filter: 状态筛选
            
        Returns:
            包含职位描述列表和分页信息的字典
            
        Raises:
            Exception: 查询失败时抛出异常
        """
        logger.info(f"📥 获取JD列表请求: page={page}, size={size}, status_filter={status_filter}, user_id={user_id}")

        try:
            # 准备查询参数
            additional_params = {
                "page": page,
                "size": size
            }
            if status_filter:
                additional_params["status_filter"] = status_filter
            
            # 发送GET请求到远程服务
            result_data = await remote_service_client.get(
                endpoint="/job-descriptions/",
                user_id=user_id,
                additional_params=additional_params
            )
            
            logger.info(f"📋 返回 {len(result_data.get('items', []))} 条记录")
            return result_data

        except Exception as e:
            logger.error(f"❌ 获取JD列表失败: {str(e)}", exc_info=True)
            raise
    
    async def delete_job_description(
        self, 
        jd_id: str, 
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        删除职位描述（软删除）
        
        Args:
            jd_id: 职位描述ID
            user_id: 用户ID
            
        Returns:
            删除结果消息
            
        Raises:
            ValueError: 职位描述不存在或无权限访问
            Exception: 删除失败时抛出异常
        """
        try:
            deleted_criteria = []
            criteria_failures = []
            try:
                from app.services.scoring_criteria_service import ScoringCriteriaService

                scoring_service = ScoringCriteriaService(self.db)
                criteria_list = await scoring_service.get_scoring_criteria_list(
                    user_id=user_id,
                    page=1,
                    size=100,
                    job_description_id=jd_id,
                )
                for criteria in criteria_list.items:
                    try:
                        await scoring_service.delete_scoring_criteria(str(criteria.id), user_id)
                        deleted_criteria.append({"id": str(criteria.id), "title": criteria.title})
                    except Exception as exc:
                        criteria_failures.append({"id": str(criteria.id), "title": criteria.title, "error": str(exc)})
                        logger.warning("删除 JD 关联评分标准失败 jd_id=%s criteria_id=%s: %s", jd_id, criteria.id, exc)
            except Exception as exc:
                criteria_failures.append({"error": str(exc)})
                logger.warning("查询 JD 关联评分标准失败 jd_id=%s: %s", jd_id, exc)

            # 发送DELETE请求到远程服务
            result_data = await remote_service_client.delete(
                endpoint=f"/job-descriptions/{jd_id}",
                user_id=user_id
            )
            if isinstance(result_data, dict):
                result_data["deleted_scoring_criteria"] = deleted_criteria
                result_data["scoring_criteria_failures"] = criteria_failures
            
            logger.info(f"成功删除职位描述: {jd_id}，关联删除评分标准 {len(deleted_criteria)} 条")
            return result_data

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"删除职位描述失败: {str(e)}")
            raise
    

    
