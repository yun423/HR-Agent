"""
用于管理文档上传、处理和向量搜索的文档服务：
    传统文档服务，负责上传、保存、查询、更新、删除和搜索文档。
    上传时会计算 hash、判断重复、保存文件、提取文本、生成 embedding，并写入 Document 表。
    搜索时会根据 query 生成向量，结合数据库里的文档 embedding 做语义检索。
"""
import logging
import os
import hashlib
from typing import List, Optional, Dict, Any, BinaryIO
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.services.llm_service import LLMService
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """用于管理文档和向量搜索的服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()

    async def upload_document(
        self,
        user_id: UUID,
        file: BinaryIO,
        filename: str,
        knowledge_base_id: Optional[UUID] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Document:
        """上传并处理文档"""
        try:
            # 读取文件内容
            file_content = file.read()
            file_size = len(file_content)

            # 生成文件哈希用于去重
            file_hash = hashlib.sha256(file_content).hexdigest()

            # 检查文档是否已存在
            existing_doc = await self._get_document_by_hash(file_hash, user_id)
            if existing_doc:
                logger.info(f"哈希为{file_hash}的文档已存在")
                return existing_doc

            # 确定MIME类型
            mime_type = self._get_mime_type(filename)

            # 提取文本内容
            extracted_content = await self._extract_text_content(file_content, mime_type)

            # 为文档生成嵌入
            embedding = await self.llm_service.generate_embedding(
                f"{filename} {extracted_content[:1000]}"
            )

            # 保存文件到存储
            file_path = await self._save_file(file_content, filename, user_id)

            # 创建文档记录
            document = Document(
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_hash=file_hash,
                mime_type=mime_type,
                extracted_content=extracted_content,
                embedding=embedding,
                category=category,
                tags=tags or [],
                meta_data={
                    "upload_method": "api",
                    "processing_status": "completed"
                }
            )

            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            # 将文档处理成块以获得更好的搜索效果
            await self._create_document_chunks(document)

            logger.info(f"为用户{user_id}上传了文档{document.id}")
            return document

        except Exception as e:
            await self.db.rollback()
            logger.error(f"上传文档时出错: {e}")
            raise

    async def get_document(
        self,
        document_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Document]:
        """通过ID获取文档"""
        try:
            query = select(Document).where(Document.id == document_id)

            if user_id:
                query = query.where(Document.user_id == user_id)

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取文档{document_id}时出错: {e}")
            raise

    async def get_user_documents(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        knowledge_base_id: Optional[UUID] = None
    ) -> List[Document]:
        """获取用户的文档"""
        try:
            query = select(Document).where(Document.user_id == user_id)

            if category:
                query = query.where(Document.category == category)

            if knowledge_base_id:
                query = query.where(Document.knowledge_base_id == knowledge_base_id)

            query = query.order_by(desc(Document.created_at)).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取用户{user_id}的文档时出错: {e}")
            raise

    async def update_document(
        self,
        document_id: UUID,
        user_id: UUID,
        document_data: DocumentUpdate
    ) -> Optional[Document]:
        """更新文档"""
        try:
            # 检查文档是否存在且属于用户
            document = await self.get_document(document_id, user_id)
            if not document:
                return None

            update_data = document_data.dict(exclude_unset=True)
            if update_data:
                query = (
                    update(Document)
                    .where(Document.id == document_id)
                    .values(**update_data)
                )
                await self.db.execute(query)
                await self.db.commit()
                await self.db.refresh(document)

            logger.info(f"更新了文档{document_id}")
            return document

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新文档{document_id}时出错: {e}")
            raise

    async def delete_document(
        self,
        document_id: UUID,
        user_id: UUID
    ) -> bool:
        """删除文档及其块"""
        try:
            # 检查文档是否存在且属于用户
            document = await self.get_document(document_id, user_id)
            if not document:
                return False

            # 从存储中删除文件
            if document.file_path and os.path.exists(document.file_path):
                os.remove(document.file_path)

            # 从langchain_pg_embedding表中删除文档块
            from sqlalchemy import text
            delete_query = text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' = :document_id
            """)
            await self.db.execute(delete_query, {"document_id": str(document_id)})

            # 删除文档
            await self.db.execute(
                delete(Document).where(Document.id == document_id)
            )

            await self.db.commit()
            logger.info(f"删除了文档{document_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除文档{document_id}时出错: {e}")
            raise

    async def search_documents(
        self,
        query: str,
        user_id: UUID,
        limit: int = 10,
        knowledge_base_id: Optional[UUID] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """使用向量相似性搜索文档"""
        try:
            # 生成查询嵌入
            query_embedding = await self.llm_service.generate_embedding(query)

            # 构建基础查询
            base_query = select(Document).where(Document.user_id == user_id)

            if knowledge_base_id:
                base_query = base_query.where(Document.knowledge_base_id == knowledge_base_id)

            if category:
                base_query = base_query.where(Document.category == category)

            # 现在，我们将进行简单的文本搜索
            # 在生产环境中，您将使用pgvector进行相似性搜索
            text_query = base_query.where(
                Document.extracted_content.ilike(f"%{query}%")
            ).limit(limit)

            result = await self.db.execute(text_query)
            documents = result.scalars().all()

            # 格式化结果
            search_results = []
            for doc in documents:
                search_results.append({
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "content": doc.extracted_content[:500],
                    "category": doc.category,
                    "tags": doc.tags,
                    "created_at": doc.created_at.isoformat()
                })

            return search_results

        except Exception as e:
            logger.error(f"搜索文档时出错: {e}")
            raise

    async def _get_document_by_hash(
        self,
        file_hash: str,
        user_id: UUID
    ) -> Optional[Document]:
        """通过文件哈希获取文档"""
        query = select(Document).where(
            Document.file_hash == file_hash,
            Document.user_id == user_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_mime_type(self, filename: str) -> str:
        """从文件名确定MIME类型"""
        extension = filename.lower().split('.')[-1]
        mime_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'html': 'text/html',
            'json': 'application/json',
            'csv': 'text/csv'
        }
        return mime_types.get(extension, 'application/octet-stream')

    async def _extract_text_content(self, file_content: bytes, mime_type: str) -> str:
        """从文件中提取文本内容"""
        try:
            if mime_type == 'text/plain':
                return file_content.decode('utf-8')
            elif mime_type == 'application/json':
                return file_content.decode('utf-8')
            elif mime_type == 'text/csv':
                return file_content.decode('utf-8')
            else:
                # 对于其他类型，返回占位符
                # 在生产环境中，您将使用PyPDF2、python-docx等库
                return f"从{mime_type}文件中提取的内容"

        except Exception as e:
            logger.error(f"提取文本内容时出错: {e}")
            return "提取内容时出错"

    async def _save_file(self, file_content: bytes, filename: str, user_id: UUID) -> str:
        """将文件保存到存储"""
        try:
            # 创建用户目录
            user_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
            os.makedirs(user_dir, exist_ok=True)

            # 生成唯一文件名
            file_hash = hashlib.sha256(file_content).hexdigest()[:8]
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{file_hash}{ext}"

            file_path = os.path.join(user_dir, unique_filename)

            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)

            return file_path

        except Exception as e:
            logger.error(f"保存文件时出错: {e}")
            raise

    # 注意: _create_document_chunks方法已移除 - 现在直接使用langchain_pg_embedding表
    # 文档块通过enhanced_document_service.py中的PGVector创建