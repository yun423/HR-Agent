"""
 OpenAI 兼容 embedding 封装。
    CompatibleOpenAIEmbeddings 实现 LangChain 的 Embeddings 接口，
    内部用 OpenAI 兼容 API 生成文本向量，同时提供同步和异步方法。它让项目可以使用自定义 base_url、模型名和向量维度。
"""

import asyncio
from typing import List, Optional
from openai import OpenAI
from langchain_core.embeddings import Embeddings
from ..core.config import settings
import logging
logger = logging.getLogger(__name__)

class CompatibleOpenAIEmbeddings(Embeddings):
    """使用OpenAI兼容API的兼容嵌入。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "text-embedding-v1",
        dimensions: int = None
    ):
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = base_url
        self.model = model
        self.dimensions = dimensions or settings.VECTOR_DIMENSION

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"DashScope兼容嵌入已使用模型初始化: {self.model}")

    BATCH_SIZE = 20  # API限制为25，留余量

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入搜索文档，自动分批次处理以符合API限制。"""
        try:
            all_embeddings = []
            for i in range(0, len(texts), self.BATCH_SIZE):
                batch = texts[i:i + self.BATCH_SIZE]
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                    encoding_format="float"
                )
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend(d.embedding for d in sorted_data)
            return all_embeddings
        except Exception as e:
            logger.error(f"嵌入文档时出错: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本。"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"嵌入查询时出错: {e}")
            raise

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步嵌入搜索文档。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_documents, texts)

    async def aembed_query(self, text: str) -> List[float]:
        """异步嵌入查询文本。"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_query, text)