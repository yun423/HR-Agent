"""
 会话和消息管理服务。
    负责创建、查询、更新、删除会话，添加/查询/更新/删除消息，更新消息反馈，以及搜索会话。
    BaseConversationService 做权限检查和错误封装，
    ConversationService 做实际 CRUD，并维护会话消息数量、状态等信息。
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, func, case
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message, MessageRole, ConversationStatus
from app.schemas.conversation import ConversationCreate, ConversationUpdate, MessageCreate, MessageUpdate
from app.schemas.user import User as UserSchema

logger = logging.getLogger(__name__)


class BaseConversationService:
    """对话服务基类，包含通用辅助方法"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversation_with_permission_check(
        self,
        conversation_id: str,
        current_user: UserSchema
    ) -> Any:
        """
        获取对话并进行权限检查
        
        Args:
            conversation_id: 对话ID
            current_user: 当前用户
            
        Returns:
            对话对象
            
        Raises:
            HTTPException: 当对话未找到或权限不足时
        """
        conversation = await self.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话未找到"
            )
        
        # 检查用户所有权
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        return conversation

    def handle_conversation_error(self, error: Exception, operation: str) -> HTTPException:
        """
        统一处理对话相关错误
        
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


class ConversationService(BaseConversationService):
    """用于管理对话和消息的服务"""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create_conversation(
        self,
        user_id: UUID,
        conversation_data: ConversationCreate
    ) -> Conversation:
        """创建新的对话"""
        try:
            conversation = Conversation(
                user_id=user_id,
                title=conversation_data.title,
                description=conversation_data.description,
                status=ConversationStatus.ACTIVE,
                meta_data=conversation_data.meta_data or {}
            )

            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)

            logger.info(f"为用户{user_id}创建了对话{conversation.id}")
            return conversation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建对话时出错: {e}")
            raise

    async def get_conversation(
        self,
        conversation_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Conversation]:
        """通过ID获取对话"""
        try:
            query = select(Conversation).where(Conversation.id == conversation_id)

            if user_id:
                query = query.where(Conversation.user_id == user_id)

            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取对话{conversation_id}时出错: {e}")
            raise

    async def get_user_conversations(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ConversationStatus] = None
    ) -> List[Conversation]:
        """获取用户的对话"""
        try:
            query = select(Conversation).where(Conversation.user_id == user_id)

            if status:
                query = query.where(Conversation.status == status)

            query = query.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取用户{user_id}的对话时出错: {e}")
            raise

    async def update_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        conversation_data: ConversationUpdate
    ) -> Optional[Conversation]:
        """更新对话"""
        try:
            # 检查对话是否存在且属于用户
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return None

            update_data = conversation_data.dict(exclude_unset=True)
            if update_data:
                query = (
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(**update_data)
                )
                await self.db.execute(query)
                await self.db.commit()
                await self.db.refresh(conversation)

            logger.info(f"更新了对话{conversation_id}")
            return conversation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新对话{conversation_id}时出错: {e}")
            raise

    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID
    ) -> bool:
        """删除对话及其消息"""
        try:
            # 检查对话是否存在且属于用户
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False

            # 先删除所有消息
            await self.db.execute(
                delete(Message).where(Message.conversation_id == conversation_id)
            )

            # 删除对话
            await self.db.execute(
                delete(Conversation).where(Conversation.id == conversation_id)
            )

            await self.db.commit()
            logger.info(f"删除了对话{conversation_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除对话{conversation_id}时出错: {e}")
            raise

    async def add_message(
        self,
        conversation_id: UUID,
        content: str,
        role: MessageRole,
        model_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        parent_id: Optional[UUID] = None
    ) -> Message:
        """向对话添加消息"""
        try:
            message = Message(
                conversation_id=conversation_id,
                content=content,
                role=role,
                model_name=model_name,
                context=context or {},
                parent_message_id=parent_id
            )

            self.db.add(message)
            print('消息保存成功')
            # 更新对话消息计数和最后活动时间
            await self.db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(
                    total_messages=Conversation.total_messages + 1,
                    updated_at=func.now()
                )
            )

            await self.db.commit()
            await self.db.refresh(message)
            print('update conversation message number success')
            logger.info(f"向对话{conversation_id}添加了消息")
            return message

        except Exception as e:
            # await self.db.rollback()
            logger.error(f"向对话{conversation_id}添加消息时出错: {e}")
            raise

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """获取对话的消息"""
        try:
            query = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
                .offset(skip)
                .limit(limit)
            )

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取对话{conversation_id}的消息时出错: {e}")
            raise

    async def get_message(self, message_id: UUID) -> Optional[Message]:
        """通过ID获取消息"""
        try:
            query = select(Message).where(Message.id == message_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取消息{message_id}时出错: {e}")
            raise

    async def update_message(
        self,
        conversation_id: UUID,
        message_id: UUID,
        message_update: MessageUpdate
    ) -> Optional[Message]:
        """更新对话中的单条消息"""
        try:
            message = await self.get_message(message_id)
            if not message or str(message.conversation_id) != str(conversation_id):
                return None

            update_data = message_update.model_dump(exclude_unset=True)
            if "user_feedback" in update_data:
                update_data["feedback"] = update_data.pop("user_feedback")
            if update_data:
                await self.db.execute(
                    update(Message)
                    .where(
                        Message.id == message_id,
                        Message.conversation_id == conversation_id
                    )
                    .values(**update_data, updated_at=func.now())
                )
                await self.db.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(updated_at=func.now())
                )
                await self.db.commit()
                await self.db.refresh(message)

            logger.info(f"更新了对话{conversation_id}中的消息{message_id}")
            return message

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新消息{message_id}时出错: {e}")
            raise

    async def delete_message(self, conversation_id: UUID, message_id: UUID) -> bool:
        """删除对话中的单条消息"""
        try:
            message = await self.get_message(message_id)
            if not message or str(message.conversation_id) != str(conversation_id):
                return False

            await self.db.execute(
                delete(Message).where(
                    Message.id == message_id,
                    Message.conversation_id == conversation_id
                )
            )
            await self.db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(
                    total_messages=case(
                        (Conversation.total_messages > 0, Conversation.total_messages - 1),
                        else_=0
                    ),
                    updated_at=func.now()
                )
            )
            await self.db.commit()
            logger.info(f"删除了对话{conversation_id}中的消息{message_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除消息{message_id}时出错: {e}")
            raise

    async def update_message_feedback(
        self,
        message_id: str,
        rating: int,
        feedback: str = ""
    ) -> bool:
        """更新消息反馈"""
        try:
            message_uuid = UUID(message_id)
            query = (
                update(Message)
                .where(Message.id == message_uuid)
                .values(
                    user_feedback={
                        "rating": rating,
                        "feedback": feedback
                    }
                )
            )

            result = await self.db.execute(query)
            await self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新消息反馈{message_id}时出错: {e}")
            raise

    async def search_conversations(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10
    ) -> List[Conversation]:
        """按标题或内容搜索对话"""
        try:
            # 简单文本搜索 - 在生产环境中，您可能希望使用全文搜索
            search_query = (
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.title.ilike(f"%{query}%")
                )
                .order_by(desc(Conversation.updated_at))
                .limit(limit)
            )

            result = await self.db.execute(search_query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"搜索用户{user_id}的对话时出错: {e}")
            raise
