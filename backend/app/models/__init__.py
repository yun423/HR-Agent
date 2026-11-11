""""""
"""
总体说明
    models目录主要放 SQLAlchemy ORM 数据模型，也就是数据库表和 Python 类之间的映射。
    大多数模型都继承BaseModel，因此自动拥有 id、created_at、updated_at、is_active 等公共字段。
"""

# 导入所有模型，确保关系映射正确
from app.models.base import BaseModel
from app.models.user import User
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.models.conversation import Conversation, Message
from app.models.resume_evaluation import ResumeEvaluation
from app.models.exam import Exam, Question
from app.models.exam_result import ExamResult

# 导出所有模型：这个包对外推荐导出的名字列表
__all__ = [
    "BaseModel",
    "User",
    "Document",
    "KnowledgeBase",
    "Conversation",
    "Message",
    "ResumeEvaluation",
    "Exam",
    "Question",
    "ExamResult"
]
