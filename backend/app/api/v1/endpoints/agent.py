"""
HR Agent API 端点

负责 HR Agent 的高级编排接口，挂载前缀是 /agent。
主要接口：
    POST /agent/chat
    POST /agent/chat/stream
    POST /agent/stream
    POST /agent/resume-screen/stream
    POST /agent/interview-plan/stream
    POST /agent/exam/stream
    POST /agent/exam/document-stream

"""

import json
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.agent import AgentChatRequest
from app.schemas.user import User as UserSchema
from app.services.agent_service import AgentService

router = APIRouter()


@router.post("/chat")
async def chat_with_agent(
    request: AgentChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
        通过HR Agent处理自然语言任务
            chat_with_agent 是非流式 Agent 对话。
    """
    try:
        agent_service = AgentService(db)
        response = await agent_service.chat(
            message=request.message.strip(),
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            auto_execute=request.auto_execute,
            confirmed_requirements=request.confirmed_requirements,
            attachments=[item.model_dump() for item in request.attachments],
        )
        return response.model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HR Agent 执行失败: {str(exc)}",
        ) from exc


# 自然语言总入口
@router.post("/chat/stream")
async def stream_chat_with_agent(
    request: AgentChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
        流式处理 HR Agent 自然语言任务
            stream_chat_with_agent 返回流式执行过程。
    """

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_chat_agent(
                message=request.message.strip(),
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                auto_execute=request.auto_execute,
                confirmed_requirements=request.confirmed_requirements,
                attachments=[item.model_dump() for item in request.attachments],
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"HR Agent 执行失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/stream")
async def stream_agent_progress(
    request: AgentChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
        流式返回 HR Agent 执行进度
             stream_agent_progress 返回流式执行过程。
    """
    if not request.confirmed_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="stream 接口需要 confirmed_requirements",
        )

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_recruitment_agent(
                message=request.message.strip(),
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                confirmed_requirements=request.confirmed_requirements,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"HR Agent 执行失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/resume-screen/stream")
async def stream_resume_screening(
    job_description_id: UUID = Form(...),
    conversation_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
        批量上传简历并流式返回筛选进度
            resume-screen/stream 支持上传多个简历文件，流式返回筛选进度。
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少上传一份简历")
    if len(files) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单次最多上传 20 份简历")

    file_payloads = []
    for upload_file in files:
        content = await upload_file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{upload_file.filename} 文件内容为空")
        file_payloads.append({"filename": upload_file.filename, "content": content})

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_resume_screening(
                user_id=current_user.id,
                job_description_id=job_description_id,
                files=file_payloads,
                conversation_id=conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"简历批量筛选失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/interview-plan/stream")
async def stream_interview_plan(
    resume_evaluation_id: UUID = Form(...),
    conversation_id: Optional[str] = Form(None),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    根据已评分简历流式生成面试计划
        interview-plan/stream 根据简历评价生成面试计划。
    """

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_interview_plan(
                user_id=current_user.id,
                resume_evaluation_id=resume_evaluation_id,
                conversation_id=conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"面试计划生成失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/exam/stream")
async def stream_exam_generation(
    request: AgentChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    流式生成并保存考试试卷
        exam/stream 根据结构化需求生成试卷。
    """
    if not request.confirmed_requirements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="exam stream 接口需要 confirmed_requirements",
        )

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_exam_generation(
                user_id=current_user.id,
                exam_requirements=request.confirmed_requirements,
                conversation_id=request.conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"考试生成失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/exam/document-stream")
async def stream_exam_generation_with_documents(
    exam_requirements: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
        上传参考文档后，基于文档流式生成并保存考试试卷
            exam/document-stream 支持上传参考文档后生成试卷。
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少上传一个参考文档")
    if len(files) > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单次最多上传 5 个参考文档")

    try:
        parsed_requirements = json.loads(exam_requirements)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="考试配置 JSON 格式不正确") from exc

    file_payloads = []
    for upload_file in files:
        content = await upload_file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{upload_file.filename} 文件内容为空")
        file_payloads.append({"filename": upload_file.filename, "content": content})

    async def generate():
        try:
            agent_service = AgentService(db)
            async for event in agent_service.stream_exam_generation_with_documents(
                user_id=current_user.id,
                exam_requirements=parsed_requirements,
                files=file_payloads,
                conversation_id=conversation_id,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            error_event = {"type": "error", "error": f"基于文档生成考试失败: {str(exc)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
