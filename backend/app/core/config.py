"""
    应用程序配置设置
"""
from pathlib import Path
from typing import List, Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


'''
    config.py 是后端的全局配置文件：
        项目里很多模块都会导入这里的 settings，统一读取应用端口、数据库、LLM、RAG、上传、日志等配置。
        Settings继承自 pydantic_settings.BaseSettings。配置值可以来自两处：
            1. 类里写的默认值。
            2. .env 文件或环境变量中的同名配置。
'''

class Settings(BaseSettings):
    """应用程序设置"""

    # 基本应用设置:
    #   定义项目名称、版本、调试模式、监听地址和端口：
    PROJECT_NAME: str = "HR Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # API设置
    API_V1_STR: str = "/api/v1"

    # 安全设置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8天

    # CORS设置
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """
            组装CORS源

            assemble_cors_origins() 是一个字段校验器:
                1. 如果是普通逗号字符串，就拆成列表；
                2. 如果已经是列表或JSON字符串，就直接返回
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 数据库设置:
    #    DATABASE_URL是完整连接串，
    #    DATABASE_POOL_SIZE 和 DATABASE_MAX_OVERFLOW 控制 SQLAlchemy连接池。
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/hr_agent"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "hr_agent"
    DATABASE_USER: str = "username"
    DATABASE_PASSWORD: str = "password"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # 远程服务配置
    HR_SERVICE_HOST: str = "127.0.0.1"
    HR_SERVICE_PORT: int = 8000
    HR_SERVICE_APIKEY: str = "your - api - key"

    @property
    def DATABASE_NAME_FROM_URL(self) -> str:
        """
            从DATABASE_URL中提取数据库名称：
                DATABASE_NAME_FROM_URL 会从 DATABASE_URL 最后一个 / 后面提取数据库名。
                如果 URL 不符合格式，则返回 DATABASE_NAME。
        """
        if "/" in self.DATABASE_URL:
            return self.DATABASE_URL.split("/")[-1]
        return self.DATABASE_NAME


    # AI / RAG 配置
    """
        AI 能力相关配置：
            VECTOR_DIMENSION：向量维度，当前是 1536。
            LLM_API_KEY、LLM_BASE_URL、LLM_MODEL：大模型配置。
            EMBEDDING_API_KEY、EMBEDDING_BASE_URL、EMBEDDING_MODEL： Embedding配置。
            QWEN_API_KEY、QWEN_MODEL： 通义千问重排模型配置。
            RERANK_ENABLED、RERANK_TOP_K、RERANK_FINAL_K：重排开关和数量。
            KB_QUERY_ENHANCE_ENABLED、KB_QUERY_EXPANSION_MAX_TERMS：知识库查询改写配置。
            RAG_CONTENT_WEIGHT、RAG_TEXT_WEIGHT、RAG_MIN_SIMILARITY_SCORE：RAG 检索结果打分权重和过滤阈值。
            CONTEXT_LIMIT：检索上下文文档数量。
        这些配置会被知识库、RAG、重排、LLM 服务等模块使用。
    """

    # 向量数据库设置
    VECTOR_DIMENSION: int = 1536  # 通义千问 text-embedding-v1维度

    # LLM设置
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL: str = "qwen-max"

    # 嵌入设置
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-v1"

    # Qwen设置
    QWEN_API_KEY: Optional[str] = None
    QWEN_MODEL: str = "gte-rerank-v2"  # 默认Qwen重排模型

    # 文件上传设置
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"

    # Dify 工作流配置
    DIFY_BASE_URL: str = "http://nginx.docker.orb.local/v1"
    DIFY_API_KEY: str = ""
    DIFY_USER_ID: str = "hr-agent-user"

    # 重排设置
    RERANK_ENABLED: bool = True  # 启用重排（使用Qwen模型）
    RERANK_TOP_K: int = 10  # 需要重排的候选项数量
    RERANK_FINAL_K: int = 10  # 重排后的最终结果数量

    # 查询改写设置
    KB_QUERY_ENHANCE_ENABLED: bool = True  # 启用查询改写功能
    KB_QUERY_EXPANSION_MAX_TERMS: int = 6  # 查询扩展最大术语数量

    # RAG 分数组合权重设置
    RAG_CONTENT_WEIGHT: float = 0.7  # 向量相似度权重
    RAG_TEXT_WEIGHT: float = 0.3  # 文本匹配权重
    RAG_MIN_SIMILARITY_SCORE: float = 0.2  # 低于该阈值的检索结果将被过滤

    # 上下文设置
    CONTEXT_LIMIT: int = Field(10, description="要检索的上下文文档数量")  # 要检索的上下文文档数量

    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 远程服务请求/响应日志设置
    REMOTE_SERVICE_LOG_ENABLED: bool = False  # 是否输出远程服务请求/响应详情

    """
        model_config 是 pydantic-settings 的配置项，用来告诉 Settings 这个配置类怎么读取和处理配置。
          1. env_file：指定从哪个 .env 文件读取配置。
          2. 所以 Settings() 初始化时，会自动读取 backend/.env 里的环境变量
          3. 如果 .env里有, Settings类没有声明的配置项，就忽略它，不报错。
    
        参数说明：
          env_file： .env 文件路径是 backend/.env。
          case_sensitive： 环境变量大小写敏感。
          extra： .env 里多出来但 Settings 没定义的字段会被忽略，不会报错。
    """
    model_config = {
        "env_file": Path(__file__).parent.parent.parent / ".env",  # 正确的.env文件路径
        "case_sensitive": True,
        "extra": "ignore"
    }


settings = Settings()
