"""
职位描述模式，用于API请求/响应验证
"""
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.jd_status import JDStatus


class JobDescriptionBase(BaseModel):
    """职位描述基础类"""
    title: str = Field(..., description="标题")
    department: Optional[str] = Field(None, description="所属部门")
    location: Optional[str] = Field(None, description="工作地点")
    salary_range: Optional[str] = Field(None, description="薪资范围")
    experience_level: Optional[str] = Field(None, description="经验等级")
    education: Optional[str] = Field(None, description="学历要求")
    job_type: Optional[str] = Field(None, description="工作类型")
    skills: Optional[list[str]] = Field(None, description="技能要求列表")
    content: str = Field(..., description="职位描述正文")
    requirements: Optional[str] = Field(None, description="职位要求")
    status: Optional[str] = Field("draft", description="状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    workflow_type: Optional[str] = Field("jd_generation", description="工作流类型")


class JobDescriptionCreate(JobDescriptionBase):
    """创建新职位描述的类"""
    pass


class JobDescriptionUpdate(BaseModel):
    """更新职位描述的模式"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="标题")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    location: Optional[str] = Field(None, max_length=100, description="工作地点")
    salary_range: Optional[str] = Field(None, max_length=100, description="薪资范围")
    experience_level: Optional[str] = Field(None, max_length=100, description="经验等级")
    education: Optional[str] = Field(None, max_length=100, description="学历要求")
    job_type: Optional[str] = Field(None, max_length=50, description="工作类型")
    skills: Optional[list[str]] = Field(None, description="技能要求列表")
    content: Optional[str] = Field(None, min_length=1, description="职位描述正文")
    requirements: Optional[str] = Field(None, description="职位要求")
    status: Optional[JDStatus] = Field(None, description="状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class JobDescriptionInDB(JobDescriptionBase):
    """数据库中的职位描述模式"""
    id: UUID = Field(..., description="唯一标识ID")
    user_id: UUID = Field(..., description="用户ID")
    workflow_type: str = Field(..., description="工作流类型")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    is_active: bool = Field(..., description="是否启用")

    class Config:
        from_attributes = True


class JobDescriptionResponse(JobDescriptionInDB):
    """职位描述API响应模式"""
    pass


class JobDescriptionListResponse(BaseModel):
    """职位描述列表响应模式"""
    items: list[JobDescriptionResponse] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class JDGenerateRequest(BaseModel):
    """职位描述(JD)生成请求模型"""
    requirements: str = Field(..., description="职位要求描述")
    position_title: Optional[str] = Field(None, description="职位名称")
    department: Optional[str] = Field(None, description="所属部门")
    experience_level: Optional[str] = Field(None, description="经验等级")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(True, description="是否流式返回")

