"""
试卷相关的Pydantic模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ExamGenerateRequest(BaseModel):
    """试卷生成请求模型"""
    title: str = Field(..., description="标题")
    subject: str = Field(..., description="科目")
    description: Optional[str] = Field(None, description="试卷描述")
    difficulty: Optional[str] = Field(None, description="难度等级")
    duration: Optional[int] = Field(None, description="考试时长，单位分钟")
    total_score: int = Field(..., description="总分")
    question_types: Optional[List[str]] = Field(None, description="题型列表")
    question_counts: Optional[Dict[str, int]] = Field(None, description="题目数量配置")
    knowledge_files: Optional[List[Dict[str, Any]]] = Field(None, description="知识库文件列表")
    special_requirements: Optional[str] = Field(None, description="特殊要求")
    conversation_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(True, description="是否流式返回")


class ExamSubmitRequest(BaseModel):
    """考试提交请求模型"""
    exam_id: str = Field(..., description="考试ID")
    student_name: str = Field(..., description="学生姓名")
    department: str = Field(..., description="学生所在院系")
    answers: Dict[str, Any] = Field(..., description="学生答案，使用字典格式存储，键为题目ID，值为答案内容")
    exam_content: str = Field(..., description="试卷内容")


class ExamCreateRequest(BaseModel):
    """试卷创建请求模型"""
    title: str = Field(..., description="标题")
    subject: str = Field(..., description="科目")
    description: Optional[str] = Field(None, description="试卷描述")
    difficulty: Optional[str] = Field(None, description="难度等级")
    duration: Optional[int] = Field(None, description="考试时长，单位分钟")
    total_score: int = Field(..., description="总分")
    question_types: Optional[List[str]] = Field(None, description="题型列表")
    question_counts: Optional[Dict[str, int]] = Field(None, description="题目数量配置")
    knowledge_files: Optional[List[Dict[str, Any]]] = Field(None, description="知识库文件列表")
    special_requirements: Optional[str] = Field(None, description="特殊要求")
    content: Optional[str] = Field(None, description="内容")
    questions: Optional[List[Dict[str, Any]]] = Field(None, description="题目列表")


