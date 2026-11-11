"""
   用户和角色相关 API 数据结构
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """ 用户基础字段 """
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    position: Optional[str] = Field(None, max_length=100, description="职位")
    employee_id: Optional[str] = Field(None, max_length=50, description="员工编号")
    role: Optional[UserRole] = Field(None, description="用户角色")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserCreate(UserBase):
    """ 创建用户 """
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserUpdate(BaseModel):
    """ 用于部分更新 """
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    position: Optional[str] = Field(None, max_length=100, description="职位")
    employee_id: Optional[str] = Field(None, max_length=50, description="员工编号")
    role: Optional[UserRole] = Field(None, description="用户角色")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="密码")
    avatar_url: Optional[str] = Field(None, description="头像地址")
    is_superuser: Optional[bool] = Field(None, description="是否为超级管理员")
    is_verified: Optional[bool] = Field(None, description="是否已验证")
    is_active: Optional[bool] = Field(None, description="是否启用")


class UserInDB(UserBase):
    """ 数据库字段 """
    id: UUID = Field(..., description="唯一标识ID")
    is_active: bool = Field(..., description="是否启用")
    is_superuser: bool = Field(..., description="是否为超级管理员")
    is_verified: bool = Field(..., description="是否已验证")
    avatar_url: Optional[str] = Field(..., description="头像地址")
    last_login: Optional[datetime] = Field(..., description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class User(UserInDB):
    """ 公开返回用户信息，不包含密码 """
    pass


class UserLogin(BaseModel):
    """ 用户登录 """
    email: EmailStr
    password: str


class UserRegister(UserCreate):
    """用户注册"""
    pass


class Token(BaseModel):
    """ access_token认证 """
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌有效期，单位秒")


class TokenData(BaseModel):
    """ token 数据 """
    user_id: Optional[UUID] = Field(None, description="用户ID")




class RoleBase(BaseModel):
    """角色基类"""
    name: str = Field(..., description="名称")
    description: Optional[str] = Field(None, description="描述信息")


class RoleCreate(RoleBase):
    """创建角色"""
    is_builtin: Optional[bool] = Field(False, description="是否为系统内置角色")


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, description="名称")
    description: Optional[str] = Field(None, description="描述信息")


class Role(BaseModel):
    """角色字段"""
    id: UUID = Field(..., description="唯一标识ID")
    name: str = Field(..., description="名称")
    description: Optional[str] = Field(..., description="描述信息")
    is_builtin: bool = Field(..., description="是否为系统内置角色")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AssignRolesRequest(BaseModel):
    """分配角色请求"""
    role_ids: List[UUID] = Field(..., description="角色ID列表")


class UserWithRoles(BaseModel):
    """具有角色的用户"""
    id: UUID = Field(..., description="唯一标识ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(..., description="用户全名")
    phone: Optional[str] = Field(..., description="手机号")
    department: Optional[str] = Field(..., description="所属部门")
    position: Optional[str] = Field(..., description="职位")
    employee_id: Optional[str] = Field(..., description="员工编号")
    role: Optional[UserRole] = Field(..., description="用户角色")
    is_superuser: bool = Field(..., description="是否为超级管理员")
    is_verified: bool = Field(..., description="是否已验证")
    is_active: bool = Field(..., description="是否启用")
    bio: Optional[str] = Field(..., description="个人简介")
    avatar_url: Optional[str] = Field(..., description="头像地址")
    last_login: Optional[datetime] = Field(..., description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    roles: List[Role] = Field(..., description="角色列表")


