
"""
    Pydantic Schema，主要用于 FastAPI 的请求参数校验、响应数据结构定义、字段类型约束。
        它们不是数据库表，和 models 的区别是：models 管数据库结构，schemas 管 API 输入输出格式。
"""

"""
    本文件是schemas包入口。把user、conversation、document、knowledge_base、chat里的schema用 import * 暴露出来，方便其他地方统一导入。
"""
from .user import *
from .conversation import *
from .document import *
from .knowledge_base import *
from .chat import *