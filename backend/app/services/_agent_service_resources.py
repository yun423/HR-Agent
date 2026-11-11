

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
    资源管理、内容生成和数据规范化.
"""

class _AgentServiceResourcesMixin:

    async def _handle_resource_delete(
        self,
        message: str,
        user_id: UUID,
        selected_tool: Optional[AgentToolSpec],
        conversation_id: Optional[str] = None,
    ) -> AgentChatResponse:
        """
        资源删除的流程是：
            1._parse_delete_request() 用 LLM 解析删除目标。
            2.解析失败时 _fallback_parse_delete_request() 用正则兜底。
            3.如果用户说“删除刚才那个”“删除最新的”，会先查最近对话上下文。
            4.如果没有上下文，就从对应业务列表查询可删除资源。
            5.如果匹配多个，要求用户说得更具体。
            6.如果唯一匹配，调用 _delete_resource_by_type()  执行删除。

            这里比较关键的是 _recent_generated_resources() ：
                会从历史 assistant 消息的 context.agent_response.artifacts 里找最近生成的产物，因此才能理解“刚才那个”。
        """

        delete_request = await self._parse_delete_request(message)
        resource_type = delete_request.get("type")
        keyword = delete_request.get("keyword") or ""
        if (
            resource_type == "resume"
            and not delete_request.get("confirm_context_low_scores")
            and re.search(r"低分|不合格|小于\s*60|低于\s*60|没通过|未通过", message)
        ):
            followup_action = await self._resolve_resume_screening_followup_action(message, user_id, conversation_id)
            if followup_action.get("action") == "confirm_delete_low_scores":
                return self._build_resume_screening_followup_response(
                    followup_action,
                    "/recruitment/resume-screening",
                    selected_tool,
                )
        if resource_type == "resume" and delete_request.get("confirm_context_low_scores"):
            low_score_matches = await self._recent_low_score_resume_resources(user_id, conversation_id)
            if not low_score_matches:
                return AgentChatResponse(
                    message="我没有在当前对话最近的评分结果里找到低分候选人，因此没有执行删除。你可以先完成简历评分，或明确说出候选人姓名。",
                    intent="resource_delete",
                    route="/recruitment/resume-screening",
                    steps=[
                        self._planning_step(selected_tool, "识别到确认删除低分候选人的请求。"),
                        AgentStep(id="locate_resource", title="定位低分候选人", status="failed", detail="没有找到可删除的低分候选人。"),
                    ],
                    suggestions=["先评分简历", "说出候选人姓名", "查看简历筛选列表"],
                )
            steps = [
                self._planning_step(selected_tool, "用户确认删除最近评分中的低分候选人。"),
                AgentStep(id="locate_resource", title="定位低分候选人", status="completed", detail=f"匹配到 {len(low_score_matches)} 位低分候选人。"),
                AgentStep(id="delete_resource", title="执行删除操作", status="running", detail="正在删除低分简历记录。"),
            ]
            return await self._delete_matched_resources(
                resource_type="resume",
                matches=low_score_matches,
                user_id=user_id,
                steps=steps,
                keyword="低分候选人",
                matched_from_context=True,
            )
        context_first = bool(delete_request.get("context_reference")) and not keyword
        steps = [
            self._planning_step(selected_tool, "识别到删除类请求，准备定位目标资源。"),
            AgentStep(
                id="locate_resource",
                title="定位删除目标",
                status="running",
                detail=self._delete_target_detail(resource_type, keyword),
                tool="delete_resource",
            ),
            AgentStep(id="delete_resource", title="执行删除操作", status="pending", detail="匹配到唯一目标后执行删除。"),
        ]
        if not resource_type:
            steps[1] = steps[1].model_copy(update={"status": "failed", "detail": "缺少要删除的资源类型。"})
            return AgentChatResponse(
                message="我还不确定你要删除哪类内容。请明确说明要删除 JD、简历记录、面试方案还是试卷，例如：帮我删除产品经理的 JD。",
                intent="resource_delete",
                route=None,
                steps=steps,
                artifacts=[],
                suggestions=["删除产品经理的 JD", "删除张三的简历记录", "删除 Java 试卷"],
            )

        if context_first:
            context_matches = await self._recent_generated_resources(resource_type, user_id, conversation_id)
            if context_matches:
                matches = context_matches if delete_request.get("delete_all") else context_matches[:1]
                return await self._delete_matched_resources(
                    resource_type=resource_type,
                    matches=matches,
                    user_id=user_id,
                    steps=steps,
                    keyword=keyword,
                    matched_from_context=True,
                )

        resources = await self._list_deletable_resources(resource_type, user_id, keyword)
        matches = self._match_delete_resources(resources, keyword, delete_request.get("latest"))
        if not matches:
            steps[1] = steps[1].model_copy(update={"status": "failed", "detail": "没有找到匹配资源。"})
            return AgentChatResponse(
                message=f"没有找到匹配的{self._resource_type_label(resource_type)}。你可以换个名称再试，或先到对应列表确认名称。",
                intent="resource_delete",
                route=self._resource_type_route(resource_type),
                steps=steps,
                artifacts=[
                    AgentArtifact(
                        type="delete_resource_result",
                        title="删除结果",
                        content={"resource_type": resource_type, "keyword": keyword, "deleted": [], "matches": []},
                    )
                ],
                suggestions=self._delete_suggestions(resource_type),
            )

        if len(matches) > 1 and not delete_request.get("delete_all"):
            steps[1] = steps[1].model_copy(update={"status": "running", "detail": f"找到 {len(matches)} 个匹配项，需要用户确认。"})
            return AgentChatResponse(
                message=(
                    f"我找到了 {len(matches)} 个匹配的{self._resource_type_label(resource_type)}，为避免误删，请说得更具体一点：\n"
                    + "\n".join(f"- {item['name']}" for item in matches[:8])
                ),
                intent="resource_delete",
                route=self._resource_type_route(resource_type),
                steps=steps,
                artifacts=[
                    AgentArtifact(
                        type="delete_resource_candidates",
                        title="待确认删除目标",
                        content={"resource_type": resource_type, "keyword": keyword, "candidates": matches[:8]},
                    )
                ],
                suggestions=["补充更完整的名称", "说“删除最新的那个”", "到列表中确认后再删除"],
            )

        return await self._delete_matched_resources(
            resource_type=resource_type,
            matches=matches,
            user_id=user_id,
            steps=steps,
            keyword=keyword,
            matched_from_context=False,
        )

    async def _parse_delete_request(self, message: str) -> Dict[str, Any]:
        prompt = (
            "你是 HR Agent 的删除请求解析器。请从用户消息中识别要删除的招聘资源，并严格返回 JSON，不要解释。\n"
            "resource_type 只能是 jd、resume、interview、exam、unknown。\n"
            "含义：\n"
            "- jd：JD、岗位、职位、职位描述、招聘需求、岗位说明书。\n"
            "- resume：简历、候选人、简历评分/筛选记录。\n"
            "- interview：面试方案、面试计划、面试安排。\n"
            "- exam：试卷、考试、笔试题、测评题。\n"
            "keyword 填用户用于定位目标的名称/关键词，例如“AI训练师”“产品经理”“张三”“Java基础”。不要包含“删除、帮我、JD、岗位、试卷”等动作词或类型词。\n"
            "context_reference 表示用户是否用“这个/这份/这条/该/刚才/刚生成的/上一个/它”等指代最近生成的产物。\n"
            "latest 为用户是否表达最新/刚才/上一个/最近。\n"
            "delete_all 为用户是否明确表达全部/所有/都删。\n"
            "confirm_context_low_scores 表示用户是否在上文低分候选人确认后，明确说“确认删除这些低分候选人/确认删除不合格简历”。\n"
            "如果资源类型不明确，resource_type 返回 unknown。\n"
            "返回格式：{\"resource_type\":\"jd|resume|interview|exam|unknown\",\"keyword\":\"...\",\"context_reference\":false,\"latest\":false,\"delete_all\":false,\"confirm_context_low_scores\":false}\n\n"
            f"用户消息：{message}"
        )
        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            response = await self.llm_service.generate_response(prompt)
            parsed = self._safe_json_loads(response)
            resource_type = str(parsed.get("resource_type") or parsed.get("type") or "").strip().lower()
            if resource_type in {"jd", "resume", "interview", "exam"}:
                keyword = self._clean_optional_value(parsed.get("keyword")) or ""
                return {
                    "type": resource_type,
                    "keyword": keyword,
                    "context_reference": bool(parsed.get("context_reference")),
                    "latest": bool(parsed.get("latest")),
                    "delete_all": bool(parsed.get("delete_all")),
                    "confirm_context_low_scores": bool(parsed.get("confirm_context_low_scores")),
                    "source": "llm",
                }
        except Exception as exc:
            logger.warning("删除请求大模型解析失败，使用规则兜底: %s", exc)

        return self._fallback_parse_delete_request(message)

    def _fallback_parse_delete_request(self, message: str) -> Dict[str, Any]:
        lowered = message.lower()
        resource_type = None
        if re.search(r"jd|职位描述|岗位说明书|招聘需求|职位|岗位", lowered):
            resource_type = "jd"
        elif re.search(r"面试方案|面试计划|面试", lowered):
            resource_type = "interview"
        elif re.search(r"试卷|考试|笔试", lowered):
            resource_type = "exam"
        elif re.search(r"简历|候选人", lowered):
            resource_type = "resume"

        keyword = re.sub(r"请|帮我|麻烦|一下|这个|这份|这条|记录|生成的|已生成的", "", message, flags=re.I)
        keyword = re.sub(r"删除|删掉|移除|清理|取消", "", keyword, flags=re.I)
        keyword = re.sub(r"jd|职位描述|岗位说明书|招聘需求|职位|岗位|简历评分|简历记录|简历|候选人|面试方案|面试计划|面试|试卷|考试|笔试", "", keyword, flags=re.I)
        keyword = keyword.strip(" 的：:，,。.?？!！「」『』【】[]()（）")
        return {
            "type": resource_type,
            "keyword": keyword,
            "context_reference": bool(re.search(r"这个|这份|这条|该|刚才|刚刚|上一个|上一条|最近|最新|它|其|刚生成", message)),
            "latest": bool(re.search(r"最近|最新|刚才|上一个|最后", message)),
            "delete_all": bool(re.search(r"全部|所有|都删|全删", message)),
            "confirm_context_low_scores": bool(re.search(r"确认|确定", message) and re.search(r"低分|不合格|没通过|未通过|这些", message)),
            "source": "fallback",
        }

    async def _recent_low_score_resume_resources(
        self,
        user_id: UUID,
        conversation_id: Optional[str],
        threshold: int = 60,
    ) -> List[Dict[str, Any]]:
        groups = await self._recent_resume_screening_groups(conversation_id, user_id, threshold)
        return [
            {
                "id": item["id"],
                "name": item.get("name") or item.get("filename") or "低分候选人",
                "search_text": self._resource_search_text(item, ["name", "filename", "position"]),
                "source": "conversation_context",
            }
            for item in groups.get("low_score_candidates") or []
            if item.get("id")
        ]

    def _delete_target_detail(self, resource_type: Optional[str], keyword: str) -> str:
        label = self._resource_type_label(resource_type) if resource_type else "资源"
        return f"目标类型：{label}；关键词：{keyword or '未提供'}。"

    async def _recent_generated_resources(
        self,
        resource_type: str,
        user_id: UUID,
        conversation_id: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        conditions = [
            Conversation.user_id == user_id,
            Message.role == MessageRole.ASSISTANT,
        ]
        if conversation_id:
            try:
                conditions.append(Message.conversation_id == UUID(str(conversation_id)))
            except Exception:
                logger.warning("删除指代匹配收到非法 conversation_id: %s", conversation_id)
        query = (
            select(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(*conditions)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        resources: List[Dict[str, Any]] = []
        for message in result.scalars().all():
            response = (message.context or {}).get("agent_response") if isinstance(message.context, dict) else None
            if not isinstance(response, dict):
                continue
            resources.extend(self._resources_from_agent_response(response, resource_type))
            if resources:
                return resources
        return resources

    def _resources_from_agent_response(self, response: Dict[str, Any], resource_type: str) -> List[Dict[str, Any]]:
        resources: List[Dict[str, Any]] = []
        for artifact in response.get("artifacts") or []:
            metadata = artifact.get("metadata") or {}
            content = artifact.get("content")
            if resource_type == "jd" and metadata.get("saved_jd_id"):
                resources.append({
                    "id": str(metadata["saved_jd_id"]),
                    "name": artifact.get("title") or metadata.get("job_title") or "最近生成的 JD",
                    "search_text": self._resource_search_text({
                        "title": artifact.get("title"),
                        "job_title": metadata.get("job_title"),
                        "content": content if isinstance(content, str) else "",
                    }),
                    "source": "conversation_context",
                })
            elif resource_type == "criteria" and metadata.get("saved_criteria_id"):
                resources.append({
                    "id": str(metadata["saved_criteria_id"]),
                    "name": artifact.get("title") or metadata.get("job_title") or "最近生成的评分标准",
                    "search_text": self._resource_search_text({
                        "title": artifact.get("title"),
                        "job_title": metadata.get("job_title"),
                        "content": content if isinstance(content, str) else "",
                    }),
                    "source": "conversation_context",
                })
            elif resource_type == "resume" and artifact.get("type") == "resume_screening_results" and isinstance(content, list):
                for item in content:
                    if item.get("id") and item.get("status") != "failed":
                        resources.append({
                            "id": str(item["id"]),
                            "name": item.get("name") or item.get("filename") or "最近评分的简历",
                            "search_text": self._resource_search_text(item, ["name", "filename", "position", "summary"]),
                            "source": "conversation_context",
                        })
            elif resource_type == "interview" and metadata.get("saved_plan_id"):
                resources.append({
                    "id": str(metadata["saved_plan_id"]),
                    "name": artifact.get("title") or metadata.get("candidate_name") or "最近生成的面试方案",
                    "content": content if isinstance(content, str) else "",
                    "search_text": self._resource_search_text({
                        "title": artifact.get("title"),
                        "candidate_name": metadata.get("candidate_name"),
                        "content": content if isinstance(content, str) else "",
                    }),
                    "source": "conversation_context",
                })
            elif resource_type == "exam" and metadata.get("saved_exam_id"):
                resources.append({
                    "id": str(metadata["saved_exam_id"]),
                    "name": artifact.get("title") or metadata.get("subject") or "最近生成的试卷",
                    "search_text": self._resource_search_text({
                        "title": artifact.get("title"),
                        "subject": metadata.get("subject"),
                        "content": content if isinstance(content, str) else "",
                    }),
                    "source": "conversation_context",
                })
        return resources

    async def _delete_matched_resources(
        self,
        resource_type: str,
        matches: List[Dict[str, Any]],
        user_id: UUID,
        steps: List[AgentStep],
        keyword: str,
        matched_from_context: bool = False,
    ) -> AgentChatResponse:
        deleted = []
        failures = []
        for item in matches:
            try:
                delete_result = await self._delete_resource_by_type(resource_type, item["id"], user_id)
                deleted.append({**item, "delete_result": delete_result or {}})
            except Exception as exc:
                logger.warning("Agent 删除资源失败 type=%s id=%s: %s", resource_type, item.get("id"), exc)
                failures.append({"id": item.get("id"), "name": item.get("name"), "error": str(exc)})

        match_detail = "从最近对话产物中匹配到目标。" if matched_from_context else f"匹配到 {len(matches)} 个目标。"
        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": match_detail})
        steps[2] = steps[2].model_copy(update={
            "status": "completed" if deleted and not failures else ("failed" if not deleted else "completed"),
            "detail": f"已删除 {len(deleted)} 个，失败 {len(failures)} 个。",
        })
        deleted_names = "、".join(item["name"] for item in deleted[:5])
        failure_text = f"；{len(failures)} 个删除失败" if failures else ""
        context_text = "（已按最近对话中的“这个/刚才”指代匹配）" if matched_from_context else ""
        cascade_count = sum(len((item.get("delete_result") or {}).get("deleted_scoring_criteria") or []) for item in deleted)
        cascade_text = f"，并删除关联评分标准 {cascade_count} 条" if resource_type == "jd" and cascade_count else ""
        return AgentChatResponse(
            message=f"已删除{self._resource_type_label(resource_type)}{context_text}：{deleted_names or '无'}{cascade_text}{failure_text}。",
            intent="resource_delete",
            route=self._resource_type_route(resource_type),
            steps=steps,
            artifacts=[
                AgentArtifact(
                    type="delete_resource_result",
                    title="删除结果",
                    content={
                        "resource_type": resource_type,
                        "keyword": keyword,
                        "deleted": deleted,
                        "failures": failures,
                        "matched_from_context": matched_from_context,
                    },
                )
            ],
            suggestions=self._delete_suggestions(resource_type),
        )

    async def _list_deletable_resources(self, resource_type: str, user_id: UUID, keyword: str = "") -> List[Dict[str, Any]]:
        if resource_type == "jd":
            result = await JobDescriptionService(self.db).list_job_descriptions(user_id=user_id, page=1, size=100)
            return [
                {
                    "id": str(item.get("id")),
                    "name": item.get("title") or item.get("job_title") or item.get("name") or "未命名 JD",
                    "location": item.get("location"),
                    "salary_range": item.get("salary_range"),
                    "experience_level": item.get("experience_level"),
                    "updated_at": str(item.get("updated_at")) if item.get("updated_at") else "",
                    "search_text": self._resource_search_text(item, ["id", "title", "job_title", "department", "location", "salary_range", "experience_level", "content", "requirements"]),
                }
                for item in result.get("items", [])
                if item.get("id")
            ]
        if resource_type == "resume":
            evaluations, _ = await ResumeEvaluationService(self.db).get_evaluation_history(user_id=user_id, skip=0, limit=100)
            return [
                {
                    "id": str(item.id),
                    "name": item.candidate_name or item.original_filename or "未命名简历",
                    "search_text": self._resource_search_text({
                        "candidate_name": item.candidate_name,
                        "original_filename": item.original_filename,
                        "candidate_position": item.candidate_position,
                        "education_level": item.education_level,
                    }),
                }
                for item in evaluations
            ]
        if resource_type == "interview":
            result = await InterviewPlanService(self.db).list_interview_plans(user_id=user_id, page=1, size=100)
            items = result.get("items") or result.get("data") or []
            return [
                {
                    "id": str(item.get("id")),
                    "name": item.get("title") or item.get("candidate_name") or item.get("name") or "未命名面试方案",
                    "search_text": self._resource_search_text(item, ["title", "candidate_name", "candidate_position", "job_title", "content"]),
                }
                for item in items
                if item.get("id")
            ]
        if resource_type == "exam":
            result = await ExamService(self.db).get_exam_list(skip=0, limit=100, search=keyword or None)
            return [
                {
                    "id": str(item.get("id")),
                    "name": item.get("title") or item.get("subject") or "未命名试卷",
                    "search_text": self._resource_search_text(item, ["title", "subject", "description", "special_requirements"]),
                }
                for item in result.get("items", [])
                if item.get("id")
            ]
        return []

    def _match_delete_resources(self, resources: List[Dict[str, Any]], keyword: str, latest: bool = False) -> List[Dict[str, Any]]:
        if latest and resources:
            return [resources[0]]
        normalized_keyword = self._normalize_candidate_match_text(keyword)
        if not normalized_keyword:
            return resources[:1] if latest else []
        exact_matches = [
            item for item in resources
            if normalized_keyword == self._normalize_candidate_match_text(item.get("name"))
        ]
        if exact_matches:
            return exact_matches
        return [
            item for item in resources
            if normalized_keyword in self._normalize_candidate_match_text(item.get("search_text"))
            or self._normalize_candidate_match_text(item.get("name")) in normalized_keyword
        ]

    async def _delete_resource_by_type(self, resource_type: str, resource_id: str, user_id: UUID) -> Optional[Dict[str, Any]]:
        if resource_type == "jd":
            return await JobDescriptionService(self.db).delete_job_description(resource_id, user_id)
        if resource_type == "resume":
            success = await ResumeEvaluationService(self.db).delete_evaluation(UUID(resource_id), user_id)
            if not success:
                raise ValueError("简历记录不存在")
            return {}
        if resource_type == "interview":
            await InterviewPlanService(self.db).delete_interview_plan(UUID(resource_id), user_id)
            return {}
        if resource_type == "exam":
            await ExamService(self.db).delete_exam(resource_id)
            return {}
        raise ValueError("不支持的删除类型")

    def _resource_search_text(self, item: Any, keys: Optional[List[str]] = None) -> str:
        if not isinstance(item, dict):
            return ""
        values = []
        source_keys = keys or list(item.keys())
        for key in source_keys:
            value = item.get(key)
            if value is None:
                continue
            values.append(str(value))
        return " ".join(values)

    def _resource_type_label(self, resource_type: Optional[str]) -> str:
        return {
            "jd": "JD",
            "resume": "简历记录",
            "interview": "面试方案",
            "exam": "试卷",
        }.get(resource_type or "", "资源")

    def _resource_type_route(self, resource_type: Optional[str]) -> Optional[str]:
        return {
            "jd": "/recruitment/jd-generator",
            "resume": "/recruitment/resume-screening",
            "interview": "/recruitment/smart-interview",
            "exam": "/training/exam-generator",
        }.get(resource_type or "")

    def _delete_suggestions(self, resource_type: str) -> List[str]:
        return {
            "jd": ["查看 JD 列表", "重新生成 JD"],
            "resume": ["查看简历筛选列表", "重新评分简历"],
            "interview": ["查看面试方案列表", "重新生成面试方案"],
            "exam": ["查看试卷列表", "重新生成试卷"],
        }.get(resource_type, ["查看列表", "换个名称再试"])

    async def _parse_requirements(
        self,
        text: str,
        conversation_id: Optional[str],
        memory_context: str = "",
    ) -> Dict[str, Any]:
        prompt = (
            "你是招聘助手。请从用户需求中提取结构化字段，并严格返回 JSON，不要解释。\n"
            "字段：job_title, department, location, salary, experience, education, job_type, skills, benefits, additional_requirements。\n"
            "优先结合历史对话记忆理解“继续、这个岗位、刚才”等指代；仍未明确的信息返回 null。\n"
            "只提取用户或历史对话中明确提到的信息；未提到的字段必须返回 null，skills/benefits 未提到时返回 []，不要自行推断默认值。\n"
            "additional_requirements 只填写用户明确提出的额外岗位要求、加分项、福利或特殊约束；不要填入历史对话原文、当前用户原句或已结构化到其他字段的信息。\n"
            f"{self._format_memory_for_prompt(memory_context)}"
            f"用户需求：{text}"
        )
        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            response = await self.llm_service.generate_response(prompt)
            parsed = self._safe_json_loads(response)
            if parsed:
                return self._normalize_requirements(parsed, text)
        except Exception as exc:
            logger.warning("Agent 需求解析失败，使用本地兜底解析: %s", exc)
        # 如果 LLM 失败，使用 _fallback_parse()用正则兜底提取岗位、薪资、经验、学历、地点、技能。
        return self._fallback_parse(text)

    async def _parse_exam_requirements(
        self,
        text: str,
        conversation_id: Optional[str],
        memory_context: str = "",
    ) -> Dict[str, Any]:
        parsed = self._fallback_exam_parse("\n".join([memory_context, text]) if memory_context else text)
        return self._normalize_exam_requirements(parsed, original_text=text)

    async def _select_exam_knowledge_files(
        self,
        exam: Dict[str, Any],
        message: str,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        query = " ".join(
            item for item in [
                self._clean_optional_value(exam.get("subject")),
                self._clean_optional_value(exam.get("title")),
                self._clean_optional_value(exam.get("special_requirements")),
                message,
            ] if item
        ).strip()
        if not query:
            return []
        try:
            selector = KBSelectionService(self.db)
            selection = await selector.select_kb_for_question(
                question=query,
                user_id=user_id,
                max_candidates=200,
            )
        except Exception as exc:
            logger.warning("Agent 试卷知识库文档匹配失败: %s", exc)
            return []
        if not selection or not selection.get("document_id"):
            return []
        confidence = float(selection.get("confidence") or 0)
        if confidence and confidence < 0.35:
            return []
        return [{
            "id": str(selection.get("document_id")),
            "fileName": selection.get("filename") or "知识库文档",
        }]

    async def _generate_jd(self, original_text: str, parsed: Dict[str, Any], conversation_id: Optional[str]) -> str:
        query = self._build_jd_query(original_text, parsed)
        response = await self.dify_service.call_workflow_sync(
            workflow_type=1,
            query=query,
            conversation_id=None,
            additional_inputs={
                "position_title": parsed.get("job_title"),
                "department": parsed.get("department"),
                "experience_level": parsed.get("experience"),
                "task": "agent_generate_jd",
            },
        )
        return self._extract_answer(response).strip()

    async def _generate_jd_stream(
        self,
        original_text: str,
        parsed: Dict[str, Any],
        conversation_id: Optional[str],
    ) -> AsyncGenerator[str, None]:
        query = self._build_jd_query(original_text, parsed)
        full_text = ""
        try:
            async for chunk in self.dify_service.call_workflow_stream(
                workflow_type=1,
                query=query,
                conversation_id=None,
                additional_inputs={
                    "position_title": parsed.get("job_title"),
                    "department": parsed.get("department"),
                    "experience_level": parsed.get("experience"),
                    "task": "agent_generate_jd",
                },
            ):
                raw_delta = self._extract_stream_delta(chunk)
                delta = self._dedupe_stream_delta(raw_delta, full_text)
                if not delta:
                    continue
                full_text += delta
                yield delta
        except Exception as exc:
            logger.warning("Agent JD 流式生成失败，回退同步生成: %s", exc)

        if not full_text.strip():
            fallback = await self._generate_jd(original_text, parsed, conversation_id)
            async for delta in self._stream_text(fallback):
                yield delta

    def _build_jd_query(self, original_text: str, parsed: Dict[str, Any]) -> str:
        query_parts = [f"请基于以下招聘需求生成一份专业、完整、适合发布的中文岗位JD：{original_text}"]
        field_map = {
            "job_title": "岗位名称",
            "department": "部门",
            "location": "工作地点",
            "salary": "薪资范围",
            "experience": "经验要求",
            "education": "学历要求",
        }
        for key, label in field_map.items():
            if parsed.get(key):
                query_parts.append(f"{label}：{parsed[key]}")
        if parsed.get("skills"):
            query_parts.append(f"技能要求：{'、'.join(parsed['skills'])}")
        return "\n".join(query_parts)

    async def _generate_interview_plan_content(
        self,
        resume: ResumeEvaluation,
        jd_content: str,
        conversation_id: Optional[str],
    ) -> str:
        query = self._build_interview_plan_query()
        response = await self.dify_service.call_workflow_sync(
            workflow_type=4,
            query=query,
            conversation_id=None,
            additional_inputs={
                "jianli": resume.resume_content,
                "jd": jd_content,
                "evaluation_metrics": resume.evaluation_metrics or [],
                "total_score": resume.total_score,
                "candidate_name": resume.candidate_name,
                "task": "agent_generate_interview_plan",
            },
        )
        return self._extract_answer(response).strip()

    async def _generate_interview_plan_stream(
        self,
        resume: ResumeEvaluation,
        jd_content: str,
        conversation_id: Optional[str],
    ) -> AsyncGenerator[str, None]:
        query = self._build_interview_plan_query()
        full_text = ""
        try:
            async for chunk in self.dify_service.call_workflow_stream(
                workflow_type=4,
                query=query,
                conversation_id=None,
                additional_inputs={
                    "jianli": resume.resume_content,
                    "jd": jd_content,
                    "evaluation_metrics": resume.evaluation_metrics or [],
                    "total_score": resume.total_score,
                    "candidate_name": resume.candidate_name,
                    "task": "agent_generate_interview_plan",
                },
            ):
                raw_delta = self._extract_stream_delta(chunk)
                delta = self._dedupe_stream_delta(raw_delta, full_text)
                if not delta:
                    continue
                full_text += delta
                yield delta
        except Exception as exc:
            logger.warning("Agent 面试计划流式生成失败，回退同步生成: %s", exc)

        if not full_text.strip():
            fallback = await self._generate_interview_plan_content(resume, jd_content, conversation_id)
            async for delta in self._stream_text(fallback):
                yield delta

    def _build_interview_plan_query(self) -> str:
        return "请根据候选人简历、JD要求和简历评分结果生成一份结构化面试计划。"

    async def _get_resume_evaluation(self, user_id: UUID, resume_evaluation_id: UUID) -> ResumeEvaluation:
        result = await self.db.execute(
            select(ResumeEvaluation).where(
                ResumeEvaluation.id == resume_evaluation_id,
                ResumeEvaluation.user_id == user_id,
            )
        )
        resume = result.scalar_one_or_none()
        if not resume:
            raise ValueError("简历评价记录未找到或无权限访问")
        return resume

    async def _save_exam_source_document(self, filename: str, content: bytes, user_id: UUID) -> Document:
        file_hash = hashlib.sha256(content).hexdigest()
        existing_result = await self.db.execute(
            select(Document).where(
                Document.file_hash == file_hash,
                Document.user_id == user_id,
            )
        )
        existing_document = existing_result.scalar_one_or_none()
        if existing_document:
            return existing_document

        upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        base_name, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(upload_dir, f"{base_name}_{counter}{extension}")
            counter += 1

        with open(file_path, "wb") as file:
            file.write(content)

        document = Document(
            filename=os.path.basename(file_path),
            original_filename=filename,
            file_path=file_path,
            file_size=len(content),
            file_hash=file_hash,
            mime_type=self._get_document_mime_type(filename),
            extracted_content=None,
            embedding=None,
            category="exam_source",
            tags=["hr_agent", "exam_generation"],
            user_id=user_id,
            knowledge_base_id=None,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    def _get_document_mime_type(self, filename: str) -> str:
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        mime_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "md": "text/markdown",
        }
        return mime_types.get(extension, "application/octet-stream")

    async def _generate_scoring_criteria(
        self,
        jd_content: str,
        parsed: Dict[str, Any],
        conversation_id: Optional[str],
    ) -> str:
        query = self._build_scoring_criteria_query(jd_content)
        response = await self.dify_service.call_workflow_sync(
            workflow_type=2,
            query=query,
            conversation_id=None,
            additional_inputs={
                "job_title": parsed.get("job_title"),
                "task": "agent_generate_scoring_criteria",
            },
        )
        return self._extract_answer(response).strip()

    async def _generate_scoring_criteria_stream(
        self,
        jd_content: str,
        parsed: Dict[str, Any],
        conversation_id: Optional[str],
    ) -> AsyncGenerator[str, None]:
        query = self._build_scoring_criteria_query(jd_content)
        full_text = ""
        try:
            async for chunk in self.dify_service.call_workflow_stream(
                workflow_type=2,
                query=query,
                conversation_id=None,
                additional_inputs={
                    "job_title": parsed.get("job_title"),
                    "task": "agent_generate_scoring_criteria",
                },
            ):
                raw_delta = self._extract_stream_delta(chunk)
                delta = self._dedupe_stream_delta(raw_delta, full_text)
                if not delta:
                    continue
                full_text += delta
                yield delta
        except Exception as exc:
            logger.warning("Agent 评分标准流式生成失败，回退同步生成: %s", exc)

        if not full_text.strip():
            fallback = await self._generate_scoring_criteria(jd_content, parsed, conversation_id)
            async for delta in self._stream_text(fallback):
                yield delta

    def _build_scoring_criteria_query(self, jd_content: str) -> str:
        return (
            f"请基于以下JD内容，生成简历初筛评分标准，总分100分。\n\n{jd_content}\n\n"
            "请包含技能匹配、工作经验、教育背景、项目经验、加分项和淘汰项，并给出可操作的分值区间。"
        )

    async def _save_job_description(
        self,
        jd_content: str,
        parsed: Dict[str, Any],
        original_text: str,
        user_id: UUID,
        conversation_id: Optional[str],
    ):
        jd_data = JobDescriptionCreate(
            title=parsed.get("job_title") or "未命名岗位",
            department=parsed.get("department"),
            location=parsed.get("location"),
            salary_range=parsed.get("salary"),
            experience_level=parsed.get("experience"),
            education=parsed.get("education"),
            job_type=parsed.get("job_type") or "全职",
            skills=parsed.get("skills") or [],
            content=jd_content,
            requirements=parsed.get("additional_requirements") or original_text,
            status="draft",
            meta_data={
                "source": "hr_agent",
                "salary": parsed.get("salary"),
                "location": parsed.get("location"),
                "benefits": parsed.get("benefits") or [],
            },
            conversation_id=conversation_id,
            workflow_type="agent_jd_generation",
        )
        service = JobDescriptionService(self.db)
        return await service.create_job_description(jd_data, user_id)

    async def _save_scoring_criteria(
        self,
        criteria_content: str,
        parsed: Dict[str, Any],
        user_id: UUID,
        conversation_id: Optional[str],
        saved_jd_id: Optional[UUID] = None,
    ):
        criteria_data = ScoringCriteriaCreate(
            title=f"{parsed.get('job_title') or '岗位'}简历评分标准",
            job_title=parsed.get("job_title"),
            content=criteria_content,
            total_score="100",
            status="draft",
            meta_data={"source": "hr_agent"},
            conversation_id=conversation_id,
            workflow_type="agent_scoring_criteria_generation",
            job_description_id=saved_jd_id,
        )
        service = ScoringCriteriaService(self.db)
        return await service.save_scoring_criteria(criteria_data, user_id)

    def _extract_answer(self, response: Any) -> str:
        if isinstance(response, dict):
            if response.get("answer"):
                return str(response["answer"])
            data = response.get("data")
            if isinstance(data, dict) and data.get("answer"):
                return str(data["answer"])
            if response.get("text"):
                return str(response["text"])
            return json.dumps(response, ensure_ascii=False)
        return str(response)

    def _extract_stream_delta(self, chunk: Any) -> str:
        if isinstance(chunk, str):
            try:
                chunk = json.loads(chunk)
            except json.JSONDecodeError:
                return chunk
        if not isinstance(chunk, dict):
            return str(chunk)

        event = chunk.get("event")
        if event in {
            "message_end",
            "agent_message_end",
            "workflow_finished",
            "node_finished",
            "tts_message",
            "tts_message_end",
            "message_file",
        }:
            return ""
        if event and event not in {"message", "agent_message", "text_chunk"}:
            return ""

        for key in ("answer", "delta", "text"):
            value = chunk.get(key)
            if isinstance(value, str):
                return value

        data = chunk.get("data")
        if isinstance(data, dict):
            for key in ("answer", "delta", "text"):
                value = data.get(key)
                if isinstance(value, str):
                    return value
        return ""

    def _normalize_sse_chunk(self, chunk: Any) -> Any:
        if not isinstance(chunk, str):
            return chunk
        text = chunk.strip()
        if not text:
            return ""
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if line and line != "[DONE]":
                lines.append(line)
        return "\n".join(lines)

    def _dedupe_stream_delta(self, delta: str, full_text: str) -> str:
        """兼容 Dify 流式返回增量/累计全文/最终全文，避免前端重复拼接。"""
        if not delta:
            return ""
        if not full_text:
            return delta
        if delta == full_text or delta.strip() == full_text.strip():
            return ""
        if delta.startswith(full_text):
            return delta[len(full_text):]

        # 较大的 chunk 往往是累计全文或最终全文，尝试按前后缀重叠裁剪。
        # 小 token 不做重叠裁剪，避免把正常重复字符误删。
        if len(delta) < 20:
            return delta

        max_overlap = min(len(full_text), len(delta))
        for size in range(max_overlap, 0, -1):
            if full_text.endswith(delta[:size]):
                return delta[size:]
        return delta

    def _safe_json_loads(self, text: str) -> Dict[str, Any]:
        json_text = text.strip()
        if "```" in json_text:
            json_text = re.sub(r"^```(?:json)?", "", json_text, flags=re.IGNORECASE).strip()
            json_text = re.sub(r"```$", "", json_text).strip()
        match = re.search(r"\{.*\}", json_text, re.S)
        if match:
            json_text = match.group(0)
        try:
            value = json.loads(json_text)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _normalize_requirements(self, parsed: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        normalized = {
            "job_title": self._clean_optional_value(parsed.get("job_title")),
            "department": self._clean_optional_value(parsed.get("department")),
            "location": self._clean_optional_value(parsed.get("location")),
            "salary": self._clean_optional_value(parsed.get("salary")),
            "experience": self._clean_optional_value(parsed.get("experience")),
            "education": self._clean_optional_value(parsed.get("education")),
            "job_type": self._clean_optional_value(parsed.get("job_type")),
            "skills": parsed.get("skills") or [],
            "benefits": parsed.get("benefits") or [],
            "additional_requirements": self._clean_optional_value(parsed.get("additional_requirements")),
        }
        if isinstance(normalized["skills"], str):
            normalized["skills"] = [item.strip() for item in re.split(r"[,，、/]", normalized["skills"]) if item.strip()]
        if isinstance(normalized["benefits"], str):
            normalized["benefits"] = [item.strip() for item in re.split(r"[,，、/]", normalized["benefits"]) if item.strip()]
        return normalized

    def _normalize_exam_requirements(
        self,
        parsed: Dict[str, Any],
        original_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        question_counts = parsed.get("question_counts") or {}
        if not isinstance(question_counts, dict):
            question_counts = {}
        normalized = {
            "title": self._clean_optional_value(parsed.get("title")) or (f"{self._clean_optional_value(parsed.get('subject')) or '候选人'}能力测试"),
            "subject": self._clean_optional_value(parsed.get("subject")) or self._infer_exam_subject(original_text or ""),
            "description": self._clean_optional_value(parsed.get("description")),
            "difficulty": self._clean_optional_value(parsed.get("difficulty")) or "medium",
            "duration": self._safe_int(parsed.get("duration"), 60),
            "total_score": self._safe_int(parsed.get("total_score"), 100),
            "question_types": parsed.get("question_types") or ["single_choice", "multiple_choice", "short_answer"],
            "question_counts": {
                "single_choice": self._safe_int(question_counts.get("single_choice"), 5),
                "multiple_choice": self._safe_int(question_counts.get("multiple_choice"), 3),
                "short_answer": self._safe_int(question_counts.get("short_answer"), 2),
            },
            "knowledge_files": self._normalize_knowledge_files(parsed.get("knowledge_files")),
            "special_requirements": self._clean_optional_value(parsed.get("special_requirements")) or "",
            "interview_plan_context": parsed.get("interview_plan_context") if isinstance(parsed.get("interview_plan_context"), dict) else None,
        }
        if isinstance(normalized["question_types"], str):
            normalized["question_types"] = [item.strip() for item in re.split(r"[,，、/]", normalized["question_types"]) if item.strip()]
        return normalized

    def _safe_int(self, value: Any, default: int) -> int:
        if value is None or value == "":
            return default
        match = re.search(r"\d+", str(value))
        return int(match.group(0)) if match else default

    def _normalize_knowledge_files(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        files = []
        for item in value:
            if isinstance(item, dict) and item.get("id"):
                files.append({"id": item.get("id"), "fileName": item.get("fileName") or item.get("filename") or "知识库文档"})
        return files

    def _infer_exam_subject(self, text: str) -> str:
        patterns = ["Java", "Python", "Go", "前端", "后端", "产品经理", "AI产品经理", "测试", "算法", "运营"]
        for pattern in patterns:
            if pattern.lower() in text.lower():
                return pattern
        return "通用岗位"

    def _brief_exam_requirements(self, exam: Dict[str, Any]) -> str:
        counts = exam.get("question_counts") or {}
        count_text = "、".join([f"{key}:{value}" for key, value in counts.items() if value])
        return f"{exam.get('title')} / {exam.get('subject')} / {exam.get('total_score')}分 / {exam.get('duration')}分钟 / {count_text}"

    def _clean_optional_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "n/a", "na"}:
            return None
        if text in {"无", "暂无", "未提及", "未说明", "未知"}:
            return None
        return text

    def _normalize_optional_list(self, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, list):
            items = [self._clean_optional_value(item) for item in value]
            return [item for item in items if item] or None
        if isinstance(value, str):
            items = [item.strip() for item in re.split(r"[,，、/]", value) if item.strip()]
            return items or None
        return None

    def _is_jd_edit_request(self, message: str) -> bool:
        lowered = message.lower()
        has_jd_target = bool(re.search(r"jd|职位描述|岗位说明书|招聘需求|职位|岗位", lowered))
        if (
            has_jd_target
            and re.search(r"删除|删掉|移除|清理", message)
            and not re.search(r"把|将|内容|职责|要求|福利|技能|薪资|地点|经验|学历", message)
        ):
            return False
        has_edit_action = bool(re.search(r"改改|修改|调整|优化|更新|编辑|润色|改成|改为|换成|加上|增加|删掉|删除|去掉", message))
        has_context = bool(re.search(r"上次|刚才|刚刚|这个|这份|这条|那个|上一版|最近|最新|原来", message))
        return has_jd_target and has_edit_action and (has_context or "jd" in lowered or "职位描述" in message or "岗位说明书" in message)

    def _is_criteria_edit_request(self, message: str) -> bool:
        has_target = bool(re.search(r"评分标准|评分规则|打分标准|筛选标准|简历评分标准|简历评分规则", message))
        has_edit_action = bool(re.search(r"改改|修改|调整|优化|更新|编辑|润色|改成|改为|换成|加上|增加|删掉|删除|去掉|降低|提高", message))
        return has_target and has_edit_action

    def _is_jd_edit_followup(self, message: str, memory_context: str = "") -> bool:
        if not memory_context:
            return False
        waiting_for_changes = bool(re.search(r"你想具体改哪些内容|等待用户说明要修改哪些内容|等待修改要求|想具体改哪些内容", memory_context))
        if not waiting_for_changes:
            return False
        return bool(re.search(r"改成|改为|换成|加上|增加|删掉|删除|去掉|薪资|地点|职责|技能|要求|福利|经验|学历|React|Vue|Python|Java", message, re.I))

    def _is_criteria_edit_followup(self, message: str, memory_context: str = "") -> bool:
        if not memory_context:
            return False
        waiting_for_changes = bool(re.search(r"想具体改哪些评分规则|等待用户说明要修改哪些评分规则|等待修改要求", memory_context))
        if not waiting_for_changes:
            return False
        return bool(re.search(r"改成|改为|换成|加上|增加|删掉|删除|去掉|降低|提高|分|权重|维度|技能|经验|学历|项目|加分|淘汰", message, re.I))

    def _is_generic_jd_edit_request(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text)
        normalized = re.sub(r"请|帮我|麻烦|一下|这个|那个|上次|刚才|刚刚|JD|jd|职位描述|岗位说明书", "", normalized)
        return normalized in {"", "改改", "修改", "调整", "优化", "更新", "编辑", "润色", "帮改", "再改"}

    def _is_generic_criteria_edit_request(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text)
        normalized = re.sub(r"请|帮我|麻烦|一下|这个|那个|上次|刚才|刚刚|评分标准|评分规则|打分标准|筛选标准|简历评分", "", normalized)
        return normalized in {"", "改改", "修改", "调整", "优化", "更新", "编辑", "润色", "帮改", "再改"}

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        parsed = {
            "job_title": None,
            "department": None,
            "location": None,
            "salary": None,
            "experience": None,
            "education": None,
            "job_type": None,
            "skills": [],
            "benefits": [],
            "additional_requirements": None,
        }
        patterns = {
            "experience": r"(\d+\s*-\s*\d+年|\d+年以上|\d+年\+?)",
            "salary": r"(\d+\s*-\s*\d+\s*[kK]|\d+\s*[kK]\s*-\s*\d+\s*[kK]|\d+\s*-\s*\d+)",
            "education": r"本科|专科|硕士|博士|大专",
            "job_type": r"全职|兼职|实习",
            "location": r"北京|上海|深圳|广州|杭州|南京|成都|重庆|苏州|武汉|西安|长沙",
        }
        title_match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9+#]+(?:开发|测试|算法|产品|运营|销售|人事|财务|行政)?(?:工程师|经理|专员|主管|顾问|设计师|架构师))", text)
        if title_match:
            parsed["job_title"] = title_match.group(1)
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed[key] = match.group(0).replace(" ", "")
        skill_candidates = ["Java", "Python", "Go", "Vue", "React", "Spring", "MySQL", "Redis", "Docker", "Kubernetes", "AI", "大模型"]
        parsed["skills"] = [skill for skill in skill_candidates if skill.lower() in text.lower()]
        return parsed

    def _fallback_exam_parse(self, text: str) -> Dict[str, Any]:
        title = None
        subject = None
        clean_text = text.strip()
        title_match = re.search(r"(?:生成|出|创建|制作)(?:一份|一个)?(.{1,30}?)(?:试卷|考试|笔试题|题目)", clean_text)
        if title_match:
            subject = title_match.group(1).strip(" ，,。的")
            title = f"{subject}试卷" if subject else None

        named_title_match = re.search(
            r"(?:试卷名称|试卷名|标题|名称|名字)(?:是|为|叫|设为|定为)?[:：]?\s*([^\n，,。；;]+)|(?:就叫|叫做|叫|命名为|取名为|起名为)\s*([^\n，,。；;]+?)(?:吧|。|$)",
            clean_text,
        )
        if named_title_match:
            title_value = (named_title_match.group(1) or named_title_match.group(2) or "").strip()
            title = re.sub(r"(?:的)?试卷$", "", title_value).strip() or title

        subject_candidates = ["Java", "Python", "Go", "前端", "后端", "产品经理", "AI产品经理", "测试", "算法", "运营", "大模型"]
        for candidate in subject_candidates:
            if subject:
                break
            if candidate.lower() in clean_text.lower():
                subject = candidate
                title = title or f"{candidate}试卷"
                break

        total_score_match = re.search(r"(\d+)\s*分", clean_text)
        duration_match = re.search(r"(\d+)\s*(?:分钟|分(?:钟)?|min)", clean_text, re.IGNORECASE)
        counts = {
            "single_choice": self._extract_question_count(clean_text, ["单选题", "单选", "选择题"], 5),
            "multiple_choice": self._extract_question_count(clean_text, ["多选题", "多选"], 3),
            "short_answer": self._extract_question_count(clean_text, ["简答题", "简答", "问答题", "问答"], 2),
        }

        difficulty = None
        if re.search(r"简单|基础|入门", clean_text):
            difficulty = "easy"
        elif re.search(r"困难|高阶|高级", clean_text):
            difficulty = "hard"
        elif re.search(r"中等|中级", clean_text):
            difficulty = "medium"

        special_requirements_match = re.search(r"(?:要求|注意事项|其他)[:：]\s*(.+)", clean_text)

        return {
            "title": title,
            "subject": subject,
            "difficulty": difficulty,
            "duration": int(duration_match.group(1)) if duration_match else None,
            "total_score": int(total_score_match.group(1)) if total_score_match else None,
            "question_types": ["single_choice", "multiple_choice", "short_answer"],
            "question_counts": counts,
            "special_requirements": special_requirements_match.group(1).strip() if special_requirements_match else "",
        }

    def _extract_question_count(self, text: str, labels: List[str], default: int) -> int:
        for label in labels:
            match = re.search(rf"(\d+)\s*(?:道|个)?\s*{label}|{label}\s*(\d+)\s*(?:道|个)?", text)
            if match:
                return int(match.group(1) or match.group(2))
        return default

    def _brief_requirements(self, parsed: Dict[str, Any]) -> str:
        parts = [
            parsed.get("job_title"),
            parsed.get("location"),
            parsed.get("salary"),
            parsed.get("experience"),
        ]
        return " / ".join([str(part) for part in parts if part]) or "已提取基础字段。"

    def _missing_required_fields(self, parsed: Dict[str, Any]) -> List[str]:
        required_fields = ["job_title", "location", "salary", "experience", "education"]
        missing = []
        for field in required_fields:
            value = parsed.get(field)
            if value is None or value == "" or value == []:
                missing.append(field)
        return missing

    def _field_label(self, field: str) -> str:
        labels = {
            "job_title": "岗位名称",
            "location": "工作地点",
            "salary": "薪资范围",
            "experience": "经验要求",
            "education": "学历要求",
            "skills": "核心技能",
        }
        return labels.get(field, field)

    def _fallback_message(self, intent: str, message: str = "") -> str:
        mapping = {
            "interview_plan": "我识别到你想做面试方案。这个工具可以跳转到智能面试页继续处理。",
            "exam_generate": "我识别到你想生成考试/试卷。这个工具可以跳转到试卷生成页继续处理。",
        }
        if intent == "general":
            return (
                "我是招聘场景的 HR Agent，当前主要能帮你做这些事：生成 JD、生成简历评分标准、筛选简历、生成面试计划、基于文档和面试方案生成试卷、生成邮件草稿，以及删除已生成内容。"
                "如果你想让我执行任务，可以直接说其中一个目标。"
            )
        return mapping.get(intent, "我已经识别到需求，但当前还没有可安全自动执行的招聘工具。")

    def _suggestions_for_intent(self, intent: str) -> List[str]:
        mapping = {
            "interview_plan": ["生成面试计划", "先筛选简历", "查看已评分候选人"],
            "exam_generate": ["生成试卷", "上传参考文档", "补充考试配置"],
        }
        return mapping.get(intent, ["生成 JD", "筛选简历", "生成试卷"])
