"""
    负责用户管理和角色管理：
        这个文件是“用户与权限管理”的 API 层。
        普通用户接口用于查看、更新自己的信息；
        管理员接口通过 get_current_admin_by_role 做权限控制。
"""
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import User as UserSchema, UserUpdate, UserCreate, Role as RoleSchema, RoleCreate, AssignRolesRequest, UserWithRoles
from app.services.user_service import UserService, RoleService
from app.api.deps import get_current_user, get_current_admin_by_role
from app.models.user import UserRole

router = APIRouter()


@router.get("/", response_model=List[UserWithRoles])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取所有用户（仅管理员）
            get_users 支持分页和搜索，搜索时走UserService.search_users，否则走 get_users_with_roles。
    """
    user_service = UserService(db)

    # 如果有搜索关键字，使用搜索功能
    if search:
        try:
            search_results = await user_service.search_users(search, current_user, limit)
            # 转换搜索结果为UserWithRoles格式
            result = []
            for user in search_results:
                # 获取用户的角色信息
                role_service = RoleService(db)
                user_roles = await role_service.list_user_roles(user.id)

                # 构造返回数据
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "department": user.department,
                    "position": user.position,
                    "employee_id": user.employee_id,
                    "role": user.role,
                    "is_superuser": user.is_superuser,
                    "is_verified": user.is_verified,
                    "is_active": user.is_active,
                    "bio": user.bio,
                    "avatar_url": user.avatar_url,
                    "last_login": user.last_login,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                    "roles": [
                        {
                            "id": r.id,
                            "name": r.name,
                            "description": r.description,
                            "is_builtin": r.is_builtin,
                            "created_at": r.created_at,
                            "updated_at": r.updated_at,
                        }
                        for r in user_roles
                    ],
                }
                result.append(user_data)
            return result
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
    else:
        # 否则返回所有用户
        result = await user_service.get_users_with_roles(skip=skip, limit=limit)
        return result


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    根据ID获取用户
    """
    user_service = UserService(db)
    user = await user_service.get_user(UUID(user_id), include_inactive=True)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )

    # 检查权限
    if not user_service.can_view_user(current_user, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    更新用户信息
    """
    user_service = UserService(db)
    user = await user_service.get_user(UUID(user_id), include_inactive=True)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )

    # 检查权限
    if not user_service.can_update_user(current_user, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    updated_user = await user_service.update_user(user.id, user_update, current_user)
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    删除用户（仅管理员）
    """
    user_service = UserService(db)
    user = await user_service.get_user(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )

    # 检查权限
    if not user_service.can_delete_user(current_user, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    result = await user_service.delete_user(user.id, current_user)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="删除用户失败"
        )

    return {"message": "用户删除成功"}




@router.post("/admin/users", response_model=UserSchema)
async def admin_create_user(
    user_create: UserCreate,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员创建用户
    """
    user_service = UserService(db)
    user = await user_service.create_user(user_create)
    return user


@router.get("/admin/users/{user_id}/roles", response_model=List[RoleSchema])
async def admin_list_user_roles(
    user_id: str,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员列出用户角色
    """
    role_service = RoleService(db)
    roles = await role_service.list_user_roles(UUID(user_id))
    return roles


@router.put("/admin/users/{user_id}/roles", response_model=List[RoleSchema])
async def admin_assign_user_roles(
    user_id: str,
    payload: AssignRolesRequest,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员分配用户角色
    """
    role_service = RoleService(db)
    roles = await role_service.assign_roles_to_user(UUID(user_id), payload.role_ids)
    return roles


# Admin-only role management

@router.get("/admin/roles", response_model=List[RoleSchema])
async def admin_list_roles(
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员列出所有角色
    """
    role_service = RoleService(db)
    return await role_service.list_roles()


@router.post("/admin/roles", response_model=RoleSchema)
async def admin_create_role(
    role_create: RoleCreate,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员创建角色
    """
    role_service = RoleService(db)
    return await role_service.create_role(role_create.name, role_create.description, role_create.is_builtin or False)


@router.delete("/admin/roles/{role_id}")
async def admin_delete_role(
    role_id: str,
    current_user: UserSchema = Depends(get_current_admin_by_role),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    管理员删除角色
    """
    role_service = RoleService(db)
    ok = await role_service.delete_role(UUID(role_id))
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色未找到")
    return {"message": "角色删除成功"}

@router.get("/me/roles", response_model=List[RoleSchema])
async def get_my_roles(
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    获取当前用户的角色
    """
    role_service = RoleService(db)
    return await role_service.list_user_roles(current_user.id)
