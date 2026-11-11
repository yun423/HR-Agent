"""
检索结果重排服务：
    根据配置初始化 Qwen/DashScope相关重排能力，对 RAG检索出的文档重新打分并排序；
    如果重排不可用，会保留原始结果。get_rerank_service() 提供单例入口。
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain_core.documents import Document as LangChainDocument

from app.core.config import settings

logger = logging.getLogger(__name__)

# 导入DashScope用于Qwen重排
try:
    import dashscope
    from dashscope import TextReRank
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.warning("DashScope不可用，Qwen重排将无法工作")


class RerankService:
    """使用Qwen模型提高检索结果质量的重排服务"""

    def __init__(self):
        self.model = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialize_model()

    def _initialize_model(self):
        """根据配置初始化重排模型"""
        if not settings.RERANK_ENABLED:
            logger.info("配置中已禁用重排")
            return

        if not DASHSCOPE_AVAILABLE:
            logger.error("DashScope不可用，Qwen重排无法工作")
            return

        if not settings.QWEN_API_KEY:
            logger.error("QWEN_API_KEY未设置，Qwen重排无法工作")
            return

        # 使用API密钥初始化DashScope
        dashscope.api_key = settings.QWEN_API_KEY
        self.model = "qwen"
        logger.info("Qwen重排模型初始化成功")

    def _compute_rerank_scores(self, query: str, documents: List[str]) -> List[float]:
        """使用Qwen模型计算文档的重排分数"""
        if not self.model:
            # 如果模型不可用，返回原始顺序分数
            return [1.0 - i * 0.1 for i in range(len(documents))]

        # 处理Qwen重排
        return self._compute_qwen_rerank_scores(query, documents)

    def _compute_qwen_rerank_scores(self, query: str, documents: List[str]) -> List[float]:
        """通过DashScope API使用Qwen模型计算重排分数"""
        if not DASHSCOPE_AVAILABLE or not settings.QWEN_API_KEY:
            logger.error("DashScope不可用或QWEN_API_KEY未设置")
            return [1.0 - i * 0.1 for i in range(len(documents))]

        try:
            # 调用DashScope TextReRank API
            response = TextReRank.call(
                model=settings.QWEN_MODEL,
                query=query,
                documents=documents,
                top_n=len(documents),  # 返回所有带分数的文档
                return_documents=True  # 返回带分数的文档
            )

            if response.status_code != 200:
                logger.error(f"Qwen重排API调用失败，状态码 {response.status_code}: {response.message}")
                return [1.0 - i * 0.1 for i in range(len(documents))]

            # 从响应中提取分数
            # 响应应包含带分数的文档列表
            results = response.output.results
            scores = [0.0] * len(documents)

            # 将分数映射回原始文档顺序
            for result in results:
                if 0 <= result.index < len(documents):
                    scores[result.index] = result.relevance_score

            return scores

        except Exception as e:
            logger.error(f"计算Qwen重排分数时出错: {e}")
            # 返回备用分数
            return [1.0 - i * 0.1 for i in range(len(documents))]

    async def rerank_documents(
        self,
        query: str,
        documents: List[LangChainDocument],
        sources: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> Tuple[List[LangChainDocument], List[Dict[str, Any]]]:
        """
        使用Qwen模型根据查询相关性对文档进行重排

        Args:
            query: 搜索查询
            documents: LangChain文档列表
            sources: 源元数据列表
            top_k: 要返回的顶级结果数（默认为RERANK_FINAL_K）

        Returns:
            (重排文档, 重排源)的元组
        """
        if not settings.RERANK_ENABLED or not self.model or not documents:
            return documents, sources

        if top_k is None:
            top_k = settings.RERANK_FINAL_K

        try:
            # 限制候选数量为RERANK_TOP_K以提高效率
            max_candidates = min(len(documents), settings.RERANK_TOP_K)
            candidate_docs = documents[:max_candidates]
            candidate_sources = sources[:max_candidates]

            # 提取文档文本用于重排
            doc_texts = [doc.page_content for doc in candidate_docs]

            # 在线程池中计算重排分数以避免阻塞
            loop = asyncio.get_event_loop()
            rerank_scores = await loop.run_in_executor(
                self.executor,
                self._compute_rerank_scores,
                query,
                doc_texts
            )

            # 将文档与其重排分数结合
            doc_score_pairs = []
            for i, (doc, source, rerank_score) in enumerate(zip(candidate_docs, candidate_sources, rerank_scores)):
                # 存储原始分数以供比较
                original_score = source.get('combined_score', 0.0)

                # 使用重排信息更新源
                updated_source = source.copy()
                updated_source.update({
                    'rerank_score': float(rerank_score),
                    'original_score': float(original_score),
                    'rerank_enabled': True,
                    'rerank_model': settings.QWEN_MODEL
                })

                doc_score_pairs.append((doc, updated_source, float(rerank_score)))

            # 按重排分数降序排序
            doc_score_pairs.sort(key=lambda x: x[2], reverse=True)

            # 提取top_k结果
            top_pairs = doc_score_pairs[:top_k]
            reranked_docs = [pair[0] for pair in top_pairs]
            reranked_sources = [pair[1] for pair in top_pairs]

            logger.info(f"重排了{len(candidate_docs)}个文档，返回前{len(reranked_docs)}个")

            return reranked_docs, reranked_sources

        except Exception as e:
            logger.error(f"重排过程中出错: {e}")
            # 出错时返回原始结果
            return documents[:top_k], sources[:top_k]

    def is_enabled(self) -> bool:
        """检查重排是否启用且模型可用"""
        return settings.RERANK_ENABLED and self.model is not None


# 全局重排服务实例
_rerank_service = None


def get_rerank_service() -> RerankService:
    """获取全局重排服务实例"""
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service