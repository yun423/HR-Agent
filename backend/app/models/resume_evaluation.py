"""
    定义简历评价模型
        用于存储简历信息和评价结果的简历评价模型
"""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Integer, Float, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class ResumeStatus(enum.Enum):
    """简历状态枚举"""
    PENDING = "pending"  # 待处理
    REJECTED = "rejected"  # 不通过
    INTERVIEW = "interview"  # 面试


class ResumeEvaluation(BaseModel):
    """简历评价模型：用于保存简历文件、候选人信息和 AI评价结果"""

    __tablename__ = "resume_evaluations"

    # 文件信息
    email_id = Column(String(20), nullable=True, comment="邮件唯一ID，用于简历邮件去重")
    original_filename = Column(String(255), nullable=False, comment="简历原始文件名")
    file_path = Column(String(500), nullable=True, comment="简历文件存储路径")
    file_type = Column(String(10), nullable=False, comment="简历文件类型(pdf, txt, doc, docx)")
    file_size = Column(Integer, nullable=True, comment="简历文件大小，单位字节")

    # 简历文本内容
    resume_content = Column(Text, nullable=False, comment="解析后的简历文本内容")

    # 候选人基本信息（从简历中提取）
    candidate_name = Column(String(100), nullable=True, comment="候选人姓名")
    candidate_position = Column(String(200), nullable=True, comment="候选人应聘岗位")
    candidate_age = Column(Integer, nullable=True, comment="候选人年龄")
    candidate_gender = Column(String(10), nullable=True, comment="候选人性别")
    work_years = Column(Float, nullable=True, comment="工作年限（年）")
    education_level = Column(String(100), nullable=True, comment="教育水平")
    school = Column(String(200), nullable=True, comment="毕业院校")

    # 评价结果
    total_score = Column(Float, nullable=True, comment="简历评价总分")
    evaluation_metrics = Column(JSON, nullable=True, comment="简历详细评价指标")
    """
        evaluation_metrics 格式示例:
        [
            {
                "name": "学历",
                "score": 15,
                "max": 20,
                "reason": "本科学历符合要求"
            },
            {
                "name": "工作经验",
                "score": 18,
                "max": 20,
                "reason": "3年相关工作经验"
            }
        ]
    """

    # 简历状态
    status = Column(Enum(ResumeStatus), nullable=False, default=ResumeStatus.PENDING, comment="简历处理状态")


    # 评价上下文
    job_description_id = Column(UUID(as_uuid=True), nullable=False, comment="关联职位描述ID")
    scoring_criteria_id = Column(UUID(as_uuid=True), nullable=True, comment="关联评分标准ID")
    conversation_id = Column(String(255), nullable=True, comment="关联对话ID")

    # AI评价的原始响应
    ai_response = Column(JSON, nullable=True, comment="Dify返回的完整响应")

    # 关联关系
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="创建用户ID")
    created_by_user = relationship("User")

    def __repr__(self):
        return f"<ResumeEvaluation(id={self.id}, candidate_name='{self.candidate_name}', total_score={self.total_score})>"

    def to_evaluation_result(self):
        """ 把数据库模型转换成前端需要的简历评价结果格式。"""
        return {
            "id": str(self.id),
            "evaluation_metrics": self.evaluation_metrics or [],
            "total_score": self.total_score,
            "name": self.candidate_name,
            "position": self.candidate_position,
            "workYears": self.work_years,
            "教育水平": self.education_level,
            "年龄": self.candidate_age,
            "sex": self.candidate_gender,
            "school": self.school,
            "resume_content": self.resume_content,
            "original_filename": self.original_filename,
            "status": self.status.value if self.status else "pending",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }