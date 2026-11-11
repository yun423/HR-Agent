"""
    评分标准API请求/响应验证的Schema定义
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.scoring_status import ScoringStatus


class ScoringCriteriaBase(BaseModel):
    """评分标准基础Schema"""
    title: str = Field(..., description="标题")
    job_title: Optional[str] = Field(None, description="职位名称")
    content: str = Field(..., description="评分标准正文")
    criteria_data: Optional[Dict[str, Any]] = Field(None, description="结构化评分标准数据")
    total_score: Optional[str] = Field("100", description="总分")
    scoring_dimensions: Optional[List[Dict[str, Any]]] = Field(None, description="评分维度列表")
    status: Optional[str] = Field("draft", description="状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    workflow_type: Optional[str] = Field("scoring_criteria_generation", description="工作流类型")
    job_description_id: Optional[UUID] = Field(None, description="职位描述ID")


class ScoringCriteriaCreate(ScoringCriteriaBase):
    """创建新评分标准的Schema"""
    pass


class ScoringCriteriaUpdate(BaseModel):
    """更新评分标准的Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="标题")
    job_title: Optional[str] = Field(None, max_length=255, description="职位名称")
    content: Optional[str] = Field(None, min_length=1, description="评分标准正文")
    criteria_data: Optional[Dict[str, Any]] = Field(None, description="结构化评分标准数据")
    total_score: Optional[str] = Field(None, max_length=10, description="总分")
    scoring_dimensions: Optional[List[Dict[str, Any]]] = Field(None, description="评分维度列表")
    status: Optional[ScoringStatus] = Field(None, description="状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")
    job_description_id: Optional[UUID] = Field(None, description="职位描述ID")


class ScoringCriteriaInDB(ScoringCriteriaBase):
    """数据库中评分标准的Schema"""
    id: UUID = Field(..., description="唯一标识ID")
    user_id: UUID = Field(..., description="用户ID")
    workflow_type: str = Field(..., description="工作流类型")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_active: bool = Field(..., description="是否启用")

    class Config:
        from_attributes = True


class ScoringCriteriaResponse(ScoringCriteriaInDB):
    """评分标准API响应的Schema"""
    pass


class ScoringCriteriaListResponse(BaseModel):
    """评分标准列表响应的Schema"""
    items: List[ScoringCriteriaResponse] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class ScoringCriteriaGenerateRequest(BaseModel):
    """评分标准生成请求模型"""
    jd_content: str = Field(..., description="职位描述内容")
    job_title: Optional[str] = Field(None, description="职位名称")
    requirements: Optional[Dict[str, Any]] = Field(None, description="结构化职位要求")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(True, description="是否流式返回")

