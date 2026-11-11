"""
负责普通聊天接口，挂载前缀是 /chat。
    POST /chat/send
    POST /chat/stream
    GET  /chat/suggestions
    POST /chat/feedback

    通用聊天，不负责复杂 HR Agent 工具编排。
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.chat import ChatResponse, ChatRequest
from app.schemas.user import User as UserSchema
from app.schemas.conversation import ConversationCreate
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.api.deps import get_current_user


router = APIRouter()


@router.post("/send", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    向HR Agent发送消息并获取响应
        send_message 接收 ChatRequest，调用 ChatService.process_message，返回一次性 AI 回复。
    """
    chat_service = ChatService(db)
    
    try:
        conversation = await chat_service.get_or_create_conversation(
            chat_request, current_user
        )
        
        response = await chat_service.process_message(
            user_id=current_user.id,
            conversation_id=conversation.id,
            message=chat_request.message,
            context=chat_request.context
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise chat_service.handle_chat_error(e, "处理消息")


@router.post("/stream")
async def stream_message(
    chat_request: ChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息并获取流式响应
        stream_message 调用 ChatService.stream_message，返回 StreamingResponse，适合前端逐字显示。
    """
    chat_service = ChatService(db)
    
    try:
        conversation = await chat_service.get_or_create_conversation(
            chat_request, current_user
        )
        
        async def generate_response():
            async for chunk in chat_service.stream_message(
                user_id=current_user.id,
                conversation_id=conversation.id,
                message=chat_request.message,
                context=chat_request.context
            ):
                yield f"data: {chunk}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise chat_service.handle_chat_error(e, "处理流式消息")


@router.get("/suggestions")
async def get_suggestions(
    query: str = "",
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    获取AI驱动的用户查询建议
        get_suggestions 根据用户输入生成建议问题。
    """
    chat_service = ChatService(db)
    
    try:
        suggestions = await chat_service.get_suggestions(
            query=query, user_id=current_user.id
        )
        return suggestions
        
    except Exception as e:
        raise chat_service.handle_chat_error(e, "获取建议")


@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    rating: int,
    feedback: str = "",
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    提交聊天消息的反馈
        submit_feedback 给某条聊天消息提交评分和反馈。
    """

    chat_service = ChatService(db)
    
    try:
        await chat_service.submit_feedback(
            message_id=message_id,
            user_id=current_user.id,
            rating=rating,
            feedback=feedback
        )
        
        return {"message": "反馈提交成功"}
        
    except Exception as e:
        raise chat_service.handle_chat_error(e, "提交反馈")
