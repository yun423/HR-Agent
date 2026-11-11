"""
    知识库：
        用于组织文档和信息的知识库模型
"""
from sqlalchemy import Column, String, Text, JSON, Integer, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class KnowledgeBase(BaseModel):
    """ 知识库模型 ： 对应 knowledge_bases 表，用于组织文档"""

    __tablename__ = "knowledge_bases"

    # 基本信息
    name = Column(String(255), nullable=False, unique=True, comment="知识库名称")
    description = Column(Text, nullable=True, comment="知识库描述")

    # 配置
    is_public = Column(Boolean, default=False, nullable=False, comment="是否公开")
    is_searchable = Column(Boolean, default=True, nullable=False, comment="是否允许搜索")

    # 元数据
    meta_data = Column(JSON, nullable=True, comment="知识库扩展元数据")
    document_count = Column(Integer, default=0, nullable=False, comment="文档数量")

    # 分类
    category = Column(String(100), nullable=True, comment="知识库分类")
    tags = Column(JSON, nullable=True, comment="知识库标签列表")

    # 关系：表示一个知识库下可以有多个文档
    documents = relationship("Document", back_populates="knowledge_base")

    def __repr__(self):
        return f"<KnowledgeBase(name='{self.name}', category='{self.category}')>"
