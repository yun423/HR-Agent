"""
简历评价核心服务：
    负责上传简历、解析文本、匹配JD、获取评分模型、调用Dify/AI评价、解析AI返回、保存评价结果、查询历史、详情、删除、更新简历状态。
    自动评价流程会根据邮件主题和简历内容找最匹配JD，再生成候选人分数和评价指标。
"""
import logging
import json
import re
import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import numpy as np
from app.models.user import User
import aiofiles
from datetime import datetime
from app.core.config import settings
import httpx

from app.models.resume_evaluation import ResumeEvaluation, ResumeStatus
# from app.models.job_description import JobDescription
from app.schemas.resume_evaluation import (
    ResumeEvaluationCreate,
    AIEvaluationResult,
    EvaluationMetric,
    ResumeEvaluationResponse,
    ResumeEvaluationListResponse
)
from app.schemas.job_description import JobDescriptionResponse
from app.services.dify_service import DifyService
from app.services.resume_parser_service import ResumeParserService
from app.services.llm_service import LLMService
from app.services.remote_service_client import remote_service_client
# 通过大模型进行JD匹配，而非embedding

logger = logging.getLogger(__name__)


class ResumeEvaluationService:
    """简历评价服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dify_service = DifyService()
        self.llm_service = LLMService()
        self.resume_parser = ResumeParserService()

    async def evaluate_resume(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        job_description_id: UUID,
        conversation_id: Optional[UUID] = None,
        email_id: Optional[str] = None,
        jd_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """评价简历

        Args:
            user_id: 评价记录归属的用户ID
            jd_user_id: JD所属的用户ID，用于查询JD详情。不传则使用user_id
        """
        try:
            # 1. 验证文件
            is_valid, message = self.resume_parser.validate_file(filename, len(file_content))
            if not is_valid:
                raise ValueError(message)

            # 2. 提取文本内容
            resume_text = await self.resume_parser.extract_text_from_file(file_content, filename)
            if not resume_text.strip():
                raise ValueError("无法从文件中提取到有效内容")

            # 3. 获取文件信息
            file_info = self.resume_parser.get_file_info(filename, file_content)

            # 4. 获取JD信息（使用JD所属用户ID查询）
            _jd_uid = jd_user_id or user_id
            jd = await self._get_job_description(job_description_id, _jd_uid)
            if not jd:
                raise ValueError("职位描述不存在")

            # 5. 获取评价模型
            evaluation_model = await self._get_evaluation_model(job_description_id)

            # 6. 调用Dify API进行评价
            ai_result, raw_response = await self._call_dify_evaluation(
                resume_text=resume_text,
                evaluation_model=evaluation_model,
                jd_info=jd
            )

            # 7. 保存上传的文件到磁盘
            saved_file_path = await self._save_uploaded_file_content(filename, file_content, user_id)
            logger.info(f"文件已保存到: {saved_file_path}")

            # 更新file_info以包含保存的文件路径
            file_info['file_path'] = saved_file_path

            # 8. 保存评价结果
            evaluation_record = await self._save_evaluation_result(
                user_id=user_id,
                created_by=user_id,
                file_info=file_info,
                resume_text=resume_text,
                ai_result=ai_result,
                job_description_id=job_description_id,
                conversation_id=conversation_id,
                email_id=email_id,
                raw_response=raw_response
            )

            logger.info(f"评价记录已保存，ID: {evaluation_record.id}, 文件路径: {evaluation_record.file_path}")

            # 8. 返回完整结果
            return {
                "id": evaluation_record.id,
                "evaluation_metrics": [metric.model_dump() for metric in ai_result.evaluation_metrics],
                "total_score": ai_result.total_score,
                "name": ai_result.name,
                "position": ai_result.position,
                "workYears": (self._parse_work_years_to_float(ai_result.workYears) or 0.0),
                "education": ai_result.教育水平,
                "age": ai_result.年龄,
                "sex": ai_result.sex,
                "school": ai_result.school,
                "resume_content": resume_text,
                "original_filename": file_info['filename'],
                "created_at": evaluation_record.created_at.isoformat(),
                "updated_at": evaluation_record.updated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"简历评价失败: {e}")
            raise

    async def _save_uploaded_file_content(self, filename: str, file_content: bytes, user_id: UUID) -> str:
        """保存上传的文件内容到磁盘"""
        try:
            # 创建用户特定的上传目录
            upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
            os.makedirs(upload_dir, exist_ok=True)

            # 构建安全的文件路径
            safe_filename = Path(filename).name
            file_path = os.path.join(upload_dir, safe_filename)

            # 如果文件名已存在，添加数字后缀
            counter = 1
            base_name, extension = os.path.splitext(safe_filename)
            original_file_path = file_path

            while os.path.exists(file_path):
                new_filename = f"{base_name}_{counter}{extension}"
                file_path = os.path.join(upload_dir, new_filename)
                counter += 1

            # 实际保存文件内容
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)

            return file_path
        except Exception as e:
            logger.error(f"保存上传文件内容失败: {e}")
            raise

    # 根据简历内容与投递邮件的主题匹配最合适的JD
    async def evaluate_resume_auto(
            self,
            user_id: UUID,
            file_content: bytes,
            filename: str,
            subject: str,
            email_id: str = None,
            conversation_id: Optional[UUID] = None
        ) -> Dict[str, Any]:
            """无JD输入时，自动匹配最合适的JD并进行评价"""
            # 解析文本（复用 evaluate_resume 的前置逻辑）
            is_valid, message = self.resume_parser.validate_file(filename, len(file_content))
            if not is_valid:
                raise ValueError(message)
            resume_text = await self.resume_parser.extract_text_from_file(file_content, filename)
            if not resume_text or not resume_text.strip():
                raise ValueError("无法从简历中提取有效文本")
            # 自动匹配 JD
            #拼接主题与邮件正文
            logger.info(f"开始自动匹配JD，邮件主题: {subject}")
            jd_id, jd_owner_user_id = await self._match_best_jd(subject=subject, resume_text= resume_text, create_by=str(user_id))
            if not jd_id:
                logger.error(f"未匹配到合适的职位描述，邮件主题: {subject}")
                raise ValueError("未匹配到合适的职位描述")
            logger.info(f"匹配到JD: {jd_id}, JD所属用户: {jd_owner_user_id}")
            # 调用已有评价流程，传入JD所属用户ID用于查询JD详情和保存评价记录
            return await self.evaluate_resume(
                user_id=jd_owner_user_id,
                file_content=file_content,
                filename=filename,
                job_description_id=jd_id,
                jd_user_id=jd_owner_user_id,
                conversation_id=conversation_id,
                email_id=email_id
            )

    async def evaluate_resume_text_auto(
        self,
        login_name: str,
        resume_text: str,
        filename: Optional[str] = None,
        subject: str = ""
    ) -> Dict[str, Any]:
        """
        处理文本简历的自动评价流程

        Args:
            login_name: 用户登录名
            resume_text: 简历文本内容
            filename: 文件名（可选）
            subject: 投递邮件主题（可选）

        Returns:
            评价结果字典
        """

        # 验证用户是否存在
        if not login_name:
            raise ValueError("login_name不能为空")

        users = await self.db.execute(select(User).where(User.username == login_name))
        user = users.scalar_one_or_none()
        if not user:
            raise ValueError(f"用户{login_name}不存在")

        user_id = user.id

        # 验证简历文本
        resume_text = (resume_text or "").strip()
        if not resume_text:
            raise ValueError("简历文本内容不能为空")

        # 生成或使用提供的文件名
        safe_default_name = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename = (filename or safe_default_name).strip() or safe_default_name
        # 简单清理可能的非法字符
        filename = Path(filename).name
        if not filename.lower().endswith('.txt'):
            filename = f"{filename}.txt"

        # 保存文本为本地附件 uploads/{user_id}/{filename}
        user_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, filename)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(resume_text.encode("utf-8"))

        # 调用自动匹配与评分服务
        result = await self.evaluate_resume_auto(
            user_id=user_id,
            file_content=resume_text.encode("utf-8"),
            filename=filename,
            subject=subject or ""
        )

        # 回写 file_path 到评价记录
        try:
            from app.models.resume_evaluation import ResumeEvaluation
            eval_id = result.get("id")
            if eval_id:
                stmt = select(ResumeEvaluation).where(
                    ResumeEvaluation.id == eval_id,
                    ResumeEvaluation.user_id == user_id,
                )
                db_result = await self.db.execute(stmt)
                evaluation = db_result.scalar_one_or_none()
                if evaluation:
                    evaluation.file_path = file_path
                    await self.db.commit()
        except Exception as e:
            # 不影响主流程，记录日志
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"评价记录回写 file_path 失败: {e}")

        return result

    async def _fetch_jds(self, user_id: UUID) -> List[JobDescriptionResponse]:
        """从远程服务获取指定用户的JD列表"""
        result_data = await remote_service_client.get(
            endpoint="job-descriptions/",
            user_id=user_id,
            additional_params={"page": 1, "size": 100}
        )
        jd_items = result_data.get("items", [])
        return [JobDescriptionResponse(**jd_data) for jd_data in jd_items]

    async def _match_best_jd(self, subject:str ,resume_text: str,create_by: str) -> Tuple[Optional[UUID], Optional[UUID]]:
        """通过大模型服务判断最匹配的JD

        Returns:
            (jd_id, jd_owner_user_id) - 匹配的JD ID和该JD所属的用户ID
        """
        logger.info(f"开始查询职位描述，create_by: {create_by}")
        try:
            # 调用远程服务获取所有JD
            jds = await self._fetch_jds(UUID(create_by))
            jd_owner_user_id = UUID(create_by)  # 记录当前JD所属的用户ID

            # 如果当前用户没有JD，尝试查找本地其他用户的JD
            if not jds:
                logger.info(f"用户 {create_by} 没有JD，尝试查找其他本地用户的JD")
                try:
                    from sqlalchemy import select as sql_select
                    users_result = await self.db.execute(
                        sql_select(User).where(User.is_active == True).limit(10)
                    )
                    local_users = users_result.scalars().all()
                    for u in local_users:
                        if str(u.id) == create_by:
                            continue
                        logger.info(f"尝试查询用户 {u.id} 的JD")
                        jds = await self._fetch_jds(u.id)
                        if jds:
                            logger.info(f"从用户 {u.id} 找到 {len(jds)} 个JD")
                            jd_owner_user_id = u.id
                            break
                except Exception as e:
                    logger.warning(f"查找其他用户JD失败: {e}")

            logger.info(f"查询到 {len(jds)} 个职位描述")

            # 输出所有JD标题用于调试
            for jd in jds:
                logger.info(f"JD标题: {jd.title}")

            if not jds:
                return None, None

            # 新增逻辑：根据邮件主题关键词匹配职位描述
            # 主题格式：简历-职位名称-姓名
            if subject and "简历-" in subject:
                try:
                    # 解析主题中的职位名称
                    parts = subject.split("-")
                    if len(parts) >= 2:
                        position_name = parts[1].strip()  # 获取职位名称部分
                        logger.info(f"从邮件主题解析出职位名称: {position_name}")

                        # 在JD列表中查找匹配的职位名称
                        for jd in jds:
                            if jd.title:
                                # 使用更宽松的匹配策略，忽略大小写
                                jd_title_clean = jd.title.replace(" ", "").replace("-", "").lower()
                                position_name_clean = position_name.replace(" ", "").replace("-", "").lower()

                                logger.info(f"比较职位名称: '{position_name_clean}' 与 JD标题: '{jd_title_clean}'")

                                # 多种匹配方式
                                if (position_name_clean in jd_title_clean or
                                    jd_title_clean in position_name_clean):
                                    logger.info(f"通过邮件主题匹配到JD: {jd.title}")
                                    return jd.id, jd_owner_user_id

                        # 如果没有精确匹配，尝试模糊匹配
                        logger.info("未找到精确匹配，尝试模糊匹配...")
                        best_match = self._fuzzy_match_jd(position_name, jds)
                        if best_match:
                            logger.info(f"通过模糊匹配找到JD: {best_match.title}")
                            return best_match.id, jd_owner_user_id

                except Exception as e:
                    logger.error(f"邮件主题解析失败: {e}")

            # 组装简洁的 JD 选项，避免超长提示
            jd_options = [
                {
                    "id": str(jd.id),
                    "title": jd.title
                }
                for jd in jds
            ]
            # 构造提示词
            prompt = (
                "你是一个职位匹配助手。"
                "1、如果候选人投递邮件的主题中包括了他要投递的岗位，则直接根据主题subject从给定的JD列表中选择最匹配的一项，匹配到直接输出jd id，不需要再根据简历内容匹配。若没有匹配到，则直接输出None"
                "2、如果投递邮件主题中没有要投递的岗位，则从候选人的简历内容，去从给定的JD列表中选择最匹配的一项。如果没有匹配到合适的岗位，则直接输出None"
                "输出要求：不要给出匹配理由，直接输出jd id的值,或者None"
            )
            try:
                # 使用通用 LLM 服务进行匹配，而不是 Dify 工作流
                import json as _json
                jd_compact = _json.dumps(jd_options, ensure_ascii=False)[:12000]
                llm_input = (
                    f"{prompt}\n\n候选人投递邮件主题：{subject}\n\n候选人简历：\n{resume_text[:8000]}\n\nJD列表(JSON)：\n{jd_compact}\n\n"
                    " "
                )
                jd_id_str = await self.llm_service.generate_response(message=llm_input)
                print(f"LLM JD匹配结果：{jd_id_str}")
                if not jd_id_str:
                    raise ValueError("匹配结果不包含jd_id")
                # 返回UUID
                for jd in jds:
                    if str(jd.id) in jd_id_str:
                        print(f"LLM JD匹配成功：{jd.title}")
                        return jd.id, jd_owner_user_id
                return None, None
            except Exception as e:
                logger.error(f"LLM JD匹配失败，回退关键词匹配: {e}")
                # 回退：按关键词匹配（简单匹配）
                keywords = ["Java", "Python", "前端", "后端", "AI", "算法", "产品", "测试"]
                scores = []
                lower_text = resume_text.lower()
                for jd in jds:
                    agg = " ".join([jd.title or "", jd.requirements or "", jd.skills or ""]).lower()
                    score = sum(1 for kw in keywords if kw.lower() in lower_text and kw.lower() in agg)
                    scores.append(score)
                best_idx = int(np.argmax(scores)) if scores else 0
                return (jds[best_idx].id, jd_owner_user_id) if jds else (None, None)
        except Exception as e:
            logger.error(f"获取所有JD失败: {e}")
            return None, None

    def _partial_match(self, term1: str, term2: str) -> bool:
        """检查两个字符串是否部分匹配"""
        if not term1 or not term2:
            return False

        # 如果一个字符串包含另一个字符串
        if term1 in term2 or term2 in term1:
            return True

        # 检查是否有共同的子串（至少3个字符）
        min_len = min(len(term1), len(term2))
        if min_len >= 3:
            for i in range(min_len - 2):
                substr = term1[i:i+3] if len(term1[i:i+3]) == 3 else None
                if substr and substr in term2:
                    return True

        return False

    def _fuzzy_match_jd(self, position_name: str, jds: List[JobDescriptionResponse]) -> Optional[JobDescriptionResponse]:
        """模糊匹配职位描述"""
        if not position_name or not jds:
            return None

        position_name_clean = position_name.replace(" ", "").replace("-", "").lower()
        logger.info(f"开始模糊匹配职位名称: {position_name_clean}")

        # 尝试多种匹配方式
        for jd in jds:
            if jd.title:
                jd_title_clean = jd.title.replace(" ", "").replace("-", "").lower()
                logger.info(f"比较职位名称: '{position_name_clean}' 与 JD标题: '{jd_title_clean}'")

                # 1. 直接包含关系
                if position_name_clean in jd_title_clean or jd_title_clean in position_name_clean:
                    logger.info(f"模糊匹配成功: {position_name} 匹配到 {jd.title}")
                    return jd

                # 2. 关键词匹配
                position_keywords = set(position_name_clean)
                jd_keywords = set(jd_title_clean)

                # 如果有超过30%的字符重叠，认为匹配（降低阈值）
                union_len = len(position_keywords | jd_keywords)
                if union_len > 0:
                    overlap_ratio = len(position_keywords & jd_keywords) / union_len
                    logger.info(f"关键词重叠比例: {overlap_ratio}")
                    if overlap_ratio > 0.3:
                        logger.info(f"通过关键词匹配成功: {position_name} 匹配到 {jd.title}")
                        return jd

        return None

    async def _get_job_description(self, jd_id: UUID, user_id: UUID) -> Optional[JobDescriptionResponse]:
        """获取职位描述 - 使用远程服务"""
        try:
            result_data = await remote_service_client.get(
                endpoint=f"job-descriptions/{jd_id}",
                user_id=user_id
            )
            return JobDescriptionResponse(**result_data)
        except Exception as e:
            logger.error(f"获取职位描述失败: {e}")
            return None

    async def _get_evaluation_model(self, jd_id: UUID) -> str:
        """获取评价模型"""
        try:
            # 从远程服务获取与JD关联的评分标准
            # 注意：该接口不需要current_user_id参数，直接使用httpx调用
            url = f"{remote_service_client.base_url}/scoring-criteria/by-jd/{jd_id}"
            headers = remote_service_client._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=remote_service_client.timeout
                )
            
            result_data = remote_service_client._handle_response(response)

            # 检查返回数据中是否有content字段
            if result_data and result_data.get('content'):
                return result_data['content']

            # 如果没有找到特定的评价模型，返回默认模型
            return self._get_default_evaluation_model()

        except Exception as e:
            logger.error(f"获取评价模型失败: {e}")
            return self._get_default_evaluation_model()

    def _get_default_evaluation_model(self) -> str:
        """获取默认评价模型"""
        return """
        请根据以下职位要求对简历进行评价，并按照指定的JSON格式返回结果：

        评价维度：
        1. 学历匹配度 (0-20分)
        2. 工作经验匹配度 (0-25分)
        3. 技能匹配度 (0-25分)
        4. 项目经验匹配度 (0-20分)
        5. 综合素质 (0-10分)

        请提取简历中的以下信息：
        - 姓名
        - 应聘岗位
        - 工作年限
        - 教育水平
        - 年龄
        - 性别
        - 毕业院校

        返回格式必须是有效的JSON：
        {
          "evaluation_metrics": [
            {
              "name": "学历",
              "score": 15,
              "max": 20,
              "reason": "本科学历，符合岗位要求"
            }
          ],
          "total_score": 85,
          "name": "张三",
          "position": "前端开发工程师",
          "workYears": "3年",
          "education": "本科",
          "age": 28,
          "sex": "男",
          "school": "上海理工大学"
        }
        """

    async def _call_dify_evaluation(
        self,
        resume_text: str,
        evaluation_model: str,
        jd_info: JobDescriptionResponse
    ) -> tuple[AIEvaluationResult, str]:
        """调用Dify API进行简历评价"""
        try:

            # 调用Dify API (使用工作流类型2进行简历评价)
            response = await self.dify_service.call_workflow_sync(
                workflow_type=3,  # 简历评价工作流
                query=evaluation_model,
                additional_inputs={
                    "jianli": resume_text,
                    "jobName": jd_info.title
                }
            )

            # 解析AI响应
            ai_result = self._parse_ai_response(response)
            raw_response = str(response)  # 保存原始响应
            return ai_result, raw_response

        except Exception as e:
            logger.error(f"调用Dify API失败: {e}")
            raise Exception(f"AI评价服务暂时不可用: {str(e)}")

    def _parse_ai_response(self, response: Dict[str, Any]) -> AIEvaluationResult:
        """解析AI响应，提取评价结果"""
        try:
            # 从Dify响应中提取答案文本
            answer_text = ""
            if "answer" in response:
                answer_text = response["answer"]
            elif "data" in response and "answer" in response["data"]:
                answer_text = response["data"]["answer"]
            else:
                # 如果没有找到answer字段，尝试从其他可能的字段获取
                answer_text = str(response)

            if not answer_text:
                raise ValueError("AI响应为空")

            # 尝试解析JSON
            try:
                # 尝试直接解析JSON
                if answer_text.startswith('{') and answer_text.endswith('}'):
                    result_data = json.loads(answer_text)
                else:
                    # 如果响应包含代码块，提取JSON部分
                    if '```json' in answer_text:
                        start = answer_text.find('```json') + 7
                        end = answer_text.find('```', start)
                        json_str = answer_text[start:end].strip()
                    elif '```' in answer_text:
                        start = answer_text.find('```') + 3
                        end = answer_text.find('```', start)
                        json_str = answer_text[start:end].strip()
                    else:
                        # 如果不是纯JSON，尝试提取JSON部分
                        json_start = answer_text.find('{')
                        json_end = answer_text.rfind('}') + 1
                        if json_start != -1 and json_end > json_start:
                            json_str = answer_text[json_start:json_end]
                        else:
                            raise ValueError("No valid JSON found in response")

                    # 解析JSON
                    result_data = json.loads(json_str)

                # 验证必要字段
                if 'evaluation_metrics' not in result_data:
                    raise ValueError("缺少evaluation_metrics字段")

                if 'total_score' not in result_data:
                    raise ValueError("缺少total_score字段")

                # 构建评价指标列表
                metrics = []
                for metric_data in result_data.get('evaluation_metrics', []):
                    metric = EvaluationMetric(
                        name=metric_data.get('评价指标', ''),
                        score=metric_data.get('score', 0),
                        max=metric_data.get('max', 100),
                        reason=metric_data.get('reason', '')
                    )
                    metrics.append(metric)

                # 规范化字段别名，兼容不同返回命名
                normalized_work_years = (
                    result_data.get('workYears')
                    or result_data.get('work_years')
                    or result_data.get('work_experience')
                    or result_data.get('工作年限')
                    or result_data.get('工作经验')
                )
                # 处理workYears字段，确保能正确转换为float
                try:
                    if normalized_work_years is not None and normalized_work_years != '' and normalized_work_years != '未知':
                        normalized_work_years = float(normalized_work_years)
                    else:
                        normalized_work_years = 0.0
                except (ValueError, TypeError):
                    normalized_work_years = 0.0
                normalized_education = (
                    result_data.get('education')
                    or result_data.get('education_level')
                    or result_data.get('学历')
                    or result_data.get('教育水平')
                )
                try:
                    normalized_age = int(result_data.get('age', result_data.get('年龄', 0)))
                except (ValueError, TypeError):
                    normalized_age = 0

                normalized_sex = (
                    result_data.get('sex')
                    or result_data.get('gender')
                    or result_data.get('性别')
                )
                normalized_school = (
                    result_data.get('school')
                    or result_data.get('毕业院校')
                    or result_data.get('院校')
                    or result_data.get('学校')
                )

                # 构建AI评价结果
                ai_result = AIEvaluationResult(
                    evaluation_metrics=metrics,
                    total_score=result_data.get('total_score', 0),
                    name=result_data.get('name', ''),
                    position=result_data.get('position', ''),
                    workYears=normalized_work_years,
                    教育水平=normalized_education or '',
                    年龄=normalized_age,
                    sex=normalized_sex or '',
                    school=normalized_school or ''
                )

                return ai_result

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}, 原始响应: {answer_text}")
                # 返回默认结果
                return self._create_default_result(answer_text)

        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            return self._create_default_result(str(e))

    def _create_default_result(self, raw_response: str) -> AIEvaluationResult:
        """创建默认评价结果"""
        return AIEvaluationResult(
            evaluation_metrics=[
                EvaluationMetric(
                    name="综合评价",
                    score=60,
                    max=100,
                    reason="AI解析失败，给出默认评分"
                )
            ],
            total_score=60,
            name="未知",
            position="未知",
            workYears=0.0,
            教育水平="未知",
            年龄=None,
            sex="未知",
            school="未知"
        )

    async def _save_evaluation_result(
        self,
        user_id: UUID,
        created_by: UUID,
        file_info: Dict[str, Any],
        resume_text: str,
        ai_result: AIEvaluationResult,
        job_description_id: UUID,
        raw_response: str = "",
        email_id: Optional[str] = None,
        conversation_id: Optional[UUID] = None
    ) -> ResumeEvaluation:
        """保存评价结果 - 从参数获取已保存的文件路径"""
        try:
            # 直接创建ResumeEvaluation对象（文件已经保存）
            evaluation = ResumeEvaluation(
                user_id=user_id,
                created_by = created_by,
                updated_by= created_by,
                email_id =  email_id,
                original_filename=file_info['filename'],
                file_path=file_info.get('file_path'),  # 使用传入的文件路径
                file_type=file_info['file_type'],
                file_size=file_info['file_size'],
                resume_content=resume_text,
                candidate_name=ai_result.name,
                candidate_position=ai_result.position,
                candidate_age=ai_result.年龄,
                candidate_gender=ai_result.sex,
                work_years=(self._parse_work_years_to_float(ai_result.workYears) or 0.0),
                education_level=ai_result.教育水平,
                school=ai_result.school,
                total_score=ai_result.total_score,
                evaluation_metrics=[metric.model_dump() for metric in ai_result.evaluation_metrics],
                job_description_id=job_description_id,
                conversation_id=str(conversation_id) if conversation_id else None,
                ai_response=raw_response
            )
            self.db.add(evaluation)
            await self.db.commit()
            await self.db.refresh(evaluation)

            return evaluation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"保存评价结果失败: {e}")
            raise

    async def get_evaluation_history(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional['ResumeStatus'] = None
    ) -> tuple[List[ResumeEvaluation], int]:
        """获取评价历史和总记录数"""
        try:
            # 构建查询条件 - 按创建时间降序排序
            query = select(ResumeEvaluation).where(ResumeEvaluation.user_id == user_id).order_by(ResumeEvaluation.created_at.desc())

            # 添加状态过滤
            if status:
                query = query.where(ResumeEvaluation.status == status)

            # 获取总记录数
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            # 添加分页
            query = query.offset(skip).limit(limit)

            result = await self.db.execute(query)
            evaluations = result.scalars().all()

            # 添加调试日志
            logger.info(f"查询到 {len(evaluations)} 个评价记录，总记录数: {total}")
            if evaluations:
                logger.info(f"第一个评价记录类型: {type(evaluations[0])}")
                if hasattr(evaluations[0], 'id'):
                    logger.info(f"第一个评价记录ID: {evaluations[0].id}")
                else:
                    logger.info("第一个评价记录没有id属性")

            return evaluations, total

        except Exception as e:
            logger.error(f"获取评价历史失败: {e}", exc_info=True)
            return [], 0

    async def get_evaluation_by_id(
        self,
        evaluation_id: UUID,
        user_id: UUID
    ) -> Optional[ResumeEvaluation]:
        """根据ID获取评价结果"""
        try:
            result = await self.db.execute(
                select(ResumeEvaluation)
                .where(
                    ResumeEvaluation.id == evaluation_id,
                    ResumeEvaluation.user_id == user_id
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取评价结果失败: {e}")
            return None

    def _parse_work_years_to_float(self, text: Optional[str]) -> Optional[float]:
        """将工作年限字符串解析为数字（年）。支持格式如"3年"、"1.5年"、"1-3年"、"约2年"。
        - 解析到范围时取平均值；
        - 仅提取到一个数值时使用该数值；
        - 解析失败返回None。
        """
        if not text:
            return None
        s = str(text).strip().lower()
        # 常见非数值占位统一视为0（回退到调用处做 or 0.0）
        if s in {"未知", "不详", "none", "null", "n/a", "na", "--", "-", "", "应届", "应届生", "fresh"}:
            return 0.0
        # 匹配范围 "a-b" 或 "a – b"
        m_range = re.search(r"(\d+(?:\.\d+)?)\s*[\-~–—]\s*(\d+(?:\.\d+)?)", s)
        if m_range:
            try:
                a = float(m_range.group(1))
                b = float(m_range.group(2))
                return (a + b) / 2.0
            except Exception:
                pass
        # 提取第一个数字
        m_single = re.search(r"(\d+(?:\.\d+)?)", s)
        if m_single:
            try:
                return float(m_single.group(1))
            except Exception:
                return None
        return None

    # 静态方法用于参数验证
    @staticmethod
    async def validate_uuid_param(param: str, param_name: str) -> UUID:
        """验证UUID格式参数"""
        try:
            return UUID(param)
        except ValueError:
            raise ValueError(f"无效的{param_name}格式")

    @staticmethod
    async def validate_evaluation_params(
        job_description_id: str,
        conversation_id: Optional[str] = None
    ) -> Tuple[UUID, Optional[UUID]]:
        """验证评价参数格式"""
        # 验证job_description_id格式
        try:
            jd_uuid = UUID(job_description_id)
        except ValueError:
            raise ValueError("无效的职位描述ID格式")

        # 验证conversation_id格式（如果提供）
        conv_uuid = None
        if conversation_id:
            try:
                conv_uuid = UUID(conversation_id)
            except ValueError:
                raise ValueError("无效的对话ID格式")

        return jd_uuid, conv_uuid

    @staticmethod
    async def validate_status_param(status: Optional[str]) -> Optional[ResumeStatus]:
        """验证状态参数"""
        if not status:
            return None

        try:
            return ResumeStatus(status)
        except ValueError:
            raise ValueError("无效的状态值，支持的状态: pending, rejected, interview")

    @staticmethod
    async def get_supported_formats() -> Dict[str, Any]:
        """获取支持的文件格式"""
        return {
            "supported_extensions": [".pdf", ".txt", ".doc", ".docx"],
            "max_file_size": "10MB",
            "description": "支持PDF、TXT、DOC、DOCX格式的简历文件"
        }

    async def get_evaluation_history_with_pagination(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ResumeStatus] = None
    ) -> ResumeEvaluationListResponse:
        """获取评价历史并返回分页响应"""
        evaluations, total = await self.get_evaluation_history(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status
        )

        # 转换为响应格式
        evaluation_responses = []
        for evaluation in evaluations:
            response = ResumeEvaluationResponse(
                id=evaluation.id,
                original_filename=evaluation.original_filename,
                file_type=evaluation.file_type,
                resume_content=evaluation.resume_content,
                candidate_name=evaluation.candidate_name,
                candidate_position=evaluation.candidate_position,
                candidate_age=evaluation.candidate_age,
                candidate_gender=evaluation.candidate_gender,
                work_years=evaluation.work_years,
                education_level=evaluation.education_level,
                school=evaluation.school,
                total_score=evaluation.total_score,
                evaluation_metrics=evaluation.evaluation_metrics,
                job_description_id=evaluation.job_description_id,
                scoring_criteria_id=evaluation.scoring_criteria_id,
                user_id=evaluation.user_id,
                created_at=evaluation.created_at,
                updated_at=evaluation.updated_at
            )
            evaluation_responses.append(response)

        # 计算分页信息
        page = (skip // limit) + 1 if limit > 0 else 1
        pages = (total + limit - 1) // limit if limit > 0 else 1
        return ResumeEvaluationListResponse(
            items=evaluation_responses,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

    async def get_evaluation_detail(
        self,
        evaluation_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """获取评价详情并返回扁平化结果"""
        evaluation = await self.get_evaluation_by_id(
            evaluation_id=evaluation_id,
            user_id=user_id
        )

        if not evaluation:
            return None

        # 获取关联的职位描述信息（保留但不参与返回，避免schema不匹配）
        jd = await self._get_job_description(evaluation.job_description_id, user_id)

        # 构建扁平化的结果，符合 ResumeEvaluationResult schema
        result = {
            "id": evaluation.id,
            "evaluation_metrics": evaluation.evaluation_metrics,
            "total_score": evaluation.total_score,
            "name": evaluation.candidate_name,
            "position": evaluation.candidate_position,
            "workYears": evaluation.work_years,
            "education": evaluation.education_level,
            "age": evaluation.candidate_age,
            "sex": evaluation.candidate_gender,
            "school": evaluation.school,
            "resume_content": evaluation.resume_content,
            "original_filename": evaluation.original_filename,
            "created_at": evaluation.created_at.isoformat(),
            "updated_at": evaluation.updated_at.isoformat()
        }

        return result

    async def delete_evaluation(
        self,
        evaluation_id: UUID,
        user_id: UUID
    ) -> bool:
        """删除评价记录"""
        try:
            evaluation = await self.get_evaluation_by_id(
                evaluation_id=evaluation_id,
                user_id=user_id
            )

            if not evaluation:
                return False

            # 先删除关联的面试计划记录 - 使用远程服务
            try:
                # 调用远程服务根据简历评价ID删除所有关联的面试方案
                result_data = await remote_service_client.delete(
                    endpoint=f"/interview-plans/delete-by-evaluation/{evaluation_id}",
                    user_id=user_id
                )
                logger.info(f"成功删除与评价 {evaluation_id} 关联的面试方案")
            except Exception as e:
                raise e
                logger.exception(f"删除关联面试方案失败: {e}")

            # 再删除评价记录
            await self.db.delete(evaluation)
            await self.db.commit()

            return True

        except Exception as e:
            logger.exception(f"删除评价记录失败: {e}")
            await self.db.rollback()
            raise

    async def update_evaluation_status(
        self,
        evaluation_id: UUID,
        user_id: UUID,
        new_status: ResumeStatus
    ) -> Optional[Dict[str, Any]]:
        """更新评价状态"""
        try:
            evaluation = await self.get_evaluation_by_id(
                evaluation_id=evaluation_id,
                user_id=user_id
            )

            if not evaluation:
                return None

            # 更新状态
            evaluation.status = new_status
            await self.db.commit()

            return {
                "message": "状态更新成功",
                "evaluation_id": str(evaluation.id),
                "status": new_status.value
            }

        except Exception as e:
            logger.error(f"更新简历状态失败: {e}")
            await self.db.rollback()
            raise


    def _build_evaluation_prompt(
        self,
        evaluation_model: str,
        jd_info: JobDescriptionResponse,
        resume_text: str,
        candidate_name: Optional[str] = None
    ) -> str:
        """构建评价提示词"""
        base_prompt = f"""
        {evaluation_model}

        职位信息：
        - 职位名称: {jd_info.title}
        - 部门: {jd_info.department or "未知部门"}
        - 职位要求: {jd_info.requirements}
        - 技能要求: {jd_info.skills}
        - 教育要求: {jd_info.education}
        - 工作经验要求: {jd_info.experience_level or "不限"}

        简历内容：
        """

        if candidate_name:
            base_prompt += f"候选人：{candidate_name}\n"

        base_prompt += f"简历内容：\n{resume_text}\n\n请严格按照JSON格式返回评价结果。"

        return base_prompt