"""
Dify工作流API端点
通过Dify工作流处理各种HR自动化任务，支持工作流类型1-6

负责一组 HR 工作流接口，挂载前缀是 /hr-workflows。
主要接口：
    POST /hr-workflows/parse-requirements
    POST /hr-workflows/generate-jd
    POST /hr-workflows/generate-scoring-criteria
    POST /hr-workflows/evaluate
    POST /hr-workflows/generate-interview-plan-by-resume
    POST /hr-workflows/papers/parse-intent
    POST /hr-workflows/papers/generate
    POST /hr-workflows/papers/submit

它把多个业务串起来：需求解析、JD生成、评分标准生成、简历评价、面试方案生成、试卷意图解析、试卷生成、考试提交。
很多接口会调用 DifyService 走 Dify工作流，
也会调用 ResumeEvaluationService、JobDescriptionService、ScoringCriteriaService、ExamService 等服务保存结果。
这个文件更像“组合型业务入口”，把多个 service 编排成完整 HR 流程。

"""
from typing import Any, Optional, Dict, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import time
import logging

from app.core.database import get_db
from app.schemas.user import User as UserSchema
from app.models.user import User
from app.models.resume_evaluation import ResumeEvaluation
from app.services.dify_service import DifyService
from app.services.resume_evaluation_service import ResumeEvaluationService
from app.services.job_description_service import JobDescriptionService
from app.schemas.resume_evaluation import ResumeEvaluationResult
from app.api.deps import get_current_user
from app.core.logging import logger
from app.schemas.job_description import JDGenerateRequest
from app.schemas.scoring_criteria import ScoringCriteriaGenerateRequest
from app.schemas.exam import ExamGenerateRequest, ExamSubmitRequest
from app.services.kb_selection_service import KBSelectionService
from app.schemas.intent import RequirementParseRequest, RequirementParseResponse, ExamIntentParseRequest, KnowledgeFileInfo, ExamIntentParseResponse

router = APIRouter()


from pydantic import BaseModel

