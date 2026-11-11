"""
知识助手业务服务：处理知识库相关的业务逻辑
    组合 EnhancedDocumentService、LightweightDocumentService、RAGService，
    对外提供知识助手配置、流式问答、文档列表。
    核心方法 ask_question_stream 会把用户问题交给 RAG 服务检索并生成回答
"""
import json
import logging
from typing import Any, List, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.services.enhanced_document_service import EnhancedDocumentService
from app.services.lightweight_document_service import LightweightDocumentService
from app.services.rag_service import RAGService
from app.core.config import settings
from app.schemas.user import User as UserSchema

logger = logging.getLogger(__name__)


class KnowledgeAssistantService:
    """知识助手服务类，处理所有知识库相关的业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.enhanced_document_service = EnhancedDocumentService(db)
        self.lightweight_document_service = LightweightDocumentService(db)
        self.rag_service = RAGService(db)

    async def get_config(self) -> Dict[str, Any]:
        """
        获取知识助手配置信息
        
        Returns:
            Dict: 配置信息字典
        """
        logger.info("获取知识助手配置")
        return {
            "context_limit": settings.CONTEXT_LIMIT
        }


    async def ask_question_stream(
        self,
        question: str,
        user_id: str,
        knowledge_base_id: Optional[str] = None,
        context_limit: int = 10,
        conversation_history: Optional[List[Dict]] = None
    ):
        """
        向知识助手提问，使用RAG工作流生成流式响应
        
        Args:
            question: 问题
            user_id: 用户ID
            knowledge_base_id: 知识库ID（可选）
            context_limit: 上下文限制
            conversation_history: 对话历史（可选）
            
        Yields:
            Dict: 流式响应数据块
            
        Raises:
            Exception: 生成答案时发生错误
        """
        logger.info(f"用户 {user_id} 提问: {question}")
        
        try:
            # 转换知识库ID从字符串到UUID（如果提供）
            kb_id = None
            if knowledge_base_id:
                try:
                    kb_id = UUID(knowledge_base_id)
                except (ValueError, TypeError):
                    logger.warning(f"无效的知识库ID格式: {knowledge_base_id}")
                    pass  # 如果UUID无效则使用None
            
            # 解析对话历史
            conv_history = conversation_history or []
            
            # 使用RAG服务生成流式答案
            async for chunk in self.rag_service.ask_question_stream(
                question=question,
                user_id=user_id,
                knowledge_base_id=kb_id,
                conversation_history=conv_history,
                context_limit=context_limit
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"生成答案时发生错误: {str(e)}")
            error_data = {
                "type": "error",
                "error": str(e)
            }
            yield error_data

    async def get_documents(
        self,
        user_id: str,
        knowledge_base_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取知识库中的文档列表（性能优化版本）
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID（可选）
            skip: 跳过的文档数量
            limit: 返回的文档数量限制
            
        Returns:
            Dict: 包含文档列表和总数的字典
            
        Raises:
            HTTPException: 知识库ID格式无效时抛出异常
            Exception: 获取文档失败时抛出异常
        """
        logger.info(f"用户 {user_id} 获取文档列表")
        
        try:
            # 转换知识库ID从字符串到UUID（如果提供）
            kb_id = None
            if knowledge_base_id:
                try:
                    kb_id = UUID(knowledge_base_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="无效的知识库ID格式"
                    )
            
            # 使用轻量级服务获取文档列表（无需LLM初始化）
            documents = await self.lightweight_document_service.get_user_documents(
                user_id=user_id,
                knowledge_base_id=kb_id,
                skip=skip,
                limit=limit
            )
            
            # 将SQLAlchemy模型转换为字典以进行序列化
            documents_data = []
            for doc in documents:
                doc_dict = {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "original_filename": doc.original_filename,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "file_hash": doc.file_hash,
                    "mime_type": doc.mime_type,
                    "extracted_content": doc.extracted_content,
                    "category": doc.category,
                    "tags": doc.tags or [],
                    "knowledge_base_id": str(doc.knowledge_base_id) if doc.knowledge_base_id else None,
                    "user_id": str(doc.user_id),
                    "meta_data": doc.meta_data or {},
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
                }
                documents_data.append(doc_dict)
            
            logger.info(f"获取到 {len(documents_data)} 个文档")
            return {
                "documents": documents_data,
                "total": len(documents_data)
            }
            
        except HTTPException:
            raise  # 重新抛出HTTP异常
        except Exception as e:
            logger.error(f"获取文档列表时发生错误: {str(e)}")
            raise Exception(f"获取文档列表错误: {str(e)}")
