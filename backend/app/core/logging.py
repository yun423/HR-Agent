"""
    日志配置
"""
import logging
import logging.config
import sys
import os
from pathlib import Path

from app.core.config import settings

'''
    logging.py 是后端的日志配置模块。负责统一设置控制台日志、普通日志文件、错误日志文件，以及处理控制台编码问题。
    整体作用:
    1. 项目启动时会调用：
        setup_logging()
    2. 调用后，整个后端里的：
        logger = logging.getLogger(__name__)
        logger.info(...)
        logger.error(...)
    
    都会按照这里定义的格式和输出位置写日志。
'''


class SafeStreamHandler(logging.StreamHandler):
    """
        自定义日志处理器:
            1. 继承Python标准库的logging.StreamHandler（能够优雅处理编码错误的StreamHandler），主要用于控制台输出
            2. 这个类主要是为了避免中文、特殊符号等日志内容在某些终端里导致程序报错。

    """

    '''
        核心逻辑在emit()方法：
            1. 正常情况下调用super().emit(record)输出日志。
            2. 如果遇到UnicodeEncodeError，说明控制台编码不支持某些字符。
            3. 它会把日志消息重新用UTF-8编码，并用errors='replace'替换无法编码的字符。
            4. 如果还是失败，就输出简单的提示:"[编码错误] 日志消息无法显示"
            
    '''
    def emit(self, record):
        try:
            super().emit(record)

        except UnicodeEncodeError:
            # 如果编码失败，替换有问题的字符
            try:
                msg = self.format(record)

                # 用安全的替代字符替换有问题的Unicode字符
                safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
                self.stream.write(safe_msg + self.terminator)
                self.flush()
            except Exception:
                # 最后的手段：只打印一个简单的错误消息
                self.stream.write(f"[编码错误] 日志消息无法显示\n")
                self.flush()


def setup_logging() -> None:
    """
        设置应用程序日志配置:
            是这个文件的核心函数，用来初始化日志系统
    """
    # 创建logs目录:
    #   如果目录不存在，就自动创建，避免文件日志写入失败。
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 判断是否是Windows：如果是，将控制台编码设置为UTF-8（Windows）
    if os.name == 'nt':  # Windows
        try:
            # 如果是Windows，就执行：“chcp 65001”，这是把控制台代码页切到UTF-8，减少中文日志乱码问题。
            os.system('chcp 65001 >nul 2>&1')
        except:
            pass

    # 日志格式
    '''
        定义logging_config字典
          里面定义了两个formatter：
            default：使用配置里的 settings.LOG_FORMAT，通常用于控制台。
            detailed：更详细，包含：时间-logger名称-日志等级-模块名-函数名-消息。这个通常用于日志文件，方便定位代码位置。
        
        日志输出位置：定义了三个handler：
            console：输出到控制台，使用SafeStreamHandler，日志级别来自settings.LOG_LEVEL。
            file：使用RotatingFileHandler，单个文件最大10MB，最多保留5个备份，输出到“logs/hr_agent.log”。
            error_file：只记录ERROR及以上级别日志，单个文件最大10MB，最多5个备份。输出到“logs/hr_agent_error.log”
        
        日志器配置： 配置了几个logger：
            根日志记录器 ""：项目大多数日志会同时输出到控制台、普通日志文件、错误日志文件。
            uvicorn：Uvicorn日志只输出到控制台，避免过多服务器运行日志进入项目日志文件。
            sqlalchemy：SQLAlchemy只有warning及以上写入普通日志文件，避免SQL日志太长。
            
            "propagate"参数： 默认为True，用于控制日志记录器（Logger）是否将日志事件向上传播（propagate）给其父级Logger。
    '''
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": settings.LOG_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "()": SafeStreamHandler,
                "level": settings.LOG_LEVEL,
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "detailed",
                "filename": "logs/hr_agent.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/hr_agent_error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # 根日志记录器
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
        },
    }

    # 注册配置：正式让Python logging使用这套配置。
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger(__name__)
    logger.info("日志配置设置完成")  # 表示日志系统初始化成功。


# 创建全局日志记录器实例
#   __name__可以让日志里显示是哪个模块输出的，便于排查问题
logger = logging.getLogger(__name__)





