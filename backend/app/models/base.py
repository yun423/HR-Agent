"""
  这是所有数据库模型的公共基类。
"""
import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.core.database import Base


class BaseModel(Base):
    """Base model 包括公共字段"""

    __abstract__ = True

    # 自动生成tablename
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # 分别是主键、创建时间、更新时间、是否启用、创建人、更新人
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, comment="主键ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_by = Column(UUID(as_uuid=True), nullable=True, comment="创建人用户ID")
    updated_by = Column(UUID(as_uuid=True), nullable=True, comment="更新人用户ID")

    def to_dict(self) -> Dict[str, Any]:
        """将模型实例转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """根据字典批量更新模型字段，并刷新 updated_at。"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()