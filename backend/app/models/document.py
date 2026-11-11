"""
    用于文件管理和向量存储的文档模型
        用于存储上传文件的信息、解析内容、向量 embedding 和知识库归属
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.models.base import BaseModel
from app.core.config import settings


class Document(BaseModel):
    """ 用于存储文件及其元数据的文档模型 """

    __tablename__ = "documents"

    # 基本信息
    filename = Column(String(255), nullable=False, comment="存储文件名")
    original_filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="文件存储路径")
    file_size = Column(Integer, nullable=False, comment="文件大小，单位字节")
    file_hash = Column(String(64), nullable=False, comment="文件SHA256哈希值")
    mime_type = Column(String(100), nullable=False, comment="文件MIME类型")

    # 内容和元数据
    extracted_content = Column(Text, nullable=True, comment="文件解析后的文本内容")
    meta_data = Column(JSON, nullable=True, comment="文档扩展元数据")

    # 用于语义搜索的向量嵌入
    #     表示文档的向量，用于语义搜索，依赖 PostgreSQL 的 pgvector。
    embedding = Column(Vector(settings.VECTOR_DIMENSION), nullable=True, comment="文档语义向量")

    # 分类
    category = Column(String(100), nullable=True, comment="文档分类")
    tags = Column(JSON, nullable=True, comment="文档标签列表")

    # 关系： 文档由哪个用户上传
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="上传用户ID")
    uploaded_by = relationship("User", back_populates="documents")

    # 文档属于哪个知识库
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=True, comment="所属知识库ID")

    def __repr__(self):
        return f"<Document at {hex(id(self))}>"


