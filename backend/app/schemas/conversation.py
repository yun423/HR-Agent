"""
对话相关的Pydantic模式定义
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.conversation import MessageRole, ConversationStatus


class ConversationBase(BaseModel):
    """基础对话模式"""
    title: str = Field(..., min_length=1, max_length=200, description="对话标题")
    description: Optional[str] = Field(None, max_length=500, description="对话描述")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ConversationCreate(ConversationBase):
    """创建对话的模式"""
    pass


class ConversationUpdate(BaseModel):
    """更新对话的模式"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="对话标题")
    description: Optional[str] = Field(None, max_length=500, description="对话描述")
    status: Optional[ConversationStatus] = Field(None, description="对话状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ConversationInDB(ConversationBase):
    """数据库中的对话模式"""
    id: UUID = Field(..., description="对话ID")
    user_id: UUID = Field(..., description="用户ID")
    status: ConversationStatus = Field(..., description="对话状态")
    message_count: int = Field(..., description="消息数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class Conversation(ConversationInDB):
    """公开对话模式"""
    pass


class MessageBase(BaseModel):
    """基础消息模式"""
    model_config = {"protected_namespaces": ()}
    
    content: str = Field(..., min_length=1, description="消息内容")
    role: MessageRole = Field(..., description="消息角色")
    model_name: Optional[str] = Field(None, description="模型名称")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class MessageCreate(MessageBase):
    """创建消息的模式"""
    conversation_id: UUID = Field(..., description="对话ID")
    parent_id: Optional[UUID] = Field(None, description="父消息ID")


class MessageUpdate(BaseModel):
    """更新消息的模式"""
    content: Optional[str] = Field(None, min_length=1, description="消息内容")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    user_feedback: Optional[Dict[str, Any]] = Field(None, description="用户反馈")


class MessageInDB(MessageBase):
    """数据库中的消息模式"""
    id: UUID = Field(..., description="消息ID")
    conversation_id: UUID = Field(..., description="对话ID")
    parent_id: Optional[UUID] = Field(None, description="父消息ID")
    user_feedback: Optional[Dict[str, Any]] = Field(None, description="用户反馈")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class Message(MessageInDB):
    """公开消息模式"""
    pass


class ConversationWithMessages(Conversation):
    """包含消息的对话模式"""
    messages: List[Message] = Field(default=[], description="消息列表")


class MessageFeedback(BaseModel):
    """消息反馈模式"""
    rating: int = Field(..., ge=1, le=5, description="评分，1-5分")
    feedback: Optional[str] = Field(None, max_length=500, description="反馈内容")
