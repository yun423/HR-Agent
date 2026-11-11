"""
    招聘邮箱配置和日志的Pydantic模式
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class EmailConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    imap_server: str = Field(..., min_length=1, max_length=255)
    imap_port: int = Field(993, ge=1, le=65535)
    imap_ssl: bool = True
    smtp_server: Optional[str] = Field(None, max_length=255)
    smtp_port: Optional[int] = Field(587, ge=1, le=65535)
    smtp_ssl: bool = True
    fetch_interval: int = Field(30, ge=1, le=1440)
    auto_fetch: bool = False
    status: str = Field("active")
    # 逗号分隔的主题过滤关键词；支持全角/半角逗号
    subject_keywords: Optional[str] = None


class EmailConfigCreate(EmailConfigBase):
    password: str = Field(..., min_length=1, max_length=512)


class EmailConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="名称")
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    imap_server: Optional[str] = Field(None, min_length=1, max_length=255, description="IMAP服务器地址")
    imap_port: Optional[int] = Field(None, ge=1, le=65535, description="IMAP端口")
    imap_ssl: Optional[bool] = Field(None, description="IMAP是否启用SSL")
    smtp_server: Optional[str] = Field(None, max_length=255, description="SMTP服务器地址")
    smtp_port: Optional[int] = Field(None, ge=1, le=65535, description="SMTP端口")
    smtp_ssl: Optional[bool] = Field(None, description="SMTP是否启用SSL")
    fetch_interval: Optional[int] = Field(None, ge=1, le=1440, description="自动抓取间隔，单位分钟")
    auto_fetch: Optional[bool] = Field(None, description="是否启用自动抓取")
    status: Optional[str] = Field(None, description="状态")
    password: Optional[str] = Field(None, min_length=0, max_length=512, description="邮箱授权码或密码")
    subject_keywords: Optional[str] = Field(None, description="邮件主题过滤关键词")


class EmailConfigInDB(EmailConfigBase):
    id: UUID = Field(..., description="唯一标识ID")
    connection_status: str = Field(..., description="连接状态")
    last_fetch_at: Optional[datetime] = Field(..., description="最后抓取时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class EmailConfig(EmailConfigInDB):
    pass


class EmailConnectionTest(BaseModel):
    imap_server: str = Field(..., description="IMAP服务器地址")
    imap_port: int = Field(..., description="IMAP端口")
    imap_ssl: bool = Field(..., description="IMAP是否启用SSL")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class EmailFetchLogBase(BaseModel):
    status: str = Field(..., description="状态")
    emails_found: int = Field(..., description="发现的邮件数量")
    resumes_extracted: int = Field(..., description="提取的简历数量")
    error_message: Optional[str] = Field(None, description="错误信息")


class EmailFetchLog(EmailFetchLogBase):
    id: UUID = Field(..., description="唯一标识ID")
    email_config_id: UUID = Field(..., description="邮箱配置ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class EmailFetchLogList(BaseModel):
    items: List[EmailFetchLog] = Field(..., description="数据列表")

class AutoEvaluateRequest(BaseModel):
    resume_text: str = Field(..., description="简历文本内容")
    position: Optional[str] = Field("", description="投递邮件主题，用于辅助匹配JD")
    filename: Optional[str] = Field(None, description="保存的文件名，默认为生成的 .txt 文件")
    login_name: str = Field(..., description="用户登录名称")
