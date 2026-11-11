"""
   认证相关请求/响应schema
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserLogin(BaseModel):
    """ 用户登录请求 """
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="用户全名")
    phone: Optional[str] = Field(None, description="手机号")
    department: Optional[str] = Field(None, description="所属部门")
    position: Optional[str] = Field(None, description="职位")
    employee_id: Optional[str] = Field(None, description="员工编号")
    bio: Optional[str] = Field(None, description="个人简介")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


class UserCreate(BaseModel):
    """ 创建用户 """
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="用户全名")
    phone: Optional[str] = Field(None, description="手机号")
    department: Optional[str] = Field(None, description="所属部门")
    position: Optional[str] = Field(None, description="职位")
    employee_id: Optional[str] = Field(None, description="员工编号")
    bio: Optional[str] = Field(None, description="个人简介")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


class Token(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="令牌有效期，单位秒")


class TokenData(BaseModel):
    """解析 token 后内部使用的数据"""
    user_id: Optional[str] = Field(None, description="用户ID")
    email: Optional[str] = Field(None, description="邮箱地址")


class PasswordReset(BaseModel):
    """ 重置密码 """
    email: EmailStr = Field(..., description="邮箱地址")


class PasswordResetConfirm(BaseModel):
    """ 确认重置 """
    token: str = Field(..., description="验证令牌")
    new_password: str = Field(..., description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v


class ChangePassword(BaseModel):
    """ 修改密码 """
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度至少 6 位")
        return v