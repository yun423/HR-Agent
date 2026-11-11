"""
v1端点的主API路由
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, conversations, documents, knowledge_base, chat, knowledge_assistant, stats, hr_workflows, scoring_criteria, job_description, resume_evaluation, interview_plan, email_configs, exam_management, intent_router, agent

api_router = APIRouter()

# 包含所有端点路由
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(knowledge_assistant.router, prefix="/knowledge-assistant", tags=["knowledge-assistant"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(hr_workflows.router, prefix="/hr-workflows", tags=["hr-workflows"])
api_router.include_router(job_description.router, prefix="/job-descriptions", tags=["job-descriptions"])
api_router.include_router(scoring_criteria.router, prefix="/scoring-criteria", tags=["scoring-criteria"])
api_router.include_router(resume_evaluation.router, prefix="/resume-evaluation", tags=["resume-evaluation"])
api_router.include_router(interview_plan.router, prefix="/interview-plans", tags=["interview-plans"])
api_router.include_router(email_configs.router, prefix="/email-configs", tags=["email-configs"])
api_router.include_router(exam_management.router, prefix="/exam-management", tags=["exam-management"])
api_router.include_router(intent_router.router, prefix="/intent", tags=["intent"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])


@api_router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "message": "HR Agent API正在运行"}
