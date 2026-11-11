"""
    文档相关的Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
import numpy as np
from pydantic import BaseModel, Field, field_validator


class DocumentBase(BaseModel):
    """  文档基础类 schema"""
    filename: str = Field(..., min_length=1, max_length=255, description="文件名")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class DocumentCreate(DocumentBase):
    """ 创建文档 """
    knowledge_base_id: Optional[UUID] = Field(None, description="知识库ID")


class DocumentUpdate(BaseModel):
    """ 更新文档 """
    filename: Optional[str] = Field(None, min_length=1, max_length=255, description="文件名")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    knowledge_base_id: Optional[UUID] = Field(None, description="知识库ID")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class DocumentInDB(DocumentBase):
    """ 数据库中的文档 """
    id: UUID = Field(..., description="唯一标识ID")
    user_id: UUID = Field(..., description="用户ID")
    knowledge_base_id: Optional[UUID] = Field(..., description="知识库ID")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小，单位字节")
    file_hash: str = Field(..., description="文件哈希值")
    mime_type: str = Field(..., description="文件MIME类型")
    extracted_content: Optional[str] = Field(..., description="提取后的文本内容")
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    @field_validator('embedding', mode='before')
    @classmethod
    def convert_embedding(cls, v):
        """将numpy数组转换为list以进行JSON序列化"""
        if v is None:
            return None
        if isinstance(v, np.ndarray):
            return v.tolist()
        return v

    class Config:
        from_attributes = True


class Document(DocumentInDB):
    pass


class DocumentUpload(BaseModel):
    """ 文档上传 """
    knowledge_base_id: Optional[UUID] = Field(None, description="知识库ID")
    category: Optional[str] = Field(None, max_length=100, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class DocumentSearch(BaseModel):
    """ 文档查询 """
    query: str = Field(..., min_length=1, max_length=500, description="查询内容")
    knowledge_base_id: Optional[UUID] = Field(None, description="知识库ID")
    category: Optional[str] = Field(None, description="分类")
    limit: Optional[int] = Field(10, ge=1, le=50, description="限制数量")


class DocumentSearchResult(BaseModel):
    """ 文档查询结果 """
    id: str = Field(..., description="唯一标识ID")
    filename: str = Field(..., description="文件名")
    content: str = Field(..., description="内容")
    category: Optional[str] = Field(..., description="分类")
    tags: List[str] = Field(..., description="标签列表")
    created_at: str = Field(..., description="创建时间")
    relevance_score: Optional[float] = Field(None, description="相关性分数")


class DocumentChunkBase(BaseModel):
    """ 基础文档快类  """
    content: str = Field(..., description="内容")
    chunk_index: int = Field(..., description="分块序号")
    chunk_size: int = Field(..., description="分块大小")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class DocumentChunkInDB(DocumentChunkBase):
    """ 数据库中的文档块 """
    id: UUID = Field(..., description="唯一标识ID")
    document_id: UUID = Field(..., description="文档ID")
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    @field_validator('embedding', mode='before')
    @classmethod
    def convert_embedding(cls, v):
        """ 将numpy数组转换为list以进行JSON序列化 """
        if v is None:
            return None
        if isinstance(v, np.ndarray):
            return v.tolist()
        return v

    class Config:
        from_attributes = True


class DocumentChunk(DocumentChunkInDB):
    pass

