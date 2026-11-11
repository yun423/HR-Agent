""""""
"""
HR Agent后端数据库管理脚本

db_manager.py 是一个命令行数据库管理脚本，用来在开发或部署时管理后端数据库和 Alembic迁移。

此脚本提供数据库管理工具：
- 初始化数据库： db_manager.py init
- 创建迁移： db_manager.py migrate "add user table"
- 应用迁移： db_manager.py upgrade
- 回滚迁移:  db_manager.py downgrade
- 重置数据库： db_manager.py reset
- 查看迁移历史： db_manager.py history
- 查看当前版本： db_manager.py current


支持这些操作：
python backend/scripts/db_manager.py init
python backend/scripts/db_manager.py migrate "add user table"
python backend/scripts/db_manager.py upgrade
python backend/scripts/db_manager.py downgrade
python backend/scripts/db_manager.py reset
python backend/scripts/db_manager.py history
python backend/scripts/db_manager.py current
"""

import asyncio
import sys
from pathlib import Path

# 将后端目录添加到Python路径
# 把 backend 目录加入 sys.path：
#       因为这个脚本在 backend/scripts 下，直接运行时 Python 默认不一定能找到 app 包，
#       所以这里手动把后端根目录加入模块搜索路径。
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 导入 Alembic、SQLAlchemy、项目配置和数据库模型相关对象。
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

from app.core.config import settings

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 核心管理类
class DatabaseManager:
    """数据库管理工具"""

    # 初始化 Alembic 配置。
    #   读取 backend/alembic.ini，然后把配置里的 sqlalchemy.url 替换成当前项目配置里的 settings.DATABASE_URL。
    #   这样迁移命令会连接到项目实际配置的数据库。
    def __init__(self):
        self.alembic_cfg = Config(str(backend_dir / "alembic.ini"))
        self.alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    async def create_database(self):
        """
            如果数据库不存在则创建数据库

            流程是：
                1. 从配置中拿到数据库名 settings.DATABASE_NAME。
                2. 把连接 URL 中的目标数据库替换成 /postgres。
                3. 连接 PostgreSQL 默认库 postgres。
                4. 查询 pg_database 判断目标数据库是否存在。
                5. 不存在就执行 CREATE DATABASE xxx。
                6. 最后释放连接池。
            这里要先连 /postgres，是因为目标数据库如果还不存在，就不能直接连接目标库来创建它。
        """
        try:
            # 从URL中提取数据库名称
            db_name = settings.DATABASE_NAME

            # 连接到postgres数据库以创建我们的数据库
            postgres_url = settings.DATABASE_URL.replace(f"/{db_name}", "/postgres")
            engine = create_async_engine(postgres_url)

            async with engine.connect() as conn:
                # 检查数据库是否存在
                #  :db_name 是参数占位符
                result = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )

                if not result.fetchone():
                    # 创建数据库
                    await conn.execute(text("COMMIT"))  # 结束事务
                    await conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.info(f"数据库 '{db_name}' 创建成功")
                else:
                    logger.info(f"数据库 '{db_name}' 已存在")

            # 释放连接池
            await engine.dispose()

        except Exception as e:
            logger.error(f"创建数据库时出错: {e}")
            raise

    async def drop_database(self):
        """
            删除数据库
                1. 连接默认库 postgres。
                2. 执行 pg_terminate_backend 终止目标数据库上的其他连接。
                3. 执行 DROP DATABASE IF EXISTS xxx 删除数据库。

        """
        try:
            db_name = settings.DATABASE_NAME
            postgres_url = settings.DATABASE_URL.replace(f"/{db_name}", "/postgres")
            engine = create_async_engine(postgres_url)

            async with engine.connect() as conn:
                # 终止现有连接
                await conn.execute(text("COMMIT"))
                await conn.execute(
                    text("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :db_name AND pid <> pg_backend_pid()
                    """),
                    {"db_name": db_name}
                )

                # 删除数据库
                await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
                logger.info(f"数据库 '{db_name}' 删除成功")

            await engine.dispose()

        except Exception as e:
            logger.error(f"删除数据库时出错: {e}")
            raise

    def create_migration(self, message: str):
        """
            创建新的迁移
                1. 会根据当前 ORM 模型和数据库状态自动生成 Alembic 迁移文件。
        """
        try:
            command.revision(self.alembic_cfg, autogenerate=True, message=message)
            logger.info(f"迁移已创建: {message}")
        except Exception as e:
            logger.error(f"创建迁移时出错: {e}")
            raise

    def apply_migrations(self):
        """
            应用所有待处理的迁移
                1. 把数据库升级到最新迁移版本
        """
        try:
            command.upgrade(self.alembic_cfg, "head")
            logger.info("迁移应用成功")
        except Exception as e:
            logger.error(f"应用迁移时出错: {e}")
            raise

    def downgrade_migration(self, revision: str = "-1"):
        """
            降级到特定版本
                1. 用来回滚迁移。默认参数是 -1，表示回退一个版本；也可以传入具体 revision。
        """
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"已降级到版本: {revision}")
        except Exception as e:
            logger.error(f"降级迁移时出错: {e}")
            raise

    def show_migration_history(self):
        """
            显示迁移历史
        """
        try:
            command.history(self.alembic_cfg)
        except Exception as e:
            logger.error(f"显示迁移历史时出错: {e}")
            raise

    def show_current_revision(self):
        """
            显示当前数据库版本
        """
        try:
            command.current(self.alembic_cfg)
        except Exception as e:
            logger.error(f"显示当前版本时出错: {e}")
            raise

    async def reset_database(self):
        """
            重置数据库（删除、创建、迁移）
                1. 删除数据库。
                2. 重新创建数据库。
                3. 应用所有迁移。
            这是完全重置数据库，数据会丢失。
        """
        logger.info("正在重置数据库...")
        await self.drop_database()
        await self.create_database()
        self.apply_migrations()
        logger.info("数据库重置完成")

    async def init_database(self):
        """
            初始化数据库（创建、迁移）
                1. 创建数据库，如果不存在。
                2. 应用迁移。
            这是比较常规的初始化流程，不主动删除已有数据库。
        """
        logger.info("正在初始化数据库...")
        await self.create_database()
        self.apply_migrations()
        logger.info("数据库初始化完成")


async def main():
    """处理命令行参数的主函数"""
    if len(sys.argv) < 2:
        print("用法: python db_manager.py <命令> [参数]")
        print("命令:")
        print("  init                    - 初始化数据库")
        print("  reset                   - 重置数据库（删除并重新创建）")
        print("  migrate <消息>          - 创建新迁移")
        print("  upgrade                 - 应用迁移")
        print("  downgrade [版本]        - 降级迁移")
        print("  history                 - 显示迁移历史")
        print("  current                 - 显示当前版本")
        return

    command = sys.argv[1]
    db_manager = DatabaseManager()

    try:
        if command == "init":
            await db_manager.init_database()

        elif command == "reset":
            await db_manager.reset_database()

        elif command == "migrate":
            if len(sys.argv) < 3:
                print("错误: 需要迁移消息")
                return
            message = " ".join(sys.argv[2:])
            db_manager.create_migration(message)

        elif command == "upgrade":
            db_manager.apply_migrations()

        elif command == "downgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
            db_manager.downgrade_migration(revision)

        elif command == "history":
            db_manager.show_migration_history()

        elif command == "current":
            db_manager.show_current_revision()

        else:
            print(f"未知命令: {command}")
            return

    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())