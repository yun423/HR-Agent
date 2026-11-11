from __future__ import annotations

"""
邮件配置、抓取和发送服务：
    EmailConfigService 管理招聘邮箱配置的增删改查和连接测试；
    EmailFetchService 抓取最近邮件附件、记录抓取日志，并可触发简历评价；
    EmailSendService 用 SMTP 发送 Agent 生成的邮件。
    文件顶部的 _email_config_model() 等函数是延迟导入，减少循环依赖。
"""
import smtplib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from email.message import EmailMessage as SMTPMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, UUID

from app.utils.email_utils import EmailConfig as ReaderConfig, EmailReader
from pathlib import Path
import os

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.models.email_config import EmailConfig, EmailFetchLog
    from app.schemas.email_config import EmailConfigCreate, EmailConfigUpdate


def _email_config_model():
    from app.models.email_config import EmailConfig
    return EmailConfig


def _email_fetch_log_model():
    from app.models.email_config import EmailFetchLog
    return EmailFetchLog


def _resume_evaluation_model():
    from app.models.resume_evaluation import ResumeEvaluation
    return ResumeEvaluation


def _resume_evaluation_service():
    from app.services.resume_evaluation_service import ResumeEvaluationService
    return ResumeEvaluationService


@dataclass(frozen=True)
class SkillMailConfig:
    """Skill bundle 中的发送邮箱配置。"""

    email: str
    password: str
    smtp_server: str
    smtp_port: int
    use_ssl: bool


class EmailConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, skip: int = 0, limit: int = 100) -> List[EmailConfig]:
        EmailConfig = _email_config_model()
        stmt = select(EmailConfig).offset(skip).limit(limit).order_by(EmailConfig.created_at.desc())
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get(self, config_id: str) -> Optional[EmailConfig]:
        EmailConfig = _email_config_model()
        stmt = select(EmailConfig).where(EmailConfig.id == config_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: EmailConfigCreate,create_by: UUID) -> EmailConfig:
        EmailConfig = _email_config_model()
        config = EmailConfig(
            name=data.name,
            email=data.email,
            imap_server=data.imap_server,
            imap_port=data.imap_port,
            imap_ssl=data.imap_ssl,
            smtp_server=data.smtp_server,
            smtp_port=data.smtp_port,
            smtp_ssl=data.smtp_ssl,
            password=data.password,
            fetch_interval=data.fetch_interval,
            auto_fetch=data.auto_fetch,
            status=data.status,
            subject_keywords = data.subject_keywords,
            connection_status="unknown",
            created_by = create_by,
            updated_by = create_by
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update(self, config: EmailConfig, data: EmailConfigUpdate) -> EmailConfig:
        update_data = data.model_dump(exclude_unset=True)
        # 避免设置空密码
        if "password" in update_data and not update_data.get("password"):
            update_data.pop("password")
        for k, v in update_data.items():
            setattr(config, k, v)
        await self.db.commit()
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def delete(self, config: EmailConfig) -> None:
        await self.db.delete(config)
        await self.db.commit()
        await self.db.flush()

    async def test_connection(self, config: EmailConfig, password: Optional[str] = None) -> bool:
        reader_cfg = ReaderConfig(
            host=config.imap_server,
            port=config.imap_port,
            username=config.email,
            password=password or config.password or "",
            use_ssl=config.imap_ssl,
            protocol="IMAP",
        )
        reader = EmailReader(reader_cfg)
        ok = reader.connect()
        reader.disconnect()
        config.connection_status = "connected" if ok else "error"
        await self.db.flush()
        return ok


class EmailFetchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def manual_fetch(self, config: EmailConfig) -> EmailFetchLog:
        EmailFetchLog = _email_fetch_log_model()
        log = EmailFetchLog(email_config_id=config.id, status="running")
        self.db.add(log)
        await self.db.flush()

        reader_cfg = ReaderConfig(
            host=config.imap_server,
            port=config.imap_port,
            username=config.email,
            password=config.password or "",
            use_ssl=config.imap_ssl,
            protocol="IMAP",
        )
        reader = EmailReader(reader_cfg)
        try:
            if not reader.connect():
                log.status = "failed"
                log.error_message = "无法连接到邮箱服务器"
                return log

            # 选择收件箱并获取最近50封邮件
            reader.select_folder("INBOX")
            ids = reader.search_emails(["ALL"]) or []
            log.emails_found = len(ids)

            resumes = 0
            take = ids[-50:] if len(ids) > 50 else ids
            for msg_id in take:
                msg = reader.get_email(msg_id)
                if not msg:
                    continue
                for att in msg.attachments:
                    filename = (att.get("filename") or "").lower()
                    if filename.endswith((".pdf", ".doc", ".docx")):
                        resumes += 1

            log.resumes_extracted = resumes
            log.status = "success"
            config.last_fetch_at = datetime.utcnow()
            config.connection_status = "connected"
            return log
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            config.connection_status = "error"
            return log
        finally:
            reader.disconnect()

    async def list_logs(self, config_id: str, skip: int = 0, limit: int = 100) -> List[EmailFetchLog]:
        EmailFetchLog = _email_fetch_log_model()
        stmt = (
            select(EmailFetchLog)
            .where(EmailFetchLog.email_config_id == config_id)
            .offset(skip)
            .limit(limit)
            .order_by(EmailFetchLog.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def fetch_recent_attachments(
        self,
        config: EmailConfig,
        create_by: UUID,
        limit: int = 10,
        subject_keyword: list = None,
        output_dir: Optional[Path] = None,
    ) -> EmailFetchLog:
        """
        获取最近的邮件并在主题包含关键词时下载附件。
        """
        EmailFetchLog = _email_fetch_log_model()
        log = EmailFetchLog(email_config_id=config.id, status="running")
        self.db.add(log)
        await self.db.flush()

        base_dir = output_dir or (Path(__file__).resolve().parent.parent.parent / "uploads" / "email_attachments" / str(create_by))
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception:
            pass

        reader_cfg = ReaderConfig(
            host=config.imap_server,
            port=config.imap_port,
            username=config.email,
            password=config.password or "",
            use_ssl=config.imap_ssl,
            protocol="IMAP",
        )
        reader = EmailReader(reader_cfg)
        try:
            if not reader.connect():
                log.status = "failed"
                log.error_message = "无法连接到邮箱服务器"
                return log
            logger.debug("邮箱连接状态: %s", getattr(reader.connection, "state", "unknown"))
            select_result = reader.select_folder("INBOX")
            if select_result:
                logger.debug("成功选择邮箱: INBOX")

            ids = reader.search_emails(["ALL"]) or []
            if not ids:
                log.status = "success"
                log.emails_found = 0
                log.resumes_extracted = 0
                return log
            logger.debug("找到邮件 ID: %s", ids)
            take = ids[-limit:] if len(ids) > limit else ids
            log.emails_found = len(take)
            resumes = 0

            for msg_id in reversed(take):
                msg = reader.get_email(msg_id)
                if not msg:
                    continue
                subject = (msg.subject or "").lower()

                if subject_keyword and not any(keyword.lower() in subject for keyword in subject_keyword):
                    continue

                logger.info("发现符合条件的邮件: %s (ID: %s)", subject, msg_id)

                for att in (msg.attachments or []):
                    fname = att.get("filename") or "attachment"
                    content = att.get("content")
                    if not content:
                        continue
                    logger.debug("处理附件: %s", fname)
                    try:
                        ResumeEvaluation = _resume_evaluation_model()
                        existing = await self.db.execute(select(ResumeEvaluation).where(ResumeEvaluation.email_id == str(msg_id)))
                        records = existing.scalars().first()
                        if records:
                            logger.info("邮件 ID %s 已存在评价记录，跳过", msg_id)
                            continue
                    except Exception as e:
                        logger.warning("检查邮件 ID %s 是否已存在评价记录时出错: %s", msg_id, e)
                        pass
                    target_path = base_dir / fname
                    idx = 1
                    while target_path.exists():
                        stem = target_path.stem
                        suffix = target_path.suffix
                        target_path = base_dir / f"{stem}_{idx}{suffix}"
                        idx += 1
                    try:
                        with open(target_path, "wb") as f:
                            f.write(content)
                        resumes += 1
                        logger.info("保存附件成功: %s", target_path)
                        try:
                            ResumeEvaluationService = _resume_evaluation_service()
                            ev_svc = ResumeEvaluationService(self.db)
                            user_id = create_by
                            if user_id:
                                logger.info("开始评价简历: %s", fname)
                                await ev_svc.evaluate_resume_auto(user_id=user_id, subject=subject, file_content=content, filename=fname, email_id=str(msg_id))
                                logger.info("成功评价简历: %s", fname)
                        except Exception as e:
                            logger.warning("评价简历 %s 时出错: %s", fname, e)
                            pass
                    except Exception as e:
                        logger.warning("保存附件 %s 时出错: %s", fname, e)
                        pass

            log.resumes_extracted = resumes
            log.error_message = None
            log.status = "success"
            config.last_fetch_at = datetime.utcnow()
            config.connection_status = "connected"
            return log
        except Exception as e:
            log.status = "failed"
            log.error_message = str(e)
            config.connection_status = "error"
            return log
        finally:
            reader.disconnect()


class EmailSendService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config_path = Path(__file__).resolve().parents[2] / "skills" / "hr-agent-email" / "config.txt"

    async def send_agent_email(
        self,
        user_id: UUID,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> dict:
        config = self._load_skill_mail_config()
        if not recipient_email:
            raise ValueError("缺少收件人邮箱地址。")
        if not subject:
            raise ValueError("缺少邮件主题。")
        if not body:
            raise ValueError("缺少邮件正文。")

        rejected_recipients = self._send_via_smtp(
            config=config,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )
        if rejected_recipients:
            reason = rejected_recipients.get(recipient_email) or next(iter(rejected_recipients.values()))
            raise ValueError(f"SMTP 服务器拒收该邮件：{reason}")

        return {
            "recipient_email": recipient_email,
            "subject": subject,
            "sender_email": config.email,
            "config_path": str(self.config_path),
            "status": "submitted",
            "delivery_note": "SMTP 服务器已接受邮件，但最终投递结果以收件方服务器返回为准。",
        }

    def _load_skill_mail_config(self) -> SkillMailConfig:
        if not self.config_path.exists():
            raise ValueError(f"未找到邮箱配置文件：{self.config_path}")

        raw: dict[str, str] = {}
        for line in self.config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            raw[key.strip()] = value.strip()

        def require(key: str) -> str:
            value = raw.get(key, "").strip()
            if not value or value.startswith("your_") or value.endswith("example.com"):
                raise ValueError(f"邮箱配置缺少有效字段：{key}，请先填写 {self.config_path}")
            return value

        def optional_int(key: str, default: int) -> int:
            value = raw.get(key, "").strip()
            if not value:
                return default
            try:
                return int(value)
            except ValueError as exc:
                raise ValueError(f"邮箱配置字段 {key} 必须是整数") from exc

        use_ssl = raw.get("MAIL_ACCOUNT_1_USE_SSL", "true").strip().lower() in {"1", "true", "yes", "on"}

        return SkillMailConfig(
            email=require("MAIL_ACCOUNT_1_EMAIL"),
            password=require("MAIL_ACCOUNT_1_PASSWORD"),
            smtp_server=require("MAIL_ACCOUNT_1_SMTP_SERVER"),
            smtp_port=optional_int("MAIL_ACCOUNT_1_SMTP_PORT", 465 if use_ssl else 587),
            use_ssl=use_ssl,
        )

    def _send_via_smtp(
        self,
        config: SkillMailConfig,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> dict:
        message = SMTPMessage()
        message["From"] = config.email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content(body)

        if config.use_ssl:
            with smtplib.SMTP_SSL(config.smtp_server, config.smtp_port or 465, timeout=20) as server:
                server.login(config.email, config.password or "")
                return server.send_message(message) or {}

        with smtplib.SMTP(config.smtp_server, config.smtp_port or 587, timeout=20) as server:
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception:
                pass
            server.login(config.email, config.password or "")
            return server.send_message(message) or {}
