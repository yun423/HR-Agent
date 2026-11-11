"""
应用程序的异常处理程序
"""

"""
    exception_handlers.py 是 FastAPI 的统一异常处理模块。它负责把项目里抛出的各种异常转换成统一格式的 JSON响应，并记录日志。
    exception_handlers.py这个文件和前面的 exceptions.py 是配套的
    整体作用：
        exceptions.py 定义 有哪些异常。
        exception_handlers.py 定义 这些异常发生后怎么返回给前端。

    返回格式基本统一为：
        {
            "error": {
                "message": "...",
                "type": "...",
                "details": {}
            }
        }

"""

import logging
from typing import Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from app.core.exceptions import BaseHTTPException, DatabaseIntegrityError, DatabaseError

'''
上面导入的模块说明：
    FastAPI 的 HTTPException异常类
    Starlette 的 HTTPException异常类，改名成了 StarletteHTTPException 防止冲突
    FastAPI 请求校验异常 RequestValidationError
    Pydantic 数据校验异常 ValidationError
    SQLAlchemy 数据库异常 SQLAlchemyError, IntegrityError
    项目自定义异常（exceptions.py） BaseHTTPException

    Starlette 是一个轻量级的 ASGI（异步服务器网关接口）框架，FastAPI 是基于 Starlette 构建的。
'''

logger = logging.getLogger(__name__)


async def base_http_exception_handler(request: Request, exc: BaseHTTPException) -> JSONResponse:
    """
        处理自定义基础HTTP异常： 处理项目自己的异常
        比如：
            raise UserNotFoundError()
            raise ValidationError("xxx")
            raise DatabaseConnectionError()

        异常都继承自 BaseHTTPException, 自带message、status_code、details
            所以处理器直接用这些字段生成响应
            同时会把请求路径、请求方法、状态码、详情写入日志。

    """
    logger.error(
        f"HTTP异常: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": exc.__class__.__name__,
                "details": exc.details,
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理FastAPI HTTP异常"""
    logger.error(
        f"HTTP异常: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "HTTPException",
            }
        }
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
        处理Starlette HTTP异常:
            主要处理 Starlette层面的 HTTP异常，比如路由不存在产生的404。
    """
    logger.error(
        f"Starlette HTTP异常: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "HTTPException",
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
        处理请求参数校验错误
            处理 FastAPI请求校验失败。
            常见场景：
                1. 请求体字段类型错误。
                2. 必填字段缺失。
                3. query/path参数不符合类型。
                4. 上传表单格式不对。

    """
    # 获取请求的表单数据（如果是POST请求）
    form_data = {}
    try:
        if request.method == "POST":
            form_data = await request.form()
            form_data = {k: str(v)[:100] for k, v in form_data.items()}  # 限制长度避免日志过长
    except:
        pass
    
    logger.warning(
        f"验证错误: {exc.errors()}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
            "received_form_fields": list(form_data.keys()) if form_data else [],
            "status_code": 422
        }
    )

    # 格式化验证错误
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "验证失败",
                "type": "ValidationError",
                "details": {
                    "errors": formatted_errors
                }
            }
        }
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
        处理Pydantic校验错误:
            处理代码内部使用Pydantic模型时产生的校验错误。
            和validation_exception_handler请求校验错误类似，也会把 exc.errors()转成统一结构，返回422。
    """
    logger.warning(
        f"Pydantic验证错误: {exc.errors()}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        }
    )

    # 格式化验证错误
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "数据验证失败",
                "type": "ValidationError",
                "details": {
                    "errors": formatted_errors
                }
            }
        }
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """处理SQLAlchemy数据库错误"""
    logger.error(
        f"数据库错误: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": exc.__class__.__name__,
        },
        exc_info=True
    )

    # 处理特定的SQLAlchemy异常
    '''
    如果异常是IntegrityError，会进一步判断具体是哪类约束错误：
        1. 包含unique constraint：唯一约束冲突，返回 409。
        2. 包含foreign key constraint：外键引用无效，返回 400。
        3. 其他完整性约束问题：返回 400。
    '''

    if isinstance(exc, IntegrityError):
        # 检查常见的完整性约束违规
        error_message = str(exc.orig) if hasattr(exc, 'orig') else str(exc)

        if "unique constraint" in error_message.lower():
            return JSONResponse(
                status_code=409,
                content={
                    "error": {
                        "message": "资源已存在",
                        "type": "ConflictError",
                        "details": {
                            "constraint": "unique_constraint_violation"
                        }
                    }
                }
            )
        elif "foreign key constraint" in error_message.lower():
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "message": "对相关资源的引用无效",
                        "type": "ValidationError",
                        "details": {
                            "constraint": "foreign_key_constraint_violation"
                        }
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "message": "数据完整性约束被违反",
                        "type": "ValidationError",
                        "details": {
                            "constraint": "integrity_constraint_violation"
                        }
                    }
                }
            )

    # 通用数据库错误
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "数据库操作失败",
                "type": "DatabaseError",
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
        处理所有其他未处理的异常: 兜底异常处理
            捕获所有没有被前面处理器匹配到的异常。
            这相当于最后一道防线，避免后端直接暴露Python报错堆栈给前端。会记录详细日志，但返回给前端的是通用错误
    """
    logger.error(
        f"未处理的异常: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": exc.__class__.__name__,
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "发生意外错误",
                "type": "InternalServerError",
            }
        }
    )


def setup_exception_handlers(app):
    """设置所有异常处理程序: 注册异常处理器的入口函数。"""

    # app.add_exception_handler：
    #   把各种异常类型和对应处理函数注册到FastAPI应用上。

    '''
    注册的异常：
        项目自定义异常。
        FastAPI和Starlette的异常。
        请求和Pydantic校验异常。
        SQLAlchemy数据库异常。
        所有其他未知异常。

    '''

    # 自定义异常处理程序
    app.add_exception_handler(BaseHTTPException, base_http_exception_handler)

    # FastAPI和Starlette异常处理程序
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)

    # 验证异常处理程序
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

    # 数据库异常处理程序
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # 通用异常处理程序（捕获所有）兜底
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("异常处理程序设置完成")

