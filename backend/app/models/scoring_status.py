import enum

class ScoringStatus(str, enum.Enum):
    """评分标准状态枚举"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 激活
    ARCHIVED = "archived"  # 归档