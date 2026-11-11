"""
API依赖项 - 认证和授权
    作用是：集中定义 API 路由里常用的依赖项，尤其是“当前用户是谁、有没有权限、数据库会话怎么拿”。
            一般不直接处理业务，而是给 endpoint复用

"""
"""
解释：
    async def route_by_intent(
        payload: Dict[str, Any],
        current_user: UserSchema = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    )

    上面代码意思是：
        在真正执行 route_by_intent 之前，FastAPI 会先自动执行 get_current_user 和 get_db，把它们的返回值注入到参数里。

    其中：
    Depends(...) 是 FastAPI 的依赖注入机制。你可以把它理解成：
        async def route_by_intent(
            payload,
            current_user = get_current_user(),
            db = get_db()
        ):

    但实际更强大，因为 FastAPI 会自动处理：
        1. 从请求里取 Authorization token
        2. 调用 get_current_user 校验 token
        3. 查数据库拿到当前用户
        4. 如果用户无效，直接返回 401，不进入路由函数
        5. 调用 get_db 创建数据库 session
        6. 把 current_user 和 db 传进 route_by_intent
        7. 请求结束后自动关闭 db session

"""
from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, Role, UserRoleAssociation
from app.schemas.user import User as UserSchema
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    获取当前认证用户
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("🔍 调用get_current_user")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.info(f" 正在解码令牌: {token[:20]}...")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        logger.info(f" 提取的用户ID: {user_id}")
        if user_id is None:
            logger.error(" 令牌载荷中没有user_id")
            raise credentials_exception
    except JWTError as e:
        logger.error(f" JWT decode error: {e}")
        raise credentials_exception

    try:
        from uuid import UUID
        user_service = UserService(db)
        logger.info(f" 正在查找用户ID: {user_id}")
        user_uuid = UUID(user_id)
        user = await user_service.get_user(user_uuid)

        if user is None:
            logger.error(f" 未找到用户ID: {user_id}")
            raise credentials_exception

        logger.info(f" 找到用户: {user.username}, 活跃状态: {user.is_active}")

        if not user.is_active:
            logger.error(f" 用户 {user.username} 处于非活跃状态")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        logger.info(f" 返回用户: {user.username}")
        return user
    except Exception as e:
        logger.error(f" Error in get_current_user: {e}")
        raise



async def get_current_hr_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前HR用户（HR经理或HR专员）
    """
    from app.models.user import UserRole
    
    if current_user.role not in [UserRole.HR_MANAGER, UserRole.HR_SPECIALIST] and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR permissions required"
        )
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前超级管理员用户
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser permissions required"
        )
    return current_user


async def get_current_admin_by_role(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    query = (
        select(Role)
        .join(UserRoleAssociation, Role.id == UserRoleAssociation.role_id)
        .where(UserRoleAssociation.user_id == current_user.id, Role.is_active == True)
    )
    result = await db.execute(query)
    roles = {r.name for r in result.scalars().all()}
    if "超级管理员" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员角色"
        )
    return current_user


def require_any_role_names(required: List[str]):
    async def dependency(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        query = (
            select(Role)
            .join(UserRoleAssociation, Role.id == UserRoleAssociation.role_id)
            .where(UserRoleAssociation.user_id == current_user.id, Role.is_active == True)
        )
        result = await db.execute(query)
        roles = {r.name for r in result.scalars().all()}
        if not any(name in roles for name in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="角色权限不足"
            )
        return current_user
    return dependency