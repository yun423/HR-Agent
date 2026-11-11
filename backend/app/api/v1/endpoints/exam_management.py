"""
试卷管理API端点
处理试卷的CRUD操作和考试结果管理
负责试卷管理和考试结果管理，挂载前缀是 /exam-management。
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.schemas.user import User as UserSchema
# from app.models.exam import Exam, Question  # 注释掉未使用的导入
# from app.models.exam_result import ExamResult  # 注释掉未使用的导入
from app.api.deps import get_current_user
from app.core.logging import logger
from app.services.exam_service import ExamService
from app.schemas.exam import ExamGenerateRequest, ExamSubmitRequest, ExamCreateRequest

router = APIRouter()


# 获取试卷列表
@router.get("/papers")
async def get_exam_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取试卷列表
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.get_exam_list(skip, limit, search)
        return result
    except Exception as e:
        logger.error(f"Error getting exam list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取试卷列表失败: {str(e)}"
        )


# 保存试卷
@router.post("/papers")
async def save_exam(
    exam_data: ExamCreateRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    保存试卷到数据库
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.save_exam(exam_data.dict(), current_user.id)
        return result
    except Exception as e:
        logger.error(f"Error saving exam to database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存试卷失败: {str(e)}"
        )


# 获取试卷详情
@router.get("/papers/{paper_id}")
async def get_exam_detail(
    paper_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取试卷详情
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.get_exam_detail(paper_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting exam detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取试卷详情失败: {str(e)}"
        )


# 更新试卷
@router.put("/papers/{paper_id}")
async def update_exam(
    paper_id: str,
    exam_data: ExamCreateRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    更新试卷
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.update_exam(paper_id, exam_data.dict(), current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating exam: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新试卷失败: {str(e)}"
        )


# 删除试卷
@router.delete("/papers/{paper_id}")
async def delete_exam(
    paper_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    删除试卷
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.delete_exam(paper_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting exam: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除试卷失败: {str(e)}"
        )


# 获取单个试卷（用于分享页面）
@router.get("/papers/{paper_id}/share")
async def get_exam_for_share(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取单个试卷（用于分享页面，无需认证）
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.get_exam_for_share(paper_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting exam: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取试卷失败: {str(e)}"
        )


# 获取考试结果列表
@router.get("/exam-results")
async def get_exam_results(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query(None, description="搜索关键词（学生姓名或考试名称）"),
    exam_id: Optional[UUID] = Query(None, description="考试ID筛选"),
    department: str = Query(None, description="部门筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取考试结果列表，支持分页和筛选
    """
    try:
        exam_service = ExamService(db)
        # 转换UUID为字符串
        exam_id_str = str(exam_id) if exam_id else None
        result = await exam_service.get_exam_results(page, page_size, search, exam_id_str, department)
        return result
    except Exception as e:
        logger.error(f"Error getting exam results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取考试结果失败: {str(e)}"
        )




# 获取考试结果
@router.get("/exam-results/{result_id}")
async def get_exam_result(
    result_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取考试结果详情
    """
    try:
        exam_service = ExamService(db)
        result = await exam_service.get_exam_result(result_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting exam result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取考试结果失败: {str(e)}"
        )


# 导出考试结果为CSV
@router.get("/exam-results/{result_id}/export")
async def export_exam_result(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    导出考试结果为CSV文件
    """
    try:
        exam_service = ExamService(db)
        csv_content = await exam_service.export_exam_result_to_csv(result_id)

        # 创建响应头，指定为CSV文件下载
        from fastapi import Response

        headers = {
            "Content-Disposition": f"attachment; filename=exam_result_{result_id}.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }

        # 返回响应，使用 utf-8-sig 编码确保Excel正确显示中文
        return Response(
            content=csv_content.encode('utf-8-sig'),
            headers=headers
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error exporting exam result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出考试结果失败: {str(e)}"
        )