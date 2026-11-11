"""
  聊天相关的Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.conversation import MessageRole


class ChatMessage(BaseModel):
    """ 聊天消息 """
    message: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    conversation_id: Optional[UUID] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

class ChatRequest(BaseModel):
    """ 聊天请求 """
    message: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    conversation_id: Optional[UUID] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ChatResponse(BaseModel):
    """ 聊天响应 """
    message_id: str = Field(..., description="消息ID")
    conversation_id: str = Field(..., description="会话ID")
    content: str = Field(..., description="回复内容")
    role: MessageRole = Field(..., description="角色")
    timestamp: datetime = Field(..., description="时间戳")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class ChatStreamMessage(BaseModel):
    """ 聊天消息（流式） """
    message: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    conversation_id: Optional[UUID] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ChatSuggestionRequest(BaseModel):
    """ 聊天建议请求 """
    query: str = Field(..., min_length=1, max_length=200, description="查询内容")
    limit: Optional[int] = Field(5, ge=1, le=10, description="限制数量")


class ChatSuggestionResponse(BaseModel):
    """ 聊天建议响应 """
    suggestions: List[str] = Field(..., description="建议列表")


class ChatFeedback(BaseModel):
    """ 聊天反馈 """
    message_id: str = Field(..., description="消息ID")
    rating: int = Field(..., ge=1, le=5, description="评分")
    feedback: Optional[str] = Field(None, max_length=500, description="反馈内容")


class ChatContext(BaseModel):
    """ 聊天上下文 """
    search_documents: bool = Field(True, description="是否搜索文档")
    knowledge_base_id: Optional[UUID] = Field(None, description="知识库ID")
    include_history: bool = Field(True, description="是否包含历史消息")
    max_history_messages: Optional[int] = Field(10, ge=1, le=50, description="最大历史消息数量")

