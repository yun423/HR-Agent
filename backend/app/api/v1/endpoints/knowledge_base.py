"""
知识库管理端点
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.knowledge_base import KnowledgeBase as KnowledgeBaseSchema, KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.schemas.user import User as UserSchema
from app.services.knowledge_base_service import KnowledgeBaseEndpointService
from app.api.deps import get_current_user, get_current_admin_by_role
import logging 

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[KnowledgeBaseSchema])
async def get_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取知识库列表
        GET 返回当前用户可访问的知识库，同时会补充知识库统计信息。
    """
    service = KnowledgeBaseEndpointService(db)
    
    try:
        knowledge_bases = await service.get_accessible_knowledge_bases(
            user_id=str(current_user.id),
            skip=skip,
            limit=limit
        )
        
        # 为每个知识库更新文档数量
        from app.services.knowledge_base_service import KnowledgeBaseService
        kb_service = KnowledgeBaseService(db)
        for kb in knowledge_bases:
            try:
                # 获取并更新知识库统计信息
                stats = await kb_service.get_knowledge_base_stats(kb.id)
                # 更新知识库对象的文档数量
                kb.document_count = stats.get("document_count", 0)
            except Exception as e:
                logger.warning(f"更新知识库 {kb.id} 文档数量时出错: {e}")
                # 如果更新失败，保持原值
        
        return knowledge_bases
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表错误: {str(e)}"
        )


@router.post("/", response_model=KnowledgeBaseSchema)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    创建新的知识库
    """
    service = KnowledgeBaseEndpointService(db)
    
    try:
        knowledge_base = await service.create_knowledge_base(kb_data)
        return knowledge_base
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库错误: {str(e)}"
        )



@router.put("/{kb_id}", response_model=KnowledgeBaseSchema)
async def update_knowledge_base(
    kb_id: str,
    kb_update: KnowledgeBaseUpdate,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    更新知识库（仅管理员）
            需要管理员权限，使用 get_current_admin_by_role。
    """
    service = KnowledgeBaseEndpointService(db)
    
    try:
        updated_kb = await service.update_knowledge_base_with_permission_check(
            kb_id=kb_id,
            kb_update=kb_update,
            current_user=current_user
        )
        return updated_kb
        
    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识库错误: {str(e)}"
        )


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除知识库（仅管理员）
    """
    service = KnowledgeBaseEndpointService(db)
    
    try:
        result = await service.delete_knowledge_base_with_permission_check(
            kb_id=kb_id,
            current_user=current_user
        )
        return result
        
    except HTTPException:
        raise  # 重新抛出HTTP异常
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识库错误: {str(e)}"
        )
