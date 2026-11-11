import re


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _fallback_draft() -> str:
    return (
        "主题：【待补充岗位】面试/考试通知\n\n"
        "候选人您好，\n\n"
        "感谢您关注我们的【待补充岗位】机会。我们希望邀请您参与下一轮招聘环节。\n\n"
        "时间：【待补充】\n地点/方式：【待补充】\n需准备材料：【待补充】\n\n"
        "如时间不便，请回复可替代时间，我们会尽快协调。\n\n"
        "祝好，\n【HR姓名/公司】"
    )


def _build_send_request(user_text: str, draft_text: str, confirmation_action: str) -> dict[str, str]:
    recipient_email = ""
    email_match = EMAIL_PATTERN.search(user_text or "")
    if email_match:
        recipient_email = email_match.group(0)

    subject = "【待补充主题】"
    body = draft_text.strip()
    lines = draft_text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("主题：") or stripped.startswith("Subject:"):
            subject = stripped.split("：", 1)[-1].split(":", 1)[-1].strip() or subject
            body = "\n".join(lines[index + 1:]).strip() or body
            break

    return {
        "action": confirmation_action,
        "recipient_email": recipient_email,
        "subject": subject,
        "body": body,
        "draft_text": draft_text.strip(),
    }


async def run_draft_phase(context: dict) -> dict:
    llm_service = context.get("llm_service")
    message = context.get("message", "")
    memory_context = context.get("memory_context", "")
    skill_markdown = context.get("skill_markdown", "")
    confirmation_action = context.get("confirmation_action", "send_email")
    draft_override = str(context.get("draft_text") or "").strip()

    memory_block = f"历史上下文：\n{memory_context}\n" if memory_context else ""
    prompt = (
        "你正在执行 hr-agent-email skill。请先遵循下面的 SKILL.md 工作流，再完成当前任务。\n\n"
        f"{skill_markdown}\n\n"
        "当前执行阶段：draft phase。\n"
        "你是专业 HR。请根据 skill 工作流生成一封中文候选人邮件草稿。\n"
        "请优先按以下结构输出：\n"
        "主题：...\n"
        "\n"
        "正文：\n"
        "要求：包含主题、称呼、正文、下一步动作、署名占位；如果关键信息缺失，用【待补充】标注，不要编造具体时间地点。不要把具体的面试题目发给候选人\n"
        f"{memory_block}"
        f"用户需求：{message}"
    )

    if draft_override:
        draft = draft_override
    else:
        try:
            if llm_service is None:
                from app.services.llm_service import LLMService
                llm_service = LLMService()
            draft = (await llm_service.generate_response(prompt)).strip()
        except Exception:
            draft = _fallback_draft()

    send_request = _build_send_request(message, draft, confirmation_action)
    return {
        "message": draft,
        "steps": [
            {"id": "draft", "title": "生成邮件草稿", "status": "completed", "detail": "已生成可编辑邮件草稿。", "tool": "draft"},
            {"id": "confirm_send", "title": "等待人工确认", "status": "running", "detail": "请确认收件人、主题和正文后再发送。"},
            {"id": "send_email", "title": "发送邮件", "status": "pending", "detail": "确认后使用 backend/skills/hr-agent-email/config.txt 中配置的 SMTP 邮箱发出邮件。", "tool": "send"},
        ],
        "artifacts": [
            {"type": "email_draft", "title": "邮件通知草稿", "content": draft, "metadata": {"skill": "hr-agent-email", "phase": "draft"}},
            {"type": "email_send_request", "title": "确认并发送邮件", "content": send_request, "metadata": {"skill": "hr-agent-email", "phase": "draft"}},
        ],
        "suggestions": [],
        "requires_confirmation": True,
        "missing_fields": ["recipient_email"] if not send_request.get("recipient_email") else [],
    }


async def run_send_phase(context: dict) -> dict:
    payload = context.get("confirmed_requirements") or {}
    email_service = context.get("email_service")
    user_id = context.get("user_id")
    recipient_email = str(payload.get("recipient_email") or "").strip()
    subject = str(payload.get("subject") or "").strip()
    body = str(payload.get("body") or "").strip()

    missing_fields = []
    if not recipient_email:
        missing_fields.append("recipient_email")
    if not subject:
        missing_fields.append("subject")
    if not body:
        missing_fields.append("body")

    try:
        result = await email_service.send_agent_email(
            user_id=user_id,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )
    except ValueError as exc:
        return {
            "message": str(exc),
            "steps": [
                {"id": "confirm_send", "title": "确认邮件内容", "status": "completed", "detail": "已收到人工确认。"},
                {"id": "send_email", "title": "发送邮件", "status": "failed", "detail": str(exc), "tool": "send"},
            ],
            "artifacts": [
                {"type": "email_send_request", "title": "确认并发送邮件", "content": payload, "metadata": {"skill": "hr-agent-email", "phase": "send"}}
            ],
            "suggestions": ["填写 backend/skills/hr-agent-email/config.txt", "修改收件人后重试", "重新生成邮件草稿"],
            "requires_confirmation": True,
            "missing_fields": missing_fields,
        }

    return {
        "message": f"邮件已提交给 SMTP 服务器，收件人：{result['recipient_email']}。如果后续收到退信，请以退信原因排查收件地址、域名策略或发件邮箱信誉。",
        "steps": [
            {"id": "confirm_send", "title": "确认邮件内容", "status": "completed", "detail": "已收到人工确认。"},
            {"id": "send_email", "title": "提交邮件", "status": "completed", "detail": f"已通过 {result['sender_email']} 提交给 SMTP 服务器；最终投递结果以收件方服务器为准。", "tool": "send"},
        ],
        "artifacts": [
            {"type": "email_send_result", "title": "邮件提交结果", "content": result, "metadata": {"skill": "hr-agent-email", "phase": "send"}}
        ],
        "suggestions": ["继续生成下一封邮件", "查看 backend/skills/hr-agent-email/config.txt"],
        "requires_confirmation": False,
        "missing_fields": [],
    }
