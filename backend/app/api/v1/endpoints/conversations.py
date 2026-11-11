"""
负责会话和消息管理

    调用 ConversationService。
    会话接口负责创建、查询、更新、删除会话。
    消息接口负责列出对话消息、追加消息、更新消息、删除消息。
    所有接口都依赖 get_current_user，所以会按用户权限限制访问自己的会话。
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.conversation import (
    Conversation as ConversationSchema,
    ConversationCreate,
    MessageCreate,
    MessageUpdate,
    ConversationUpdate
)
from app.schemas.user import User as UserSchema
from app.services.conversation_service import ConversationService
from app.api.deps import get_current_user


router = APIRouter()


@router.get("/", response_model=List[ConversationSchema])
async def get_conversations(
    skip: int = 0,
    limit: int = 100,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取用户的对话列表
    """
    conversation_service = ConversationService(db)
    
    try:
        conversations = await conversation_service.get_user_conversations(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        result = []
        for conv in conversations:
            result.append({
                "id": conv.id,
                "user_id": conv.user_id,
                "title": conv.title,
                "description": conv.description,
                "status": conv.status,
                "message_count": conv.total_messages,  # Map total_messages to message_count for schema
                "meta_data": conv.meta_data,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at
            })
        
        return result
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "获取对话列表")


@router.post("/", response_model=ConversationSchema)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    创建新的对话
    """
    conversation_service = ConversationService(db)
    
    try:
        conversation = await conversation_service.create_conversation(
            user_id=current_user.id,
            conversation_data=conversation_data
        )
        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "description": conversation.description,
            "status": conversation.status,
            "message_count": conversation.total_messages,
            "meta_data": conversation.meta_data,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }

    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "创建对话")


@router.get("/{conversation_id}", response_model=ConversationSchema)
async def get_conversation(
    conversation_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    根据ID获取对话
    """
    conversation_service = ConversationService(db)
    
    try:
        conversation = await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )
        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "description": conversation.description,
            "status": conversation.status,
            "message_count": conversation.total_messages,
            "meta_data": conversation.meta_data,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "获取对话")


@router.put("/{conversation_id}", response_model=ConversationSchema)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    更新对话信息
    """
    conversation_service = ConversationService(db)

    try:
        # 权限检查
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )
        
        updated_conversation = await conversation_service.update_conversation(
            conversation_id, current_user.id, conversation_update
        )
        return updated_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "更新对话")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除对话
    """
    conversation_service = ConversationService(db)
    
    try:
        # 权限检查
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )
        
        success = await conversation_service.delete_conversation(
            conversation_id, current_user.id
        )
        if not success:
            raise HTTPException(
                status_code=400,
                detail="删除对话失败"
            )
        return {"message": "对话删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "删除对话")


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取对话中的消息列表
    """
    conversation_service = ConversationService(db)
    
    try:
        # 权限检查
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )
        
        messages = await conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit
        )
        # Convert messages to dict to avoid PydanticSerializationError
        result = []
        for message in messages:
            result.append({
                "id": message.id,
                "conversation_id": message.conversation_id,
                "content": message.content,
                "role": message.role,
                "model_name": message.model_name,
                "context": message.context,
                "meta_data": message.meta_data,
                "rating": message.rating,
                "feedback": message.feedback,
                "parent_message_id": message.parent_message_id,
                "created_at": message.created_at,
                "updated_at": message.updated_at
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "获取对话消息")


@router.post("/{conversation_id}/messages")
async def add_conversation_message(
    conversation_id: str,
    message_data: MessageCreate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    向对话追加单条消息
    """
    conversation_service = ConversationService(db)

    try:
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )

        message = await conversation_service.add_message(
            conversation_id=conversation_id,
            content=message_data.content,
            role=message_data.role,
            model_name=message_data.model_name,
            context=message_data.context,
            parent_id=message_data.parent_id
        )
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "content": message.content,
            "role": message.role,
            "model_name": message.model_name,
            "context": message.context,
            "meta_data": message.meta_data,
            "created_at": message.created_at,
            "updated_at": message.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "保存对话消息")


@router.put("/{conversation_id}/messages/{message_id}")
async def update_conversation_message(
    conversation_id: str,
    message_id: str,
    message_update: MessageUpdate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    更新对话中的单条消息
    """
    conversation_service = ConversationService(db)

    try:
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )

        message = await conversation_service.update_message(
            conversation_id=conversation_id,
            message_id=message_id,
            message_update=message_update
        )
        if not message:
            raise HTTPException(status_code=404, detail="消息未找到")
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "content": message.content,
            "role": message.role,
            "model_name": message.model_name,
            "context": message.context,
            "meta_data": message.meta_data,
            "created_at": message.created_at,
            "updated_at": message.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "更新对话消息")


@router.delete("/{conversation_id}/messages/{message_id}")
async def delete_conversation_message(
    conversation_id: str,
    message_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除对话中的单条消息
    """
    conversation_service = ConversationService(db)

    try:
        await conversation_service.get_conversation_with_permission_check(
            conversation_id, current_user
        )

        success = await conversation_service.delete_message(
            conversation_id=conversation_id,
            message_id=message_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="消息未找到")
        return {"message": "消息删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise conversation_service.handle_conversation_error(e, "删除对话消息")
