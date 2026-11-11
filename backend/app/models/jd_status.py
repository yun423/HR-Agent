import enum

class JDStatus(str, enum.Enum):
    """职位描述状态枚举"""
    DRAFT = "draft"  # 草稿
    PUBLISHED = "published"  # 发布
    ARCHIVED = "archived"  # 归档