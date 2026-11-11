"""
    知识库相关的Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field


class KnowledgeBaseBase(BaseModel):
    """ 知识库基础类 """
    name: str = Field(..., min_length=1, max_length=200, description="名称")
    description: Optional[str] = Field(None, max_length=1000, description="描述信息")
    is_public: bool = Field(False, description="is_public字段")
    is_searchable: bool = Field(True, description="is_searchable字段")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """ 创建一个知识库 """
    pass


class KnowledgeBaseUpdate(BaseModel):
    """ 更新知识库 """
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="名称")
    description: Optional[str] = Field(None, max_length=1000, description="描述信息")
    is_public: Optional[bool] = Field(None, description="is_public字段")
    is_searchable: Optional[bool] = Field(None, description="is_searchable字段")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class KnowledgeBaseInDB(KnowledgeBaseBase):
    """数据库中的知识库"""
    id: UUID = Field(..., description="唯一标识ID")
    document_count: int = Field(..., description="document_count字段")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class KnowledgeBase(KnowledgeBaseInDB):
    """公开的知识库类"""
    pass


class KnowledgeBaseSearch(BaseModel):
    """ 知识库查询 """
    query: str = Field(..., min_length=1, max_length=500, description="查询内容")
    limit: Optional[int] = Field(10, ge=1, le=50, description="限制数量")


class KnowledgeBaseSearchResult(BaseModel):
    """ 知识库查询结果 """
    knowledge_base: Dict[str, Any] = Field(..., description="知识库信息")
    documents: List[Dict[str, Any]] = Field(..., description="文档列表")

