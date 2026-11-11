from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class IntentRouteRequest(BaseModel):
    """意图路由请求"""
    query: str = Field(..., description="查询内容")


class IntentRouteResponse(BaseModel):
    """意图路由响应"""
    intent: str = Field(..., description="用户意图")
    route: str = Field(..., description="处理路由")
    query: str = Field("", description="查询内容")


class RequirementParseRequest(BaseModel):
    """ 需求解析请求 """
    text: str = Field(..., description="待解析的招聘需求文本")
    conversation_id: Optional[str] = Field(None, description="会话ID")


class RequirementParseResponse(BaseModel):
    """ 需求解析响应 """
    job_title: Optional[str] = Field(None, description="职位名称")
    department: Optional[str] = Field(None, description="所属部门")
    location: Optional[str] = Field(None, description="工作地点")
    salary: Optional[str] = Field(None, description="薪资范围")
    experience: Optional[str] = Field(None, description="经验要求")
    education: Optional[str] = Field(None, description="学历要求")
    job_type: Optional[str] = Field(None, description="工作类型")
    skills: Optional[List[str]] = Field(None, description="技能要求列表")
    benefits: Optional[List[str]] = Field(None, description="福利待遇列表")
    additional_requirements: Optional[str] = Field(None, description="补充要求")


class ExamIntentParseRequest(BaseModel):
    """试卷意图解析请求"""
    text: str = Field(..., description="待解析的试卷需求文本")
    conversation_id: Optional[str] = Field(None, description="会话ID")


class KnowledgeFileInfo(BaseModel):
    """知识库文件信息模型"""
    id: str = Field(..., description="唯一标识ID")
    fileName: Optional[str] = Field(None, description="文件名称")


class ExamIntentParseResponse(BaseModel):
    """试卷意图解析响应"""
    title: Optional[str] = Field(None, description="标题")
    subject: Optional[str] = Field(None, description="科目")
    total_score: Optional[int] = Field(100, description="总分")
    difficulty: Optional[str] = Field("medium", description="难度等级")
    duration: Optional[int] = Field(90, description="考试时长，单位分钟")
    question_counts: Dict[str, int] = Field({}, description="题目数量配置")
    special_requirements: Optional[str] = Field(None, description="特殊要求")
    knowledge_files: List[KnowledgeFileInfo] = Field([], description="知识库文件列表")


