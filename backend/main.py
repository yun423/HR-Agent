"""
    HR Agent后端 - FastAPI应用程序入口点
"""
import uvicorn  # 用于直接运行FastAPI服务。
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 处理跨域请求
from contextlib import asynccontextmanager
import logging

from app.core.config import settings  # 项目配置
from app.core.database import init_db, close_db  # 启动时初始化数据库，关闭时释放连接
from app.api.v1.api import api_router  # 后端所有API路由入口
from app.core.middleware import setup_middleware   # 注册自定义中间件
from app.core.logging import setup_logging  # 初始化日志系统
from app.core.exception_handlers import setup_exception_handlers  # 注册统一异常处理器
from app.services.email_scheduler import EmailScheduler  # 邮件定时抓取/调度服务

logger = logging.getLogger(__name__)


"""
    main.py 是后端FastAPI应用的入口文件
        负责创建应用、注册路由、中间件、异常处理器，并在应用启动/关闭时初始化或释放资源
"""


"""
@asynccontextmanager 
    异步上下文管理器 则用于异步编程（async/await），它们通过实现 __aenter__ 和 __aexit__ 方法，并配合 async with 语句使用
    
    函数体内使用 yield 来分隔“进入”和“退出”逻辑：
        yield 之前：相当于 __aenter__
        yield 之后（通常在 finally 块中）：相当于 __aexit__
    
    必须配合 async with 使用。
    
    非常适合管理异步资源，如：
        异步数据库连接
        HTTP 客户端会话（如 aiohttp.ClientSession）
        异步锁（asyncio.Lock）
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
        应用程序生命周期事件
            这是FastAPI的生命周期管理函数。yield前是应用启动逻辑，yield后是应用关闭逻辑。
    """
    # 启动
    logger.info("正在启动HR Agent后端...")
    setup_logging()
    logger.info("日志配置完成")

    try:
        await init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    # 初始化并启动邮件调度器
    email_scheduler = EmailScheduler()
    await email_scheduler.start()
    app.state.email_scheduler = email_scheduler
    logger.info("邮件调度器启动成功")

    logger.info("HR Agent后端启动成功")
    yield

    # 关闭
    logger.info("正在关闭HR Agent后端...")
    try:
        # 停止邮件调度器
        if hasattr(app.state, 'email_scheduler') and app.state.email_scheduler:
            for stopper in app.state.email_scheduler.stoppers.values():
                stopper.set()
            for task in app.state.email_scheduler.tasks.values():
                task.cancel()
            logger.info("邮件调度器已停止")

        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭时出错: {e}")
    logger.info("HR Agent后端关闭完成")


def create_application() -> FastAPI:
    """
        创建并配置FastAPI应用程序 : 应用工厂函数
    """

    """
    参数：
        openapi_url: OpenAPI规范JSON的访问地址, 这个接口返回的是机器可读的API描述JSON，里面包含所有接口路径、请求参数、响应模型等信息。Swagger UI和ReDoc都依赖它来生成文档页面。
        docs_url： Swagger UI文档页面地址，这是给人看的交互式API文档页面,可以在浏览器里打开它,查看接口、填写参数、直接发送请求测试接口
        redoc_url: ReDoc文档页面地址, 是给人看的API文档页面，但风格和Swagger不同,ReDoc更偏阅读型文档，结构更清晰，适合浏览接口说明；Swagger更偏调试型，适合直接在线调用接口
        lifespan: 告诉FastAPI应用启动时先执行什么, 应用关闭时执行什么清理工作
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,  # 接口文档标题
        description="HR Agent - AI驱动的人力资源助手",  # 接口文档描述
        version=settings.VERSION,  # 版本号
        openapi_url=f"{settings.API_V1_STR}/openapi.json",  # OpenAPI规范JSON的访问地址
        docs_url=f"{settings.API_V1_STR}/docs",  # Swagger文档地址
        redoc_url=f"{settings.API_V1_STR}/redoc",  # ReDoc文档地址
        lifespan=lifespan  # 绑定前面定义的生命周期逻辑,
    )

    # 设置异常处理程序
    setup_exception_handlers(app)

    # 设置CORS
    app.add_middleware(
        CORSMiddleware,  # 添加跨域中间件
        allow_origins=settings.BACKEND_CORS_ORIGINS,  # 允许配置里的前端地址访问后端API
        allow_credentials=True,  # 允许携带凭证
        allow_methods=["*"],  # 允许所有HTTP方法
        allow_headers=["*"],  # 允许所有HTTP请求头
    )

    # 设置自定义中间件
    setup_middleware(app)

    # 包含API路由
    #   prefix：路由路径前缀
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # 添加根端点
    @app.get("/")
    async def root():
        """ 带有API信息的根端点 """
        return {
            "message": "欢迎使用HR Agent API",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_STR}/docs",
            "redoc": f"{settings.API_V1_STR}/redoc",
            "health": f"{settings.API_V1_STR}/health"
        }

    return app


# 使用uvicorn运行，会找到这个app
app = create_application()


if __name__ == "__main__":
    # 直接运行入口，如果直接运行这个文件，就调用uvicorn.run
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,  # 如果调试模式下代码变更会自动重启服务
        log_level="info"
    )