@router.post("/parse-requirements")
async def parse_requirements(
    request: RequirementParseRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    将用户自然语言需求解析为结构化字段，供前端表单自动填充
    示例输入："JAVA开发工程师、3-5年工作经验、工作地点北京，薪资15000-20000"
    返回JSON字段：job_title, location, salary, experience, education, job_type, skills, benefits, department, additional_requirements
    """
    try:
        dify_service = DifyService()
        prompt = (
            "你是一个招聘助手。请从以下中文需求中提取结构化字段，并严格以JSON格式返回。\n"
            "不要添加解释，不要返回除JSON外的任何内容。\n"
            "需求文本：\n" + request.text + "\n\n"
            "JSON字段定义：{\n"
            "  \"job_title\": 岗位名称（如JAVA开发工程师、财务经理），\n"
            "  \"department\": 部门（如技术部、财务部，若无法判断可为空），\n"
            "  \"location\": 工作地点（城市名），\n"
            "  \"salary\": 薪资范围（原样返回，如15000-20000或25-35K），\n"
            "  \"experience\": 工作经验（如3-5年、5年以上），\n"
            "  \"education\": 学历要求（如本科、专科，若未提及可为空），\n"
            "  \"job_type\": 工作性质（如全职、兼职，若未提及可为空），\n"
            "  \"skills\": 技能标签数组（如[\"Java\", \"Spring\"]），\n"
            "  \"benefits\": 福利数组（如[\"五险一金\", \"带薪年假\"]），\n"
            "  \"additional_requirements\": 其他补充要求（原文提炼）。\n"
            "}\n"
            "示例返回：{\n"
            "  \"job_title\": \"JAVA开发工程师\",\n"
            "  \"department\": \"技术部\",\n"
            "  \"location\": \"北京\",\n"
            "  \"salary\": \"15000-20000\",\n"
            "  \"experience\": \"3-5年\",\n"
            "  \"education\": \"本科\",\n"
            "  \"job_type\": \"全职\",\n"
            "  \"skills\": [\"Java\", \"Spring\", \"MySQL\"],\n"
            "  \"benefits\": [\"五险一金\", \"带薪年假\"],\n"
            "  \"additional_requirements\": \"具备良好的沟通能力\"\n"
            "}"
        )

        ai_response = await dify_service.call_workflow_sync(
            workflow_type=1,
            query=prompt,
            conversation_id=request.conversation_id,
            additional_inputs={"task": "parse_requirements"}
        )

        answer_text = ""
        if isinstance(ai_response, dict):
            if "answer" in ai_response:
                answer_text = ai_response["answer"]
            elif "data" in ai_response and isinstance(ai_response["data"], dict) and "answer" in ai_response["data"]:
                answer_text = ai_response["data"]["answer"]
            else:
                answer_text = json.dumps(ai_response, ensure_ascii=False)
        else:
            answer_text = str(ai_response)

        json_str = answer_text.strip()
        if "```" in json_str:
            if "```json" in json_str:
                start = json_str.find("```json") + 7
            else:
                start = json_str.find("```") + 3
            end = json_str.find("```", start)
            if end > start:
                json_str = json_str[start:end].strip()

        parsed: Dict[str, Any] = {}
        try:
            parsed = json.loads(json_str)
        except Exception:
            import re
            text = request.text
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
                "additional_requirements": text
            }
            title_match = re.search(r"([A-Za-z]+开发工程师|[\u4e00-\u9fa5A-Za-z]+经理|[\u4e00-\u9fa5A-Za-z]+工程师)", text)
            if title_match:
                parsed["job_title"] = title_match.group(1)
            exp_match = re.search(r"(\d+\s*-\s*\d+年|\d+年以上)", text)
            if exp_match:
                parsed["experience"] = exp_match.group(1).replace(" ", "")
            loc_match = re.search(r"北京|上海|深圳|广州|杭州|南京|成都|重庆|苏州|武汉|西安", text)
            if loc_match:
                parsed["location"] = loc_match.group(0)
            sal_match = re.search(r"(\d+\s*-\s*\d+K|\d+\s*-\s*\d+|\d+K\s*-\s*\d+K)", text, re.IGNORECASE)
            if sal_match:
                parsed["salary"] = sal_match.group(1).replace(" ", "")
            edu_match = re.search(r"本科|专科|硕士|博士", text)
            if edu_match:
                parsed["education"] = edu_match.group(0)
            jobtype_match = re.search(r"全职|兼职|实习", text)
            if jobtype_match:
                parsed["job_type"] = jobtype_match.group(0)

        result = RequirementParseResponse(
            job_title=parsed.get("job_title"),
            department=parsed.get("department"),
            location=parsed.get("location"),
            salary=parsed.get("salary"),
            experience=parsed.get("experience"),
            education=parsed.get("education"),
            job_type=parsed.get("job_type"),
            skills=parsed.get("skills") or [],
            benefits=parsed.get("benefits") or [],
            additional_requirements=parsed.get("additional_requirements")
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error parsing requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析需求失败: {str(e)}"
        )

@router.post("/generate-jd")
async def generate_job_description(
    request: JDGenerateRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    生成岗位JD (Job Description)
    工作流类型: type=1
    """
    try:
        dify_service = DifyService()
        
        # 构建查询内容
        query_parts = [f"请基于给定要求，生成岗位JD。要求如下：{request.requirements}"]
        
        if request.position_title:
            query_parts.append(f"岗位名称：{request.position_title}")
        if request.department:
            query_parts.append(f"部门：{request.department}")
        if request.experience_level:
            query_parts.append(f"经验要求：{request.experience_level}")
        
        query = "\n".join(query_parts)
        
        # 额外输入参数
        additional_inputs = {}
        if request.position_title:
            additional_inputs["position_title"] = request.position_title
        if request.department:
            additional_inputs["department"] = request.department
        if request.experience_level:
            additional_inputs["experience_level"] = request.experience_level
        
        if request.stream:
            # 流式响应
            async def generate_stream():
                async for chunk in dify_service.call_workflow_stream(
                    workflow_type=1,
                    query=query,
                    conversation_id=request.conversation_id,
                    additional_inputs=additional_inputs
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 同步响应
            result = await dify_service.call_workflow_sync(
                workflow_type=1,
                query=query,
                conversation_id=request.conversation_id,
                additional_inputs=additional_inputs
            )
            return result
            
    except Exception as e:
        logger.error(f"生成JD失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成JD失败: {str(e)}"
        )


@router.post("/generate-scoring-criteria")
async def generate_scoring_criteria(
    request: ScoringCriteriaGenerateRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    生成简历评分标准
    基于JD内容生成对应的简历评分标准
    工作流类型: type=2
    """
    try:
        dify_service = DifyService()
        
        # 构建查询内容
        query_parts = [
            f"请基于以下JD内容，生成详细的简历评分标准：\n{request.jd_content}",
            "\n请生成包含以下维度的评分标准：",
            "1. 技能匹配度（40%）",
            "2. 工作经验匹配度（30%）", 
            "3. 教育背景匹配度（15%）",
            "4. 项目经验匹配度（15%）",
            "\n每个维度请提供具体的评分细则和分数区间。"
        ]
        
        if request.job_title:
            query_parts.append(f"\n岗位名称：{request.job_title}")
            
        if request.requirements:
            if request.requirements.get('experience'):
                query_parts.append(f"经验要求：{request.requirements['experience']}")
            if request.requirements.get('education'):
                query_parts.append(f"学历要求：{request.requirements['education']}")
            if request.requirements.get('skills'):
                skills = request.requirements['skills']
                if isinstance(skills, list):
                    query_parts.append(f"技能要求：{', '.join(skills)}")
                else:
                    query_parts.append(f"技能要求：{skills}")
        
        query = "\n".join(query_parts)
        
        # 额外输入参数
        additional_inputs = {
            "jd_content": request.jd_content
        }
        if request.job_title:
            additional_inputs["job_title"] = request.job_title
        if request.requirements:
            additional_inputs["requirements"] = json.dumps(request.requirements, ensure_ascii=False)
        
        if request.stream:
            # 流式响应
            async def generate_stream():
                async for chunk in dify_service.call_workflow_stream(
                    workflow_type=2,  # 使用type=2用于评分标准生成
                    query=query,
                    conversation_id=request.conversation_id,
                    additional_inputs=additional_inputs
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 同步响应
            result = await dify_service.call_workflow_sync(
                workflow_type=2,
                query=query,
                conversation_id=request.conversation_id,
                additional_inputs=additional_inputs
            )
            return result
        
    except Exception as e:
        logger.error(f"生成评分标准失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成评分标准失败: {str(e)}"
        )
    
@router.post("/evaluate", response_model=ResumeEvaluationResult)
async def evaluate_resume(
    file: UploadFile = File(..., description="简历文件 (支持PDF、TXT、DOC、DOCX)"),
    job_description_id: str = Form(..., description="职位描述ID"),
    conversation_id: Optional[str] = Form(None, description="对话ID"),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上传简历并进行AI评价
    工作流类型: type=3
    """
    try:
        # 验证参数格式
        jd_uuid, conv_uuid = await ResumeEvaluationService.validate_evaluation_params(
            job_description_id, conversation_id
        )
        
        # 读取文件内容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 创建评价服务并执行评价
        evaluation_service = ResumeEvaluationService(db)
        result = await evaluation_service.evaluate_resume(
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            job_description_id=jd_uuid,
            conversation_id=conv_uuid
        )
        
        return ResumeEvaluationResult(**result)
        
    except ValueError as e:
        logger.warning(f"简历评价参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"简历评价失败: {e}")
        raise HTTPException(status_code=500, detail="简历评价服务暂时不可用")
    
@router.post("/generate-interview-plan-by-resume")
async def generate_interview_plan_by_resume(
    resume_id: str = Form(..., description="简历ID"),
    conversation_id: str = Form(None, description="对话ID"),
    stream: bool = Form(True, description="是否流式返回"),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    根据简历ID生成面试方案
    工作流类型: type=4
    """
    try:
        # 查询简历评价记录
        result = await db.execute(
            select(ResumeEvaluation).where(
                ResumeEvaluation.id == resume_id,
                ResumeEvaluation.user_id == current_user.id
            )
        )
        resume_evaluation = result.scalar_one_or_none()
        
        if not resume_evaluation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="简历记录未找到"
            )
        
        # 通过远程服务查询关联的JD
        jd_service = JobDescriptionService(db)
        try:
            job_description = await jd_service.get_job_description(
                jd_id=str(resume_evaluation.job_description_id),
                user_id=current_user.id
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="关联的职位描述未找到"
            )
        except Exception as e:
            logger.error(f"获取职位描述失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取职位描述失败: {str(e)}"
            )

        # 构建简历内容
        jianli_content = resume_evaluation.resume_content
        
        dify_service = DifyService()
        
        # 构建查询内容
        query = f"请根据简历和JD要求生成面试方案。"
        
        # 额外输入参数
        additional_inputs = {
            "jianli": jianli_content,
            "jd": job_description.content
        }
        
        if stream:
            # 流式响应
            async def generate_stream():
                async for chunk in dify_service.call_workflow_stream(
                    workflow_type=4,
                    query=query,
                    conversation_id=conversation_id,
                    additional_inputs=additional_inputs
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 同步响应
            result = await dify_service.call_workflow_sync(
                workflow_type=4,
                query=query,
                conversation_id=conversation_id,
                additional_inputs=additional_inputs
            )
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating interview plan by resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成面试方案失败: {str(e)}"
        )

@router.post("/papers/parse-intent")
async def parse_exam_intent(
    request: ExamIntentParseRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    将自然语言试卷意图解析为结构化字段，供前端表单自动填充
    支持解析：标题/科目、总分、难度、时长、题量（单选/多选/简答/填空）、特殊要求
    """
    import re
    try:
        dify_service = DifyService()
        prompt = (
            "你是考试出题助手。请从以下中文需求中提取结构化字段，并严格以JSON格式返回。\n"
            "不要添加解释，不要返回除JSON外的任何内容。\n"
            "需求文本：\n" + request.text + "\n\n"
            "JSON字段定义：{\n"
            "  \"title\": 试卷标题（若未提及可从语义中提取或留空）,\n"
            "  \"subject\": 科目（如Java、市场营销，若未提及可留空）,\n"
            "  \"total_score\": 整数，总分（若未提及，默认100）,\n"
            "  \"difficulty\": 难度（easy/medium/hard）,\n"
            "  \"duration\": 整数，考试时长（分钟）,\n"
            "  \"question_counts\": 对象，包含各题型数量，如{\n"
            "    \"single_choice\": 单选题数量（整数，若未提及默认为5）,\n"
            "    \"multiple_choice\": 多选题数量（整数，若未提及默认为5）,\n"
            "    \"short_answer\": 简答题数量（整数，若未提及默认为2）\n"
            "  },\n"
            "  \"special_requirements\": 其他补充要求（原文提炼，若无则空字符串）\n"
            "}\n"
            "示例返回：{\n"
            "  \"title\": \"Java基础测试\",\n"
            "  \"subject\": \"Java\",\n"
            "  \"total_score\": 100,\n"
            "  \"difficulty\": \"medium\",\n"
            "  \"duration\": 90,\n"
            "  \"question_counts\": {\n"
            "    \"single_choice\": 10,\n"
            "    \"multiple_choice\": 5,\n"
            "    \"short_answer\": 2,\n"
            "    \"fill_blank\": 0\n"
            "  },\n"
            "  \"special_requirements\": \"题目覆盖集合、泛型、异常处理等\"\n"
            "}"
        )

        ai_response = await dify_service.call_workflow_sync(
            workflow_type=5,
            query=prompt,
            conversation_id=request.conversation_id,
            additional_inputs={"task": "parse_exam_intent"}
        )

        answer_text = ""
        if isinstance(ai_response, dict):
            if "answer" in ai_response:
                answer_text = ai_response["answer"]
            else:
                try:
                    answer_text = json.dumps(ai_response, ensure_ascii=False)
                except Exception:
                    answer_text = ""
        elif isinstance(ai_response, str):
            answer_text = ai_response

        parsed: Dict[str, Any] = {}
        if answer_text:
            try:
                parsed = json.loads(answer_text)
            except json.JSONDecodeError:
                parsed = {}

        text = request.text
        def find_int(pattern: str) -> Optional[int]:
            m = re.search(pattern, text)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
            return None

        def extract_named_title(raw_text: str) -> Optional[str]:
            patterns = [
                r"(?:试卷名称|试卷名|标题|名称|名字)(?:是|为|叫|设为|定为)?[:：]?\s*([^\n，,。；;]+)",
                r"(?:就叫|叫做|叫|命名为|取名为|起名为)\s*([^\n，,。；;]+?)(?:吧|。|$)",
            ]
            for pattern in patterns:
                match = re.search(pattern, raw_text)
                if match:
                    title_value = match.group(1).strip()
                    return re.sub(r"(?:的)?试卷$", "", title_value).strip() or None
            return None

        def extract_subject(raw_text: str) -> Optional[str]:
            patterns = [
                r"(?:生成|出|创建|制作)(?:一份|一个)?\s*([^\n，,。；;]{1,30}?)(?:的)?(?:试卷|考试|测试|笔试)",
                r"([^\n，,。；;]{1,30}?)(?:的)?(?:试卷|考试|测试|笔试)",
            ]
            for pattern in patterns:
                match = re.search(pattern, raw_text)
                if match:
                    subject_value = match.group(1).strip(" 的")
                    return subject_value or None
            return None

        def extract_question_count(labels: List[str]) -> Optional[int]:
            for label in labels:
                match = re.search(rf"(\d+)\s*(?:道|个)?\s*{label}|{label}\s*(\d+)\s*(?:道|个)?", text)
                if match:
                    return int(match.group(1) or match.group(2))
            return None

        difficulty_map = {
            '简单': 'easy', '易': 'easy', '基础': 'easy',
            '中等': 'medium', '一般': 'medium',
            '困难': 'hard', '难': 'hard', '高级': 'hard'
        }
        difficulty = parsed.get('difficulty') or next((difficulty_map[k] for k in difficulty_map if k in text), None) or 'medium'

        total_score = parsed.get('total_score')
        if not isinstance(total_score, int):
            total_score = find_int(r"总分[:：]?\s*(\d+)") or find_int(r"(\d+)\s*分") or 100

        duration = parsed.get('duration')
        if not isinstance(duration, int):
            duration = find_int(r"时长[:：]?\s*(\d+)\s*分钟") or find_int(r"(\d+)\s*分钟") or 90

        qc = parsed.get('question_counts') or {}
        def qc_val(key: str, patterns: List[str]) -> int:
            v = qc.get(key)
            if isinstance(v, int) and v >= 0:
                return v
            for p in patterns:
                res = find_int(p)
                if isinstance(res, int):
                    return res
            return 0

        single_choice = (
            qc_val('single_choice', [r"单选题\s*(\d+)", r"单选\s*(\d+)"])
            or extract_question_count(["单选题", "单选", "选择题"])
            or 0
        )
        multiple_choice = (
            qc_val('multiple_choice', [r"多选题\s*(\d+)", r"多选\s*(\d+)"])
            or extract_question_count(["多选题", "多选"])
            or 0
        )
        short_answer = (
            qc_val('short_answer', [r"简答题\s*(\d+)", r"简答\s*(\d+)"])
            or extract_question_count(["简答题", "简答", "问答题", "问答"])
            or 0
        )
        fill_blank = (
            qc_val('fill_blank', [r"填空题\s*(\d+)", r"填空\s*(\d+)"])
            or extract_question_count(["填空题", "填空"])
            or 0
        )

        title_match = re.search(r"(试卷名称|标题)[:：]?\s*([^\n]+)", text)
        subject_match = re.search(r"(科目|主题)[:：]?\s*([^\n]+)", text)
        explicit_title = extract_named_title(text)
        title = explicit_title or parsed.get('title') or (title_match and title_match.group(2).strip())
        subject = parsed.get('subject') or (subject_match and subject_match.group(2).strip()) or extract_subject(text)
        if not subject and title:
            subject = title

        special_requirements = parsed.get('special_requirements')
        if not special_requirements:
            m = re.search(r"(要求|注意事项|其他)[:：]?\s*(.+)", text)
            special_requirements = m.group(2).strip() if m else ""

        result = ExamIntentParseResponse(
            title=title,
            subject=subject,
            total_score=total_score,
            difficulty=difficulty,
            duration=duration,
            question_counts={
                'single_choice': single_choice,
                'multiple_choice': multiple_choice,
                'short_answer': short_answer,
                'fill_blank': fill_blank
            },
            special_requirements=special_requirements
        )

        # 自动选择最匹配的知识库文档，填充 knowledge_files
        try:
            selector = KBSelectionService(db)
            question = "".join([
                subject or "",
                " ",
                title or "",
                " ",
                special_requirements or "",
            ]).strip() or (request.text if hasattr(request, 'text') else '')
            selection = await selector.select_kb_for_question(
                question=question,
                user_id=current_user.id,
                max_candidates=200,
            )
            knowledge_files: List[KnowledgeFileInfo] = []
            if selection and selection.get("document_id"):
                knowledge_files.append(
                    KnowledgeFileInfo(
                        id=str(selection.get("document_id")),
                        fileName=selection.get("filename")
                    )
                )
            result.knowledge_files = knowledge_files
        except Exception as se:
            logger.warning(f"知识库自动选择失败: {se}")

        return result
    except Exception as e:
        logger.error(f"试卷意图解析失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"试卷意图解析失败: {str(e)}"
        )

# 生成试卷
@router.post("/papers/generate")
async def generate_exam(
    request: ExamGenerateRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    基于文档内容生成试卷
    type=5
    """
    try:
        from app.services.exam_service import ExamService

        # 初始化试卷服务
        exam_service = ExamService(db)

        if request.stream:
            # 流式响应
            stream_generator = await exam_service.generate_exam(
                title=request.title,
                subject=request.subject,
                total_score=request.total_score,
                user_id=current_user.id,
                description=request.description,
                difficulty=request.difficulty,
                duration=request.duration,
                question_types=request.question_types,
                question_counts=request.question_counts,
                knowledge_files=request.knowledge_files,
                special_requirements=request.special_requirements,
                conversation_id=request.conversation_id,
                stream=True
            )

            return StreamingResponse(
                stream_generator,
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 同步响应
            result = await exam_service.generate_exam(
                title=request.title,
                subject=request.subject,
                total_score=request.total_score,
                user_id=current_user.id,
                description=request.description,
                difficulty=request.difficulty,
                duration=request.duration,
                question_types=request.question_types,
                question_counts=request.question_counts,
                knowledge_files=request.knowledge_files,
                special_requirements=request.special_requirements,
                conversation_id=request.conversation_id,
                stream=False
            )
            return result

    except Exception as e:
        logger.error(f"Error generating exam: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成试卷失败: {str(e)}"
        )    

# 提交考试答案
@router.post("/papers/submit")
async def submit_exam(
    request: ExamSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    提交考试答案并进行自动评分：选择题直接判分，其他题型调用 Dify。
    """
    try:
        from app.services.exam_service import ExamService

        # 初始化试卷服务
        exam_service = ExamService(db)

        # 提交考试答案
        result = await exam_service.submit_exam(
            exam_id=request.exam_id,
            student_name=request.student_name,
            department=request.department,
            answers=request.answers,
            exam_content=request.exam_content
        )

        return result
        
    except Exception as e:
        logger.error(f"Error submitting exam: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交考试失败: {str(e)}"
        )
    
