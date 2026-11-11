"""
简历评价API端点，负责简历评价记录管理
"""
import asyncio
import io
import logging
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.resume_evaluation import ResumeEvaluation
import logging
from typing import List, Optional
from uuid import UUID
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.resume_evaluation_service import ResumeEvaluationService
from pydantic import BaseModel, Field
from app.schemas.resume_evaluation import (
    ResumeEvaluationResponse,
    ResumeEvaluationListResponse,
    ResumeEvaluationResult
)
from app.models.resume_evaluation import ResumeStatus
from app.core.config import settings
from app.schemas.resume_evaluation import ExportZipRequest
from app.schemas.email_config import AutoEvaluateRequest

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/evaluate-auto", response_model=ResumeEvaluationResult)
async def evaluate_resume_auto(
    payload: AutoEvaluateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    接收简历文本字符串，自动匹配最合适的JD并进行AI评分，同时将文本作为附件保存在本地。

    - **resume_text**: 简历文本内容
    - **subject**: 投递邮件主题（可选，用于辅助匹配JD）
    - **filename**: 文件名（可选，默认自动生成 .txt 文件名）
    - **login_name**: 登录用户名（必选）
    """
    try:
        # 调用服务层的文本简历自动评价方法
        evaluation_service = ResumeEvaluationService(db)
        result = await evaluation_service.evaluate_resume_text_auto(
            login_name=payload.login_name,
            resume_text=payload.resume_text,
            filename=payload.filename,
            subject=payload.position or ""
        )

        return ResumeEvaluationResult(**result)

    except ValueError as e:
        logger.warning(f"简历评价参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动匹配并评价简历失败: {e}")
        raise HTTPException(status_code=500, detail="自动匹配评价服务暂时不可用")

@router.get("/history", response_model=ResumeEvaluationListResponse)
async def get_evaluation_history(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的简历评价历史

    - **skip**: 跳过的记录数
    - **limit**: 返回的记录数限制
    - **status**: 状态过滤 (pending, rejected, interview)
    """
    try:
        # 验证状态参数
        status_filter = await ResumeEvaluationService.validate_status_param(status)
        
        # 限制查询数量
        limit = min(limit, 100)

        evaluation_service = ResumeEvaluationService(db)
        result = await evaluation_service.get_evaluation_history_with_pagination(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status_filter
        )
        
        return result

    except ValueError as e:
        logger.warning(f"获取评价历史参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取评价历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取评价历史失败")


@router.get("/supported-formats")
async def get_supported_formats():
    """
    获取支持的文件格式
    """
    return await ResumeEvaluationService.get_supported_formats()

@router.get("/{evaluation_id}", response_model=ResumeEvaluationResult)
async def get_evaluation_detail(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取特定评价结果的详细信息

    - **evaluation_id**: 评价记录ID
    """
    try:
        # 验证evaluation_id格式
        eval_uuid = await ResumeEvaluationService.validate_uuid_param(evaluation_id, "评价ID")

        evaluation_service = ResumeEvaluationService(db)
        result = await evaluation_service.get_evaluation_detail(
            evaluation_id=eval_uuid,
            user_id=current_user.id
        )

        if not result:
            raise HTTPException(status_code=404, detail="评价记录不存在")

        return ResumeEvaluationResult(**result)

    except ValueError as e:
        logger.warning(f"获取评价详情参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取评价详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取评价详情失败")


@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除评价记录

    - **evaluation_id**: 评价记录ID
    """
    try:
        # 验证evaluation_id格式
        eval_uuid = await ResumeEvaluationService.validate_uuid_param(evaluation_id, "评价ID")

        evaluation_service = ResumeEvaluationService(db)
        success = await evaluation_service.delete_evaluation(
            evaluation_id=eval_uuid,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=404, detail="评价记录不存在")

        return {"message": "评价记录已删除"}

    except ValueError as e:
        logger.warning(f"删除评价记录参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除评价记录失败: {e}")
        raise HTTPException(status_code=500, detail="删除评价记录失败")


@router.put("/{evaluation_id}/status")
async def update_resume_status(
    evaluation_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新简历状态

    - **evaluation_id**: 评价记录ID
    - **status**: 新状态 (pending, rejected, interview)
    """
    try:
        # 验证参数格式
        eval_uuid = await ResumeEvaluationService.validate_uuid_param(evaluation_id, "评价ID")
        new_status = await ResumeEvaluationService.validate_status_param(status)

        evaluation_service = ResumeEvaluationService(db)
        result = await evaluation_service.update_evaluation_status(
            evaluation_id=eval_uuid,
            user_id=current_user.id,
            new_status=new_status
        )

        if not result:
            raise HTTPException(status_code=404, detail="评价记录不存在")

        return result

    except ValueError as e:
        logger.warning(f"更新简历状态参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新简历状态失败: {e}")
        raise HTTPException(status_code=500, detail="更新简历状态失败")



@router.post("/export-zip")
async def export_zip(
        payload: ExportZipRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """批量导出简历原始附件 ZIP"""
    resume_ids = payload.resume_ids
    if not resume_ids:
        raise HTTPException(status_code=400, detail="resume_ids 不能为空")
    if len(resume_ids) > 50:
        raise HTTPException(status_code=400, detail="单次导出数量不能超过 50")

    # 使用ORM查询用户可见的简历附件
    from sqlalchemy import select

    stmt = (
        select(ResumeEvaluation)
        .where(
            ResumeEvaluation.id.in_(resume_ids),
            ResumeEvaluation.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    resume_evaluations = result.scalars().all()

    if not resume_evaluations:
        raise HTTPException(status_code=400, detail="未找到相关简历")

    # 打包 ZIP - 修复版本
    io_buf = io.BytesIO()
    failed = []

    try:
        logger.info(f"准备导出 {len(resume_evaluations)} 个简历")
        with zipfile.ZipFile(io_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for resume in resume_evaluations:
                logger.info(f"处理简历: {resume.original_filename}, 路径: {resume.file_path}")
                original_filename = resume.original_filename
                # 简单过滤路径穿越
                safe_name = Path(original_filename).name

                file_found = False
                # 直接使用数据库中存储的文件路径
                if resume.file_path and os.path.exists(resume.file_path):
                    logger.info(f"文件路径存在: {resume.file_path}")
                    try:
                        async with aiofiles.open(resume.file_path, "rb") as f:
                            data = await f.read()
                            logger.info(f"成功读取文件 {resume.file_path}, 大小: {len(data)} 字节")

                            # 使用 ZipInfo 设置正确的文件信息
                            zip_info = zipfile.ZipInfo(safe_name)
                            zip_info.date_time = time.localtime(time.time())[:6]
                            zip_info.compress_type = zipfile.ZIP_DEFLATED
                            # 设置文件权限 (可读)
                            zip_info.external_attr = 0o644 << 16

                            zf.writestr(zip_info, data)
                            file_found = True

                    except Exception as e:
                        logger.error(f"读取文件失败 {resume.file_path}: {e}")
                        failed.append({"name": safe_name, "reason": str(e)})
                else:
                    logger.warning(f"数据库中的文件路径不存在或无效: {resume.file_path}")
                    # 尝试在旧路径中查找文件
                    user_id = str(current_user.id)
                    possible_paths = [
                        os.path.join(settings.UPLOAD_DIR, user_id, original_filename),
                        os.path.join(settings.UPLOAD_DIR, str(resume.user_id), original_filename),
                        resume.file_path  # 即使文件不存在也尝试一下
                    ]

                    for file_path in possible_paths:
                        if file_path and os.path.exists(file_path):
                            try:
                                async with aiofiles.open(file_path, "rb") as f:
                                    data = await f.read()
                                    logger.info(f"成功从备用路径读取文件 {file_path}, 大小: {len(data)} 字节")

                                    # 使用 ZipInfo 设置正确的文件信息
                                    zip_info = zipfile.ZipInfo(safe_name)
                                    zip_info.date_time = time.localtime(time.time())[:6]
                                    zip_info.compress_type = zipfile.ZIP_DEFLATED
                                    # 设置文件权限 (可读)
                                    zip_info.external_attr = 0o644 << 16

                                    zf.writestr(zip_info, data)
                                    file_found = True
                                    break  # 成功找到文件，退出循环

                            except Exception as e:
                                logger.error(f"从备用路径读取文件失败 {file_path}: {e}")
                                continue  # 尝试下一个可能的路径

                        if file_found:
                            break

                    if not file_found:
                        logger.warning(f"所有可能的文件路径都尝试过，但未找到: {original_filename}")
                        failed.append({"name": safe_name, "reason": "文件不存在"})

        # 关键修复：在关闭ZipFile后获取完整的字节数据
        zip_data = io_buf.getvalue()

    except Exception as e:
        # 记录错误日志
        logger.error(f"创建ZIP文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建下载文件失败: {str(e)}")
    finally:
        # 确保流被关闭
        if not io_buf.closed:
            io_buf.close()

    # 生成文件名
    filename = f"resume_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    # 返回响应 - 使用Response替代StreamingResponse
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Length": str(len(zip_data)),  # 重要：设置正确的Content-Length
            "Content-Type": "application/zip"
        }
    )
