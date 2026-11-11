

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


from app.services._agent_service_core import _AgentServiceCoreMixin
from app.services._agent_service_editing import _AgentServiceEditingMixin
from app.services._agent_service_resources import _AgentServiceResourcesMixin

"""
HR Agent 服务
    第一版聚焦工具编排：理解用户 HR 需求，并按意图调用 JD 生成、简历筛选等工具。

    HR Agent 的核心编排服务，也是最大文件。负责识别用户意图、选择工具、组织ReAct决策、处理普通/流式对话，
    并串联JD生成、评分标准生成、简历筛选、面试方案生成、试卷生成、资源删除等完整 HR工作流。
"""
"""
    兜底机制
    这个文件有很多兜底设计，避免 LLM 或 Dify 失败后系统完全不可用：
        ReAct 决策失败 -> 本地关键词规则。
        JD 字段解析失败 -> 正则提取。
        删除请求解析失败 -> 正则提取。
        流式生成失败 -> 同步生成。
        Dify 返回累计全文 -> 去重。
        普通聊天流式失败 -> 使用默认能力说明。
"""


class AgentService(
    _AgentServiceCoreMixin,
    _AgentServiceEditingMixin,
    _AgentServiceResourcesMixin,
):
    """HR Agent service"""

    def __init__(self, db: AsyncSession):
        """
        初始化
            self.db：异步数据库会话。
            self.dify_service：调用 Dify 工作流。
            self.intent_service：关键词/LLM 意图分类服务。
            self.skill_dispatcher：加载可插拔 Skill。
            self.tool_registry：构建 Agent 可用工具表。
            self.email_send_service：邮件发送服务。
            self.llm_service：懒加载 LLM 服务。
            llm_service 没有在构造时立即创建，而是在真正需要 LLM 时才初始化，避免普通请求不必要地加载模型客户端。
        """
        self.db = db
        self.dify_service = DifyService()
        self.intent_service = IntentService(db)
        self.skill_dispatcher = self._build_skill_dispatcher()
        self.tool_registry = self._build_tool_registry()
        self.email_send_service = EmailSendService(db)
        self.llm_service = None

    async def chat(
        self,
        message: str,
        user_id: UUID,
        conversation_id: Optional[str] = None,
        auto_execute: bool = True,
        confirmed_requirements: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        agent_plan: Optional[Dict[str, Any]] = None,
    ) -> AgentChatResponse:
        """
        处理用户消息并执行招聘 Agent 任务

        主入口 chat()
            chat() 是非流式核心入口。它的流程是：
            1.标准化附件。
            2.读取历史对话记忆。
            3.如果用户已经确认 confirmed_requirements，直接进入确认后的工具链。
            4.如果是删除类请求，直接走删除工具，避免 LLM 误判。
            5.否则调用 _plan_agent_action() 做 ReAct 决策。
            6.根据 intent 分发到不同业务分支。

            普通聊天时，返回 intent="general"，不调用业务工具，只给出 Agent 能力说明或 LLM 回复。
        """
        # 1.标准化附件。
        normalized_attachments = self._normalize_attachments(attachments or [])
        # 2.读取历史对话记忆。
        memory_context = await self._build_conversation_memory(conversation_id, user_id, message)
        # 3.如果用户已经确认 confirmed_requirements，直接进入确认后的工具链。
        if confirmed_requirements:
            confirmation_action = str(confirmed_requirements.get("action") or "").strip()
            confirmed_skill = self.skill_dispatcher.match_confirmation_action(confirmation_action) if confirmation_action else None
            if confirmed_skill:
                intent = confirmed_skill.intent
                agent_plan = {
                    "mode": "tool",
                    "intent": confirmed_skill.intent,
                    "reason": f"用户已确认 {confirmed_skill.bundle_name} 所需信息，继续执行 skill。",
                    "reply": None,
                    "source": "confirmed_skill_action",
                }
            else:
                intent = "jd"
                agent_plan = {
                    "mode": "tool",
                    "intent": "jd",
                    "reason": "用户已确认 JD 生成信息，继续执行 JD 工具链。",
                    "reply": None,
                    "source": "confirmed_requirements",
                }
        # 4.否则调用 _plan_agent_action() 做 ReAct 决策。
        else:
            agent_plan = agent_plan or self._build_rule_agent_plan(message, normalized_attachments, memory_context)
            agent_plan = agent_plan or await self._plan_agent_action(message, normalized_attachments, memory_context)
            intent = agent_plan["intent"]

        # 5.根据 intent 分发到不同业务分支。
        route_result = self._route_for_intent(intent, message)
        selected_tool = self.tool_registry.get(intent)

        """
        普通聊天
        """
        if agent_plan["mode"] == "chat" or intent == "general":
            reply = self._clean_optional_value(agent_plan.get("reply")) or self._fallback_message("general", message)
            return AgentChatResponse(
                message=reply,
                intent="general",
                route=None,
                steps=[
                    AgentStep(
                        id="understand",
                        title="完成需求判断",
                        status="completed",
                        detail=agent_plan.get("reason") or "判断为普通对话，不调用招聘工具。",
                    )
                ],
                suggestions=["生成 JD", "评分简历", "基于文档生成试卷"],
            )

        """
        删除资源分支
        删除资源由 _handle_resource_delete() 处理。
        支持删除：
            JD、简历评分记录、面试方案、试卷
        """
        if intent == "resource_delete":
            return await self._handle_resource_delete(message, user_id, selected_tool, conversation_id)

        # jd编辑
        if intent == "jd_edit":
            return await self._handle_jd_edit(message, user_id, selected_tool, conversation_id, memory_context)
        # 评分标准
        if intent == "criteria_edit":
            return await self._handle_criteria_edit(message, user_id, selected_tool, conversation_id, memory_context)

        # 如果intent在skills中
        """
        邮件 Skill 分支
            邮件不是硬编码在 agent_service.py 里的完整业务，而是通过 Skill 插件机制接入。
            agent_skills.py 会扫描 backend/skills，读取 skill.json，把 email_notification 注册进工具表。
        邮件流程有两个 phase：
            - draft：生成邮件草稿。
            - send：用户确认后发送。
        在流式聊天中，如果识别到 email_notification，会走 _stream_skill_draft_response()，先用 LLM 流式生成邮件草稿，再调用 _handle_skill_intent()  生成标准 Agent 响应。
        真正发送邮件在/backend/skills/hr-agent-email/scripts/email_workflow.py ，调用 email_service.send_agent_email()。设计上邮件不会自动发送，必须人工确认。
        """
        if intent in self.skill_dispatcher.bundles:
            return await self._handle_skill_intent(
                intent=intent,
                message=message,
                user_id=user_id,
                route=route_result.get("route"),
                selected_tool=selected_tool,
                memory_context=memory_context,
                confirmed_requirements=confirmed_requirements,
            )

        """
        简历筛选分支
        在 chat() 中，如果识别为 resume_screening：
            如果消息带了简历附件，返回 resume_upload_request artifact，提示前端让用户选择 JD。
            如果没有附件，返回上传简历的引导。
        """
        if intent == "resume_screening":
            has_resume_files = bool(self._filter_attachments(normalized_attachments, {"pdf", "doc", "docx"}))
            # 有简历文件
            if has_resume_files:
                resume_count = len(self._filter_attachments(normalized_attachments, {"pdf", "doc", "docx"}))
                return AgentChatResponse(
                    message=f"我已经识别到 {resume_count} 份简历附件。下一步请选择用于匹配的 JD，确认后我会调用简历评分工具逐份评分并保存结果。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "已选择简历评分工具，并检查到简历附件。"),
                        AgentStep(id="upload", title="接收简历文件", status="completed", detail=f"已检测到 {resume_count} 份简历附件"),
                        AgentStep(id="select_jd", title="选择匹配 JD", status="running", detail="请选择用于评分匹配的 JD。"),
                        AgentStep(id="evaluate", title="执行 AI 评分", status="pending", detail="选择 JD 后开始逐份评分。", tool="evaluate_resume"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="resume_upload_request",
                            title="选择 JD 并开始评分",
                            content={"requires_job_description": True, "file_count": resume_count},
                        )
                    ],
                    suggestions=[],
                )

            # 如果当前消息没有简历附件
            return AgentChatResponse(
                message="我规划了一下：这个需求需要调用简历评分工具，但当前消息里还没有简历附件。请先在底部消息框点击“上传文件”，添加 PDF、DOC 或 DOCX 简历后再发送；收到简历后我再让你选择用于匹配的 JD。",
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    self._planning_step(selected_tool, "需要先满足前置条件：上传简历文件。"),
                    AgentStep(id="upload", title="等待上传简历", status="pending", detail="请先上传 PDF、DOC 或 DOCX 简历。"),
                    AgentStep(id="select_jd", title="选择匹配 JD", status="pending", detail="收到简历后再选择用于匹配的 JD。"),
                    AgentStep(id="evaluate", title="执行 AI 评分", status="pending", detail="选择 JD 后开始逐份评分。", tool="evaluate_resume"),
                ],
                artifacts=[
                    AgentArtifact(
                        type="resume_upload_request",
                        title="简历筛选工具",
                        content={"requires_job_description": True, "accepted_formats": ["pdf", "doc", "docx"]},
                    )
                ],
                suggestions=[],
            )

        """
            面试计划分支
            如果意图是 interview_plan，chat() 不会盲目生成，而是先解析候选人。
            _resolve_interview_candidate() 会读取最近的简历评分记录，然后用 LLM 判断用户说的是哪位候选人：
                matched：匹配到唯一候选人。
                no_match：用户说了候选人，但系统没有评分记录。
                ambiguous：匹配多个候选人，需要用户选择。
                no_specific：没有指定候选人。
            如果匹配成功，返回 interview_plan_execute artifact，前端可以据此调用流式面试方案接口，stream_interview_plan()
        """
        if intent == "interview_plan":
            followup_resume_action = await self._resolve_resume_screening_followup_action(message, user_id, conversation_id)
            if followup_resume_action.get("action") in {"generate_interview", "confirm_delete_low_scores"}:
                return self._build_resume_screening_followup_response(
                    followup_resume_action,
                    route_result.get("route"),
                    selected_tool,
                )

            # 查询最近简历评分记录，用 LLM 或本地规则匹配候选人
            candidate_resolution = await self._resolve_interview_candidate(message, user_id, memory_context)
            # 匹配到了候选人
            if candidate_resolution.get("status") == "matched" and candidate_resolution.get("candidate_id"):
                candidate_name = candidate_resolution.get("candidate_name") or "该候选人"
                return AgentChatResponse(
                    message=candidate_resolution.get("reply") or f"我已经找到候选人「{candidate_name}」，现在直接调用面试计划工具生成方案。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "用户已指定候选人，且已匹配到已评分简历。"),
                        AgentStep(id="select_resume", title="匹配候选人", status="completed", detail=f"已匹配：{candidate_name}。"),
                        AgentStep(id="generate_plan", title="生成面试计划", status="running", detail="正在调用面试计划工具。", tool="generate_interview_plan"),
                        AgentStep(id="save_plan", title="保存面试计划", status="pending", detail="生成后自动保存。"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="interview_plan_execute",
                            title="直接生成面试计划",
                            content={
                                "resume_evaluation_id": candidate_resolution["candidate_id"],
                                "candidate_name": candidate_name,
                            },
                        )
                    ],
                    suggestions=["生成面试计划", "查看该候选人评分", "重新筛选简历"],
                )
            # 没有匹配到候选人
            if candidate_resolution.get("status") == "no_match":
                requested_name = candidate_resolution.get("requested_name") or "该候选人"
                return AgentChatResponse(
                    message=candidate_resolution.get("reply") or f"我没有在已评分候选人中找到「{requested_name}」。请先上传他的简历并完成评分，然后我再基于评分结果生成面试计划。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "用户指定了候选人，但当前没有匹配的已评分简历。"),
                        AgentStep(id="match_resume", title="匹配候选人", status="failed", detail=f"未找到：{requested_name}。"),
                        AgentStep(id="upload_resume", title="上传候选人简历", status="running", detail="请上传该候选人的 PDF、DOC 或 DOCX 简历。"),
                        AgentStep(id="evaluate", title="完成简历评分", status="pending", detail="评分完成后再生成面试计划。", tool="evaluate_resume"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="resume_upload_request",
                            title="上传候选人简历",
                            content={"candidate_name": requested_name, "accepted_formats": ["pdf", "doc", "docx"]},
                        )
                    ],
                    suggestions=[],
                )
            # 匹配到多个候选人
            if candidate_resolution.get("status") == "ambiguous":
                return AgentChatResponse(
                    message=candidate_resolution.get("reply") or "我找到了多个可能匹配的候选人，还不能确定你指的是哪一位。请在这条消息里选择候选人后，我再生成面试计划。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "用户指定的候选人存在多个可能匹配项，需要用户确认。"),
                        AgentStep(id="select_resume", title="确认候选人", status="running", detail="请选择一条已评分简历。"),
                        AgentStep(id="generate_plan", title="生成面试计划", status="pending", detail="选择后开始生成。", tool="generate_interview_plan"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="interview_plan_request",
                            title="选择候选人生成面试计划",
                            content={
                                "requires_resume_evaluation": True,
                                "candidates": candidate_resolution.get("candidates") or [],
                            },
                        )
                    ],
                    suggestions=[],
                )
            return AgentChatResponse(
                message="我规划了一下：生成面试计划需要先选中一位已评分候选人，然后调用面试计划工具生成并保存方案。请在这条消息里选择候选人。",
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    self._planning_step(selected_tool, "需要先满足前置条件：选择已评分候选人。"),
                    AgentStep(id="select_resume", title="选择候选人", status="pending", detail="请选择一条已评分简历。"),
                    AgentStep(id="generate_plan", title="生成面试计划", status="pending", detail="选择后开始生成。", tool="generate_interview_plan"),
                    AgentStep(id="save_plan", title="保存面试计划", status="pending", detail="生成后自动保存。"),
                ],
                artifacts=[
                    AgentArtifact(
                        type="interview_plan_request",
                        title="选择候选人生成面试计划",
                        content={"requires_resume_evaluation": True},
                    )
                ],
                suggestions=[],
            )

        """
        考试生成分支
            如果意图是 exam_generate，chat() 会检查是否有参考文档附件。
            没有文档时，返回 exam_document_upload_request，提醒先上传文档。
            有文档时，返回 exam_generate_request，要求确认试卷配置，比如标题、方向、题型、题量、分值。
            stream_exam_generation()负责生成并保存试卷
        """
        if intent == "exam_generate":

            interview_exam_context = await self._resolve_interview_exam_followup(message, user_id, conversation_id)
            if interview_exam_context.get("matched"):
                parsed_exam = await self._parse_exam_requirements(
                    interview_exam_context.get("message") or message,
                    conversation_id,
                    memory_context,
                )
                return AgentChatResponse(
                    message=(
                        f"可以。我会基于最近的面试方案「{interview_exam_context.get('title')}」来组织笔试范围。"
                        "不过当前消息里还没有参考文档，请先在底部消息框上传岗位资料、题库材料或技术文档，上传后我再让你确认试卷配置。"
                    ),
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "识别到用户想从当前面试方案继续生成笔试试卷。"),
                        AgentStep(
                            id="load_interview_plan",
                            title="读取面试方案上下文",
                            status="completed",
                            detail=f"已匹配：{interview_exam_context.get('title')}",
                        ),
                        AgentStep(id="upload_docs", title="等待上传参考文档", status="running", detail="请上传用于出题的参考文档。"),
                        AgentStep(id="confirm_exam", title="确认考试配置", status="pending", detail="上传文档后确认题型、题量和分值。"),
                        AgentStep(id="generate_exam", title="基于文档生成试卷", status="pending", tool="generate_exam"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="exam_document_upload_request",
                            title="上传出题参考文档",
                            content={
                                **parsed_exam,
                                "requires_document_upload": True,
                                "interview_plan_context": interview_exam_context,
                            },
                        )
                    ],
                    suggestions=[],
                    requires_confirmation=False,
                    missing_fields=[field for field in ["title", "subject"] if not parsed_exam.get(field)],
                )

            # 从用户输入中解析 title、subject、duration、total_score、question_counts 等
            parsed_exam = await self._parse_exam_requirements(message, conversation_id, memory_context)
            has_exam_docs = bool(self._filter_attachments(normalized_attachments, {"pdf", "doc", "docx", "txt", "md"}))
            # 有上传考试参考文档
            if has_exam_docs:
                document_count = len(self._filter_attachments(normalized_attachments, {"pdf", "doc", "docx", "txt", "md"}))
                return AgentChatResponse(
                    message=f"我已经识别到 {document_count} 个参考文档附件。下一步先确认试卷标题、考察方向、题型、题量和分值，再调用文档出题工具生成试卷。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "已选择基于文档生成试卷工具，并检查到参考文档。"),
                        AgentStep(id="upload_docs", title="接收参考文档", status="completed", detail=f"已检测到 {document_count} 个参考文档"),
                        AgentStep(id="confirm_exam", title="确认考试配置", status="running", detail="请确认试卷标题、题型、题量和分值。"),
                        AgentStep(id="generate_exam", title="基于文档生成试卷", status="pending", tool="generate_exam"),
                        AgentStep(id="save_exam", title="保存试卷", status="pending", detail="生成后保存到考试管理。"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="exam_generate_request",
                            title="确认考试配置",
                            content={**parsed_exam, "document_count": document_count},
                        )
                    ],
                    suggestions=[],
                    missing_fields=[field for field in ["title", "subject"] if not parsed_exam.get(field)],
                )

            # 有匹配的知识库文档
            matched_knowledge_files = await self._select_exam_knowledge_files(parsed_exam, message, user_id)
            if matched_knowledge_files:
                matched_names = "、".join(file.get("fileName") or "知识库文档" for file in matched_knowledge_files)
                return AgentChatResponse(
                    message=f"我已经按你的描述提取了试卷配置，并在知识库中匹配到参考文档：{matched_names}。请确认配置后即可生成试卷。",
                    intent=intent,
                    route=route_result.get("route"),
                    steps=[
                        self._planning_step(selected_tool, "已选择基于文档生成试卷工具，并匹配到知识库参考文档。"),
                        AgentStep(id="select_docs", title="匹配参考文档", status="completed", detail=f"已匹配：{matched_names}"),
                        AgentStep(id="confirm_exam", title="确认考试配置", status="running", detail="请确认试卷标题、题型、题量和分值。"),
                        AgentStep(id="generate_exam", title="基于文档生成试卷", status="pending", tool="generate_exam"),
                        AgentStep(id="save_exam", title="保存试卷", status="pending", detail="生成后保存到考试管理。"),
                    ],
                    artifacts=[
                        AgentArtifact(
                            type="exam_generate_request",
                            title="确认考试配置",
                            content={**parsed_exam, "knowledge_files": matched_knowledge_files},
                        )
                    ],
                    suggestions=[],
                    missing_fields=[field for field in ["title", "subject"] if not parsed_exam.get(field)],
                )

            # 没有文档，要上传文档
            return AgentChatResponse(
                message="我规划了一下：基于文档出题需要先拿到参考文档，但当前消息里还没有可用附件。请先在底部消息框点击“上传文件”添加附件，然后再发送生成试卷的需求。",
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    self._planning_step(selected_tool, "需要先满足前置条件：上传出题参考文档。"),
                    AgentStep(id="upload_docs", title="等待上传参考文档", status="pending", detail="请上传 PDF、DOC、DOCX、TXT 或 MD 文档。"),
                    AgentStep(id="confirm_exam", title="确认考试配置", status="pending", detail="上传文档后再配置试卷。"),
                    AgentStep(id="generate_exam", title="基于文档生成试卷", status="pending", tool="generate_exam"),
                    AgentStep(id="save_exam", title="保存试卷", status="pending", detail="生成后保存到考试管理。"),
                ],
                artifacts=[
                    AgentArtifact(
                        type="exam_document_upload_request",
                        title="上传出题参考文档",
                        content={**parsed_exam, "requires_document_upload": True},
                    )
                ],
                suggestions=[],
                requires_confirmation=False,
                missing_fields=[field for field in ["title", "subject"] if not parsed_exam.get(field)],
            )

        if intent != "jd":
            return AgentChatResponse(
                message=self._fallback_message(intent, message),
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    AgentStep(
                        id="plan",
                        title="理解需求并规划",
                        status="completed",
                        detail="当前没有匹配到可安全自动执行的招聘工具，我先给出说明或建议。",
                    )
                ],
                suggestions=self._suggestions_for_intent(intent),
            )


        """
        JD 生成分支
            如果意图是 jd，chat() 会先解析招聘需求：
            - _parse_requirements()用 LLM 提取结构化字段。如果 LLM 失败，使用 _fallback_parse()  用正则兜底提取岗位、薪资、经验、学历、地点、技能。
            - _missing_required_fields()  检查必要字段：岗位名称、地点、薪资、经验、学历。

            如果缺字段，它不会直接生成，而是返回 requires_confirmation=True，让前端弹窗补充信息。
            用户确认后，_run_recruitment_agent() 会执行：
                1.生成 JD。
                2.保存 JD。
                3.基于 JD 生成评分标准。
                4.保存评分标准。
                5.返回两个 artifact：job_description 和 scoring_criteria。

            JD生成调用的是 Dify workflow type 1：_generate_jd() 。
            评分标准调用 Dify workflow type 2：_generate_scoring_criteria()

        """
        if not auto_execute:
            return AgentChatResponse(
                message="我识别到这是 JD 生成任务。确认信息后我会调用 JD 生成工具并保存到 JD 管理。",
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    self._planning_step(selected_tool, "JD 生成需要先确认结构化招聘信息。"),
                    AgentStep(id="confirm", title="等待确认", status="pending", detail="确认后调用 JD 生成工具。"),
                ],
                suggestions=[],
                requires_confirmation=True,
            )

        if confirmed_requirements:
            parsed = self._normalize_requirements(confirmed_requirements, message)
            return await self._run_recruitment_agent(
                message,
                conversation_id,
                route_result.get("route"),
                parsed_requirements=parsed,
                user_id=user_id,
            )

        # 用 LLM 从自然语言中提取岗位字段
        parsed = await self._parse_requirements(message, conversation_id, memory_context)
        #  检查必要字段：岗位名称、地点、薪资、经验、学历。
        missing_fields = self._missing_required_fields(parsed)
        # 如果缺字段，不会直接生成，而是返回 `requires_confirmation=True`，让前端弹窗补充信息。
        if missing_fields:
            return AgentChatResponse(
                message="我先补齐 JD 生成的必要信息，再生成会更稳。请在弹窗里确认或补充这些字段。",
                intent=intent,
                route=route_result.get("route"),
                steps=[
                    self._planning_step(selected_tool, "已选择 JD 生成工具；先补齐必要字段再执行。"),
                    AgentStep(id="parse", title="解析招聘需求", status="completed", detail=self._brief_requirements(parsed), tool="parse_requirements"),
                    AgentStep(id="confirm", title="确认招聘信息", status="pending", detail=f"待补充：{'、'.join(self._field_label(field) for field in missing_fields)}"),
                    AgentStep(id="jd", title="生成岗位 JD", status="pending", tool="generate_jd"),
                ],
                artifacts=[AgentArtifact(type="requirements", title="待确认招聘需求", content=parsed)],
                suggestions=[],
                requires_confirmation=True,
                missing_fields=missing_fields,
            )

        return AgentChatResponse(
            message="我已提取到 JD 生成所需信息。请在弹窗中确认，确认后我再调用 JD 生成工具。",
            intent=intent,
            route=route_result.get("route"),
            steps=[
                self._planning_step(selected_tool, "已选择 JD 生成工具；等待用户确认后执行。"),
                AgentStep(id="parse", title="解析招聘需求", status="completed", detail=self._brief_requirements(parsed), tool="parse_requirements"),
                AgentStep(id="confirm", title="确认招聘信息", status="pending", detail="等待用户确认后执行生成。"),
                AgentStep(id="jd", title="生成岗位 JD", status="pending", tool="generate_jd"),
            ],
            artifacts=[AgentArtifact(type="requirements", title="待确认招聘需求", content=parsed)],
            suggestions=[],
            requires_confirmation=True,
        )

    async def stream_chat_agent(
        self,
        message: str,
        user_id: UUID,
        conversation_id: Optional[str] = None,
        auto_execute: bool = True,
        confirmed_requirements: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理普通 Agent 聊天：
            先推送思考状态，再返回最终规划/回复。
            """
        thinking_response = AgentChatResponse(
            message="我正在理解你的需求。",
            intent="thinking",
            route=None,
            steps=[
                AgentStep(
                    id="understand",
                    title="理解用户需求",
                    status="running",
                    detail="正在判断是否需要调用 HR 工具。",
                ),
                AgentStep(
                    id="plan",
                    title="选择下一步动作",
                    status="pending",
                    detail="识别完成后选择 chat、ask_user 或 use_tool。",
                ),
            ],
            suggestions=[],
        )
        yield {"type": "thinking", "response": thinking_response.model_dump()}

        # 附件
        normalized_attachments = self._normalize_attachments(attachments or [])
        # 读取对话记忆
        memory_context = await self._build_conversation_memory(conversation_id, user_id, message)

        agent_plan = None
        # 是否有用户确认后的结构化招聘需求
        if not confirmed_requirements:
            # 规划：下一步动作，轻量意图分类：优先规则和附件上下文，不为路由单独调用大模型
            agent_plan = self._build_rule_agent_plan(message, normalized_attachments, memory_context)
            if not agent_plan:
                # 规划：受控LLM ReAct决策
                agent_plan = await self._plan_agent_action(message, normalized_attachments, memory_context)

            # 常规聊天
            if agent_plan.get("mode") == "chat" or agent_plan.get("intent") == "general":
                chat_response = AgentChatResponse(
                    message="",
                    intent="general",
                    route=None,
                    steps=[
                        AgentStep(
                            id="understand",
                            title="完成需求判断",
                            status="completed",
                            detail=agent_plan.get("reason") or "判断为普通对话，不调用招聘工具。",
                        )
                    ],
                    suggestions=["生成 JD", "评分简历", "基于文档生成试卷"],
                )
                yield {"type": "plan", "response": chat_response.model_dump()}

                full_text = ""
                try:
                    if self.llm_service is None:
                        self.llm_service = LLMService()
                    chat_prompt = self._build_memory_augmented_prompt(message, memory_context)
                    async for delta in self.llm_service.stream_response(chat_prompt):
                        full_text += delta
                        yield {"type": "delta", "delta": delta}
                except Exception as exc:
                    logger.warning("Agent 普通聊天原生流式失败，使用规划回复兜底: %s", exc)
                    fallback_reply = self._clean_optional_value(agent_plan.get("reply")) or self._fallback_message("general", message)
                    async for delta in self._stream_text(fallback_reply):
                        full_text += delta
                        yield {"type": "delta", "delta": delta}

                final_response = chat_response.model_copy(update={"message": full_text.strip() or self._fallback_message("general", message)})
                yield {"type": "final", "response": final_response.model_dump()}
                return

            # jd编辑
            if agent_plan.get("intent") == "jd_edit":
                async for event in self._stream_jd_edit_response(
                    message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_context=memory_context,
                ):
                    yield event
                return
            # 评分标准编辑
            if agent_plan.get("intent") == "criteria_edit":
                async for event in self._stream_criteria_edit_response(
                    message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    memory_context=memory_context,
                ):
                    yield event
                return
            # skill
            if agent_plan.get("intent") in self.skill_dispatcher.bundles:
                # 发送邮件
                if agent_plan.get("intent") == "email_notification":
                    async for event in self._stream_skill_draft_response(
                        intent="email_notification",
                        message=message,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        route=self._route_for_intent("email_notification", message).get("route"),
                        memory_context=memory_context,
                        confirmed_requirements=confirmed_requirements,
                    ):
                        yield event
                    return

                response = await self.chat(
                    message=message,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    auto_execute=auto_execute,
                    confirmed_requirements=confirmed_requirements,
                    attachments=attachments,
                    agent_plan=agent_plan,
                )
                yield {
                    "type": "plan",
                    "response": response.model_copy(update={"message": ""}).model_dump(),
                }
                async for delta in self._stream_text(response.message):
                    yield {"type": "delta", "delta": delta}
                yield {"type": "final", "response": response.model_dump()}
                return

        # 根据 intent 构造响应
        response = await self.chat(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id,
            auto_execute=auto_execute,
            confirmed_requirements=confirmed_requirements,
            attachments=attachments,
            agent_plan=agent_plan,
        )
        # 返回执行计划 steps 和 artifact阶段性产物
        yield {
            "type": "plan",
            "response": response.model_copy(update={"message": ""}).model_dump(),
        }
        async for delta in self._stream_text(response.message):
            # 流式文本片段
            yield {"type": "delta", "delta": delta}
        # 最终完整结果
        yield {"type": "final", "response": response.model_dump()}

    async def stream_recruitment_agent(
        self,
        message: str,
        user_id: UUID,
        conversation_id: Optional[str],
        confirmed_requirements: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行确认后的招聘 Agent任务，向前端推送真实阶段进度

        流式JD生成
        stream_recruitment_agent() 是确认JD需求后的流式版本。它会按阶段返回：
            - progress：状态进度。
            - delta：JD或评分标准正文增量。
            - artifact：阶段产物。
            - final：最终完整响应。

        先流式生成JD，再保存JD，再流式生成评分标准，再保存评分标准。前端可以边收边显示内容。
        """

        parsed = self._normalize_requirements(confirmed_requirements, message)
        route = "/recruitment/jd-generator"
        steps: List[AgentStep] = [
            self._planning_step(self.tool_registry.get("jd"), "招聘信息已确认，按 JD → 评分标准的工具链执行。"),
            AgentStep(id="parse", title="确认招聘需求", status="completed", detail=self._brief_requirements(parsed)),
            AgentStep(id="jd", title="生成岗位 JD", status="pending", detail="等待调用大模型", tool="generate_jd"),
            AgentStep(id="save_jd", title="保存 JD", status="pending", detail="等待 JD 生成完成"),
            AgentStep(id="criteria", title="生成简历评分标准", status="pending", detail="等待 JD 保存完成", tool="generate_scoring_criteria"),
            AgentStep(id="save_criteria", title="保存评分标准", status="pending", detail="等待评分标准生成完成"),
        ]
        artifacts: List[AgentArtifact] = [
            AgentArtifact(type="requirements", title="结构化招聘需求", content=parsed)
        ]

        # 先显示: 已确认招聘需求，准备生成JD
        yield self._stream_event("progress", "已确认招聘需求，准备生成 JD。", steps, artifacts)

        # 生成岗位 JD
        steps[2] = steps[2].model_copy(update={"status": "running", "detail": "正在调用大模型生成 JD..."})
        yield self._stream_event("progress", "正在生成岗位 JD。", steps, artifacts)
        yield {"type": "delta", "delta": "## 岗位 JD\n\n", "section": "jd"}

        jd_content = ""
        async for delta in self._generate_jd_stream(message, parsed, conversation_id):
            jd_content += delta
            yield {"type": "delta", "delta": delta, "section": "jd"}
        jd_content = jd_content.strip()
        steps[2] = steps[2].model_copy(update={"status": "completed", "detail": "JD 已生成。"})
        artifacts.append(AgentArtifact(
            type="job_description",
            title=f"{parsed.get('job_title') or '岗位'} JD",
            content=jd_content,
            metadata={"job_title": parsed.get("job_title"), "route": route},
        ))
        yield self._stream_event("artifact", "JD 已生成，正在保存到 JD 管理。", steps, artifacts)

        # 保存 JD
        steps[3] = steps[3].model_copy(update={"status": "running", "detail": "正在保存 JD 记录..."})
        yield self._stream_event("progress", "正在保存 JD。", steps, artifacts)
        saved_jd = await self._save_job_description(jd_content, parsed, message, user_id, conversation_id)
        steps[3] = steps[3].model_copy(update={"status": "completed", "detail": f"已保存到 JD 列表，ID：{saved_jd.id}"})
        artifacts[-1].metadata["saved_jd_id"] = str(saved_jd.id)

        # 生成简历评分标准
        steps[4] = steps[4].model_copy(update={"status": "running", "detail": "正在基于 JD 生成简历评分标准..."})
        yield self._stream_event("progress", "JD 已保存，正在生成简历评分标准。", steps, artifacts)
        yield {"type": "delta", "delta": "\n\n## 简历评分标准\n\n", "section": "scoring_criteria"}
        criteria_content = ""
        async for delta in self._generate_scoring_criteria_stream(jd_content, parsed, conversation_id):
            criteria_content += delta
            yield {"type": "delta", "delta": delta, "section": "scoring_criteria"}
        criteria_content = criteria_content.strip()
        steps[4] = steps[4].model_copy(update={"status": "completed", "detail": "评分标准已生成。"})
        artifacts.append(AgentArtifact(
            type="scoring_criteria",
            title=f"{parsed.get('job_title') or '岗位'}评分标准",
            content=criteria_content,
            metadata={"job_title": parsed.get("job_title"), "saved_jd_id": str(saved_jd.id)},
        ))
        yield self._stream_event("artifact", "评分标准已生成，正在保存。", steps, artifacts)

        # 保存评分标准
        steps[5] = steps[5].model_copy(update={"status": "running", "detail": "正在保存评分标准..."})
        yield self._stream_event("progress", "正在保存评分标准。", steps, artifacts)
        saved_criteria = await self._save_scoring_criteria(
            criteria_content,
            parsed,
            user_id,
            conversation_id,
            saved_jd.id,
        )
        steps[5] = steps[5].model_copy(update={"status": "completed", "detail": f"已保存评分标准，ID：{saved_criteria.id}"})
        artifacts[-1].metadata["saved_criteria_id"] = str(saved_criteria.id)

        job_title = parsed.get("job_title") or "这个岗位"
        final_response = AgentChatResponse(
            message=f"我已经按「{job_title}」生成并保存了 JD，同时生成并保存了简历评分标准。需要筛选简历时，告诉我“筛选简历”，我会提醒你上传简历并调用评分工具。",
            intent="jd",
            route=route,
            steps=steps,
            artifacts=artifacts,
            suggestions=["筛选这个 JD 的简历", "去 JD 管理查看职位", "基于 JD 生成面试题"],
        )
        yield {"type": "final", "response": final_response.model_dump()}

        # 返回给前端的内容格式：
        '''
        {
          "intent": "jd",
          "route": "/recruitment/jd-generator",
          "artifacts": [
            {
              "type": "job_description",
              "content": "JD正文",
              "metadata": {
                "saved_jd_id": "..."
              }
            },
            {
              "type": "scoring_criteria",
              "content": "评分标准正文",
              "metadata": {
                "saved_criteria_id": "...",
                "saved_jd_id": "..."
              }
            }
            ...
          ],
          "suggestions": [
            "筛选这个 JD 的简历",
            "去 JD 管理查看职位",
            "基于 JD 生成面试题"
          ]
        }
        '''

    async def stream_resume_screening(
        self,
        user_id: UUID,
        job_description_id: UUID,
        files: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        批量筛选简历并推送真实进度
        简历筛选分支
        在 chat() 中，如果识别为 resume_screening：
        - 如果消息带了简历附件，它返回 resume_upload_request artifact，提示前端让用户选择 JD。
        - 如果没有附件，它返回上传简历的引导。
        真正执行批量评分的是 stream_resume_screening()。接收：
            user_id、job_description_id、files、conversation_id
        执行过程：
            1. 先返回“已收到 N 份简历”。
            2. 遍历每个文件。
            3. 调用 ResumeEvaluationService.evaluate_resume() 评分。
            4. 每评完一份，就返回一段 markdown 增量。
            5. 最后按分数排序。
            6. 生成招聘闭环建议，例如高分候选人进入面试，低分候选人可复核或删除。

        还会生成 resume_screening_followup artifact，用于后续支持“为高分候选人生成面试计划”“删除低分候选人”。
        """
        total = len(files)
        results: List[Dict[str, Any]] = []
        steps = [
            AgentStep(id="upload", title="接收简历文件", status="completed", detail=f"已接收 {total} 份简历"),
            AgentStep(id="evaluate", title="批量 AI 评分", status="running", detail="准备开始评分", tool="evaluate_resume"),
            AgentStep(id="summary", title="生成筛选摘要", status="pending", detail="等待评分完成"),
        ]

        yield self._resume_stream_event(
            "progress",
            f"已收到 {total} 份简历，开始按当前 JD 批量评分。",
            steps,
            results,
        )
        yield {"type": "delta", "delta": "## 简历评分结果\n\n", "section": "resume_screening"}

        # 逐份处理简历
        evaluation_service = ResumeEvaluationService(self.db)
        for index, file_info in enumerate(files, start=1):
            filename = file_info["filename"]
            steps[1] = steps[1].model_copy(update={
                "status": "running",
                "detail": f"正在评分第 {index}/{total} 份：{filename}",
            })
            yield self._resume_stream_event(
                "progress",
                f"正在评分：{filename}",
                steps,
                results,
            )

            try:
                # 简历评估
                result = await evaluation_service.evaluate_resume(
                    user_id=user_id,
                    file_content=file_info["content"],
                    filename=filename,
                    job_description_id=job_description_id,
                    conversation_id=conversation_id,
                )
                result_data = {
                    "id": str(result.get("id")),
                    "filename": filename,
                    "name": result.get("name") or filename,
                    "score": result.get("total_score") or 0,
                    "position": result.get("position"),
                    "education": result.get("education"),
                    "work_years": result.get("workYears"),
                    "metrics": result.get("evaluation_metrics") or [],
                    "status": "completed",
                }
            except Exception as exc:
                logger.exception("Agent 批量筛选简历失败: %s", filename)
                result_data = {
                    "filename": filename,
                    "name": filename,
                    "score": 0,
                    "status": "failed",
                    "error": str(exc),
                }

            results.append(result_data)
            yield {
                "type": "delta",
                "delta": self._format_resume_result_delta(result_data, index, total),
                "section": "resume_screening",
                "result": result_data,
            }
            yield self._resume_stream_event(
                "artifact",
                f"已完成 {index}/{total}：{filename}",
                steps,
                results,
            )

        failed_count = len([item for item in results if item.get("status") == "failed"])
        success_count = total - failed_count
        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": f"完成 {success_count} 份，失败 {failed_count} 份"})
        steps[2] = steps[2].model_copy(update={"status": "completed", "detail": "已生成批量筛选结果"})

        sorted_results = sorted(results, key=lambda item: item.get("score") or 0, reverse=True)
        loop_summary = self._build_resume_screening_loop_summary(sorted_results, threshold=60)
        final_response = AgentChatResponse(
            message=(
                f"批量简历筛选完成：成功 {success_count} 份，失败 {failed_count} 份。结果已保存到简历筛选列表。"
                f"{loop_summary['message_suffix']}"
            ),
            intent="resume_screening",
            route="/recruitment/resume-screening",
            steps=steps,
            artifacts=[
                AgentArtifact(
                    type="resume_screening_results",
                    title="批量简历筛选结果",
                    content=sorted_results,
                    metadata={
                        "job_description_id": str(job_description_id),
                        "total": total,
                        "qualified_threshold": 60,
                    },
                ),
                AgentArtifact(
                    type="resume_screening_followup",
                    title="招聘闭环建议",
                    content=loop_summary,
                    metadata={"threshold": 60},
                )
            ],
            suggestions=loop_summary["suggestions"],
        )
        yield {"type": "final", "response": final_response.model_dump()}

        # 返回内容格式：
        '''
        {
          "intent": "resume_screening",
          "route": "/recruitment/resume-screening",
          "artifacts": [
            {
              "type": "resume_screening_results",
              "content": [
                {
                  "id": "简历评分ID",
                  "filename": "xxx.pdf",
                  "name": "张三",
                  "score": 85,
                  "status": "completed"
                }
              ]
            },
            {
              "type": "resume_screening_followup",
              "title": "招聘闭环建议",
              "content": {
                "high_score_candidates": "...",
                "low_score_candidates": "..."
              }
            }
          ],
          "suggestions": [
            "生成面试计划",
            "删除低分候选人",
            "查看简历筛选列表"
          ]
        }
        '''

    async def stream_interview_plan(
        self,
        user_id: UUID,
        resume_evaluation_id: UUID,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        根据已评分简历生成并保存面试计划
        真正生成面试方案的是 stream_interview_plan()：
            1.根据 resume_evaluation_id 读取评分记录。
            2.根据评分记录里的 job_description_id 读取JD。
            3.调用 Dify workflow type 4 生成面试计划。
            4.保存到 InterviewPlanService.create_interview_plan()。
            5.把候选人状态改成 ResumeStatus.INTERVIEW。
            6.返回面试方案 artifact 和后续建议。
        """
        steps = [
            AgentStep(id="load_resume", title="读取候选人资料", status="running", detail="正在读取简历评分记录"),
            AgentStep(id="generate_plan", title="生成面试计划", status="pending", tool="generate_interview_plan"),
            AgentStep(id="save_plan", title="保存面试计划", status="pending"),
        ]
        yield self._tool_stream_event("progress", "我正在读取候选人的简历评分结果。", "interview_plan", "/recruitment/smart-interview", steps, [])

        resume = await self._get_resume_evaluation(user_id, resume_evaluation_id)
        job_description = await JobDescriptionService(self.db).get_job_description(
            jd_id=str(resume.job_description_id),
            user_id=user_id,
        )
        steps[0] = steps[0].model_copy(update={"status": "completed", "detail": f"候选人：{resume.candidate_name or resume.original_filename}"})
        steps[1] = steps[1].model_copy(update={"status": "running", "detail": "正在结合 JD、简历和评分结果生成面试计划..."})
        yield self._tool_stream_event("progress", "资料已就绪，开始生成面试计划。", "interview_plan", "/recruitment/smart-interview", steps, [])

        yield {"type": "delta", "delta": "## 面试计划\n\n", "section": "interview_plan"}
        plan_content = ""
        async for delta in self._generate_interview_plan_stream(resume, job_description.content, conversation_id):
            plan_content += delta
            yield {"type": "delta", "delta": delta, "section": "interview_plan"}
        plan_content = plan_content.strip()
        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": "面试计划已生成。"})
        artifacts = [
            AgentArtifact(
                type="interview_plan",
                title=f"{resume.candidate_name or '候选人'} 面试计划",
                content=plan_content,
                metadata={"resume_evaluation_id": str(resume.id)},
            )
        ]
        yield self._tool_stream_event("artifact", "面试计划已生成，正在保存。", "interview_plan", "/recruitment/smart-interview", steps, artifacts)

        steps[2] = steps[2].model_copy(update={"status": "running", "detail": "正在保存到面试计划列表..."})
        saved_plan = await InterviewPlanService(self.db).create_interview_plan(
            user_id=user_id,
            plan_data=InterviewPlanCreate(
                resume_evaluation_id=resume.id,
                candidate_name=resume.candidate_name or resume.original_filename,
                candidate_position=resume.candidate_position or getattr(job_description, "title", "候选岗位"),
                content=plan_content,
            ),
        )
        resume.status = ResumeStatus.INTERVIEW
        await self.db.commit()
        steps[2] = steps[2].model_copy(update={"status": "completed", "detail": f"已保存，ID：{saved_plan.id}；候选人状态已同步为面试"})
        artifacts[0].metadata["saved_plan_id"] = str(saved_plan.id)
        artifacts[0].metadata["candidate_name"] = resume.candidate_name or resume.original_filename
        artifacts[0].metadata["candidate_position"] = resume.candidate_position or getattr(job_description, "title", "候选岗位")
        response = AgentChatResponse(
            message=(
                f"面试计划已生成并保存。建议围绕「{resume.candidate_name or '该候选人'}」的高匹配项做深挖，"
                "同时对评分中较弱的能力设计追问，避免只凭简历亮点做判断。候选人状态也已推进到“面试”，刷新面试计划页面后会出现在列表中。\n\n"
                "如果你想把招聘链路继续往前推，可以上传岗位资料、技术文档或题库材料，然后告诉我“基于当前面试方案生成笔试试卷”。"
            ),
            intent="interview_plan",
            route="/recruitment/smart-interview",
            steps=steps,
            artifacts=artifacts,
            suggestions=["基于当前面试方案生成笔试试卷", "写面试邀约邮件", "查看面试计划列表"],
        )
        yield {"type": "final", "response": response.model_dump()}

    async def stream_exam_generation(
        self,
        user_id: UUID,
        exam_requirements: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        生成并保存考试试卷

        stream_exam_generation() 负责生成并保存试卷：
            1.标准化考试配置。
            2.如果用户说“基于当前面试方案出题”，会尝试关联最近面试方案。
            3.调用 ExamService.generate_exam() 流式生成。
            4.将内部题目格式转换成前端可读 markdown。
            5.调用 ExamService.save_exam() 保存。
            6.返回分享链接 /exam-share/{id}。

            stream_exam_generation_with_documents() 多做了一步：
                先保存并解析上传的参考文档，再把文档 ID 作为 knowledge_files 传给考试生成服务。
        """
        exam = self._normalize_exam_requirements(exam_requirements)
        exam = await self._hydrate_exam_interview_context(exam, user_id, conversation_id)
        steps = [
            AgentStep(id="confirm_exam", title="确认考试配置", status="completed", detail=self._brief_exam_requirements(exam)),
            AgentStep(id="generate_exam", title="生成考试试卷", status="running", detail="正在调用考试生成工具...", tool="generate_exam"),
            AgentStep(id="save_exam", title="保存试卷", status="pending", detail="等待生成完成"),
        ]
        yield self._tool_stream_event("progress", "考试配置已确认，开始生成试卷。", "exam_generate", "/training/exam-generator", steps, [])

        exam_service = ExamService(self.db)
        yield {"type": "delta", "delta": "## 考试试卷\n\n", "section": "exam_generate"}
        raw_exam_content = ""
        display_exam_content = ""
        pending_exam_buffer = ""
        question_index = 1
        async for raw_delta in self._generate_exam_content_stream(exam_service, exam, user_id, conversation_id):
            raw_exam_content += raw_delta
            pending_exam_buffer += raw_delta
            display_delta, pending_exam_buffer, question_index = self._drain_exam_display_buffer(
                pending_exam_buffer,
                question_index,
            )
            if display_delta:
                display_exam_content += display_delta
                yield {"type": "delta", "delta": display_delta, "section": "exam_generate"}

        display_delta, pending_exam_buffer, question_index = self._drain_exam_display_buffer(
            pending_exam_buffer,
            question_index,
            force=True,
        )
        if display_delta:
            display_exam_content += display_delta
            yield {"type": "delta", "delta": display_delta, "section": "exam_generate"}

        repair_content = await self._generate_missing_exam_questions(
            exam_service=exam_service,
            exam=exam,
            existing_content=raw_exam_content,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if repair_content:
            if raw_exam_content.strip():
                raw_exam_content = f"{raw_exam_content.rstrip()}\n***\n{repair_content.strip()}"
            else:
                raw_exam_content = repair_content.strip()
            display_delta, _, question_index = self._drain_exam_display_buffer(
                repair_content,
                question_index,
                force=True,
            )
            if display_delta:
                display_exam_content += display_delta
                yield {"type": "delta", "delta": display_delta, "section": "exam_generate"}

        exam_content = raw_exam_content.strip()
        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": "试卷已生成。"})
        artifacts = [
            AgentArtifact(
                type="exam_paper",
                title=exam["title"],
                content=display_exam_content.strip() or exam_content,
                metadata={"subject": exam["subject"]},
            )
        ]
        yield self._tool_stream_event("artifact", "试卷已生成，正在保存到考试管理。", "exam_generate", "/training/exam-generator", steps, artifacts)

        steps[2] = steps[2].model_copy(update={"status": "running", "detail": "正在保存试卷..."})
        saved_exam = await exam_service.save_exam({**exam, "content": exam_content}, str(user_id))
        saved_exam_id = saved_exam.get("id")
        share_url = f"/exam-share/{saved_exam_id}" if saved_exam_id else None
        steps[2] = steps[2].model_copy(update={"status": "completed", "detail": f"已保存，ID：{saved_exam.get('id')}"})
        artifacts[0].metadata["saved_exam_id"] = saved_exam_id
        artifacts[0].metadata["share_url"] = share_url
        share_message = f"\n\n分享链接：[打开试卷分享页]({share_url})\n\n也可以复制：`{share_url}`" if share_url else ""
        response = AgentChatResponse(
            message=f"试卷「{exam['title']}」已生成并保存。你可以把它作为候选人的笔试题，也可以继续让我生成考试邀请邮件。{share_message}",
            intent="exam_generate",
            route="/training/exam-generator",
            steps=steps,
            artifacts=artifacts,
            suggestions=["写考试邀请邮件", "去考试管理查看"],
        )
        yield {"type": "final", "response": response.model_dump()}

    async def stream_exam_generation_with_documents(
        self,
        user_id: UUID,
        exam_requirements: Dict[str, Any],
        files: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """上传并处理文档后，基于文档生成并保存考试试卷"""
        exam = self._normalize_exam_requirements(exam_requirements)
        total = len(files)
        steps = [
            AgentStep(id="upload_docs", title="接收参考文档", status="completed", detail=f"已接收 {total} 个文档"),
            AgentStep(id="process_docs", title="解析文档内容", status="running", detail="正在提取文档文本"),
            AgentStep(id="generate_exam", title="基于文档生成试卷", status="pending", tool="generate_exam"),
            AgentStep(id="save_exam", title="保存试卷", status="pending"),
        ]
        artifacts: List[AgentArtifact] = []
        yield self._tool_stream_event("progress", f"已收到 {total} 个参考文档，开始解析文档内容。", "exam_generate", "/training/exam-generator", steps, artifacts)

        # 如果用户是从“当前面试方案”继续生成试卷，会读取最近面试方案上下文
        exam = await self._hydrate_exam_interview_context(exam, user_id, conversation_id)
        if exam.get("interview_plan_context"):
            steps[0] = steps[0].model_copy(update={
                "detail": f"已接收 {total} 个文档，并关联当前面试方案",
            })
            artifacts.append(AgentArtifact(
                type="exam_interview_plan_context",
                title="试卷参考面试方案",
                content={
                    "title": exam["interview_plan_context"].get("title"),
                    "plan_id": exam["interview_plan_context"].get("plan_id"),
                },
            ))
            yield self._tool_stream_event(
                "artifact",
                f"已关联面试方案「{exam['interview_plan_context'].get('title')}」，出题会同时参考文档和面试方案。",
                "exam_generate",
                "/training/exam-generator",
                steps,
                artifacts,
            )

        knowledge_files: List[Dict[str, Any]] = []
        for index, file_info in enumerate(files, start=1):
            filename = file_info["filename"]
            steps[1] = steps[1].model_copy(update={"status": "running", "detail": f"正在解析第 {index}/{total} 个文档：{filename}"})
            yield self._tool_stream_event("progress", f"正在解析文档：{filename}", "exam_generate", "/training/exam-generator", steps, artifacts)

            # 保存上传文档到 Document 表
            document = await self._save_exam_source_document(
                filename=filename,
                content=file_info["content"],
                user_id=user_id,
            )
            if not document.extracted_content:
                # 如果 Document 没有 extracted_content，则提取文本
                extracted_content = await extract_text_content(document.file_path, document.mime_type)
                if not extracted_content:
                    raise ValueError(f"{filename} 未能解析出文本内容，请上传 PDF、DOCX、TXT 或 MD 格式的文本型文档")
                document.extracted_content = extracted_content
                await self.db.commit()
                await self.db.refresh(document)
            knowledge_files.append({"id": str(document.id), "fileName": document.filename})

        steps[1] = steps[1].model_copy(update={"status": "completed", "detail": f"已完成 {len(knowledge_files)} 个文档解析"})
        steps[2] = steps[2].model_copy(update={"status": "running", "detail": "正在基于文档内容生成试卷..."})
        artifacts.append(AgentArtifact(
            type="exam_source_documents",
            title="试卷参考文档",
            content=knowledge_files,
        ))
        yield self._tool_stream_event("artifact", "文档解析完成，开始基于文档生成试卷。", "exam_generate", "/training/exam-generator", steps, artifacts)

        # 进入真正试卷生成流程
        async for event in self.stream_exam_generation(
            user_id=user_id,
            exam_requirements={**exam, "knowledge_files": knowledge_files},
            conversation_id=conversation_id,
        ):
            if event.get("response") and event["response"].get("steps"):
                response = event["response"]
                response["steps"] = [step.model_dump() for step in steps[:2]] + response["steps"][1:]
                response["artifacts"] = [artifact.model_dump() for artifact in artifacts] + response.get("artifacts", [])
                if event.get("type") == "final":
                    response["message"] = f"已基于 {len(knowledge_files)} 个上传文档生成并保存试卷。{response['message']}"
            yield event
