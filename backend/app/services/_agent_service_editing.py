

from __future__ import annotations

import json
import logging
import hashlib
import os
import re
import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.conversation import Conversation, Message, MessageRole
from app.models.document import Document
from app.models.resume_evaluation import ResumeEvaluation, ResumeStatus
from app.schemas.agent import AgentArtifact, AgentChatResponse, AgentStep
from app.schemas.interview_plan import InterviewPlanCreate
from app.schemas.job_description import JobDescriptionCreate, JobDescriptionUpdate
from app.schemas.scoring_criteria import ScoringCriteriaCreate, ScoringCriteriaUpdate
from app.services.email_service import EmailSendService
from app.services.dify_service import DifyService
from app.services.agent_skills import AgentSkillBundle, AgentSkillDispatcher, build_default_skill_dispatcher
from app.services.exam_service import ExamService
from app.services.interview_plan_service import InterviewPlanService
from app.services.intent_service import IntentService
from app.services.job_description_service import JobDescriptionService
from app.services.kb_selection_service import KBSelectionService
from app.services.llm_service import LLMService
from app.services.resume_evaluation_service import ResumeEvaluationService
from app.services.scoring_criteria_service import ScoringCriteriaService
from app.utils.text_utils import extract_text_content

from app.services._agent_service_types import AgentToolSpec, ReActDecision

logger = logging.getLogger(__name__)

"""
    JD、评分标准编辑及候选人解析.
"""

