"""
知识库自动选择服务：
    先列出用户可用文档候选，再让 LLM 根据用户问题选择最匹配的文档/知识库，
    最终返回合适的 knowledge_base_id。适合用户没有手动指定知识库时自动路由问题。
"""
import logging
import json
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.lightweight_document_service import LightweightDocumentService

# 配置日志记录
logger = logging.getLogger(__name__)


class KBSelectionService:
    """通过LLM对文档进行排名来自动选择知识库的服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()
        self.document_service = LightweightDocumentService(db)

    async def list_candidates(
        self,
        user_id: UUID,
        max_candidates: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出用户的候选文档（id、filename、knowledge_base_id）。
        限制max_candidates以控制token使用量。
        """
        try:
            documents = await self.document_service.get_user_documents(
                user_id=user_id,
                skip=0,
                limit=max_candidates,
            )
            candidates: List[Dict[str, Any]] = []
            for doc in documents:
                candidates.append({
                    "document_id": str(doc.id),
                    "filename": doc.filename,
                    "knowledge_base_id": str(doc.knowledge_base_id) if doc.knowledge_base_id else None,
                })
            return candidates
        except Exception as e:
            logger.error(f"Error listing candidate documents: {e}")
            raise

    async def select_best_document(
        self,
        question: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """使用LLM从候选文档中选择最佳匹配文档。
        返回包含键的字典：document_id、confidence、reason（可选）。
        """
        if not candidates:
            return None

        # 准备紧凑的候选列表以最小化token使用
        # 仅传递filename和document_id（如果需要下游映射，可包含kb id）
        compact = [
            {
                "document_id": c.get("document_id"),
                "filename": c.get("filename"),
            }
            for c in candidates
        ]

        system_prompt = (
            "You are an expert selector. Given a user question and a list of documents "
            "(each with document_id and filename), choose the single most relevant document. "
            "Respond ONLY with valid JSON: {\"document_id\": string, \"confidence\": number, \"reason\": string}. "
            "Confidence is in [0,1]. No extra commentary."
        )
        user_message = (
            "Question: " + question + "\n\n" +
            "Documents: " + json.dumps(compact, ensure_ascii=False)
        )

        try:
            # 使用确定性选择
            response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0,
                max_tokens=400,
            )
            content = response.choices[0].message.content.strip()
            # 尝试解析JSON
            selected: Dict[str, Any] = json.loads(content)
            # 基本验证
            if not isinstance(selected, dict) or "document_id" not in selected:
                logger.warning(f"Invalid LLM selection output: {content}")
                return None
            return selected
        except Exception as e:
            logger.error(f"Error selecting best document via LLM: {e}")
            return None

    async def select_kb_for_question(
        self,
        question: str,
        user_id: UUID,
        max_candidates: int = 100,
    ) -> Dict[str, Any]:
        """高级方法：列出候选文档，请求LLM选择最佳文档，返回知识库ID。
        返回：{ knowledge_base_id, document_id, filename, confidence, reason, candidates_count }
        """
        candidates = await self.list_candidates(user_id=user_id, max_candidates=max_candidates)
        selection = await self.select_best_document(question=question, candidates=candidates)

        if not selection:
            return {
                "knowledge_base_id": None,
                "document_id": None,
                "filename": None,
                "confidence": 0.0,
                "reason": "No selection or no candidates",
                "candidates_count": len(candidates),
            }

        selected_doc_id = selection.get("document_id")
        confidence = selection.get("confidence", 0.0)
        reason = selection.get("reason", "")

        # 查找选中的候选文档以获取知识库ID和文件名
        selected_candidate = next((c for c in candidates if c["document_id"] == selected_doc_id), None)
        if not selected_candidate:
            return {
                "knowledge_base_id": None,
                "document_id": selected_doc_id,
                "filename": None,
                "confidence": confidence,
                "reason": reason or "Selected document not in candidate list",
                "candidates_count": len(candidates),
            }

        return {
            "knowledge_base_id": selected_candidate.get("knowledge_base_id"),
            "document_id": selected_doc_id,
            "filename": selected_candidate.get("filename"),
            "confidence": confidence,
            "reason": reason,
            "candidates_count": len(candidates),
        }