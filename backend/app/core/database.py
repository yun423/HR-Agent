"""
数据库配置和连接管理
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

'''
    create_engine          创建同步数据库引擎
    text                   包装原生 SQL
    create_async_engine    创建异步数据库引擎
    AsyncSession           异步数据库会话
    async_sessionmaker     异步 session 工厂
    declarative_base       ORM 模型基类生成器
    sessionmaker           同步 session 工厂
'''

logger = logging.getLogger(__name__)

# 创建SQLAlchemy引擎
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),  # DATABASE_URL
    pool_size=settings.DATABASE_POOL_SIZE,  # 控制连接池大小
    max_overflow=settings.DATABASE_MAX_OVERFLOW,   # 控制连接池大小
    echo=settings.DEBUG,  # 调试模式下会输出SQL日志
)

# 创建异步数据库会话工厂
#
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,  # 后续每个请求需要访问数据库时，会从这个工厂创建一个 AsyncSession。
    expire_on_commit=False,  # 表示提交事务后对象字段不会自动过期，方便接口继续读取返回数据
    autocommit=False,  # 是否自动提交
    autoflush=False,  # 是否自动刷新
)

# 创建模型的基类
#    项目里的 ORM 模型要继承这个Base，这样 Base.metadata.create_all 才能知道要创建哪些表。
Base = declarative_base()


def get_async_engine():
    """
    获取异步数据库引擎
    """
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖项：是FastAPI依赖函数

        1. 创建一个异步数据库 session。
        2. yield session 把 session 交给接口函数使用。
        3. 如果接口执行出错，就 rollback() 回滚事务。
        4. 最后无论成功失败，都 close() 关闭 session。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库并创建表：用于应用启动时初始化数据库

        1. 如果数据库URL是PostgreSQL，就尝试执行：CREATE EXTENSION IF NOT EXISTS vector【这是启用pgvector扩展，用于向量检索、知识库/RAG等功能】
        2. 执行Base.metadata.create_all 创建ORM模型对应的数据表。如果初始化失败，会记录错误日志并重新抛出异常，让启动流程知道数据库不可用。

    """
    try:
        async with engine.begin() as conn:

            # 如果使用PostgreSQL则启用pgvector扩展
            if "postgresql" in settings.DATABASE_URL:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    logger.info("pgvector扩展已启用")
                except Exception as e:
                    logger.warning(f"无法启用pgvector扩展: {e}")

            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)

        logger.info("数据库初始化成功")

    except Exception as e:
        logger.error(f"数据库初始化错误: {e}")
        raise


async def close_db() -> None:
    """
    关闭数据库连接： 用于应用关闭时释放数据库连接池。
    """
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库时出错: {e}")


async def check_db_connection() -> bool:
    """
    检查数据库连接：
        用 SELECT 1 测试数据库是否能正常连接，成功返回 True，失败记录日志并返回 False
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True

    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False