class _AgentServiceEditingMixin:
    async def _handle_jd_edit(
        self,
        message: str,
        user_id: UUID,
        selected_tool: Optional[AgentToolSpec],
        conversation_id: Optional[str],
        memory_context: str,
    ) -> AgentChatResponse:
        edit_request = await self._parse_jd_edit_request(message, memory_context)
        steps = [
            self._planning_step(selected_tool, "识别到 JD 修改请求，先定位目标 JD。"),
            AgentStep(id="locate_jd", title="定位要修改的 JD", status="running", detail="优先查找当前对话最近生成的 JD。", tool="edit_jd"),
            AgentStep(id="collect_changes", title="确认修改要求", status="pending", detail="拿到明确修改点后再改写。"),
            AgentStep(id="rewrite_jd", title="改写 JD 内容", status="pending", detail="基于原 JD 和修改要求生成新版。"),
            AgentStep(id="save_jd", title="保存修改", status="pending", detail="更新原 JD 记录。"),
        ]

        candidates = await self._resolve_recent_jd_candidates(user_id, conversation_id, edit_request.get("keyword") or "")
        if not candidates:
            steps[1] = steps[1].model_copy(update={"status": "failed", "detail": "没有找到可修改的 JD。"})
            return AgentChatResponse(
                message="我还没有找到可以修改的 JD。请先生成或保存一个 JD，或者明确告诉我要修改哪个岗位的 JD。",
                intent="jd_edit",
                route="/recruitment/jd-generator",
                steps=steps,
                artifacts=[],
                suggestions=["生成一个新的 JD", "说明要修改的岗位名称", "去 JD 管理查看职位"],
            )

        if len(candidates) > 1 and edit_request.get("keyword"):
            matches = self._match_delete_resources(candidates, edit_request.get("keyword") or "")
            if matches:
                candidates = matches

        if len(candidates) > 1:
            steps[1] = steps[1].model_copy(update={"status": "running", "detail": f"找到 {len(candidates)} 个可能的 JD，需要确认。"})
            return AgentChatResponse(
                message=(
                    "我找到了多个可能要修改的 JD。为避免改错，请告诉我具体是哪一个：\n"
                    + "\n".join(f"- {self._format_jd_candidate_label(item)}" for item in candidates[:5])
                ),
                intent="jd_edit",
                route="/recruitment/jd-generator",
                steps=steps,
                artifacts=[
                    AgentArtifact(
                        type="jd_edit_candidates",
                        title="待确认 JD",
                        content={"candidates": candidates[:5]},
                    )
                ],
                suggestions=["修改最新的那个 JD", "说明岗位名称", "去 JD 管理查看职位"],
            )

        target = candidates[0]
        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": f"已定位：{target.get('name') or '最近的 JD'}。"})

        edit_instructions = self._clean_optional_value(edit_request.get("changes"))
        if not edit_instructions:
            steps[2] = steps[2].model_copy(update={"status": "pending", "detail": "等待用户说明要修改哪些内容。"})
            return AgentChatResponse(
                message=f"可以，我找到了「{target.get('name') or '最近的 JD'}」。你想具体改哪些内容？比如薪资、地点、职责、技能要求或福利。",
                intent="jd_edit",
                route="/recruitment/jd-generator",
                steps=steps,
                artifacts=[
                    AgentArtifact(
                        type="jd_edit_request",
                        title="等待修改要求",
                        content={"job_description_id": target.get("id"), "title": target.get("name")},
                    )
                ],
                suggestions=["薪资改成 20-30K", "增加 React 和性能优化要求", "把工作地点改成长沙"],
            )

        steps[2] = steps[2].model_copy(update={"status": "completed", "detail": edit_instructions})
        try:
            service = JobDescriptionService(self.db)
            original_jd = await service.get_job_description(str(target["id"]), user_id)
            original_data = original_jd.model_dump(mode="json")
            original_content = original_data.get("content") or ""
            steps[3] = steps[3].model_copy(update={"status": "running", "detail": "正在生成修改后的 JD。"})
            updated_content = await self._rewrite_jd_content(original_content, edit_instructions)
            steps[3] = steps[3].model_copy(update={"status": "completed", "detail": "已生成修改后的 JD。"})

            update_data = self._build_jd_update_payload(original_data, updated_content, edit_instructions, edit_request)
            steps[4] = steps[4].model_copy(update={"status": "running", "detail": "正在保存到原 JD。"})
            updated_jd = await service.update_job_description(str(target["id"]), update_data, user_id)
            steps[4] = steps[4].model_copy(update={"status": "completed", "detail": f"已更新 JD：{updated_jd.id}"})
        except Exception as exc:
            logger.warning("Agent 修改 JD 失败: %s", exc, exc_info=True)
            steps[4] = steps[4].model_copy(update={"status": "failed", "detail": str(exc)})
            return AgentChatResponse(
                message=f"我找到了 JD，但保存修改时失败了：{str(exc)}",
                intent="jd_edit",
                route="/recruitment/jd-generator",
                steps=steps,
                artifacts=[],
                suggestions=["稍后重试", "去 JD 管理手动编辑", "重新生成 JD"],
            )

        return AgentChatResponse(
            message=f"已按你的要求更新「{updated_jd.title}」。",
            intent="jd_edit",
            route="/recruitment/jd-generator",
            steps=steps,
            artifacts=[
                AgentArtifact(
                    type="job_description",
                    title=f"{updated_jd.title} JD",
                    content=updated_jd.content,
                    metadata={
                        "job_title": updated_jd.title,
                        "saved_jd_id": str(updated_jd.id),
                        "edit_instructions": edit_instructions,
                        "route": "/recruitment/jd-generator",
                    },
                )
            ],
            suggestions=["继续修改 JD", "基于这个 JD 筛选简历", "去 JD 管理查看职位"],
        )

    async def _handle_criteria_edit(
        self,
        message: str,
        user_id: UUID,
        selected_tool: Optional[AgentToolSpec],
        conversation_id: Optional[str],
        memory_context: str,
    ) -> AgentChatResponse:
        final_response = None
        async for event in self._stream_criteria_edit_response(message, user_id, conversation_id, memory_context):
            if event.get("type") == "final" and event.get("response"):
                final_response = AgentChatResponse.model_validate(event["response"])
        if final_response:
            return final_response
        return AgentChatResponse(
            message="评分标准修改没有返回结果，请稍后重试。",
            intent="criteria_edit",
            route="/recruitment/resume-screening",
            steps=[self._planning_step(selected_tool, "评分标准修改流程未返回最终结果。")],
            suggestions=["稍后重试", "重新生成评分标准"],
        )

    async def _parse_jd_edit_request(self, message: str, memory_context: str = "") -> Dict[str, Any]:
        prompt = (
            "你是 HR Agent 的 JD 修改请求解析器。请严格返回 JSON，不要解释。\n"
            "字段：keyword, changes, title, department, location, salary_range, experience_level, education, job_type, skills。\n"
            "keyword 填用户用于定位 JD 的岗位名、地点、薪资、ID短码或序号，例如“前端”“AI产品经理”“长沙”“15K”“第一个”；没有则返回 null。\n"
            "changes 填用户明确提出的修改要求；如果用户只是说“帮我改改上次那个JD”但没有说明改什么，返回 null。\n"
            "如果用户明确要求修改薪资、地点、经验、学历、职位名称、部门、工作类型或技能，请同步填入对应结构化字段；未提到返回 null，skills 未提到返回 null。\n"
            "如果上一轮助手已经询问“你想具体改哪些内容”，当前用户消息通常就是 changes。\n"
            f"{self._format_memory_for_prompt(memory_context)}"
            f"当前用户消息：{message}\n"
            "返回格式：{\"keyword\":null,\"changes\":null,\"title\":null,\"department\":null,\"location\":null,\"salary_range\":null,\"experience_level\":null,\"education\":null,\"job_type\":null,\"skills\":null}"
        )
        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            response = await self.llm_service.generate_response(prompt)
            parsed = self._safe_json_loads(response)
            changes = self._clean_optional_value(parsed.get("changes"))
            if changes and self._is_generic_jd_edit_request(changes):
                changes = None
            if not changes and self._is_jd_edit_followup(message, memory_context):
                changes = message.strip()
            return {
                "keyword": self._clean_optional_value(parsed.get("keyword")),
                "changes": changes,
                "title": self._clean_optional_value(parsed.get("title")),
                "department": self._clean_optional_value(parsed.get("department")),
                "location": self._clean_optional_value(parsed.get("location")),
                "salary_range": self._clean_optional_value(parsed.get("salary_range")),
                "experience_level": self._clean_optional_value(parsed.get("experience_level")),
                "education": self._clean_optional_value(parsed.get("education")),
                "job_type": self._clean_optional_value(parsed.get("job_type")),
                "skills": self._normalize_optional_list(parsed.get("skills")),
                "source": "llm",
            }
        except Exception as exc:
            logger.warning("JD 修改请求解析失败，使用规则兜底: %s", exc)
        return self._fallback_parse_jd_edit_request(message, memory_context)

    def _fallback_parse_jd_edit_request(self, message: str, memory_context: str = "") -> Dict[str, Any]:
        keyword = None
        title_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9+#]+(?:开发|测试|算法|产品|运营|销售|人事|财务|行政)?(?:工程师|经理|专员|主管|顾问|设计师|架构师))", message)
        if title_match:
            keyword = title_match.group(1)
        if not keyword:
            ordinal_match = re.search(r"(第[一二三四五六七八九十1-9]\s*个|第[一二三四五六七八九十1-9]\s*条|最新|最近|上一个|最后一个)", message)
            if ordinal_match:
                keyword = ordinal_match.group(1)
        if not keyword:
            for city in ["北京", "上海", "深圳", "广州", "杭州", "南京", "成都", "重庆", "苏州", "武汉", "西安", "长沙", "济南"]:
                if city in message:
                    keyword = city
                    break
        if not keyword:
            salary_match = re.search(r"\d+(?:\.\d+)?\s*[kK万]?", message)
            if salary_match:
                keyword = salary_match.group(0).replace(" ", "")
        changes = re.sub(r"请|帮我|麻烦|一下|上次|刚才|刚刚|这个|这份|这条|那个|JD|jd|职位描述|岗位说明书", "", message)
        changes = re.sub(r"改改|修改|调整|优化|更新|编辑|润色", "", changes).strip(" ，,。")
        if changes and self._is_generic_jd_edit_request(changes):
            changes = ""
        if not changes and self._is_jd_edit_followup(message, memory_context):
            changes = message.strip()
        return {
            "keyword": keyword,
            "changes": changes or None,
            **self._fallback_parse_jd_edit_fields(message),
            "source": "fallback",
        }

    async def _parse_criteria_edit_request(self, message: str, memory_context: str = "") -> Dict[str, Any]:
        prompt = (
            "你是 HR Agent 的评分标准修改请求解析器。请严格返回 JSON，不要解释。\n"
            "字段：keyword, changes。\n"
            "keyword 填用户用于定位评分标准的岗位名或关键词，例如“前端”“AI产品经理”；没有则返回 null。\n"
            "changes 填用户明确提出的评分标准修改要求；如果用户只是说“帮我改改评分标准”但没有说明改什么，返回 null。\n"
            "如果上一轮助手已经询问“你想具体改哪些评分规则”，当前用户消息通常就是 changes。\n"
            f"{self._format_memory_for_prompt(memory_context)}"
            f"当前用户消息：{message}\n"
            "返回格式：{\"keyword\":null,\"changes\":null}"
        )
        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            response = await self.llm_service.generate_response(prompt)
            parsed = self._safe_json_loads(response)
            changes = self._clean_optional_value(parsed.get("changes"))
            if changes and self._is_generic_criteria_edit_request(changes):
                changes = None
            if not changes and self._is_criteria_edit_followup(message, memory_context):
                changes = message.strip()
            return {
                "keyword": self._clean_optional_value(parsed.get("keyword")),
                "changes": changes,
                "source": "llm",
            }
        except Exception as exc:
            logger.warning("评分标准修改请求解析失败，使用规则兜底: %s", exc)
        return self._fallback_parse_criteria_edit_request(message, memory_context)

    def _fallback_parse_criteria_edit_request(self, message: str, memory_context: str = "") -> Dict[str, Any]:
        keyword = None
        title_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9+#]+(?:开发|测试|算法|产品|运营|销售|人事|财务|行政)?(?:工程师|经理|专员|主管|顾问|设计师|架构师))", message)
        if title_match:
            keyword = title_match.group(1)
        changes = re.sub(r"请|帮我|麻烦|一下|上次|刚才|刚刚|这个|这份|这条|那个|评分标准|评分规则|打分标准|筛选标准|简历评分", "", message)
        changes = re.sub(r"改改|修改|调整|优化|更新|编辑|润色", "", changes).strip(" ，,。")
        if changes and self._is_generic_criteria_edit_request(changes):
            changes = ""
        if not changes and self._is_criteria_edit_followup(message, memory_context):
            changes = message.strip()
        return {
            "keyword": keyword,
            "changes": changes or None,
            "source": "fallback",
        }

    def _fallback_parse_jd_edit_fields(self, message: str) -> Dict[str, Any]:
        salary_match = re.search(r"(\d+(?:\.\d+)?\s*[kK万]?)(?:\s*[-~到至]\s*(\d+(?:\.\d+)?\s*[kK万]?))?", message)
        salary = None
        if salary_match and re.search(r"薪资|工资|月薪|待遇|年薪|薪酬|package", message, re.I):
            salary = salary_match.group(0).replace(" ", "")
        location = None
        for city in ["北京", "上海", "深圳", "广州", "杭州", "南京", "成都", "重庆", "苏州", "武汉", "西安", "长沙", "济南"]:
            if city in message and re.search(r"地点|城市|工作地|base|改成|改为|换成", message, re.I):
                location = city
                break
        experience = None
        experience_match = re.search(r"经验(?:改成|改为|换成)?\s*(不限|\d+\s*-\s*\d+年|\d+年以上|\d+年\+?)|工作经验(?:改成|改为|换成)?\s*(不限|\d+\s*-\s*\d+年|\d+年以上|\d+年\+?)", message)
        if experience_match:
            experience = next((group for group in experience_match.groups() if group), experience_match.group(0))
        education = None
        education_match = re.search(r"学历(?:改成|改为|换成)?\s*(不限|大专|专科|本科|硕士|博士)|(?:不限|大专|专科|本科|硕士|博士)(?:及以上)?", message)
        if education_match and re.search(r"学历|大专|专科|本科|硕士|博士", message):
            education = education_match.group(1) or education_match.group(0)
        skill_candidates = ["Java", "Python", "Go", "Vue", "React", "TypeScript", "JavaScript", "Spring", "MySQL", "Redis", "Docker", "Kubernetes", "AI", "大模型"]
        skills = [skill for skill in skill_candidates if skill.lower() in message.lower()]
        return {
            "title": None,
            "department": None,
            "location": location,
            "salary_range": salary,
            "experience_level": experience,
            "education": education,
            "job_type": None,
            "skills": skills or None,
        }

    async def _resolve_recent_jd_candidates(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        keyword: str = "",
    ) -> List[Dict[str, Any]]:
        pending_target = await self._recent_pending_jd_edit_target(user_id, conversation_id)
        if pending_target and not keyword:
            return [pending_target]

        context_matches = await self._recent_generated_resources("jd", user_id, conversation_id, limit=20)
        pending_candidates = await self._recent_pending_jd_edit_candidates(user_id, conversation_id)
        if pending_candidates and keyword:
            selected = self._match_jd_selection_candidates(pending_candidates, keyword)
            if selected:
                return selected

        resources = await self._list_deletable_resources("jd", user_id, keyword)
        if not resources:
            if keyword and context_matches:
                return self._match_delete_resources(context_matches, keyword)
            return context_matches[:1] if context_matches else []
        if keyword:
            matched = [
                *self._match_delete_resources(context_matches, keyword),
                *self._match_delete_resources(resources, keyword),
            ]
            matched = self._dedupe_candidates_by_id(matched)
            return matched or resources[:5]
        if context_matches:
            return context_matches[:1]
        return resources[:1]

    def _dedupe_candidates_by_id(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_key: Dict[str, Dict[str, Any]] = {}
        ordered_keys: List[str] = []
        for item in candidates:
            item_id = item.get("id")
            key = str(item_id) if item_id else self._normalize_candidate_match_text(item.get("name"))
            if not key:
                continue
            if key not in by_key:
                ordered_keys.append(key)
                by_key[key] = item
                continue
            by_key[key] = self._merge_candidate_details(by_key[key], item)
        return [by_key[key] for key in ordered_keys]

    def _merge_candidate_details(self, primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**primary}
        for key, value in secondary.items():
            if value and not merged.get(key):
                merged[key] = value
        if self._candidate_detail_score(secondary) > self._candidate_detail_score(primary):
            merged = {**secondary, **merged}
        return merged

    def _candidate_detail_score(self, item: Dict[str, Any]) -> int:
        return sum(1 for key in ["location", "salary_range", "salary", "experience_level", "updated_at"] if item.get(key))

    async def _recent_pending_jd_edit_candidates(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        conditions = [
            Conversation.user_id == user_id,
            Message.role == MessageRole.ASSISTANT,
        ]
        if conversation_id:
            try:
                conditions.append(Message.conversation_id == UUID(str(conversation_id)))
            except Exception:
                logger.warning("JD 候选上下文收到非法 conversation_id: %s", conversation_id)
                return []
        query = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(*conditions)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        for message in result.scalars().all():
            response = (message.context or {}).get("agent_response") if isinstance(message.context, dict) else None
            if not isinstance(response, dict):
                continue
            for artifact in response.get("artifacts") or []:
                if artifact.get("type") != "jd_edit_candidates":
                    continue
                content = artifact.get("content") if isinstance(artifact.get("content"), dict) else {}
                candidates = content.get("candidates") if isinstance(content.get("candidates"), list) else []
                return [item for item in candidates if isinstance(item, dict) and item.get("id")]
        return []

    def _match_jd_selection_candidates(
        self,
        candidates: List[Dict[str, Any]],
        keyword: str,
    ) -> List[Dict[str, Any]]:
        ordinal = self._parse_selection_ordinal(keyword)
        if ordinal is not None and 0 <= ordinal < len(candidates):
            return [candidates[ordinal]]
        if re.search(r"最新|最近|上一个|最后", keyword):
            return candidates[:1]
        return self._match_delete_resources(candidates, keyword)

    def _parse_selection_ordinal(self, text: str) -> Optional[int]:
        match = re.search(r"第\s*([一二三四五六七八九十1-9])\s*(?:个|条)?", text)
        if not match:
            return None
        value = match.group(1)
        chinese_numbers = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        number = int(value) if value.isdigit() else chinese_numbers.get(value)
        return number - 1 if number else None

    def _format_jd_candidate_label(self, item: Dict[str, Any]) -> str:
        name = item.get("name") or "未命名 JD"
        details = [
            item.get("location"),
            item.get("salary_range") or item.get("salary"),
            item.get("experience_level"),
        ]
        if item.get("updated_at"):
            details.append(f"更新于 {str(item['updated_at'])[:10]}")
        if item.get("id"):
            details.append(f"ID {str(item['id'])[:8]}")
        detail_text = " / ".join(str(value) for value in details if value)
        return f"{name}（{detail_text}）" if detail_text else name

    async def _recent_pending_criteria_edit_target(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        limit: int = 8,
    ) -> Optional[Dict[str, Any]]:
        conditions = [
            Conversation.user_id == user_id,
            Message.role == MessageRole.ASSISTANT,
        ]
        if conversation_id:
            try:
                conditions.append(Message.conversation_id == UUID(str(conversation_id)))
            except Exception:
                logger.warning("评分标准修改上下文收到非法 conversation_id: %s", conversation_id)
                return None
        query = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(*conditions)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        for message in result.scalars().all():
            response = (message.context or {}).get("agent_response") if isinstance(message.context, dict) else None
            if not isinstance(response, dict):
                continue
            for artifact in response.get("artifacts") or []:
                if artifact.get("type") != "criteria_edit_request":
                    continue
                content = artifact.get("content") if isinstance(artifact.get("content"), dict) else {}
                criteria_id = content.get("criteria_id")
                if not criteria_id:
                    continue
                title = content.get("title") or artifact.get("title") or "待修改的评分标准"
                return {
                    "id": str(criteria_id),
                    "name": title,
                    "search_text": title,
                    "source": "pending_criteria_edit_context",
                }
        return None

    async def _recent_pending_jd_edit_target(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        limit: int = 8,
    ) -> Optional[Dict[str, Any]]:
        conditions = [
            Conversation.user_id == user_id,
            Message.role == MessageRole.ASSISTANT,
        ]
        if conversation_id:
            try:
                conditions.append(Message.conversation_id == UUID(str(conversation_id)))
            except Exception:
                logger.warning("JD 修改上下文收到非法 conversation_id: %s", conversation_id)
                return None
        query = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(*conditions)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        for message in result.scalars().all():
            response = (message.context or {}).get("agent_response") if isinstance(message.context, dict) else None
            if not isinstance(response, dict):
                continue
            for artifact in response.get("artifacts") or []:
                if artifact.get("type") != "jd_edit_request":
                    continue
                content = artifact.get("content") if isinstance(artifact.get("content"), dict) else {}
                jd_id = content.get("job_description_id")
                if not jd_id:
                    continue
                title = content.get("title") or artifact.get("title") or "待修改的 JD"
                return {
                    "id": str(jd_id),
                    "name": title,
                    "search_text": title,
                    "source": "pending_jd_edit_context",
                }
        return None

    async def _resolve_recent_criteria_candidates(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        keyword: str = "",
    ) -> List[Dict[str, Any]]:
        pending_target = await self._recent_pending_criteria_edit_target(user_id, conversation_id)
        if pending_target and not keyword:
            return [pending_target]

        context_matches = await self._recent_generated_resources("criteria", user_id, conversation_id, limit=20)
        if context_matches:
            if keyword:
                matched = self._match_delete_resources(context_matches, keyword)
                if matched:
                    return matched
            else:
                return context_matches[:1]

        try:
            result = await ScoringCriteriaService(self.db).get_scoring_criteria_list(user_id=user_id, page=1, size=100)
            resources = [
                {
                    "id": str(item.id),
                    "name": item.title or item.job_title or "未命名评分标准",
                    "search_text": self._resource_search_text({
                        "title": item.title,
                        "job_title": item.job_title,
                        "content": item.content,
                    }),
                    "job_description_id": str(item.job_description_id) if item.job_description_id else None,
                    "created_at": str(item.created_at) if item.created_at else "",
                    "updated_at": str(item.updated_at) if item.updated_at else "",
                }
                for item in result.items
            ]
        except Exception as exc:
            logger.warning("读取评分标准列表失败: %s", exc)
            resources = []
        if not resources:
            return []
        if keyword:
            matched = self._match_delete_resources(resources, keyword)
            return self._collapse_criteria_candidates(matched) if matched else resources[:1]
        return resources[:1]

    def _collapse_criteria_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(candidates) <= 1:
            return candidates
        sorted_candidates = sorted(
            candidates,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        by_jd: Dict[str, Dict[str, Any]] = {}
        without_jd: List[Dict[str, Any]] = []
        for item in sorted_candidates:
            jd_id = item.get("job_description_id")
            if jd_id:
                by_jd.setdefault(str(jd_id), item)
            else:
                without_jd.append(item)
        collapsed = [*by_jd.values(), *without_jd]
        if len(collapsed) > 1:
            normalized_names = {self._normalize_candidate_match_text(item.get("name")) for item in collapsed}
            if len(normalized_names) == 1:
                return [collapsed[0]]
        return collapsed

    async def _rewrite_jd_content(self, original_content: str, edit_instructions: str) -> str:
        prompt = (
            "你是专业招聘 JD 编辑器。请在保留原 JD 结构和没有被要求修改的信息的前提下，"
            "只根据用户修改要求输出修改后的完整 JD 正文。\n"
            "不要输出解释、差异说明或 Markdown 代码块。\n\n"
            f"原 JD：\n{original_content}\n\n"
            f"用户修改要求：\n{edit_instructions}"
        )
        if self.llm_service is None:
            self.llm_service = LLMService()
        response = await self.llm_service.generate_response(prompt)
        updated = str(response or "").strip()
        if not updated:
            raise ValueError("大模型没有返回修改后的 JD")
        return updated

    async def _rewrite_criteria_content(self, original_content: str, edit_instructions: str) -> str:
        prompt = (
            "你是专业简历评分标准编辑器。请在保留原评分标准结构和未被要求修改的信息的前提下，"
            "只根据用户修改要求输出修改后的完整评分标准正文。\n"
            "如果涉及分值调整，请保持总分口径清晰，并同步调整相关维度描述，避免分值前后矛盾。\n"
            "不要输出解释、差异说明或 Markdown 代码块。\n\n"
            f"原评分标准：\n{original_content}\n\n"
            f"用户修改要求：\n{edit_instructions}"
        )
        if self.llm_service is None:
            self.llm_service = LLMService()
        response = await self.llm_service.generate_response(prompt)
        updated = str(response or "").strip()
        if not updated:
            raise ValueError("大模型没有返回修改后的评分标准")
        return updated

    def _build_jd_update_payload(
        self,
        original_data: Dict[str, Any],
        updated_content: str,
        edit_instructions: str,
        edit_request: Optional[Dict[str, Any]] = None,
    ) -> JobDescriptionUpdate:
        edit_request = edit_request or {}
        meta_data = original_data.get("meta_data") if isinstance(original_data.get("meta_data"), dict) else {}
        edit_history = list(meta_data.get("edit_history") or [])
        edit_history.append({"source": "hr_agent", "instruction": edit_instructions})
        meta_data = {**meta_data, "last_edit_source": "hr_agent", "edit_history": edit_history[-10:]}
        if edit_request.get("salary_range"):
            meta_data["salary"] = edit_request["salary_range"]
        if edit_request.get("location"):
            meta_data["location"] = edit_request["location"]
        return JobDescriptionUpdate(
            title=edit_request.get("title") or original_data.get("title"),
            department=edit_request.get("department") or original_data.get("department"),
            location=edit_request.get("location") or original_data.get("location"),
            salary_range=edit_request.get("salary_range") or original_data.get("salary_range"),
            experience_level=edit_request.get("experience_level") or original_data.get("experience_level"),
            education=edit_request.get("education") or original_data.get("education"),
            job_type=edit_request.get("job_type") or original_data.get("job_type"),
            skills=edit_request.get("skills") or original_data.get("skills"),
            content=updated_content,
            requirements=original_data.get("requirements"),
            status=original_data.get("status"),
            meta_data=meta_data,
        )

    def _build_criteria_update_payload(
        self,
        original_data: Dict[str, Any],
        updated_content: str,
        edit_instructions: str,
    ) -> ScoringCriteriaUpdate:
        meta_data = original_data.get("meta_data") if isinstance(original_data.get("meta_data"), dict) else {}
        edit_history = list(meta_data.get("edit_history") or [])
        edit_history.append({"source": "hr_agent", "instruction": edit_instructions})
        meta_data = {**meta_data, "last_edit_source": "hr_agent", "edit_history": edit_history[-10:]}
        return ScoringCriteriaUpdate(
            title=original_data.get("title"),
            job_title=original_data.get("job_title"),
            content=updated_content,
            criteria_data=original_data.get("criteria_data"),
            total_score=original_data.get("total_score"),
            scoring_dimensions=original_data.get("scoring_dimensions"),
            status=original_data.get("status"),
            meta_data=meta_data,
            job_description_id=original_data.get("job_description_id"),
        )

    async def _resolve_interview_exam_followup(
        self,
        message: str,
        user_id: UUID,
        conversation_id: Optional[str],
    ) -> Dict[str, Any]:
        if not self._is_followup_interview_exam_request(message):
            return {"matched": False}
        matches = await self._recent_generated_resources("interview", user_id, conversation_id, limit=20)
        if not matches:
            return {"matched": False}
        latest = matches[0]
        content = latest.get("content") or ""
        return {
            "matched": True,
            "plan_id": latest.get("id"),
            "title": latest.get("name") or "最近生成的面试方案",
            "content": content,
            "message": f"{message}\n\n当前面试方案上下文：\n{content[:2500]}",
        }
