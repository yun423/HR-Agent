"""
用于处理AI对话的聊天服务:
    BaseChatService 负责获取或创建会话、统一错误处理；
    ChatService 负责处理用户消息、调用LLMService 生成回复、保存用户/助手消息、流式输出回复、生成建议、提交消息反馈。
"""
import logging
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.conversation_service import ConversationService
from app.services.document_service import DocumentService
from app.schemas.chat import ChatResponse, ChatRequest
from app.schemas.conversation import ConversationCreate
from app.schemas.user import User as UserSchema
from app.models.conversation import MessageRole

logger = logging.getLogger(__name__)


class BaseChatService:
    """聊天服务基类，包含通用辅助方法"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.conversation_service = ConversationService(db)
        self.document_service = DocumentService(db)

    async def get_or_create_conversation(
        self,
        chat_request: ChatRequest,
        current_user: UserSchema
    ) -> Any:
        """
        获取或创建对话
        
        Args:
            chat_request: 聊天请求
            current_user: 当前用户
            
        Returns:
            对话对象
            
        Raises:
            HTTPException: 当对话未找到或权限不足时
        """
        if chat_request.conversation_id:
            conversation = await self.conversation_service.get_conversation(
                conversation_id=chat_request.conversation_id,
                user_id=current_user.id
            )
            if not conversation or conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="对话未找到"
                )
            return conversation
        else:
            # 创建新对话
            conversation_data = ConversationCreate(
                title=chat_request.message[:50] + "..." if len(chat_request.message) > 50 else chat_request.message
            )
            return await self.conversation_service.create_conversation(
                user_id=current_user.id,
                conversation_data=conversation_data
            )

    def handle_chat_error(self, error: Exception, operation: str) -> HTTPException:
        """
        统一处理聊天相关错误
        
        Args:
            error: 异常对象
            operation: 操作描述
            
        Returns:
            HTTPException: 格式化后的HTTP异常
        """
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{operation}时出错: {str(error)}"
        )


class ChatService(BaseChatService):
    """用于处理聊天交互的服务"""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def process_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        处理用户消息并生成AI响应
        """
        try:
            # 保存用户消息
            user_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                content=message,
                role=MessageRole.USER
            )

            # 获取对话历史
            history = await self.conversation_service.get_conversation_messages(
                conversation_id=conversation_id,
                limit=20
            )

            # 将历史记录转换为LLM期望的格式
            conversation_history = []
            for msg in history[:-1]:  # 排除当前消息
                conversation_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

            # 如需要，搜索相关文档
            relevant_context = ""
            if context and context.get("search_documents", True):
                search_results = await self.document_service.search_documents(
                    query=message,
                    user_id=user_id,
                    limit=3
                )
                if search_results:
                    relevant_context = "\n".join([
                        f"文档: {doc['filename']}\n内容: {doc['content'][:500]}..."
                        for doc in search_results
                    ])

            # 生成AI响应
            ai_response = await self.llm_service.generate_response(
                message=message,
                conversation_history=conversation_history,
                context=relevant_context
            )

            # 保存AI消息
            ai_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                content=ai_response,
                role=MessageRole.ASSISTANT,
                model_name=self.llm_service.chat_model.model_name,
                context={"relevant_documents": len(search_results) if 'search_results' in locals() else 0}
            )

            return ChatResponse(
                message_id=str(ai_message.id),
                conversation_id=str(conversation_id),
                content=ai_response,
                role=MessageRole.ASSISTANT,
                timestamp=ai_message.created_at,
                metadata={
                    "model_name": self.llm_service.chat_model.model_name,
                    "has_context": bool(relevant_context)
                }
            )

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            raise

    async def stream_message(
        self,
        user_id: UUID,
        conversation_id: UUID,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        处理消息并流式传输AI响应
        """
        try:
            # 保存用户消息
            user_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                content=message,
                role=MessageRole.USER
            )

            # 获取对话历史
            history = await self.conversation_service.get_conversation_messages(
                conversation_id=conversation_id,
                limit=20
            )

            # 将历史记录转换为LLM期望的格式
            conversation_history = []
            for msg in history[:-1]:  # 排除当前消息
                conversation_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

            # 如需要，搜索相关文档
            relevant_context = ""
            if context and context.get("search_documents", True):
                search_results = await self.document_service.search_documents(
                    query=message,
                    user_id=user_id,
                    limit=3
                )
                if search_results:
                    relevant_context = "\n".join([
                        f"文档: {doc['filename']}\n内容: {doc['content'][:500]}..."
                        for doc in search_results
                    ])

            # 流式传输AI响应
            full_response = ""
            async for token in self.llm_service.stream_response(
                message=message,
                conversation_history=conversation_history,
                context=relevant_context
            ):
                full_response += token
                yield json.dumps({"token": token, "type": "token"})

            # 保存完整的AI消息
            ai_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                content=full_response,
                role=MessageRole.ASSISTANT,
                model_name=self.llm_service.chat_model.model_name,
                context={"relevant_documents": len(search_results) if 'search_results' in locals() else 0}
            )

            # 发送完成信号
            yield json.dumps({
                "type": "complete",
                "message_id": str(ai_message.id),
                "timestamp": ai_message.created_at.isoformat()
            })

        except Exception as e:
            logger.error(f"流式传输消息时出错: {e}")
            yield json.dumps({"type": "error", "error": str(e)})

    async def get_suggestions(self, query: str, user_id: UUID) -> List[str]:
        """
        获取AI驱动的用户查询建议
        """
        try:
            # 获取用户的最近对话以获取上下文
            recent_conversations = await self.conversation_service.get_user_conversations(
                user_id=user_id,
                limit=5
            )

            context = ""
            if recent_conversations:
                context = "最近的对话主题: " + ", ".join([
                    conv.title for conv in recent_conversations
                ])

            suggestions = await self.llm_service.generate_suggestions(query, context)
            return suggestions

        except Exception as e:
            logger.error(f"获取建议时出错: {e}")
            return []

    async def submit_feedback(
        self,
        message_id: str,
        user_id: UUID,
        rating: int,
        feedback: str = ""
    ) -> None:
        """
        提交聊天消息的反馈
        """
        try:
            await self.conversation_service.update_message_feedback(
                message_id=message_id,
                rating=rating,
                feedback=feedback
            )

            logger.info(f"用户{user_id}为消息{message_id}提交了反馈")

        except Exception as e:
            logger.error(f"提交反馈时出错: {e}")
            raise