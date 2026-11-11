"""

考试/试卷业务服务：
    负责试卷列表、保存试卷、详情、更新、删除、分享查看、考试结果列表/详情、AI生成试卷、提交答案评分和导出 CSV。
    内部有 _parse_exam_content 解析 AI 生成的试卷文本，
          _allocate_question_scores 分配题目分值，
          submit_exam 处理学生答案并生成评分结果。
"""
from typing import Any, Optional, Dict, List
import ast
import json
import math
import re
import unicodedata
import uuid
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exam import Exam, Question
from app.models.exam_result import ExamResult
from app.services.dify_service import DifyService
from app.services.enhanced_document_service import EnhancedDocumentService
from app.core.logging import logger
from app.services.kb_selection_service import KBSelectionService

class ExamService:
    """试卷服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dify_service = DifyService()

    async def get_exam_list(
        self,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取试卷列表

        Args:
            skip: 跳过的记录数
            limit: 每页记录数
            search: 搜索关键词

        Returns:
            包含试卷列表和分页信息的字典
        """
        try:
            # 构建查询
            query = select(Exam).options(selectinload(Exam.questions))

            # 应用搜索过滤
            if search:
                search_filter = or_(
                    Exam.title.ilike(f"%{search}%"),
                    Exam.subject.ilike(f"%{search}%"),
                    Exam.description.ilike(f"%{search}%")
                )
                query = query.where(search_filter)

            # 获取总数
            count_query = select(func.count(Exam.id))
            if search:
                count_query = count_query.where(search_filter)

            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # 应用分页和排序
            query = query.order_by(Exam.created_at.desc()).offset(skip).limit(limit)

            result = await self.db.execute(query)
            exams = result.scalars().all()

            # 转换为响应格式
            exam_list = []
            for exam in exams:
                exam_dict = {
                    "id": exam.id,
                    "title": exam.title,
                    "subject": exam.subject,
                    "description": exam.description,
                    "difficulty": exam.difficulty,
                    "duration": exam.duration,
                    "total_score": exam.total_score,
                    "question_types": exam.question_types or [],
                    "question_counts": exam.question_counts or {},
                    "knowledge_files": exam.knowledge_files or [],
                    "special_requirements": exam.special_requirements or "",
                    "questionCount": len(exam.questions) if exam.questions else self._question_count_from_config(exam.question_counts),
                    "created_at": exam.created_at.isoformat() if exam.created_at else None,
                    "updated_at": exam.updated_at.isoformat() if exam.updated_at else None
                }
                exam_list.append(exam_dict)

            return {
                "items": exam_list,
                "total": total,
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            logger.error(f"获取试卷列表时出错: {str(e)}")
            raise

    async def save_exam(
        self,
        exam_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        保存试卷到数据库

        Args:
            exam_data: 试卷数据
            user_id: 用户ID

        Returns:
            保存的试卷信息
        """
        try:
            if not exam_data.get('questions') and exam_data.get('content'):
                exam_data['questions'] = self._parse_exam_content(exam_data.get('content'))

            # 创建试卷实例
            exam = Exam(
                title=exam_data['title'],
                subject=exam_data['subject'],
                description=exam_data.get('description'),
                difficulty=exam_data.get('difficulty'),
                duration=exam_data.get('duration'),
                total_score=exam_data['total_score'],
                question_types=exam_data.get('question_types'),
                question_counts=exam_data.get('question_counts'),
                knowledge_files=[{"id": kf["id"], "fileName": kf["fileName"]} for kf in exam_data.get('knowledge_files', [])],
                special_requirements=exam_data.get('special_requirements'),
                content=exam_data.get('content'),
                created_by=user_id,
                updated_by=user_id
            )

            # 保存到数据库
            self.db.add(exam)
            await self.db.commit()
            await self.db.refresh(exam)

            # 保存结构化试题数据
            if exam_data.get('questions'):
                for question_data in exam_data['questions']:
                    question = Question(
                        exam_id=exam.id,
                        question_type=question_data['type'],
                        question_text=question_data['text'],
                        options=question_data.get('options'),
                        correct_answer=question_data.get('correct_answers'),
                        score=question_data['score'],
                        order_index=question_data['number'],
                        explanation=question_data.get('explanation'),
                        created_by=user_id,
                        updated_by=user_id
                    )
                    self.db.add(question)

                await self.db.commit()

            # 返回保存的试卷信息
            saved_exam = {
                "id": str(exam.id),
                "title": exam.title,
                "subject": exam.subject,
                "description": exam.description,
                "difficulty": exam.difficulty,
                "duration": exam.duration,
                "total_score": exam.total_score,
                "question_types": exam.question_types,
                "question_counts": exam.question_counts,
                "knowledge_files": exam.knowledge_files,
                "special_requirements": exam.special_requirements,
                "created_at": exam.created_at.isoformat() + "Z",
                "updated_at": exam.updated_at.isoformat() + "Z",
                "created_by": str(exam.created_by)
            }

            logger.info(f"试卷成功保存到数据库: {exam.id}")
            return saved_exam

        except Exception as e:
            await self.db.rollback()
            logger.error(f"保存试卷到数据库时出错: {str(e)}")
            raise

    async def get_exam_detail(
        self,
        paper_id: str
    ) -> Dict[str, Any]:
        """
        获取试卷详情

        Args:
            paper_id: 试卷ID

        Returns:
            试卷详情信息
        """
        try:
            # 查询试卷及其关联的试题
            result = await self.db.execute(
                select(Exam)
                .options(selectinload(Exam.questions))
                .where(Exam.id == paper_id)
            )
            exam = result.scalar_one_or_none()

            if not exam:
                raise ValueError("试卷不存在")

            # 构建试题数据
            questions = []
            for question in sorted(exam.questions, key=lambda x: x.order_index):
                questions.append({
                    "id": f"q_{question.order_index}",
                    "number": question.order_index,
                    "text": question.question_text,
                    "type": question.question_type,
                    "score": question.score,
                    "correct_answers": question.correct_answer,
                    "explanation": question.explanation,
                    "options": question.options or []
                })

            # 返回试卷详情
            exam_detail = {
                "id": str(exam.id),
                "title": exam.title,
                "subject": exam.subject,
                "description": exam.description,
                "difficulty": exam.difficulty,
                "duration": exam.duration,
                "total_score": exam.total_score,
                "question_types": exam.question_types,
                "question_counts": exam.question_counts,
                "knowledge_files": exam.knowledge_files,
                "special_requirements": exam.special_requirements,
                "content": exam.content,
                "questions": questions,
                "created_at": exam.created_at.isoformat() + "Z",
                "updated_at": exam.updated_at.isoformat() + "Z",
                "created_by": str(exam.created_by)
            }

            logger.info(f"成功获取试卷详情: {exam.id}")
            return exam_detail

        except Exception as e:
            logger.error(f"获取试卷详情时出错: {str(e)}")
            raise

    async def update_exam(
        self,
        paper_id: str,
        exam_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        更新试卷

        Args:
            paper_id: 试卷ID
            exam_data: 试卷数据
            user_id: 用户ID

        Returns:
            更新后的试卷信息
        """
        try:
            if not exam_data.get('questions') and exam_data.get('content'):
                exam_data['questions'] = self._parse_exam_content(exam_data.get('content'))

            # 查找试卷及其关联的试题
            result = await self.db.execute(
                select(Exam)
                .options(selectinload(Exam.questions))
                .where(Exam.id == paper_id)
            )
            exam = result.scalar_one_or_none()

            if not exam:
                raise ValueError("试卷不存在")

            # 更新试卷字段
            exam.title = exam_data['title']
            exam.subject = exam_data['subject']
            exam.description = exam_data.get('description')
            exam.difficulty = exam_data.get('difficulty')
            exam.duration = exam_data.get('duration')
            exam.total_score = exam_data['total_score']
            exam.question_types = exam_data.get('question_types')
            exam.question_counts = exam_data.get('question_counts')
            exam.knowledge_files = [{"id": kf["id"], "fileName": kf["fileName"]} for kf in exam_data.get('knowledge_files', [])]
            exam.special_requirements = exam_data.get('special_requirements')
            exam.content = exam_data.get('content')
            exam.updated_by = user_id

            # 提交更改
            await self.db.commit()
            await self.db.refresh(exam)

            # 更新试题数据
            if exam_data.get('questions'):
                # 清空现有试题（利用cascade特性自动删除）
                # 确保关系已加载后再清空
                if exam.questions:
                    exam.questions.clear()
                await self.db.commit()

                # 添加新试题
                for question_data in exam_data['questions']:
                    question = Question(
                        exam_id=exam.id,
                        question_type=question_data['type'],
                        question_text=question_data['text'],
                        options=question_data.get('options'),
                        correct_answer=question_data.get('correct_answers'),
                        score=question_data['score'],
                        order_index=question_data['number'],
                        explanation=question_data.get('explanation'),
                        created_by=user_id,
                        updated_by=user_id
                    )
                    self.db.add(question)

                await self.db.commit()

            # 返回更新后的试卷信息
            updated_exam = {
                "id": str(exam.id),
                "title": exam.title,
                "subject": exam.subject,
                "description": exam.description,
                "difficulty": exam.difficulty,
                "duration": exam.duration,
                "total_score": exam.total_score,
                "question_types": exam.question_types,
                "question_counts": exam.question_counts,
                "knowledge_files": exam.knowledge_files,
                "special_requirements": exam.special_requirements,
                "created_at": exam.created_at.isoformat() + "Z",
                "updated_at": exam.updated_at.isoformat() + "Z",
                "created_by": str(exam.created_by)
            }

            logger.info(f"试卷更新成功: {paper_id}")
            return updated_exam

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新试卷时出错: {str(e)}")
            raise

    async def delete_exam(
        self,
        paper_id: str
    ) -> Dict[str, Any]:
        """
        删除试卷

        Args:
            paper_id: 试卷ID

        Returns:
            删除结果信息
        """
        try:
            # 查找试卷
            result = await self.db.execute(
                select(Exam).where(Exam.id == paper_id)
            )
            exam = result.scalar_one_or_none()

            if not exam:
                raise ValueError("试卷不存在")

            # 删除试卷
            await self.db.delete(exam)
            await self.db.commit()

            logger.info(f"试卷删除成功: {paper_id}")
            return {"message": "试卷删除成功", "paper_id": paper_id}

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除试卷时出错: {str(e)}")
            raise

    async def get_exam_for_share(
        self,
        paper_id: str
    ) -> Dict[str, Any]:
        """
        获取用于分享的试卷信息（无需认证）

        Args:
            paper_id: 试卷ID

        Returns:
            试卷信息
        """
        try:
            # 查找试卷及其关联的试题
            result = await self.db.execute(
                select(Exam)
                .options(selectinload(Exam.questions))
                .where(Exam.id == paper_id)
            )
            exam = result.scalar_one_or_none()

            if not exam:
                raise ValueError("试卷不存在")

            # 构建试题列表
            questions = []
            if exam.questions:
                for question in exam.questions:
                    question_data = {
                        "id": question.id,
                        "question_text": question.question_text,
                        "question_type": question.question_type,
                        "score": question.score,
                        "options": question.options if question.options else []
                    }
                    questions.append(question_data)

            # 返回试卷信息
            return {
                "id": exam.id,
                "title": exam.title,
                "subject": exam.subject,
                "description": exam.description,
                "difficulty": exam.difficulty,
                "duration": exam.duration,
                "total_score": exam.total_score,
                "content": exam.content,
                "questions": questions,
                "created_at": exam.created_at.isoformat() if exam.created_at else None
            }

        except Exception as e:
            logger.error(f"获取分享试卷时出错: {str(e)}")
            raise

    async def get_exam_results(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        exam_id: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取考试结果列表，支持分页和筛选

        Args:
            page: 页码
            page_size: 每页数量
            search: 搜索关键词
            exam_id: 考试ID筛选
            department: 部门筛选

        Returns:
            考试结果列表和分页信息
        """
        try:
            # 构建查询条件
            query = select(ExamResult)

            # 添加搜索条件
            if search:
                search_filter = or_(
                    ExamResult.student_name.ilike(f"%{search}%"),
                    ExamResult.exam_name.ilike(f"%{search}%")
                )
                query = query.where(search_filter)

            # 添加考试ID筛选
            if exam_id:
                query = query.where(ExamResult.exam_id == exam_id)

            # 添加部门筛选
            if department:
                query = query.where(ExamResult.department == department)

            # 计算总数
            count_query = select(func.count(ExamResult.id))
            if search:
                count_query = count_query.where(search_filter)
            if exam_id:
                count_query = count_query.where(ExamResult.exam_id == exam_id)
            if department:
                count_query = count_query.where(ExamResult.department == department)

            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            # 应用分页
            offset = (page - 1) * page_size
            query = query.order_by(ExamResult.submit_time.desc()).offset(offset).limit(page_size)

            result = await self.db.execute(query)
            exam_results = result.scalars().all()

            # 构建响应数据
            results_list = []
            for exam_result in exam_results:
                results_list.append({
                    "id": str(exam_result.id),
                    "exam_id": str(exam_result.exam_id) if exam_result.exam_id else None,
                    "exam_name": exam_result.exam_name,
                    "student_name": exam_result.student_name,
                    "department": exam_result.department,
                    "total_possible_score": exam_result.total_possible_score,
                    "total_actual_score": exam_result.total_actual_score,
                    "score_percentage": round((exam_result.total_actual_score / exam_result.total_possible_score) * 100, 2) if exam_result.total_possible_score > 0 else 0,
                    "submit_time": exam_result.submit_time.isoformat() + "Z" if exam_result.submit_time else None,
                    "status": exam_result.status
                })
            logger.info(f"成功获取考试结果列表，第 {page} 页，共 {total} 条结果")
            return {
                "items": results_list,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"获取考试结果时出错: {str(e)}")
            raise

    async def get_exam_result(
        self,
        result_id: str
    ) -> Dict[str, Any]:
        """
        获取考试结果详情

        Args:
            result_id: 考试结果ID

        Returns:
            考试结果详情
        """
        try:
            # 查找考试结果
            result = await self.db.execute(
                select(ExamResult).where(ExamResult.id == result_id)
            )
            exam_result = result.scalar_one_or_none()

            if not exam_result:
                raise ValueError("考试结果不存在")
            logger.info(f"成功获取考试结果详情: {result_id}")
            # 返回考试结果详情
            return {
                "id": str(exam_result.id),
                "exam_id": str(exam_result.exam_id) if exam_result.exam_id else None,
                "exam_name": exam_result.exam_name,
                "student_name": exam_result.student_name,
                "department": exam_result.department,
                "total_possible_score": exam_result.total_possible_score,
                "total_actual_score": exam_result.total_actual_score,
                "score_percentage": round((exam_result.total_actual_score / exam_result.total_possible_score) * 100, 2) if exam_result.total_possible_score > 0 else 0,
                "exam_data": exam_result.exam_data,
                "submit_time": exam_result.submit_time.isoformat() + "Z" if exam_result.submit_time else None,
                "status": exam_result.status
            }

        except Exception as e:
            logger.error(f"获取考试结果详情时出错: {str(e)}")
            raise

    async def generate_exam(
        self,
        title: str,
        subject: str,
        total_score: int,
        user_id: str,
        description: Optional[str] = None,
        difficulty: Optional[str] = None,
        duration: Optional[int] = None,
        question_types: Optional[List[str]] = None,
        question_counts: Optional[Dict[str, int]] = None,
        knowledge_files: Optional[List[Dict[str, Any]]] = None,
        special_requirements: Optional[str] = None,
        conversation_id: Optional[str] = None,
        stream: bool = True
    ) -> Any:
        """
        生成试卷

        Args:
            title: 试卷标题
            subject: 科目
            total_score: 总分
            user_id: 用户ID
            description: 试卷描述
            difficulty: 难度等级
            duration: 考试时长
            question_types: 题型列表
            question_counts: 题目数量配置
            knowledge_files: 知识库文件
            special_requirements: 特殊要求
            conversation_id: 对话ID
            stream: 是否流式输出

        Returns:
            试卷生成结果
        """
        try:
            # 初始化文档服务
            document_service = EnhancedDocumentService(self.db)

            # 若未提供知识库文档，自动选择最匹配文档
            if not knowledge_files:
                try:
                    selector = KBSelectionService(self.db)
                    selection_question = " ".join([
                        subject or "",
                        title or "",
                        description or "",
                        special_requirements or "",
                    ]).strip()
                    selection = await selector.select_kb_for_question(
                        question=selection_question,
                        user_id=user_id,
                        max_candidates=200,
                    )
                    if selection and selection.get("document_id"):
                        knowledge_files = [str(selection.get("document_id"))]
                except Exception as se:
                    logger.warning(f"知识库自动选择失败: {se}")

            # 读取文档内容
            file_contents = []
            if knowledge_files:
                for file_info in knowledge_files:
                    try:
                        # 兼容不同的文件信息格式
                        file_id = file_info.get('id') if isinstance(file_info, dict) else file_info
                        # 获取文档信息
                        document = await document_service.get_by_id(file_id, user_id)
                        if document:
                            if document.extracted_content:
                                file_contents.append({
                                    "filename": document.filename,
                                    "content": document.extracted_content
                                })
                            else:
                                logger.warning(f"文档 {file_id} 内容为空")
                        else:
                            logger.warning(f"未找到文档 {file_id}")
                    except Exception as e:
                        logger.warning(f"读取文档 {file_id} 失败: {e}")
                        continue

            # 添加日志记录文档内容状态
            logger.info(f"已处理 {len(file_contents)} 个文档，总共请求: {len(knowledge_files) if knowledge_files else 0}")
            if not file_contents and knowledge_files:
                logger.warning("未提取到文档内容，文档可能为空或不可读")

            # 合并文档内容
            combined_content = ""
            if file_contents:
                content_parts = []
                for file_info in file_contents:
                    content_parts.append(f"=== {file_info['filename']} ===\n{file_info['content']}")
                combined_content = "\n\n".join(content_parts)
            else:
                # 如果没有文档内容，记录警告日志
                logger.warning("没有可用的文档内容用于生成试卷")
                combined_content = "未提供文档内容"

            # 分值分配算法（按 2:3:5 权重，并将剩余分数依次分配给最后几题）
            question_scores = self._allocate_question_scores(total_score, question_counts or {})

            # 构建试卷生成查询
            has_interview_plan_context = bool(
                special_requirements
                and ("当前面试方案" in special_requirements or "面试方案" in special_requirements)
            )
            if has_interview_plan_context:
                total_question_count = self._question_count_from_config(question_counts)
                document_question_count = max(1, round(total_question_count * 0.8)) if total_question_count else 0
                interview_question_count = max(1, total_question_count - document_question_count) if total_question_count > 1 else 0
                if document_question_count + interview_question_count > total_question_count and total_question_count:
                    document_question_count = max(1, total_question_count - interview_question_count)
                query_parts = [
                    f"请基于下方【参考文档】生成一份{subject}笔试试卷，并参考【面试方案】调整出题重点。",
                    "题目来源配比必须接近 8:2：约 80% 题目来自【参考文档】知识点，约 20% 题目来自【面试方案】中的能力验证点、风险点或追问方向。",
                    "如果总题数较少，至少生成 1 道面试方案导向题，其余题目来自参考文档。",
                    "参考文档题：题干、选项、参考答案和解析必须主要依据【参考文档】。",
                    "面试方案导向题：可以围绕面试方案中的能力短板、风险点、追问方向设计情境题/简答题，但仍应尽量结合参考文档中的业务或知识背景。",
                    "禁止把面试流程、面试安排、候选人评价原文直接改写成试题。",
                ]
                if total_question_count:
                    query_parts.append(
                        f"本次共 {total_question_count} 题，请生成约 {document_question_count} 道参考文档题、"
                        f"{interview_question_count} 道面试方案导向题。"
                    )
            else:
                query_parts = [f"请基于以下文档内容生成一份{subject}试卷"]

            query_parts.extend([
                "请严格按以下结构化格式输出，每题之间用 *** 分隔，每题只占一条记录：",
                "题干|题型|选项|正确答案|分值|解析",
                "题型只能使用中文：单选题、多选题、简答题。不要输出 single_choice、multiple_choice、short_answer。",
                "单选题/多选题的选项用中文分号；分隔，例如：选项A；选项B；选项C；选项D。选项文本中不要再带 A.、B.、C.、D. 前缀。",
                "正确答案只填写选项字母或简答题要点，例如：A、AC、略。",
                "不要输出 Markdown 标题、编号列表或额外说明。",
            ])

            if title:
                query_parts.append(f"试卷标题：{title}")

            if description:
                query_parts.append(f"试卷描述：{description}")

            if question_types:
                type_labels = {
                    "single_choice": "单选题",
                    "multiple_choice": "多选题",
                    "short_answer": "简答题",
                    "single": "单选题",
                    "multiple": "多选题",
                    "short": "简答题",
                }
                types_str = "、".join(type_labels.get(item, item) for item in question_types)
                query_parts.append(f"题目类型：{types_str}")

            if question_counts:
                counts_parts = []
                expected_total_questions = 0
                type_labels = {
                    "single_choice": "单选题",
                    "multiple_choice": "多选题",
                    "short_answer": "简答题",
                    "single": "单选题",
                    "multiple": "多选题",
                    "short": "简答题",
                }
                for q_type, count in question_counts.items():
                    if count > 0:
                        expected_total_questions += int(count)
                        counts_parts.append(f"{type_labels.get(q_type, q_type)}：{count}题")
                if counts_parts:
                    query_parts.append(f"题目数量：{', '.join(counts_parts)}")
                    query_parts.append(
                        f"必须严格生成合计 {expected_total_questions} 题，且每种题型数量必须与上面的配置完全一致；"
                        "不得少题、多题或合并题目。"
                    )

            if total_score:
                query_parts.append(f"试卷总分：{total_score}")

            # 在提示词中明确每题分值设置，要求严格遵循
            # 仅在存在题量时附加说明
            counts_for_prompt = question_counts or {}
            if any(counts_for_prompt.get(t, 0) > 0 for t in ["single_choice", "multiple_choice", "short_answer"]):
                def fmt_scores_line(t_key: str, t_name: str) -> str:
                    arr = question_scores.get(t_key, [])
                    if not arr:
                        return ""
                    return f"{t_name}每题分值（按题序）：{', '.join(str(x) for x in arr)}"

                scores_lines = [
                    fmt_scores_line("single_choice", "单选题"),
                    fmt_scores_line("multiple_choice", "多选题"),
                    fmt_scores_line("short_answer", "简答题"),
                ]
                scores_lines = [s for s in scores_lines if s]
                if scores_lines:
                    query_parts.append("请严格按照以下每题分值设置生成试卷：")
                    query_parts.extend(scores_lines)

            if special_requirements:
                query_parts.append(f"特殊要求：{special_requirements}")

            query = "\n".join(query_parts)
            print('试卷要求：', query)

            workflow_file_content = combined_content
            if has_interview_plan_context:
                workflow_file_content = (
                    "【参考文档】\n"
                    f"{combined_content}\n\n"
                    "【面试方案】\n"
                    f"{special_requirements[:2500]}"
                )

            # 准备额外输入参数
            additional_inputs = {
                "fileContent": workflow_file_content,
                "total_score": total_score,
                # 向工作流传递结构化的分值设置，便于遵守
                "question_scores": question_scores,
            }

            # 添加调试日志
            logger.info(f"向Dify工作流发送文件内容，内容长度: {len(workflow_file_content)}")
            if len(workflow_file_content) < 100:  # 如果内容很短，记录具体内容（前100个字符）
                logger.info(f"文件内容预览: {workflow_file_content[:100]}")

            if title:
                additional_inputs["title"] = title
            if description:
                additional_inputs["description"] = description
            if question_types:
                additional_inputs["question_types"] = question_types
            if question_counts:
                additional_inputs["question_counts"] = question_counts
            if special_requirements:
                additional_inputs["special_requirements"] = special_requirements
            if has_interview_plan_context:
                additional_inputs["interview_plan_context"] = special_requirements
                additional_inputs["reference_document_content"] = combined_content
                additional_inputs["generation_strategy"] = "document_grounded_interview_plan_guided"

            # 附加自动选择的元信息，便于工作流提示词使用
            if knowledge_files:
                additional_inputs["kb_selection"] = {
                    "selected_document_id": knowledge_files[0],
                    "selected_document_filename": None,
                    "selected_kb_id": selection.get("knowledge_base_id") if 'selection' in locals() and selection else None,
                    "kb_selection_confidence": selection.get("confidence", 0.0) if 'selection' in locals() and selection else 0.0,
                }
            
            if stream:
                # 流式响应
                async def generate_stream():
                    async for chunk in self.dify_service.call_workflow_stream(
                        workflow_type=5,  # 使用类型5进行试卷生成
                        query=query,
                        # conversation_id=conversation_id,
                        additional_inputs=additional_inputs
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"

                return generate_stream()
            else:
                # 同步响应
                result = await self.dify_service.call_workflow_sync(
                    workflow_type=5,
                    query=query,
                    conversation_id=conversation_id,
                    additional_inputs=additional_inputs
                )
                return result

        except Exception as e:
            logger.error(f"生成试卷时出错: {str(e)}")
            raise

    def _question_count_from_config(self, question_counts: Optional[Dict[str, int]]) -> int:
        if not question_counts:
            return 0
        keys = ["single_choice", "multiple_choice", "short_answer", "single", "multiple", "short"]
        return sum(int(question_counts.get(key) or 0) for key in keys)

    @staticmethod
    def _choice_question_kind(question_type: Any) -> Optional[str]:
        normalized_type = unicodedata.normalize(
            "NFKC", str(question_type or "")
        ).strip().lower()
        normalized_type = re.sub(r"[\s-]+", "_", normalized_type)

        if normalized_type in {"单选题", "单选", "单项选择题", "single_choice", "single"}:
            return "single"
        if normalized_type in {"多选题", "多选", "多项选择题", "multiple_choice", "multiple"}:
            return "multiple"
        return None

    @staticmethod
    def _valid_choice_option_ids(options: Any) -> set[str]:
        if not isinstance(options, (list, tuple)):
            return set()

        option_ids = set()
        for index, option in enumerate(options):
            raw_option_id = option.get("id") if isinstance(option, dict) else None
            if raw_option_id is None or str(raw_option_id).strip() == "":
                raw_option_id = chr(65 + index)

            option_id = unicodedata.normalize(
                "NFKC", str(raw_option_id)
            ).strip().upper()
            if option_id:
                option_ids.add(option_id)

        return option_ids

    @classmethod
    def _normalize_choice_answer(
        cls,
        answer: Any,
        valid_option_ids: set[str]
    ) -> Optional[frozenset[str]]:
        """将选择题答案规范化为选项 ID 集合。

        返回 None 表示答案格式非法；空集合表示未作答。
        """
        if answer is None:
            return frozenset()

        if isinstance(answer, (list, tuple, set, frozenset)):
            normalized_items = set()
            for item in answer:
                normalized_item = cls._normalize_choice_answer(item, valid_option_ids)
                if normalized_item is None:
                    return None
                normalized_items.update(normalized_item)
            return frozenset(normalized_items)

        if not isinstance(answer, (str, int)):
            return None

        answer_text = unicodedata.normalize("NFKC", str(answer)).strip().upper()
        if not answer_text or answer_text == "未作答":
            return frozenset()

        if answer_text in valid_option_ids:
            return frozenset({answer_text})

        if answer_text[0] in "[({" and answer_text[-1] in "])}":
            try:
                parsed_answer = ast.literal_eval(answer_text)
            except (ValueError, SyntaxError):
                parsed_answer = None
            if isinstance(parsed_answer, (list, tuple, set, frozenset)):
                return cls._normalize_choice_answer(parsed_answer, valid_option_ids)

        answer_parts = [
            part.strip("[](){}'\".。")
            for part in re.split(r"(?:AND|和|及)|[,\s、，;；/|+&]+", answer_text)
            if part.strip("[](){}'\".。")
        ]
        if len(answer_parts) > 1:
            if all(part in valid_option_ids for part in answer_parts):
                return frozenset(answer_parts)
            return None

        # 兼容多选标准答案的紧凑写法，例如 AC。
        if (
            answer_parts
            and all(len(option_id) == 1 for option_id in valid_option_ids)
            and all(char in valid_option_ids for char in answer_parts[0])
        ):
            return frozenset(answer_parts[0])

        return None

    @classmethod
    def _grade_choice_answer(
        cls,
        question_type: Any,
        student_answer: Any,
        correct_answer: Any,
        options: Any,
        max_score: Any
    ) -> Optional[Dict[str, Any]]:

        # 识别单选题、多选题及其中英文名称： _choice_question_kind
        question_kind = cls._choice_question_kind(question_type)
        if question_kind is None:
            return None

        # 获取题目的有效选项ID：_valid_choice_option_ids
        valid_option_ids = cls._valid_choice_option_ids(options)
        if not valid_option_ids:
            raise ValueError("选择题缺少有效选项，无法进行自动评分")

        # 统一处理 AC、A,C、A、C、数组、大小写等答案格式。
        normalized_correct = cls._normalize_choice_answer(
            correct_answer, valid_option_ids
        )
        if not normalized_correct:
            raise ValueError("选择题标准答案为空或格式无效")
        if question_kind == "single" and len(normalized_correct) != 1:
            raise ValueError("单选题的标准答案必须且只能包含一个选项")

        normalized_student = cls._normalize_choice_answer(
            student_answer, valid_option_ids
        )

        # 单选或多选 完全匹配：normalized_student == normalized_correct 满分。
        is_correct = (
            normalized_student is not None
            and bool(normalized_student)
            and normalized_student == normalized_correct
            and (question_kind != "single" or len(normalized_student) == 1)
        )
        # 多选题中 normalized_student < normalized_correct：非空真子集，即漏选，得一半分
        is_partially_correct = (
            question_kind == "multiple"
            and normalized_student is not None
            and bool(normalized_student)
            and normalized_student < normalized_correct
        )

        # 多选、非法选项、未作答：0 分。
        try:
            numeric_max_score = float(max_score)
        except (TypeError, ValueError):
            numeric_max_score = 0.0
        if not math.isfinite(numeric_max_score) or numeric_max_score < 0:
            numeric_max_score = 0.0

        if is_correct:
            score = numeric_max_score
            grading_status = "correct"
        elif is_partially_correct:
            score = numeric_max_score / 2
            grading_status = "partial"
        else:
            score = 0.0
            grading_status = "incorrect"

        return {
            "score": score,
            "is_correct": is_correct,
            "is_partially_correct": is_partially_correct,
            "grading_status": grading_status,
            "normalized_correct_answer": sorted(normalized_correct),
            "normalized_student_answer": (
                sorted(normalized_student)
                if normalized_student is not None
                else None
            ),
            "student_answer_valid": normalized_student is not None,
        }

    def _parse_exam_content(self, content: Optional[str]) -> List[Dict[str, Any]]:
        if not content or not isinstance(content, str):
            return []

        questions: List[Dict[str, Any]] = []
        blocks = [block.strip() for block in content.split("***") if block.strip()]
        for index, block in enumerate(blocks, start=1):
            parts = [part.strip() for part in block.split("|")]
            if len(parts) != 6:
                continue

            question_text, question_type, options_text, correct_answers, score, explanation = parts
            options = []
            if question_type in {"单选题", "多选题", "单选", "多选"} and options_text:
                options = [
                    {"id": chr(65 + option_index), "text": option.strip()}
                    for option_index, option in enumerate(re.split(r"[;；]", options_text))
                    if option.strip()
                ]

            score_match = re.search(r"\d+", str(score))
            questions.append({
                "id": f"q_{index}",
                "number": index,
                "text": question_text,
                "type": question_type,
                "options": options,
                "correct_answers": correct_answers,
                "score": int(score_match.group(0)) if score_match else 0,
                "explanation": explanation,
            })

        return questions

    def _allocate_question_scores(self, total_score: int, counts: Dict[str, int]) -> Dict[str, List[int]]:
        """
        分值分配算法（按 2:3:5 权重，并将剩余分数依次分配给最后几题）

        Args:
            total_score: 总分
            counts: 题目数量配置

        Returns:
            各题型分值分配结果
        """
        # 仅支持三种题型：单选题、多选题、简答题
        weights = {
            "single_choice": 2,
            "multiple_choice": 3,
            "short_answer": 5,
        }

        # 初始化每题分值列表
        scores: Dict[str, List[int]] = {
            t: [0] * max(0, counts.get(t, 0)) for t in ["single_choice", "multiple_choice", "short_answer"]
        }
        '''示例返回格式：
        {
        "single_choice": [0, 0, 0, 0, 0],  # 5个单选题，初始分值都是0
        "multiple_choice": [0, 0, 0],       # 3个多选题，初始分值都是0  
        "short_answer": [0, 0]              # 2个简答题，初始分值都是0
        }'''

        # 计算加权题量总和
        weighted_total = 0
        for t, w in weights.items():
            weighted_total += counts.get(t, 0) * w

        if weighted_total <= 0 or total_score <= 0:
            return scores

        # 基础单位分和剩余分
        base_unit = total_score // weighted_total
        remainder = total_score % weighted_total

        # 先按权重为每题分配基础分值
        for t, w in weights.items():
            c = counts.get(t, 0)
            if c > 0:
                base_per_question = w * base_unit
                scores[t] = [base_per_question] * c

        # 将剩余分数依次分配给"最后几题"：先简答题末尾，后多选题末尾，再单选题末尾
        distribution_order = ["short_answer", "multiple_choice", "single_choice"]
        while remainder > 0:
            allocated_this_round = False
            for t in distribution_order:
                arr = scores.get(t, [])
                # 从末尾开始为每题加 1 分，直到该类型题目遍历完或剩余分数为 0
                for i in range(len(arr) - 1, -1, -1):
                    if remainder <= 0:
                        break
                    arr[i] += 1
                    remainder -= 1
                    allocated_this_round = True
            if not allocated_this_round:
                # 没有任何题目可分配（例如题量为 0），避免死循环
                break

        return scores
        '''示例返回格式：
        {
            "single_choice": [6, 6, 6, 6, 7],      # 单选题分值列表
            "multiple_choice": [9, 9, 10],          # 多选题分值列表  
            "short_answer": [15, 16]                # 简答题分值列表
        }'''

    async def submit_exam(
        self,
        exam_id: str,
        student_name: str,
        department: str,
        answers: Dict[str, Any],
        exam_content: str
    ) -> Dict[str, Any]:
        """
        提交考试答案并进行自动评分

        Args:
            exam_id: 试卷ID
            student_name: 考生姓名
            department: 考生部门
            answers: 学生答案
            exam_content: 试卷内容

        Returns:
            考试结果
        """
        try:
            # 校验 exam_content 是合法 JSON
            json.loads(exam_content)

            # 从数据库获取完整的试卷信息（包括标准答案和解析）
            result = await self.db.execute(
                select(Exam)
                .options(selectinload(Exam.questions))
                .where(Exam.id == exam_id)
            )
            exam = result.scalar_one_or_none()

            if not exam:
                raise ValueError("试卷不存在")

            # 构建完整的试题信息（包含标准答案和解析）
            questions_with_answers = []
            student_answers = json.loads(answers) if isinstance(answers, str) else answers

            for question in sorted(exam.questions, key=lambda x: x.order_index):
                # 使用题目的实际ID来匹配答案
                question_id = str(question.id)
                student_answer = student_answers.get(question_id, "未作答")

                question_info = {
                    "题目编号": question.order_index,
                    "题目类型": question.question_type,
                    "题目内容": question.question_text,
                    "选项": question.options or [],
                    "标准答案": question.correct_answer,
                    "解析": question.explanation,
                    "分值": question.score,
                    "考生答案": student_answer
                }
                questions_with_answers.append(question_info)

            # 选择题直接比较答案，其他题型逐题调用 Dify 评分
            questions_with_scores = []
            per_question_results = []
            total_score = 0.0

            for idx, q_info in enumerate(questions_with_answers, 1):

                # 实际判分 _grade_choice_answer
                choice_result = self._grade_choice_answer(
                    question_type=q_info["题目类型"],
                    student_answer=q_info["考生答案"],
                    correct_answer=q_info["标准答案"],
                    options=q_info["选项"],
                    max_score=q_info["分值"],
                )
                if choice_result is not None:
                    per_score = choice_result["score"]
                    total_score += per_score
                    per_question_results.append({
                        "题目编号": q_info["题目编号"],
                        "scoring_method": "direct_answer_comparison",
                        "parsed_score": per_score,
                        **{
                            key: value
                            for key, value in choice_result.items()
                            if key != "score"
                        },
                    })

                    question_with_score = q_info.copy()
                    question_with_score["实际得分"] = per_score
                    questions_with_scores.append(question_with_score)
                    continue

                # 为每道题构造精简评分提示，减少上下文噪声
                per_query_parts = [
                    f"请对以下试题进行评分，仅返回该题的得分(数字即可)：",
                    f"题目类型：{q_info['题目类型']}",
                    f"题目内容：{q_info['题目内容']}",
                ]
                if q_info.get('选项'):
                    per_query_parts.append(f"选项：{q_info['选项']}")
                per_query_parts.extend([
                    f"标准答案：{q_info['标准答案']}",
                    f"解析：{q_info['解析']}",
                    f"分值（满分）：{q_info['分值']}",
                    f"考生答案：{q_info['考生答案']}",
                    "",
                    "请严格返回纯数字（可为小数），不要包含其他文字、单位或标点。如果用户没有作答，必须判0分，否则会收到惩罚！"
                ])
                per_query = "\n".join([p for p in per_query_parts if p])

                # 逐题调用工作流进行评分
                try:
                    per_result = await self.dify_service.call_workflow_sync(
                        workflow_type=6,
                        query=per_query,
                        additional_inputs={
                            "type": 6,
                            "max_score": q_info["分值"],
                            "question_type": q_info["题目类型"],
                            "question_index": idx
                        }
                    )
                    # 解析返回的数值得分
                    raw_answer = per_result.get("answer", "0")
                    try:
                        per_score = float(str(raw_answer).strip())
                    except ValueError:
                        per_score = 0.0
                    # 边界保护：0 到满分
                    try:
                        max_score = float(q_info["分值"]) if q_info.get("分值") is not None else None
                    except Exception:
                        max_score = None
                    if max_score is not None:
                        per_score = max(0.0, min(per_score, max_score))
                    total_score += per_score

                    per_question_results.append({
                        "题目编号": q_info["题目编号"],
                        "scoring_method": "dify",
                        "raw_answer": raw_answer,
                        "parsed_score": per_score
                    })
                except Exception as e:
                    # 失败容错：给0分并记录错误
                    per_score = 0.0
                    per_question_results.append({
                        "题目编号": q_info["题目编号"],
                        "scoring_method": "dify",
                        "error": str(e),
                        "parsed_score": per_score
                    })

                # 汇总到题目结构
                question_with_score = q_info.copy()
                question_with_score["实际得分"] = per_score
                questions_with_scores.append(question_with_score)

            # 构建完整的考试数据JSON
            exam_data = {
                "exam_info": {
                    "exam_id": exam_id,
                    "title": exam.title,
                    "description": exam.description,
                    "total_score": exam.total_score,
                    "time_limit": exam.duration,
                    "instructions": exam.description or "请认真答题，注意时间限制。"
                },
                "questions": questions_with_scores,
                "student_answers": student_answers,
                "scoring_result": {
                    "mode": "per_question",
                    "results": per_question_results
                },
                "submit_time": datetime.utcnow().isoformat() + "Z",
                "total_actual_score": total_score,
                "score_percentage": round((total_score / exam.total_score) * 100, 2) if exam.total_score > 0 else 0
            }

            # 创建考试结果记录
            exam_result = ExamResult(
                id=uuid.uuid4(),
                exam_id=exam.id,
                exam_name=exam.title,
                student_name=student_name,
                department=department,
                total_possible_score=exam.total_score,
                total_actual_score=total_score,
                exam_data=exam_data,
                submit_time=datetime.utcnow(),
                status="completed"
            )

            self.db.add(exam_result)

            # 提交数据库事务
            await self.db.commit()

            logger.info(f"考试提交并保存成功，考生: {student_name}, 考试结果ID: {exam_result.id}")

            return {
                "message": "考试提交成功",
                "exam_result_id": str(exam_result.id),
                "student_name": student_name,
                "department": department,
                "exam_title": exam.title,
                "total_possible_score": exam.total_score,
                "total_actual_score": total_score,
                "score_percentage": round((total_score / exam.total_score) * 100, 2) if exam.total_score > 0 else 0,
                "questions": questions_with_scores
            }

        except Exception as e:
            logger.error(f"提交考试时出错: {str(e)}")
            raise

    async def export_exam_result_to_csv(
        self,
        result_id: str
    ) -> str:
        """
        导出考试结果为CSV格式

        Args:
            result_id: 考试结果ID

        Returns:
            CSV格式的字符串
        """
        try:
            # 获取考试结果详情
            exam_result = await self.get_exam_result(result_id)

            # 解析题目数据
            exam_data = exam_result.get("exam_data", {})
            if isinstance(exam_data, str):
                exam_data = json.loads(exam_data)

            questions = exam_data.get("questions", [])

            # 构建CSV内容
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow([
                "考生姓名", "所属部门", "考试名称", "总分", "得分", "得分率(%)", "提交时间"
            ])

            # 写入概要信息
            writer.writerow([
                exam_result.get("student_name", ""),
                exam_result.get("department", ""),
                exam_result.get("exam_name", ""),
                exam_result.get("total_possible_score", 0),
                exam_result.get("total_actual_score", 0),
                exam_result.get("score_percentage", 0),
                exam_result.get("submit_time", "")
            ])

            # 空行
            writer.writerow([])

            # 写入题目详情表头
            writer.writerow([
                "题号", "题目类型", "题目内容", "分值", "考生答案", "标准答案", "实际得分", "解析"
            ])

            # 写入题目详情
            for i, question in enumerate(questions, 1):
                writer.writerow([
                    i,
                    question.get("题目类型", ""),
                    question.get("题目内容", "")[:50] + "..." if len(question.get("题目内容", "")) > 50 else question.get("题目内容", ""),
                    question.get("分值", 0),
                    str(question.get("考生答案", ""))[:30] + "..." if len(str(question.get("考生答案", ""))) > 30 else str(question.get("考生答案", "")),
                    str(question.get("标准答案", ""))[:30] + "..." if len(str(question.get("标准答案", ""))) > 30 else str(question.get("标准答案", "")),
                    question.get("实际得分", 0),
                    question.get("解析", "")[:50] + "..." if len(question.get("解析", "")) > 50 else question.get("解析", "")
                ])

            csv_content = output.getvalue()
            output.close()

            logger.info(f"成功导出考试结果为CSV: {result_id}")
            return csv_content

        except Exception as e:
            logger.error(f"导出考试结果为CSV时出错: {str(e)}")
            raise
