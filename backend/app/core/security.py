"""
    用于密码哈希和JWT令牌的安全工具
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt  # 用于生成和解析JWT token。
from passlib.context import CryptContext  # 用于密码哈希和校验。

from app.core.config import settings  # 导入 settings，从配置里读取：SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

'''
    security.py是后端的安全工具模块，主要负责两类事情：
        1. 密码哈希和密码校验。
        2. JWT访问令牌的生成和验证。
    
    这个文件是认证系统的底层工具：注册时用它加密密码，登录时用它校验密码并生成JWT，请求鉴权时用它验证JWT。
        
    JWT：全称JSON Web Token
        1. 是一种开放标准（RFC 7519），用于在网络应用环境间安全地传输信息。
        2. 它以JSON对象 的形式编码声明，通常用于：
            用户身份认证（Authentication），如：登录注册功
            信息交换（Information Exchange）
    
    举例：在登录验证中
        1. 用户提交用户名和密码
        2. 服务端验证成功后，生成一个JWT（包含用户 ID、角色、过期时间等信息） 并将该JWT返回给客户端（通常放在响应体或Cookie中）
        3. 客户端后续请求 会携带该Token（JWT） 发送给服务器
        4. 服务端验证JWT的签名和有效期，确认用户身份

'''

# 创建了密码哈希上下文
#    意思是项目使用 bcrypt算法 保存密码。
#       数据库里不会存明文密码，而是存 bcrypt生成的哈希值。
#       deprecated="auto" 表示如果以后配置了更推荐的新算法，旧算法可以被识别为过时。
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 定义JWT签名算法
#   使用 HS256算法签名JWT。HS256是对称签名算法，生成和验证token都使用同一个SECRET_KEY。
ALGORITHM = "HS256"


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
        创建JWT访问令牌: 创建JWT token
            data 是要写入token的载荷，比如用户ID、用户名等。
            expires_delta 是可选的过期时间，如果调用方不传，就使用配置里的默认过期时间。
    """

    # 复制传入数据，避免修改原始字典
    to_encode = data.copy()
    # 判断是否传入自定义过期时间
    #    1. 如果传了，则使用传入的过期时间
    #    2. 如果没有传，则使用默认的过期时间ACCESS_TOKEN_EXPIRE_MINUTES
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # 更新过期时间
    #   exp 是JWT标准字段，表示过期时间。
    to_encode.update({"exp": expire})
    # 使用密钥和算法生成 token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
        验证登录密码与其哈希值
    """

    # 会把用户输入的明文密码和数据库里的哈希密码比较。
    #       返回True表示密码正确，False表示密码错误。
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
        生成密码哈希： 用来在注册或创建用户时把明文密码转换成哈希值。
            password: 要哈希的密码
    """
    """
        bcrypt 对密码长度有限制，最多处理72字节。
        如果密码超过72字节：
            1. 记录warning日志。
            2. 截断到72字节。
            3. 再进行哈希, 返回bcrypt哈希字符串，存入数据库
    """
    try:
        # bcrypt的最大密码长度为72字节
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # 截断密码到 72 字节 ，但对此进行警告
            logger.warning(f"密码长度为{len(password_bytes)}字节，截断为72字节以兼容bcrypt")
            password = password_bytes[:72].decode('utf-8', errors='ignore')

        return pwd_context.hash(password)

    except Exception as e:
        logger.error(f"密码哈希错误: {e}")
        raise


def verify_token(token: str) -> Optional[dict]:
    """
        验证并解码JWT令牌
    """
    """
        1. 使用settings.SECRET_KEY和HS256解码token。
        2. 如果token合法且未过期，返回payload字典。
        3. 如果token无效、签名错误、过期等，捕获jwt.JWTError，返回None。
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload
    except jwt.JWTError:
        return None

