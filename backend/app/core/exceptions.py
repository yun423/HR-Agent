''''''

"""
exceptions.py 自定义异常类。
这个文件的作用和价值：
    1. 让业务代码可以抛出语义明确的异常，比如“用户不存在”、“文件类型不支持”、“LLM 限流”，然后统一转换成对应的HTTP响应。
    2. 把错误分成了清晰的业务类型，并且每个异常都自带HTTP状态码。
        这样业务层只需要抛出准确的异常，统一异常处理器就可以把它转换成规范的JSON响应。
        
"""


from typing import Any, Dict, Optional


class BaseHTTPException(Exception):
    """
        基础HTTP异常类
            1. 继承 Python 原生 Exception，但额外保存了三个字段：message,status_code,details
            2. 也就是说，项目里的异常不只是错误信息，还带有HTTP状态码 status_code
            3. details 用来放额外错误信息，比如: 字段级错误、调试信息等
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# 通用HTTP异常:
#   这些类本身比较通用，后面的业务异常大多继承它们。

class ValidationError(BaseHTTPException):
    """验证错误异常: 400，参数校验失败"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class AuthenticationError(BaseHTTPException):
    """认证错误异常: 401，认证失败，比如没登录或 token 无效。"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(BaseHTTPException):
    """授权错误异常: 403，权限不足。"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class NotFoundError(BaseHTTPException):
    """资源未找到异常: 404，资源不存在。"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ConflictError(BaseHTTPException):
    """资源冲突异常: 409，资源冲突，比如重复创建。"""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class RateLimitError(BaseHTTPException):
    """速率限制超出异常: 429，请求过于频繁。"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class InternalServerError(BaseHTTPException):
    """内部服务器错误异常: 500，服务器内部错误。"""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)


class ServiceUnavailableError(BaseHTTPException):
    """服务不可用异常: 503，服务不可用。"""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, status_code=503)




# 用户和认证相关异常：
#    用户登录注册、token失效等相关的异常

class UserNotFoundError(NotFoundError):
    """用户未找到异常: 用户不存在，继承 NotFoundError，HTTP 404。"""

    def __init__(self, user_id: str = None):
        message = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(message)


class UserAlreadyExistsError(ConflictError):
    """用户已存在异常: 用户已存在，继承 ConflictError，HTTP 409。"""

    def __init__(self, field: str = "email"):
        super().__init__(f"User with this {field} already exists")


class InvalidCredentialsError(AuthenticationError):
    """无效凭据异常: 邮箱或密码错误，HTTP 401。"""

    def __init__(self):
        super().__init__("Invalid email or password")


class InactiveUserError(AuthenticationError):
    """非活跃用户异常: 用户未激活，HTTP 401。"""

    def __init__(self):
        super().__init__("User account is inactive")


class InvalidTokenError(AuthenticationError):
    """无效令牌异常: token 无效或过期，HTTP 401。"""

    def __init__(self):
        super().__init__("Invalid or expired token")


class TokenExpiredError(AuthenticationError):
    """令牌已过期异常: token 过期，HTTP 401。"""

    def __init__(self):
        super().__init__("Token has expired")




# 文件/文档处理异常：
#   这些通常会在上传简历、知识库文档解析、文件校验时使用。

class DocumentNotFoundError(NotFoundError):
    """文档未找到异常: 文档不存在，404。"""

    def __init__(self, document_id: str = None):
        message = f"Document {document_id} not found" if document_id else "Document not found"
        super().__init__(message)


class DocumentUploadError(ValidationError):
    """文档上传错误异常： 上传失败，400。"""

    def __init__(self, message: str = "Document upload failed"):
        super().__init__(message)


class UnsupportedFileTypeError(ValidationError):
    """不支持的文件类型异常： 文件类型不支持，400。"""

    def __init__(self, file_type: str = None):
        message = f"Unsupported file type: {file_type}" if file_type else "Unsupported file type"
        super().__init__(message)


class FileSizeExceededError(ValidationError):
    """文件大小超出限制异常： 文件太大，400。"""

    def __init__(self, max_size: str = None):
        message = f"File size exceeds maximum allowed size of {max_size}" if max_size else "File size too large"
        super().__init__(message)


