"""
    HR Agent 请求/响应模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentAttachment(BaseModel):
    """聊天附件元信息，用于 Agent 规划前置条件"""
    name: str = Field(..., description="附件名称")
    size: Optional[int] = Field(None, description="附件大小，单位字节")
    content_type: Optional[str] = Field(None, description="附件内容类型")

class AgentChatRequest(BaseModel):
    """HR Agent 对话请求"""
    # 用户自然语言需求、会话id、是否自动执行低风险生成类工具、已确认需求和附件信息
    message: str = Field(..., min_length=1, description="用户自然语言需求")
    conversation_id: Optional[str] = Field(None, description="会话ID，用于延续已有对话")
    auto_execute: bool = Field(True, description="是否自动执行低风险生成类工具")
    confirmed_requirements: Optional[Dict[str, Any]] = Field(None, description="用户确认后的结构化招聘需求")
    attachments: List[AgentAttachment] = Field(default_factory=list, description="聊天消息中携带的附件元信息")


class AgentStep(BaseModel):
    """Agent 执行步骤"""
    id: str = Field(..., description="执行步骤唯一标识")
    title: str = Field(..., description="标题")
    status: str = Field(..., description="状态")
    detail: Optional[str] = Field(None, description="详情说明")
    tool: Optional[str] = Field(None, description="工具名称")

class AgentArtifact(BaseModel):
    """Agent 产物"""
    type: str = Field(..., description="产物类型")
    title: str = Field(..., description="产物标题")
    content: Any = Field(..., description="产物内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")

class AgentChatResponse(BaseModel):
    """HR Agent 对话响应"""
    # 回复文本、识别出的意图、执行步骤、产物、建议、是否需要确认
    message: str = Field(..., description="Agent 返回的消息内容")
    intent: str = Field(..., description="识别出的用户意图")
    route: Optional[str] = Field(None, description="意图对应的处理路由")
    steps: List[AgentStep] = Field(default_factory=list, description="Agent 执行步骤列表")
    artifacts: List[AgentArtifact] = Field(default_factory=list, description="Agent 生成的产物列表")
    suggestions: List[str] = Field(default_factory=list, description="后续操作建议列表")
    requires_confirmation: bool = Field(False, description="是否需要用户确认")
    missing_fields: List[str] = Field(default_factory=list, description="当前仍缺失的必要字段列表")

