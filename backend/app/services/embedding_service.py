"""
单例embedding嵌入服务，避免重复初始化OpenAIEmbeddings：
    EmbeddingService 初始化 CompatibleOpenAIEmbeddings 和 LangChain 文本切分器，
    统一提供 get_embeddings()、get_text_splitter()。get_embedding_service() 是全局获取入口，避免每次请求重复初始化模型配置
"""
import logging
from typing import Optional, List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from .compatible_embeddings import CompatibleOpenAIEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """用于管理嵌入和文本分割的单例服务"""

    _instance: Optional['EmbeddingService'] = None
    _initialized: bool = False

    def __new__(cls) -> 'EmbeddingService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def _initialize(self):
        """初始化嵌入服务组件"""
        try:
            # 初始化兼容的OpenAI嵌入
            api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
            base_url = settings.EMBEDDING_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            model = settings.EMBEDDING_MODEL or "text-embedding-v1"

            # 使用新的CompatibleOpenAIEmbeddings类
            self.embeddings = CompatibleOpenAIEmbeddings(
                api_key=api_key,
                base_url=base_url,
                model=model
            )

            # 初始化文本分割器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=100,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )

            logger.info("EmbeddingService已成功初始化OpenAI嵌入")

        except Exception as e:
            logger.error(f"初始化EmbeddingService失败: {e}")
            raise

    def get_embeddings(self) -> CompatibleOpenAIEmbeddings:
        """获取兼容的OpenAI嵌入实例"""
        return self.embeddings

    def get_text_splitter(self) -> RecursiveCharacterTextSplitter:
        """获取文本分割器实例"""
        return self.text_splitter

    @classmethod
    def get_instance(cls) -> 'EmbeddingService':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# 获取单例实例的全局函数
def get_embedding_service() -> EmbeddingService:
    """获取单例EmbeddingService实例"""
    return EmbeddingService.get_instance()