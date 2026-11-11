"""
    用于身份验证和用户管理的用户模型：定义用户、角色和用户角色关联表
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    HR_MANAGER = "hr_manager"
    HR_SPECIALIST = "hr_specialist"
    EMPLOYEE = "employee"


class User(BaseModel):
    """用户模型：对应 users 表，存储用户账号信息"""

    __tablename__ = "users"

    # 基本信息
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="邮箱地址")
    full_name = Column(String(255), nullable=True, comment="用户全名")
    hashed_password = Column(String(255), nullable=False, comment="加密后的密码")

    # 个人资料信息
    phone = Column(String(20), nullable=True, comment="手机号")
    department = Column(String(100), nullable=True, comment="所属部门")
    position = Column(String(100), nullable=True, comment="职位")
    employee_id = Column(String(50), unique=True, nullable=True, comment="员工编号")

    # 角色和权限
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False, comment="用户角色")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否为超级管理员")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否已验证")

    # 附加信息
    bio = Column(Text, nullable=True, comment="个人简介")
    avatar_url = Column(String(500), nullable=True, comment="头像地址")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")

    # 关系
    #    表示一个用户可以有多个对话、多个上传文档，也可以绑定多个角色。
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="uploaded_by", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_role", back_populates="users")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Role(BaseModel):
    """Role 对应 role 表，表示系统角色"""

    __tablename__ = "role"

    name = Column(String(50), unique=True, nullable=False, index=True, comment="角色名称")
    description = Column(String(255), nullable=True, comment="角色描述")
    is_builtin = Column(Boolean, default=False, nullable=False, comment="是否为系统内置角色")

    users = relationship("User", secondary="user_role", back_populates="roles")


class UserRoleAssociation(BaseModel):
    """用户User 和 角色Role的多对多中间表"""
    __tablename__ = "user_role"

    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    role_id = Column(ForeignKey("role.id", ondelete="CASCADE"), nullable=False, index=True, comment="角色ID")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role_user_id_role_id"),
    )
    