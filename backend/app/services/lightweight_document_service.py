"""

轻量文档服务：用于不依赖LLM初始化的基础文档操作
    不初始化 LLM/embedding，只做基础文档查询、按用户列文档、按 ID 获取、删除和权限检查。
    适合不需要向量检索的接口，避免加载 AI 相关依赖。
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.document import Document
from app.schemas.user import User as UserSchema

logger = logging.getLogger(__name__)


class BaseDocumentService:
    """基础文档服务类，包含通用辅助函数"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_document_with_permission_check(
        self,
        document_id: str,
        current_user: UserSchema
    ) -> Document:
        """
        根据ID获取文档并进行权限检查

        参数:
            document_id: 文档ID
            current_user: 当前用户

        返回:
            Document: 文档对象

        异常:
            HTTPException: 404 文档未找到或 403 权限不足
        """
        document = await self.get_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档未找到"
            )

        # 检查权限
        if document.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )

        return document

    async def handle_document_service_error(
        self,
        exception: Exception,
        operation: str = "操作"
    ) -> None:
        """
        处理文档服务错误并抛出适当的HTTP异常

        参数:
            exception: 捕获的异常
            operation: 操作描述

        异常:
            HTTPException: 适当的HTTP异常
        """
        error_message = str(exception)

        if isinstance(exception, ValueError):
            if "not found" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="文档未找到"
                )
            elif "permission denied" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{operation}时出错: {error_message}"
            )


class LightweightDocumentService(BaseDocumentService):
    """轻量级服务，用于不依赖LLM的基础文档操作"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        logger.info("轻量级文档服务已初始化")

    async def get_user_documents(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        knowledge_base_id: Optional[UUID] = None
    ) -> List[Document]:
        """获取用户文档，支持可选过滤 - 性能优化版本"""
        try:
            query = select(Document).where(Document.user_id == user_id)
            
            if category:
                query = query.where(Document.category == category)
            
            if knowledge_base_id:
                query = query.where(Document.knowledge_base_id == knowledge_base_id)
            
            query = query.offset(skip).limit(limit).order_by(desc(Document.created_at))
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"获取用户文档时出错: {e}")
            raise

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """根据ID获取文档"""
        try:
            query = select(Document).where(Document.id == UUID(document_id))
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取文档 {document_id} 时出错: {e}")
            return None

    async def delete_document(self, document_id: str) -> bool:
        """根据ID删除文档"""
        try:
            document = await self.get_by_id(document_id)
            if not document:
                return False
            
            await self.db.delete(document)
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"删除文档 {document_id} 时出错: {e}")
            raise