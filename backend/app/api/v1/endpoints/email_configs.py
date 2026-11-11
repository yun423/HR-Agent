"""
招聘邮箱配置和操作的API端点
负责招聘邮箱配置和抓取，挂载前缀是 /email-configs。
主要接口：
    GET    /email-configs/
    POST   /email-configs/
    GET    /email-configs/{config_id}
    PUT    /email-configs/{config_id}
    DELETE /email-configs/{config_id}
    POST   /email-configs/{config_id}/test
    POST   /email-configs/{config_id}/fetch
    GET    /email-configs/{config_id}/logs
    GET    /email-configs/{config_id}/latest-email

    接口依赖 get_current_superuser的，只有超级管理员能管理招聘邮箱。
    EmailConfigService 负责配置 CRUD 和连接测试。
    EmailFetchService 负责手动抓取邮件和查询抓取日志。
    latest-email 会读取邮箱最近邮件，用于查看最新邮件内容或附件情况。

"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_superuser
from app.schemas.user import User as UserSchema
from app.schemas.email_config import (
    EmailConfig as EmailConfigSchema,
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailFetchLog,
    EmailFetchLogList,
    EmailConnectionTest,
)
from app.services.email_service import EmailConfigService, EmailFetchService
from app.utils.email_utils import EmailConfig as ReaderConfig, EmailReader


router = APIRouter()


@router.get("/", response_model=List[EmailConfigSchema])
async def list_email_configs(
    skip: int = 0,
    limit: int = 100,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    configs = await svc.list(skip=skip, limit=limit)
    return configs


@router.post("/", response_model=EmailConfigSchema)
async def create_email_config(
    config_data: EmailConfigCreate,
    request: Request,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    config = await svc.create(config_data,create_by=current_user.id)
    try:
        scheduler = getattr(request.app.state, "email_scheduler", None)
        if scheduler:
            await scheduler.refresh_for_config(config)
    except Exception:
        pass
    return config


@router.get("/{config_id}", response_model=EmailConfigSchema)
async def get_email_config(
    config_id: str,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    config = await svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    return config


@router.put("/{config_id}", response_model=EmailConfigSchema)
async def update_email_config(
    config_id: str,
    update_data: EmailConfigUpdate,
    request: Request,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    config = await svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    updated = await svc.update(config, update_data)
    updated.updated_by = current_user.id
    await db.flush()
    await db.refresh(updated)
    try:
        scheduler = getattr(request.app.state, "email_scheduler", None)
        if scheduler:
            await scheduler.refresh_for_config(updated)
    except Exception:
        pass
    return updated


@router.delete("/{config_id}")
async def delete_email_config(
    config_id: str,
    request: Request,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    config = await svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    await svc.delete(config)
    try:
        scheduler = getattr(request.app.state, "email_scheduler", None)
        if scheduler:
            await scheduler.stop_task_for_config(config_id)
    except Exception:
        pass
    return {"message": "邮箱配置已删除"}


@router.post("/{config_id}/test")
async def test_email_connection(
    config_id: str,
    test_data: EmailConnectionTest,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    svc = EmailConfigService(db)
    config = await svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    ok = await svc.test_connection(config, password=test_data.password)
    return {"success": ok}


@router.post("/{config_id}/fetch")
async def manual_fetch_emails(
    config_id: str,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    cfg_svc = EmailConfigService(db)
    fetch_svc = EmailFetchService(db)
    config = await cfg_svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    log = await fetch_svc.manual_fetch(config)
    await db.commit()
    return {"message": "邮件抓取完成", "log": log.to_dict()}


@router.get("/{config_id}/logs", response_model=EmailFetchLogList)
async def list_fetch_logs(
    config_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    cfg_svc = EmailConfigService(db)
    config = await cfg_svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    fetch_svc = EmailFetchService(db)
    logs = await fetch_svc.list_logs(config_id, skip=skip, limit=limit)
    return {"items": [log.to_dict() for log in logs]}


@router.get("/{config_id}/latest-email")
async def get_latest_email(
    config_id: str,
    sender: str | None = None,
    current_user: UserSchema = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> Any:
    cfg_svc = EmailConfigService(db)
    config = await cfg_svc.get(config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邮箱配置未找到")
    reader_cfg = ReaderConfig(
        host=config.imap_server,
        port=config.imap_port,
        username=config.email,
        password=config.password or "",
        use_ssl=config.imap_ssl,
        protocol="IMAP",
    )
    reader = EmailReader(reader_cfg)
    if not reader.connect():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法连接到邮箱服务器")
    try:
        reader.select_folder("INBOX")
        ids = reader.search_emails(["FROM", f'"{sender}"']) if sender else reader.search_emails(["ALL"]) or []
        if not ids:
            return {"message": "邮箱中没有邮件"}
        msg_id = ids[-1]
        msg = reader.get_email(msg_id)
        if not msg:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="读取邮件失败")
        body = msg.body or msg.html_body or ""
        snippet = body[:2000]
        return {
            "subject": msg.subject,
            "sender": msg.sender,
            "date": msg.date.isoformat(),
            "snippet": snippet,
        }
    finally:
        reader.disconnect()
