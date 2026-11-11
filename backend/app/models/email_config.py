"""
    邮箱配置和抓取日志的模型
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class EmailConfig(BaseModel):
    """ 招聘邮箱配置 ： 用于配置系统从招聘邮箱抓取简历邮件"""

    __tablename__ = "email_configs"

    name = Column(String(255), nullable=False, comment="邮箱配置名称")
    email = Column(String(255), nullable=False, unique=True, comment="邮箱地址")

    # IMAP配置
    imap_server = Column(String(255), nullable=False, comment="IMAP服务器地址")
    imap_port = Column(Integer, nullable=False, default=993, comment="IMAP端口")
    imap_ssl = Column(Boolean, nullable=False, default=True, comment="IMAP是否启用SSL")

    # SMTP配置
    smtp_server = Column(String(255), nullable=True, comment="SMTP服务器地址")
    smtp_port = Column(Integer, nullable=True, default=587, comment="SMTP端口")
    smtp_ssl = Column(Boolean, nullable=False, default=True, comment="SMTP是否启用SSL")

    # 认证信息
    password = Column(String(512), nullable=True, comment="邮箱授权码或密码")

    # 抓取设置： 抓取间隔，是否自动抓取
    fetch_interval = Column(Integer, nullable=False, default=30, comment="自动抓取间隔，单位分钟")
    auto_fetch = Column(Boolean, nullable=False, default=False, comment="是否启用自动抓取")
    # 用于过滤简历邮件的主题关键词（逗号分隔，支持全角/半角逗号）
    subject_keywords = Column(Text, nullable=True, comment="简历邮件主题过滤关键词")

    # 状态信息
    status = Column(String(50), nullable=False, default="active", comment="邮箱配置状态")
    connection_status = Column(String(50), nullable=False, default="unknown", comment="邮箱连接状态")
    last_fetch_at = Column(DateTime, nullable=True, comment="最后抓取时间")

    # 关联关系：表示一个邮箱配置可以有多条抓取日志
    logs = relationship("EmailFetchLog", back_populates="email_config", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EmailConfig(email='{self.email}', status='{self.status}', connection='{self.connection_status}')>"


class EmailFetchLog(BaseModel):
    """邮件抓取操作的日志： """

    __tablename__ = "email_fetch_logs"

    # 记录每次抓取邮件的运行状态、找到多少邮件、提取多少简历以及错误信息
    status = Column(String(50), nullable=False, default="running", comment="抓取任务状态")
    emails_found = Column(Integer, nullable=False, default=0, comment="发现的邮件数量")
    resumes_extracted = Column(Integer, nullable=False, default=0, comment="提取的简历数量")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 关系：属于哪个邮箱配置对象
    email_config_id = Column(UUID(as_uuid=True), ForeignKey("email_configs.id"), nullable=False, index=True, comment="邮箱配置ID")
    email_config = relationship("EmailConfig", back_populates="logs")

    def __repr__(self):
        return f"<EmailFetchLog(config='{self.email_config_id}', status='{self.status}', found={self.emails_found})>"

