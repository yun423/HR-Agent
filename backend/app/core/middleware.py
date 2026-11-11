""""""
import time
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


'''
    middleware.py 后端的自定义中间件。中间件会包在接口请求外层，请求进入接口前、响应返回前都可以做统一处理。
    
    这个文件主要有两个中间件：
        LoggingMiddleware：记录请求、响应和耗时。
        SecurityHeadersMiddleware：给响应添加安全相关HTTP头。
        
    这里中间件的作用：
        所有接口都会自动获得请求日志、耗时响应头和安全响应头，不需要每个接口单独写。
'''


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
        登录中间件：记录请求和响应的中间件
    """

    # 每个请求经过这个中间件时，会调用dispatch()。
    async def dispatch(self, request: Request, call_next: Callable) -> Response:

        # 记录开始时间
        start_time = time.time()

        # 记录请求方法和URL
        logger.info(f"Request: {request.method} {request.url}")

        # 把请求交给后续中间件或真正的接口函数：这一步很关键，没有它，请求就不会继续往下执行。
        response = await call_next(request)

        # 计算接口处理耗时
        process_time = time.time() - start_time

        # 日志记录响应状态码和耗时
        logger.info(
            f"Response: {response.status_code} - "
            f"Processing time: {process_time:.4f}s"
        )

        # 把耗时写入响应头
        #    前端或调试工具可以在响应 header 里看到接口耗时。
        response.headers["X-Process-Time"] = str(process_time)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
        给响应添加安全相关HTTP头的中间件
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:

        # 先执行接口逻辑
        response = await call_next(request)

        # 给响应添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"  # 防止浏览器猜测MIME类型，降低某些脚本注入风险。
        response.headers["X-Frame-Options"] = "DENY"  # 禁止页面被iframe嵌入，防止点击劫持。
        response.headers["X-XSS-Protection"] = "1; mode=block"  # 启用旧版浏览器的XSS防护机制。
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            # 告诉浏览器后续应使用HTTPS访问该站点。注意：这个头在HTTPS部署下才真正有意义。

        return response


def setup_middleware(app: FastAPI) -> None:
    """
        添加中间件
            在main.py创建FastAPI应用时调用，会把这两个中间件挂到应用上。
    """
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("Middleware中间件设置完成")



