"""
RAG检索增强生成服务：
    使用LangChain、PGVector、ChatOpenAI、rerank 服务和 PostgreSQL全文检索，
    把问题扩展、向量检索、关键词检索、结果合并重排、上下文拼接、最终回答串起来。若判断问题不需要知识库，也能走普通聊天链路。
"""
import logging
import re
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# LangChain导入
from langchain_core.documents import Document as LangChainDocument
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI

from app.services.embedding_service import get_embedding_service
from app.services.rerank_service import get_rerank_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """实现LangChain标准工作流的RAG服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

        # 初始化嵌入服务
        self.embedding_service = get_embedding_service()
        self.embeddings = self.embedding_service.get_embeddings()

        # 初始化重排服务
        self.rerank_service = get_rerank_service()

        # 初始化LLM
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            temperature=0.7,
            max_tokens=2000
        )

        # PGVector的数据库连接字符串
        self.connection_string = settings.DATABASE_URL

        logger.info("RAG服务已使用LangChain组件初始化")

    def _enhance_query_for_kb(self, question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        基于LLM的语义增强：重写查询并提供扩展关键词。
        返回: { "rewritten_query": str, "expanded_keywords": List[str] }
        """
        try:
            if not getattr(settings, "KB_QUERY_ENHANCE_ENABLED", False):
                return {"rewritten_query": question, "expanded_keywords": []}

            system_prompt = (
                "你是一个检索查询增强器。\n"
                "通过对上下文理解，理解用户真实意图，输出更清晰的检索查询和若干关键术语扩展。\n"
                "返回严格的 JSON 对象：{{\"rewritten_query\": \"...\", \"expanded_keywords\": [\"...\"]}}。\n"
                "注意：扩展术语需短而准，避免过长句子。"
            )

            conversation_history = conversation_history or []
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "原始查询：{question}\n请返回 JSON 格式结果")
            ])

            enhancer_llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                temperature=0.2,
                max_tokens=512
            )

            chain = (
                {
                    "question": RunnablePassthrough(),
                    "chat_history": lambda x: conversation_history
                }
                | prompt
                | enhancer_llm
                | StrOutputParser()
            )

            raw = chain.invoke(question)
            rewritten_query = question
            expanded_keywords: List[str] = []

            try:
                import json as pyjson
                data = pyjson.loads(raw)
                rewritten_query = data.get("rewritten_query") or question
                ek = data.get("expanded_keywords") or []
                if isinstance(ek, list):
                    expanded_keywords = [str(t).strip() for t in ek if str(t).strip()]
                elif isinstance(ek, str):
                    expanded_keywords = [t.strip() for t in ek.split(',') if t.strip()]
            except Exception:
                # 备用方案：直接提取令牌
                terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", raw)
                expanded_keywords = [t.lower() for t in terms if len(t) >= 2]

            max_terms = getattr(settings, "KB_QUERY_EXPANSION_MAX_TERMS", 6)
            if len(expanded_keywords) > max_terms:
                expanded_keywords = expanded_keywords[:max_terms]

            return {"rewritten_query": rewritten_query, "expanded_keywords": expanded_keywords}
        except Exception as e:
            logger.warning(f"查询增强失败: {e}")
            return {"rewritten_query": question, "expanded_keywords": []}

    async def _tsvector_search(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        knowledge_base_id: Optional[UUID] = None,
        extra_terms: Optional[List[str]] = None
    ) -> List[tuple]:
        """
        基于langchain_pg_embedding.document的PostgreSQL全文检索（tsvector）。
        - 集合名严格过滤：cmetadata->>'collection_name'
        - 查询重写为 OR 前缀 tsquery（类似Elasticsearch match：任一词命中即返回）
        - 对中文/英中混合词保留 ILIKE 后备，提高召回率
        返回 (LangChainDocument, score) 列表，与向量检索输出格式一致。
        """
        try:
            # 1) 查询重写：提取英文/数字/中文词元，移除常见问句停用词，构造 OR 前缀 tsquery
            stop_words = {"有哪些", "什么", "如何", "怎么", "请问", "的", "和", "与"}
            terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", query)
            terms = [t.lower() for t in terms if t not in stop_words and len(t) >= 2]
            # 追加额外的扩展术语
            if extra_terms:
                for t in extra_terms:
                    t = str(t).strip().lower()
                    if t and t not in terms and t not in stop_words:
                        terms.append(t)
            # 构造 tsquery
            tsquery_or = " | ".join(f"{t}:*" for t in terms) if terms else None

            # 2) 构建 SQL：优先使用 to_tsquery(simple, :tsq) 的 OR 匹配；保留 ILIKE 兜底
            #         'simple' 配置： 不进行词干提取、停用词过滤等，仅小写+分词
            # 从指定 collection 中，找出所有包含用户查询关键词的文档分块，并按全文检索相关性打分（rank）。支持两种搜索模式：
            #     高级全文检索（当 :tsq 有效时，使用 tsquery 匹配）；
            #     基础模糊匹配（当 :tsq 无效或作为补充，使用 ILIKE）。
            # 这在 RAG 应用中很常见：用户输入一个问题或关键词，系统既要精准匹配（通过 tsquery），又要避免漏掉因分词/格式问题未被全文索引捕获的内容（通过 ILIKE 兜底）。
            base_sql = (
                "SELECT id, document, cmetadata, "
                "ts_rank_cd(to_tsvector('simple', document), to_tsquery('simple', :tsq)) AS rank "
                "FROM langchain_pg_embedding "
                "WHERE cmetadata->>'collection_name' = :collection_name "
                "AND ("
                "     ( :tsq IS NOT NULL AND to_tsvector('simple', document) @@ to_tsquery('simple', :tsq) ) "
                "     OR document ILIKE '%' || :q || '%'"
                ") "
            )
            params = {"q": query, "tsq": tsquery_or, "collection_name": collection_name, "limit": k}

            if knowledge_base_id:
                base_sql += "AND cmetadata->>'knowledge_base_id' = :kb_id "
                params["kb_id"] = str(knowledge_base_id)

            base_sql += "ORDER BY rank DESC LIMIT :limit"

            res2 = await self.db.execute(text(base_sql), params)
            rows = res2.fetchall()
            results: List[tuple] = []
            for r in rows:
                doc_text = r[1]
                metadata = r[2] or {}
                page_content = doc_text
                lc_doc = LangChainDocument(page_content=page_content, metadata=metadata)
                results.append((lc_doc, float(r[3]) if r[3] is not None else 0.0))
            return results
        except Exception as e:
            logger.warning(f"tsvector搜索错误: {e}")
            return []

    async def _merge_docs_with_scores(
        self,
        content_results: List[tuple],
        text_results: List[tuple],
        query: str,
        top_k: int = 5,
        min_similarity_score: float = 0.2
    ) -> (List[LangChainDocument], List[Dict[str, Any]]):
        """
        使用可配置的融合方法合并向量内容结果和PostgreSQL tsvector结果。
        支持RRF（倒数排名融合）和加权和方法，可选择重排。
        """
        try:
            merged_map: Dict[tuple, Dict[str, Any]] = {}

            # 收集向量搜索结果
            for doc, score in content_results:
                key = (doc.metadata.get("document_id"), doc.metadata.get("chunk_index"))
                merged_map[key] = merged_map.get(key, {"doc": doc, "content_score": 0.0})
                merged_map[key]["doc"] = doc
                merged_map[key]["content_score"] = float(score)

            # 集成tsvector文本搜索结果
            for doc, score in text_results:
                key = (doc.metadata.get("document_id"), doc.metadata.get("chunk_index"))
                entry = merged_map.get(key, {"doc": doc, "content_score": 0.0})
                entry["doc"] = entry.get("doc") or doc
                entry["text_score"] = float(score)
                merged_map[key] = entry

            # 合并分数：优先考虑向量相似性，然后是关键词匹配
            combined_list: List[tuple] = []
            for key, entry in merged_map.items():
                content_score = float(entry.get("content_score", 0.0))
                text_score = float(entry.get("text_score", 0.0))
                # 加权组合：使用配置文件中的权重
                combined_score = (settings.RAG_CONTENT_WEIGHT * content_score + 
                                settings.RAG_TEXT_WEIGHT * text_score)
                combined_list.append((entry["doc"], combined_score, entry))

            # 按combined_score降序排序（更高相关性优先）
            combined_list.sort(key=lambda x: x[1], reverse=True)
            combined_list = [item for item in combined_list if float(item[1]) >= min_similarity_score]

            # 构建输出
            top = combined_list[:top_k]
            docs: List[LangChainDocument] = []
            sources: List[Dict[str, Any]] = []
            for doc, combined_score, entry in top:
                final_page_content = doc.page_content
                final_doc = LangChainDocument(page_content=final_page_content, metadata=doc.metadata)
                docs.append(final_doc)
                sources.append({
                    "document_id": doc.metadata.get("document_id"),
                    "document_title": doc.metadata.get("filename", "Unknown"),
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "content": final_page_content,
                    "combined_score": float(combined_score),
                    "content_score": float(entry.get("content_score", 0.0)),
                    "text_score": float(entry.get("text_score", 0.0)),
                    "metadata": doc.metadata
                })

            # 如果启用则应用重排
            if settings.RERANK_ENABLED and self.rerank_service.is_enabled():
                docs, sources = await self.rerank_service.rerank_documents(
                    query=query,
                    documents=docs,
                    sources=sources,
                    top_k=top_k
                )
            else:
                # 如果没有重排则只取top_k
                docs = docs[:top_k]
                sources = sources[:top_k]

            return docs, sources

        except Exception as e:
            logger.warning(f"合并多路径结果时出错: {e}")
            # 备用方案：仅返回content_results
            docs = [doc for doc, _ in content_results[:top_k]]
            sources = []
            for doc, score in content_results[:top_k]:
                sources.append({
                    "document_id": doc.metadata.get("document_id"),
                    "document_title": doc.metadata.get("filename", "Unknown"),
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "content": doc.page_content,
                    "combined_score": float(score),
                    "content_score": float(score),
                    "text_score": 0.0,
                    "metadata": doc.metadata
                })
            return docs, sources

    def _create_rag_chain_with_docs(self, docs: List[LangChainDocument], conversation_history: List[Dict[str, str]]):
        """创建带预检索文档的RAG链。"""
        from langchain_core.messages import HumanMessage, AIMessage
        
        # 转换对话历史格式
        formatted_history = []
        for msg in conversation_history:
            if msg.get("role") == "user":
                formatted_history.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                formatted_history.append(AIMessage(content=msg.get("content", "")))

        # 创建提示模板
        system_prompt = """你是一个智能助手，基于提供的上下文信息回答用户问题。

                        上下文信息：
                        {context}
                        
                        请根据上下文信息回答用户的问题。如果上下文信息不足以回答问题，请诚实地说明。
                        保持回答准确、有用且简洁。"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])

        # 格式化文档
        def format_docs(docs_list):
            return "\n\n".join(doc.page_content for doc in docs_list)

        # 使用预检索文档创建链
        rag_chain = (
            {
                "context": lambda x: format_docs(docs),
                "question": RunnablePassthrough(),
                "chat_history": lambda x: formatted_history
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain

    def _should_use_knowledge_base(self, question: str) -> bool:
        """决定用户问题是否应使用知识库检索。
        如果返回True则应使用KB，否则返回False。
        """
        try:
            # 先做关键词预筛：纯闲聊关键词直接走 GENERAL，避免浪费 LLM 调用
            chitchat_keywords = ["你好", "谢谢", "再见", "你是谁", "讲个笑话", "作首诗", "写首诗", "聊天"]
            question_stripped = question.strip()
            if any(question_stripped == kw for kw in chitchat_keywords):
                logger.info(f"关键词预筛命中闲聊，跳过KB检索: {question}")
                return False

            # 带明确指令和示例的基于LLM的分类
            classification_prompt = (
                "你是一个分类器。判断该问题是否需要基于知识库内容回答还是由大模型自主回答。\n"
                "只有用户在明显是闲聊的内容才输出GENERAL。\n"
                "其他情况都输出KB\n"
                "示例：\n"
                "问：讲个笑话\n答：GENERAL\n"
                "问：你好\n答：GENERAL\n"
                "问：你是谁\n答：GENERAL\n"
                "问：作首诗\n答：GENERAL\n"
                "而其他情况或者判断不准的时候，都输出KB\n"
                "重要规则：你只需要输出一个词。只能回答KB或者GENERAL。不要解释，不要说其他任何话。\n"
                f"问：{question}\n答："
            )
            # 使用确定性分类器LLM
            from langchain_openai import ChatOpenAI
            classifier_llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                temperature=0,
                max_tokens=50
            )
            resp = classifier_llm.invoke(classification_prompt)
            content = getattr(resp, "content", str(resp))
            logger.info(f"KB意图分类结果: question='{question[:50]}...', response='{content}'")
            # 如果明确包含 GENERAL 且不包含 KB，不走知识库
            if "GENERAL" in (content or "").upper() and "KB" not in (content or "").upper():
                return False
            # 其余情况一律走知识库（默认走 KB 更安全）
            return True
        except Exception as e:
            logger.warning(f"KB意图检测失败，默认使用KB: {e}")
            return True

    def _create_general_chat_chain(self, conversation_history: List[Dict[str, str]]):
        """不带KB上下文的通用聊天链。"""
        from langchain_core.messages import HumanMessage, AIMessage
        
        # 转换对话历史格式
        formatted_history = []
        for msg in conversation_history:
            if msg.get("role") == "user":
                formatted_history.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                formatted_history.append(AIMessage(content=msg.get("content", "")))
        
        system_prompt = (
            "你是一个智能助手。直接根据用户问题进行回答，不使用任何知识库上下文。"
            "保持回答准确、简洁、有帮助。"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        chain = (
            {
                "question": RunnablePassthrough(),
                "chat_history": lambda x: formatted_history
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

    async def ask_question_stream(
        self,
        question: str,
        user_id: UUID,
        knowledge_base_id: Optional[UUID] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context_limit: int = settings.CONTEXT_LIMIT
    ):
        """
        使用RAG工作流进行流式响应的问题提问

        Args:
            question: 用户问题
            user_id: 用于文档过滤的用户ID
            knowledge_base_id: 可选的知识库ID用于过滤
            conversation_history: 之前的对话消息
            context_limit: 要检索的最大上下文文档数

        Yields:
            包含流式响应数据的字典
        """
        try:
            conversation_history = conversation_history or []

            # 首先进行意图检测
            use_kb = self._should_use_knowledge_base(question)
            print('use_kb=======', use_kb)
            # 如果提供了特定的知识库，总是使用KB检索
            # if knowledge_base_id:
            #     use_kb = True

            logger.info(f"ask_question_stream: use_kb={use_kb}, knowledge_base_id={knowledge_base_id}, user_id={user_id}")

            # 不使用知识库，直接访问LLM对话
            if not use_kb:
                # 流式传输不使用KB检索的通用LLM答案
                yield {
                    "type": "start",
                    "question": question,
                    "sources": [],
                    "context_used": False,
                    "num_sources": 0
                }
                try:
                    general_chain = self._create_general_chat_chain(conversation_history)
                    # 使用真正的流式输出
                    async for chunk in general_chain.astream({"question": question}):
                        # 处理不同类型的chunk
                        if isinstance(chunk, str):
                            if chunk.strip():  # 只发送非空字符串
                                yield {"type": "chunk", "content": chunk}
                        elif isinstance(chunk, dict):
                            # 处理字典类型的chunk
                            if "content" in chunk and chunk["content"].strip():
                                yield {"type": "chunk", "content": chunk["content"]}
                            elif "output" in chunk and chunk["output"].strip():
                                yield {"type": "chunk", "content": chunk["output"]}
                    
                    yield {"type": "end", "complete": True, "sources": [], "num_sources": 0}
                except GeneratorExit:
                    logger.info("客户端断开连接，停止流式响应")
                    return
                except Exception as e:
                    logger.error(f"流式响应生成错误: {str(e)}")
                    yield {"type": "error", "error": str(e)}
                return



            print('conversation_history =======', conversation_history)
            # 可选地为KB检索增强查询：查询语句改写
            enhance = self._enhance_query_for_kb(question, conversation_history)
            print('enhance=======', enhance)
            # 改写后的query
            rewritten_query = enhance.get("rewritten_query", question)
            print('rewritten_query=======', rewritten_query)
            # 扩展关键字
            expanded_keywords = enhance.get("expanded_keywords", [])
            print('expanded_keywords=======', expanded_keywords)

            # 为用户的文档创建集合名称（仅块）
            collection_name = f"document_chunks_{user_id}".replace("-", "_")

            # 连接到向量存储
            vector_store = PGVector(
                connection=self.connection_string,
                embeddings=self.embeddings,
                collection_name=collection_name,
                use_jsonb=True
            )
            # 关键词存储已移除；仅保留块向量存储

            # 构建过滤条件
            filter_conditions = {}
            if knowledge_base_id:
                filter_conditions["knowledge_base_id"] = str(knowledge_base_id)

            # 多路径检索：内容（向量）+ 文本（tsvector）
            # 向量路径
            content_results = vector_store.similarity_search_with_relevance_scores(
                rewritten_query, k=context_limit, filter=filter_conditions if filter_conditions else None
            )

            # 第二路径：在块集合上进行PostgreSQL tsvector全文检索
            text_results = await self._tsvector_search(
                collection_name,
                question,
                k=context_limit,
                knowledge_base_id=knowledge_base_id,
                extra_terms=expanded_keywords
            )

            # # 调试：输出两个路径的结果对比
            # logger.info(f"=== 向量搜索结果 (content_results) ===")
            # for i, (doc, score) in enumerate(content_results):
            #     logger.info(f"向量结果 {i+1}: 分数={score:.4f}, 文档ID={doc.metadata.get('document_id')}, 块索引={doc.metadata.get('chunk_index')}")
            #     logger.info(f"内容预览: {doc.page_content[:200]}...")
            
            # logger.info(f"=== 全文检索结果 (text_results) ===")
            # for i, (doc, score) in enumerate(text_results):
            #     logger.info(f"文本结果 {i+1}: 分数={score:.4f}, 文档ID={doc.metadata.get('document_id')}, 块索引={doc.metadata.get('chunk_index')}")
            #     logger.info(f"内容预览: {doc.page_content[:200]}...")

            # 合并并选择最终文档和来源
            relevant_docs, sources = await self._merge_docs_with_scores(
                content_results,
                text_results,
                question,
                top_k=context_limit,
                min_similarity_score=settings.RAG_MIN_SIMILARITY_SCORE
            )

            # 没有足够相关的文档时，直接走纯 LLM 生成
            if not relevant_docs:
                yield {
                    "type": "start",
                    "question": question,
                    "query_rewrite": {
                        "rewritten_query": rewritten_query,
                        "expanded_keywords": expanded_keywords
                    },
                    "sources": [],
                    "context_used": False,
                    "num_sources": 0
                }

                try:
                    general_chain = self._create_general_chat_chain(conversation_history)
                    async for chunk in general_chain.astream({"question": question}):
                        if isinstance(chunk, str):
                            if chunk.strip():
                                yield {"type": "chunk", "content": chunk}
                        elif isinstance(chunk, dict):
                            if "content" in chunk and chunk["content"].strip():
                                yield {"type": "chunk", "content": chunk["content"]}
                            elif "output" in chunk and chunk["output"].strip():
                                yield {"type": "chunk", "content": chunk["output"]}
                    yield {"type": "end", "complete": True, "sources": [], "num_sources": 0}
                except GeneratorExit:
                    logger.info("客户端断开连接，停止纯LLM流式响应")
                    return
                except Exception as e:
                    logger.error(f"纯LLM流式响应生成错误: {str(e)}")
                    yield {"type": "error", "error": str(e)}
                return

            # 使用来源产生初始数据
            yield {
                "type": "start",
                "question": question,
                "query_rewrite": {
                    "rewritten_query": rewritten_query,
                    "expanded_keywords": expanded_keywords
                },
                "sources": sources,
                "context_used": True,
                "num_sources": len(sources)
            }

            # 使用预检索文档创建RAG链（无额外检索）
            rag_chain = self._create_rag_chain_with_docs(relevant_docs, conversation_history)

            # 流式传输LLM的响应
            try:
                # 使用真正的流式输出
                async for chunk in rag_chain.astream({"question": question}):
                    # 处理不同类型的chunk
                    if isinstance(chunk, str):
                        if chunk.strip():  # 只发送非空字符串
                            yield {"type": "chunk", "content": chunk}
                    elif isinstance(chunk, dict):
                        # 处理字典类型的chunk
                        if "content" in chunk and chunk["content"].strip():
                            yield {"type": "chunk", "content": chunk["content"]}
                        elif "output" in chunk and chunk["output"].strip():
                            yield {"type": "chunk", "content": chunk["output"]}
                    
            except GeneratorExit:
                logger.info("客户端断开连接，停止RAG流式响应")
                return
            except Exception as e:
                logger.error(f"RAG流式响应生成错误: {str(e)}")
                yield {"type": "error", "error": str(e)}

            # 使用来源产生完成信号以供前端显示
            yield {
                "type": "end",
                "complete": True,
                "sources": sources,
                "num_sources": len(sources)
            }

        except Exception as e:
            logger.error(f"流式RAG问答中出错: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }


    async def get_conversation_context(
        self,
        conversation_history: List[Dict[str, str]],
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """
        处理对话历史以获取上下文

        Args:
            conversation_history: 对话消息列表
            max_messages: 要保留的最大消息数

        Returns:
            处理后的对话历史
        """
        if not conversation_history:
            return []

        # 仅保留最后max_messages条消息
        recent_history = conversation_history[-max_messages:]

        # 为LangChain格式化
        formatted_history = []
        for msg in recent_history:
            if msg.get("role") == "user":
                formatted_history.append({"role": "human", "content": msg["content"]})
            elif msg.get("role") == "assistant":
                formatted_history.append({"role": "ai", "content": msg["content"]})

        return formatted_history
