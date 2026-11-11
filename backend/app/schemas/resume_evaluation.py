"""
请求/响应验证的简历评估方案
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


class EvaluationMetric(BaseModel):
    """单个评价指标"""
    name: str = Field(..., description="指标名称")
    score: float = Field(..., description="得分")
    max: float = Field(..., description="满分")
    reason: str = Field(..., description="评分理由")


class ResumeEvaluationCreate(BaseModel):
    """创建简历评价的请求"""
    job_description_id: UUID = Field(..., description="关联的JD ID")
    scoring_criteria_id: Optional[UUID] = Field(None, description="评分标准ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")


class ResumeEvaluationUpdate(BaseModel):
    """更新简历评价的请求"""
    candidate_name: Optional[str] = Field(None, description="候选人姓名")
    candidate_position: Optional[str] = Field(None, description="应聘岗位")
    candidate_age: Optional[int] = Field(None, description="候选人年龄")
    candidate_gender: Optional[str] = Field(None, description="候选人性别")
    work_years: Optional[float] = Field(None, description="工作年限")
    education_level: Optional[str] = Field(None, description="教育水平")
    school: Optional[str] = Field(None, description="毕业院校")
    total_score: Optional[float] = Field(None, description="总分")
    evaluation_metrics: Optional[List[EvaluationMetric]] = Field(None, description="评价指标列表")


class ResumeEvaluationResponse(BaseModel):
    """简历评价响应"""
    id: UUID = Field(..., description="简历评价ID")
    original_filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型")
    resume_content: str = Field(..., description="简历文本内容")

    # 候选人信息
    candidate_name: Optional[str] = Field(None, description="候选人姓名")
    candidate_position: Optional[str] = Field(None, description="应聘岗位")
    candidate_age: Optional[int] = Field(None, description="候选人年龄")
    candidate_gender: Optional[str] = Field(None, description="候选人性别")
    work_years: Optional[float] = Field(None, description="工作年限")
    education_level: Optional[str] = Field(None, description="教育水平")
    school: Optional[str] = Field(None, description="毕业院校")

    # 评价结果
    total_score: Optional[float] = Field(None, description="总分")
    evaluation_metrics: Optional[List[Dict[str, Any]]] = Field(None, description="评价指标列表")

    # 关联信息
    job_description_id: UUID = Field(..., description="职位描述ID")
    scoring_criteria_id: Optional[UUID] = Field(None, description="评分标准ID")
    user_id: UUID = Field(..., description="用户ID")

    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ResumeEvaluationListResponse(BaseModel):
    """简历评价列表响应"""
    items: List[ResumeEvaluationResponse] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class ResumeUploadRequest(BaseModel):
    """简历上传请求"""
    job_description_id: UUID = Field(..., description="关联的JD ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")


class AIEvaluationResult(BaseModel):
    """AI评价结果（Dify返回的格式）"""
    evaluation_metrics: List[EvaluationMetric] = Field(..., description="评价指标列表")
    total_score: float = Field(..., description="总分")
    name: Optional[str] = Field(None, description="候选人姓名")
    position: Optional[str] = Field(None, description="应聘岗位")
    workYears: Optional[float] = Field(None, description="工作年限")
    教育水平: Optional[str] = Field(None, description="教育水平")
    年龄: Optional[int] = Field(None, description="年龄")
    sex: Optional[str] = Field(None, description="性别")
    school: Optional[str] = Field(None, description="毕业院校")


class ResumeEvaluationResult(BaseModel):
    """完整的简历评价结果（返回给前端）"""
    id: UUID = Field(..., description="简历评价ID")
    evaluation_metrics: List[Dict[str, Any]] = Field(..., description="评价指标列表")
    total_score: Optional[float] = Field(..., description="总分")
    name: Optional[str] = Field(..., description="名称")
    position: Optional[str] = Field(..., description="职位")
    workYears: Optional[float] = Field(..., description="工作年限")
    education: Optional[str] = Field(..., description="学历要求")
    age: Optional[int] = Field(..., description="年龄")
    sex: Optional[str] = Field(..., description="性别")
    school: Optional[str] = Field(..., description="毕业院校")
    resume_content: str = Field(..., description="简历文本内容")
    original_filename: str = Field(..., description="原始文件名")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class ExportZipRequest(BaseModel):
    """导出zip请求"""
    resume_ids: List[UUID] = Field(..., description="简历ID列表")


