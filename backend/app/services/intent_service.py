"""

意图识别和路由服务：对用户查询进行分类并返回前端路由
    先用关键词做快速分类，无法确定时再调用 LLM 判断意图，然后把 intent映射到具体route。
    主要服务于“用户一句话到底是要问知识库、生成 JD、生成试卷、筛简历还是聊天”等入口分流。
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.kb_selection_service import KBSelectionService

logger = logging.getLogger(__name__)


class IntentService:
    """意图分类和路由服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = None
        
        # 意图到路由的映射
        self.intent_routes = {
            "jd": "/recruitment/jd-generator",
            "resume_screening": "/recruitment/resume-screening",
            "interview_plan": "/recruitment/smart-interview",
            "exam_generate": "/training/exam-generator",
            "email_notification": "/system/email-configs",
            "kb_qa": "/assistant/qa",
        }
        
        # 用于快速意图检测的关键词启发式规则
        self.keywords = [
            ("resume_screening", ["简历筛选", "筛选简历", "简历评分", "评价简历", "上传简历", "候选人筛选", "批量筛选"]),
            ("jd", ["写jd", "生成jd", "职位描述", "岗位职责", "招聘jd", "job description", "JD"]),
            ("email_notification", ["邮件通知", "邮件草稿", "写邮件", "发邮件", "发送邮件", "通知邮件", "邮件邀约", "邀约邮件", "面试邀约", "面试邀请邮件", "考试邀请", "考试邀请邮件", "通知候选人", "offer邮件"]),
            ("exam_generate", ["试卷", "生成试卷", "考试", "题库", "出题", "考试试卷", "自动阅卷"]),
            ("interview_plan", ["面试方案", "面试流程", "面试题", "面试计划", "生成面试", "安排面试"]),
            ("kb_qa", ["知识库", "问答", "根据知识库", "查文档", "文档问答", "QA"]),
        ]

    def classify_intent_fast(self, query: str) -> Optional[str]:
        """
        使用快速关键词匹配进行意图分类
        
        Args:
            query: 用户输入内容
            
        Returns:
            匹配到的意图标签，如果未匹配则返回None
        """
        q = query.lower()
        for intent, words in self.keywords:
            for w in words:
                if w.lower() in q:
                    return intent
        return None

    async def classify_intent_with_llm(self, query: str) -> str:
        """
        使用LLM作为备选方案，在预定义类别中对意图进行分类
        
        Args:
            query: 用户输入内容
            
        Returns:
            分类后的意图标签
        """
        # 约束分类提示，要求返回预定义标签之一
        prompt = (
            "你是HR系统的路由分类器。根据用户输入在以下意图中选择一个，并只返回对应标签：\n"
            "- jd: 生成/撰写职位JD\n"
            "- resume_screening: 上传/筛选/评价/评分候选人简历\n"
            "- interview_plan: 生成面试方案/流程/题目\n"
            "- exam_generate: 生成考试试卷/出题/考试管理\n"
            "- email_notification: 生成候选人邮件通知/面试邀约/考试邀请\n"
            "- kb_qa: 基于知识库的问答/查询文档\n\n"
            f"用户输入：{query}\n\n"
            "输出：仅返回上述六个标签之一，不要解释。"
        )
        
        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            result = await self.llm_service.generate_response(prompt)
            intent = result.strip().lower()
            
            # 清理意图，确保为已知意图
            if intent not in self.intent_routes:
                # 尝试简单的标准化处理
                if "jd" in intent:
                    return "jd"
                if "resume" in intent or "简历" in intent or "候选人" in intent:
                    return "resume_screening"
                if "interview" in intent or "面试" in intent:
                    return "interview_plan"
                if "exam" in intent or "考试" in intent or "试卷" in intent:
                    return "exam_generate"
                if "email" in intent or "mail" in intent or "邮件" in intent or "邀约" in intent:
                    return "email_notification"
                if "kb" in intent or "知识" in intent or "问答" in intent:
                    return "kb_qa"
                # 默认返回知识库问答
                return "kb_qa"
            return intent
        except Exception as e:
            logger.error(f"LLM意图分类失败: {e}")
            # 失败时默认返回知识库问答
            return "kb_qa"

    async def classify_intent(self, query: str) -> str:
        """
        对用户查询进行意图分类，先尝试快速匹配，再使用LLM
        
        Args:
            query: 用户输入内容
            
        Returns:
            分类后的意图标签
        """
        if not query:
            return "kb_qa"

        # 首先尝试快速关键词匹配
        intent = self.classify_intent_fast(query)
        if intent:
            return intent
            
        # 快速匹配失败时使用LLM分类
        return await self.classify_intent_with_llm(query)

    async def get_route_for_intent(self, intent: str, query: str, user_id: UUID) -> Dict[str, Any]:
        """
        根据意图获取路由信息
        
        Args:
            intent: 意图标签
            query: 用户输入内容
            user_id: 用户ID
            
        Returns:
            包含路由和意图信息的字典
        """
        route = self.intent_routes.get(intent, self.intent_routes["kb_qa"])
        
        # 如果是知识库问答，使用KBSelectionService自动选择知识库
        kb_id = None
        if intent == "kb_qa":
            try:
                selector = KBSelectionService(self.db)
                result = await selector.select_kb_for_question(
                    question=query,
                    user_id=user_id,
                    max_candidates=200,
                )
                kb_id = result["knowledge_base_id"]
            except Exception as e:
                logger.error(f"知识库选择失败: {e}")
                kb_id = None

        return {
            "intent": intent,
            "route": route,
            "query": query,
            "kb_id": kb_id
        }

    async def route_query(self, query: str, user_id: UUID) -> Dict[str, Any]:
        """
        对用户查询进行分类并返回完整路由信息
        
        Args:
            query: 用户输入内容
            user_id: 用户ID
            
        Returns:
            包含意图、路由和查询信息的字典
        """
        if not query:
            return await self.get_route_for_intent("kb_qa", query, user_id)
            
        intent = await self.classify_intent(query)
        return await self.get_route_for_intent(intent, query, user_id)