class DocumentProcessingError(InternalServerError):
    """文档处理错误异常： 文档解析或处理失败，500。"""

    def __init__(self, message: str = "Document processing failed"):
        super().__init__(message)





# 对话相关异常：
#   聊天/对话模块异常

class ConversationNotFoundError(NotFoundError):
    """对话未找到异常： 对话不存在"""

    def __init__(self, conversation_id: str = None):
        message = f"Conversation {conversation_id} not found" if conversation_id else "Conversation not found"
        super().__init__(message)


class MessageNotFoundError(NotFoundError):
    """消息未找到异常： 消息不存在。"""

    def __init__(self, message_id: str = None):
        message = f"Message {message_id} not found" if message_id else "Message not found"
        super().__init__(message)


class ConversationAccessDeniedError(AuthorizationError):
    """对话访问被拒绝异常：当前用户无权访问该对话。"""

    def __init__(self):
        super().__init__("Access to this conversation is denied")




# 知识库相关异常

class KnowledgeBaseNotFoundError(NotFoundError):
    """知识库未找到异常： 知识库不存在。"""

    def __init__(self, kb_id: str = None):
        message = f"Knowledge base {kb_id} not found" if kb_id else "Knowledge base not found"
        super().__init__(message)


# LLM/Embedding 相关异常
#    这类异常通常用于调用外部AI服务失败时，让接口返回更准确的错误状态。

class LLMServiceError(InternalServerError):
    """LLM服务错误异常： LLM 服务内部错误，500。"""

    def __init__(self, message: str = "LLM service error"):
        super().__init__(message)


class LLMRateLimitError(RateLimitError):
    """LLM速率限制超出异常： LLM API 限流，429。"""

    def __init__(self):
        super().__init__("LLM API rate limit exceeded")


class LLMQuotaExceededError(ServiceUnavailableError):
    """LLM配额超出异常： LLM 配额耗尽，503。"""

    def __init__(self):
        super().__init__("LLM API quota exceeded")


class EmbeddingServiceError(InternalServerError):
    """嵌入服务错误异常： Embedding 服务错误，500。"""

    def __init__(self, message: str = "Embedding service error"):
        super().__init__(message)





# 数据库相关异常

class DatabaseError(InternalServerError):
    """数据库错误异常： 通用数据库错误，500。"""

    def __init__(self, message: str = "Database error"):
        super().__init__(message)


class DatabaseConnectionError(ServiceUnavailableError):
    """数据库连接错误异常： 数据库连接失败，503。"""

    def __init__(self):
        super().__init__("Database connection failed")


class DatabaseIntegrityError(ConflictError):
    """数据库完整性错误异常： 唯一约束、外键等完整性冲突，409。"""

    def __init__(self, message: str = "Database integrity constraint violated"):
        super().__init__(message)



# 搜索和配置相关异常

class SearchError(InternalServerError):
    """搜索错误异常： 搜索失败。"""

    def __init__(self, message: str = "Search operation failed"):
        super().__init__(message)


class VectorSearchError(SearchError):
    """向量搜索错误异常： 向量搜索失败。"""

    def __init__(self, message: str = "Vector search failed"):
        super().__init__(message)


class ConfigurationError(InternalServerError):
    """配置错误异常： 配置错误。"""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(message)


class MissingConfigurationError(ConfigurationError):
    """缺少配置异常： 缺少必要配置。"""

    def __init__(self, config_key: str):
        super().__init__(f"Missing required configuration: {config_key}")




# 外部服务异常
#   用于第三方服务
class ExternalServiceError(ServiceUnavailableError):
    """外部服务错误异常： 外部服务不可用。"""

    def __init__(self, service_name: str = "external service"):
        super().__init__(f"{service_name} is currently unavailable")


class ExternalServiceTimeoutError(ServiceUnavailableError):
    """外部服务超时异常： 外部服务请求超时。"""

    def __init__(self, service_name: str = "external service"):
        super().__init__(f"{service_name} request timed out")







