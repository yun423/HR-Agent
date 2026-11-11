"""

知识库管理服务：用于管理知识库的服务
    KnowledgeBaseService 做知识库 CRUD、可访问知识库列表、知识库搜索、统计。
    KnowledgeBaseEndpointService 是面向 API endpoint 的包装层，额外处理管理员权限、知识库访问权限和用户角色校验。
"""
import logging
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, func
from fastapi import HTTPException, status

from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.user import Role, UserRoleAssociation
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.schemas.user import User as UserSchema

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """用于管理知识库的服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_knowledge_base(
        self,
        kb_data: KnowledgeBaseCreate
    ) -> KnowledgeBase:
        """创建新的知识库"""
        try:
            knowledge_base = KnowledgeBase(
                name=kb_data.name,
                description=kb_data.description,
                is_public=kb_data.is_public,
                is_searchable=kb_data.is_searchable,
                category=kb_data.category,
                tags=kb_data.tags or [],
                meta_data=kb_data.meta_data or {}
            )

            self.db.add(knowledge_base)
            await self.db.commit()
            await self.db.refresh(knowledge_base)

            logger.info(f"创建了知识库 {knowledge_base.id}")
            return knowledge_base

        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建知识库时出错: {e}")
            raise

    async def get_knowledge_base(self, kb_id: Union[UUID, str]) -> Optional[KnowledgeBase]:
        """通过ID获取知识库"""
        try:
            # 如果是字符串，转换为UUID
            if isinstance(kb_id, str):
                try:
                    kb_uuid = UUID(kb_id)
                except ValueError:
                    logger.error(f"无效的UUID格式: {kb_id}")
                    return None
            else:
                kb_uuid = kb_id
                
            query = select(KnowledgeBase).where(KnowledgeBase.id == kb_uuid)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取知识库 {kb_id} 时出错: {e}")
            raise

    async def get_knowledge_bases(
        self,
        skip: int = 0,
        limit: int = 20,
        is_public: Optional[bool] = None,
        category: Optional[str] = None
    ) -> List[KnowledgeBase]:
        """获取知识库并可选择过滤"""
        try:
            query = select(KnowledgeBase)

            if is_public is not None:
                query = query.where(KnowledgeBase.is_public == is_public)

            if category:
                query = query.where(KnowledgeBase.category == category)

            query = query.order_by(desc(KnowledgeBase.created_at)).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取知识库时出错: {e}")
            raise

    async def get_accessible_knowledge_bases(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[KnowledgeBase]:
        """获取用户可访问的知识库"""
        try:
            # 目前，返回所有公共知识库
            # 未来，这可能包括用户特定的访问控制
            query = select(KnowledgeBase).where(
                KnowledgeBase.is_public == True
            ).            order_by(desc(KnowledgeBase.created_at)).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取用户 {user_id} 可访问的知识库时出错: {e}")
            raise



    async def update_knowledge_base(
        self,
        kb_id: UUID,
        kb_data: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBase]:
        """更新知识库"""
        try:
            # 检查知识库是否存在
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                return None

            update_data = kb_data.dict(exclude_unset=True)
            if update_data:
                query = (
                    update(KnowledgeBase)
                    .where(KnowledgeBase.id == kb_id)
                    .values(**update_data)
                )
                await self.db.execute(query)
                await self.db.commit()
                await self.db.refresh(kb)

            logger.info(f"更新了知识库 {kb_id}")
            return kb

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新知识库 {kb_id} 时出错: {e}")
            raise

    async def delete_knowledge_base(self, kb_id: UUID) -> bool:
        """删除知识库并更新相关文档"""
        try:
            # 检查知识库是否存在
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                return False

            # 更新文档以移除知识库引用
            await self.db.execute(
                update(Document)
                .where(Document.knowledge_base_id == kb_id)
                .values(knowledge_base_id=None)
            )

            # 删除知识库
            await self.db.execute(
                delete(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )

            await self.db.commit()
            logger.info(f"删除了知识库 {kb_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除知识库 {kb_id} 时出错: {e}")
            raise

    async def search_knowledge_base(
        self,
        kb_id: UUID,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """在特定知识库中搜索"""
        try:
            # 获取知识库
            kb = await self.get_knowledge_base(kb_id)
            if not kb:
                return {"documents": []}

            # 搜索文档
            doc_query = (
                select(Document)
                .where(
                    Document.knowledge_base_id == kb_id,
                    Document.extracted_content.ilike(f"%{query}%")
                )
                .limit(limit)
            )
            doc_result = await self.db.execute(doc_query)
            documents = doc_result.scalars().all()

            return {
                "knowledge_base": {
                    "id": str(kb.id),
                    "name": kb.name,
                    "description": kb.description
                },
                "documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "content": doc.extracted_content[:300]
                    }
                    for doc in documents
                ]
            }

        except Exception as e:
            logger.error(f"搜索知识库 {kb_id} 时出错: {e}")
            raise

    async def get_knowledge_base_stats(self, kb_id: UUID) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            # 获取文档数量
            doc_count_query = select(func.count(Document.id)).where(
                Document.knowledge_base_id == kb_id
            )
            doc_count_result = await self.db.execute(doc_count_query)
            doc_count = doc_count_result.scalar()

            # 更新知识库文档数量
            await self.db.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.id == kb_id)
                .values(document_count=doc_count)
            )
            await self.db.commit()

            return {"document_count": doc_count}

        except Exception as e:
            logger.error(f"获取知识库统计信息 {kb_id} 时出错: {e}")
            raise

class KnowledgeBaseEndpointService:
    """知识库端点服务类，处理所有知识库相关的业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb_service = KnowledgeBaseService(db)

    async def get_accessible_knowledge_bases(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgeBase]:
        """获取用户可访问的知识库列表"""
        try:
            user_uuid = UUID(user_id)
            knowledge_bases = await self.kb_service.get_accessible_knowledge_bases(
                user_id=user_uuid,
                skip=skip,
                limit=limit
            )
            return knowledge_bases
        except Exception as e:
            error_msg = f"获取知识库列表错误: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def create_knowledge_base(
        self,
        kb_data: KnowledgeBaseCreate
    ) -> KnowledgeBase:
        """创建知识库"""
        try:
            knowledge_base = await self.kb_service.create_knowledge_base(kb_data)
            return knowledge_base
        except Exception as e:
            error_msg = f"创建知识库错误: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def _check_admin_permission(self, current_user: UserSchema) -> None:
        """检查管理员权限，无权限则抛出异常"""
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，只有管理员可以执行此操作"
            )

    # async def get_knowledge_base_with_permission_check(
    #     self,
    #     kb_id: str,
    #     current_user: UserSchema
    # ) -> KnowledgeBase:
    #     """获取知识库并检查权限"""
    #     try:
    #         knowledge_base = await self.kb_service.get_knowledge_base(kb_id)
    #         if not knowledge_base:
    #             raise HTTPException(
    #                 status_code=status.HTTP_404_NOT_FOUND,
    #                 detail="知识库未找到"
    #             )
    #         await self._check_knowledge_base_access(knowledge_base, current_user)
    #         return knowledge_base
    #     except HTTPException:
    #         raise
    #     except Exception as e:
    #         logger.error(f"获取知识库错误: {e}")
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail="获取知识库失败"
    #         )

    async def update_knowledge_base_with_permission_check(
        self,
        kb_id: str,
        kb_update: KnowledgeBaseUpdate,
        current_user: UserSchema
    ) -> KnowledgeBase:
        """更新知识库并检查权限"""
        try:
            knowledge_base = await self.kb_service.get_knowledge_base(kb_id)
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="知识库未找到"
                )
            await self._check_admin_permission(current_user)
            
            updated_kb = await self.kb_service.update_knowledge_base(knowledge_base.id, kb_update)
            return updated_kb
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"更新知识库错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新知识库失败"
            )

    async def delete_knowledge_base_with_permission_check(
        self,
        kb_id: str,
        current_user: UserSchema
    ) -> bool:
        """删除知识库并检查权限"""
        try:
            knowledge_base = await self.kb_service.get_knowledge_base(kb_id)
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="知识库未找到"
                )
            await self._check_admin_permission(current_user)
            
            success = await self.kb_service.delete_knowledge_base(knowledge_base.id)
            return {"message": "知识库删除成功"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"删除知识库错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除知识库失败"
            )


    async def _check_knowledge_base_access(
        self,
        knowledge_base: KnowledgeBase,
        current_user: UserSchema
    ) -> bool:
        """检查用户对知识库的访问权限"""
        try:
            # 如果是公开知识库，允许访问
            if knowledge_base.is_public:
                return True

            # 如果是超级管理员，允许访问
            if current_user.is_superuser:
                return True

            # 检查用户是否有访问权限
            query = select(Role).join(UserRoleAssociation).where(
                UserRoleAssociation.user_id == str(current_user.id),
                Role.is_active == True
            )
            result = await self.db.execute(query)
            roles = result.scalars().all()

            # 如果用户有管理员角色，允许访问
            for role in roles:
                if role.name in ["超级管理员", "系统管理员"]:
                    return True

            # 私有知识库，权限不足
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，无法访问此知识库"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"检查知识库访问权限错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="检查访问权限失败"
            )
