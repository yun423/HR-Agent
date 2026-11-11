"""
    定义聊天会话和消息
"""
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Enum, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStatus(str, enum.Enum):
    """对话状态枚举：激活、归档、删除"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Conversation(BaseModel):
    """用于存储聊天会话的对话模型"""

    __tablename__ = "conversations"

    # 基本信息
    title = Column(String(255), nullable=False, comment="会话标题")
    description = Column(Text, nullable=True, comment="会话描述")
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False, comment="会话状态")

    # 元数据
    meta_data = Column(JSON, nullable=True, comment="会话扩展元数据")
    total_messages = Column(Integer, default=0, nullable=False, comment="消息总数")

    # 关系：表示会话属于某个用户，
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="所属用户ID")
    user = relationship("User", back_populates="conversations")

    # 一个会话可以包含多条消息
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(title='{self.title}', user_id='{self.user_id}')>"


class Message(BaseModel):
    """用于在对话中存储单条消息的消息模型"""

    __tablename__ = "messages"

    model_config = {"protected_namespaces": ()}

    # 内容
    content = Column(Text, nullable=False, comment="消息内容")
    role = Column(Enum(MessageRole), nullable=False, comment="消息角色")

    # AI特定字段
    model_name = Column(String(100), nullable=True, comment="AI模型名称")
    tokens_used = Column(Integer, nullable=True, comment="消耗的Token数量")
    response_time = Column(Float, nullable=True, comment="响应耗时，单位秒")

    # 附加上下文和元数据
    context = Column(JSON, nullable=True, comment="生成消息使用的上下文")
    meta_data = Column(JSON, nullable=True, comment="消息扩展元数据")

    # 反馈
    rating = Column(Integer, nullable=True, comment="用户评分(1-5)")
    feedback = Column(Text, nullable=True, comment="用户反馈")

    # 关系： 消息属于哪个会话
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, comment="所属会话ID")
    conversation = relationship("Conversation", back_populates="messages")

    # parent_message_id 可以用于表达消息之间的父子关系，比如回复链或上下文链。
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True, comment="父消息ID")
    parent_message = relationship("Message", remote_side="Message.id")

    def __repr__(self):
        return f"<Message(role='{self.role}', conversation_id='{self.conversation_id}')>"