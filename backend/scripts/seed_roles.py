import asyncio
from sqlalchemy import select
import sys
import os
from pathlib import Path

'''
    seed_roles.py 是一个数据库初始化脚本，用来给系统预置基础角色，并创建一个测试管理员账号。
    主要做三件事：
        1. 初始化数据库表。
        2. 确保数据库里存在两个内置角色：普通用户、超级管理员。
        3. 确保存在一个测试管理员用户 testuser，并把它绑定到 超级管理员 角色。

'''

# 将后端目录添加到Python路径
#       把 backend 目录加入 Python 模块搜索路径。
#       这样这个脚本即使从 backend/scripts 目录运行，也能正常导入 app.core.database、app.models.user 这些项目模块。
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import AsyncSessionLocal, init_db
from app.models.user import Role, User, UserRoleAssociation, UserRole
from app.core.security import get_password_hash


# 定义异步主逻辑
async def seed_roles_and_admin():
    await init_db()  # 确保数据库和表结构已经初始化。

    # 创建一个异步数据库会话，后面的查询、插入、提交都通过这个 db 完成。
    async with AsyncSessionLocal() as db:
        names = ["普通用户", "超级管理员"]

        # 检查角色表中是否已有 普通用户 和 超级管理员。
        # 如果没有，就插入对应的 Role 记录，最后 commit() 保存。
        existing = await db.execute(select(Role).where(Role.name.in_(names)))
        exist_names = {r.name for r in existing.scalars().all()}

        if "普通用户" not in exist_names:
            db.add(Role(name="普通用户", description="默认普通用户角色", is_builtin=True))
        if "超级管理员" not in exist_names:
            db.add(Role(name="超级管理员", description="系统超级管理员角色", is_builtin=True))
        await db.commit()

        # 查找是否已有激活状态的 testuser。
        # 如果没有，就创建一个测试用户：
        res = await db.execute(select(User).where(User.username == "testuser", User.is_active == True))
        user = res.scalar_one_or_none()
        if not user:
            # 创建测试用户
            user = User(
                username="testuser",
                email="testuser@example.com",
                full_name="Test User",
                hashed_password=get_password_hash("test123"),  # 密码不是明文存入数据库，而是通过 get_password_hash("test123") 加密后保存。
                role=UserRole.ADMIN,
                is_superuser=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # 获取 超级管理员 角色，并检查 testuser 和该角色之间是否已经有关联。
        # 如果没有，就往 UserRoleAssociation 表里插入一条用户-角色绑定记录。
        res = await db.execute(select(Role).where(Role.name == "超级管理员"))
        role = res.scalar_one()
        link_exists = await db.execute(
            select(UserRoleAssociation).where(
                UserRoleAssociation.user_id == user.id,
                UserRoleAssociation.role_id == role.id,
            )
        )
        if not link_exists.scalar_one_or_none():
            db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))
            await db.commit()


def main():
    asyncio.run(seed_roles_and_admin())


if __name__ == "__main__":
    main()