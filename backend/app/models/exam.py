"""
    试卷和试题相关的数据库模型
"""
from sqlalchemy import Column, String, Integer, Text, JSON, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Exam(BaseModel):
    """ 试卷模型 """

    __tablename__ = "exams"

    title = Column(String(255), nullable=False, comment="试卷标题")
    subject = Column(String(100), nullable=False, comment="科目")
    description = Column(Text, nullable=True, comment="试卷描述")
    difficulty = Column(String(50), nullable=False, comment="难度等级")
    duration = Column(Integer, nullable=False, comment="考试时长(分钟)")
    total_score = Column(Float, nullable=False, comment="总分")

    # 试卷配置信息
    question_types = Column(JSON, nullable=True, comment="题型配置")
    question_counts = Column(JSON, nullable=True, comment="题目数量配置")
    knowledge_files = Column(JSON, nullable=True, comment="知识库文件")
    special_requirements = Column(Text, nullable=True, comment="特殊要求")
    content = Column(Text, nullable=True, comment="原始试卷内容")

    # 关联关系: 表示一个试卷 可以包含多道题
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    '''
        cascade="all, delete-orphan"： 级联删除关系，意思是删除试卷时，会自动删除关联的题目。
         - 保存试卷时：自动保存关联的题目
         - 删除试卷时：自动删除所有关联题目
         - 移除题目时：如果题目不再属于任何试卷，自动删除该题目
    '''


class Question(BaseModel):
    """试题模型"""

    __tablename__ = "questions"

    question_type = Column(String(50), nullable=False, comment="题型")
    question_text = Column(Text, nullable=False, comment="题目内容")
    options = Column(JSON, nullable=True, comment="选择题选项")
    correct_answer = Column(Text, nullable=True, comment="正确答案")
    score = Column(Float, nullable=False, comment="分值")
    order_index = Column(Integer, nullable=False, comment="题目顺序")
    explanation = Column(Text, nullable=True, comment="题目解释")

    # 关联关系: 表示题目所属试卷
    exam_id = Column(UUID(as_uuid=True), ForeignKey("exams.id"), nullable=False, comment="所属试卷ID")
    exam = relationship("Exam", back_populates="questions")