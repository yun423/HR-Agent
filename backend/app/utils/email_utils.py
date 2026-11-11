""""""
import imaplib
import platform
import poplib
import smtplib
import email
import socket
from email.header import decode_header
from email.message import Message
from typing import List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


"""
    email_utils.py 是一个邮件读取工具模块，主要用于连接IMAP/POP3邮箱服务器、搜索邮件、读取邮件内容、解析正文和附件。
    主要有三个类：
        EmailConfig：保存邮箱连接配置。
        EmailMessage：保存解析后的邮件内容。
        EmailReader：真正负责连接邮箱、搜索邮件、读取邮件、解析邮件。
"""



class EmailConfig:
    """
        邮箱配置类
    """
    def __init__(self, host: str, port: int, username: str, password: str,
                 use_ssl: bool = True, protocol: str = "IMAP"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.protocol = protocol.upper()  # IMAP or POP3


class EmailMessage:
    """
        邮件消息容器
    """
    def __init__(self, subject: str, sender: str, recipients: List[str],
                 date: datetime, body: str, html_body: Optional[str] = None,
                 attachments: Optional[List[dict]] = None):
        self.subject = subject  # 邮件主题
        self.sender = sender  # 发件人
        self.recipients = recipients  # 收件人列表
        self.date = date  # 邮件时间
        self.body = body  # 纯文本正文
        self.html_body = html_body  # HTML正文
        self.attachments = attachments or []  # 附件列表


class EmailReader:
    """
        核心读取类: 用于从IMAP或POP3服务器读取邮件的工具类
            拿到邮箱配置后，后续会把IMAP或POP3连接保存在self.connection
    """

    def __init__(self, config: EmailConfig):
        self.config = config
        self.connection = None

    def connect(self) -> bool:
        """
            连接到邮件服务器:
                连接成功返回True，失败记录日志并返回False。
        """
        try:
            if self.config.protocol == "IMAP":
                if self.config.use_ssl:
                    self.connection = imaplib.IMAP4_SSL(self.config.host, self.config.port)
                else:
                    self.connection = imaplib.IMAP4(self.config.host, self.config.port)
                self.connection.login(self.config.username, self.config.password)


            elif self.config.protocol == "POP3":
                if self.config.use_ssl:
                    self.connection = poplib.POP3_SSL(self.config.host, self.config.port)
                else:
                    self.connection = poplib.POP3(self.config.host, self.config.port)
                self.connection.user(self.config.username)
                self.connection.pass_(self.config.password)
            else:
                raise ValueError(f"Unsupported protocol: {self.config.protocol}")

            logger.info(f"Successfully connected to {self.config.protocol} server {self.config.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to email server: {str(e)}")
            return False

    def disconnect(self):
        """
            关闭邮箱连接
        """
        if self.connection:
            try:
                if self.config.protocol == "IMAP":
                    # 只有在SELECTED状态下才调用close()
                    # 否则直接logout以避免"command CLOSE illegal in state AUTH"错误
                    try:
                        self.connection.close()
                    except Exception as close_error:
                        # 如果close失败，很可能是因为我们不在SELECTED状态
                        # 这是可以接受的，只需记录为调试信息并继续logout
                        logger.debug(f"Close command failed (likely not in SELECTED state): {str(close_error)}")
                    self.connection.logout()
                elif self.config.protocol == "POP3":
                    self.connection.quit()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.error(f"Error while disconnecting: {str(e)}")
            finally:
                self.connection = None

    def list_folders(self) -> List[str]:
        """
            列出邮箱文件夹（仅限IMAP）

        """
        if not self.connection or self.config.protocol != "IMAP":
            return []

        try:
            imaplib.Commands["ID"] = "NONAUTH"
            args = ("name", "111",  "version", "1.0.0", "vendor", "myclient")
            typ, dat = self.connection._simple_command('ID', '("' + '" "'.join(args) + '")')
            print(self.connection._untagged_response(typ, dat, 'ID'))

            status, folders = self.connection.list()
            if status == "OK":
                folder_names = []
                for folder in folders:
                    # 从响应中解析文件夹名称
                    folder_str = folder.decode('utf-8') if isinstance(folder, bytes) else folder
                    # 提取文件夹名称（通常在引号中）
                    if '"' in folder_str:
                        folder_name = folder_str.split('"')[-2]
                    else:
                        folder_name = folder_str.split()[-1]
                    folder_names.append(folder_name)
                return folder_names
            return []
        except Exception as e:
            logger.error(f"Error listing folders: {str(e)}")
            return []

    def select_folder(self, folder: str = "INBOX") -> int:
        """
            选择要读取邮件的文件夹（仅限IMAP）
                folder (str): 文件夹名称，默认为INBOX
                返回: 文件夹中的邮件数量
        """
        if not self.connection or self.config.protocol != "IMAP":
            return 0

        try:
            imaplib.Commands["ID"] = "NONAUTH"
            args = ("name", "111",  "version", "1.0.0", "vendor", "myclient")
            typ, dat = self.connection._simple_command('ID', '("' + '" "'.join(args) + '")')
            print(self.connection._untagged_response(typ, dat, 'ID'))

            status, msg_count = self.connection.select(folder)
            print(f'status:{status}, msg_count:{msg_count}')

            if status == "OK":
                count = int(msg_count[0]) if isinstance(msg_count[0], bytes) else int(msg_count[0])
                logger.info(f"Selected folder '{folder}' with {count} messages")
                return count
            return 0
        except Exception as e:
            logger.error(f"Error selecting folder '{folder}': {str(e)}")
            return 0

    def search_emails(self, criteria: list, charset: Optional[str] = "UTF-8") -> List[int]:
        """
            根据条件搜索邮件（仅限IMAP）
                criteria (str): 搜索条件（例如："FROM user@example.com", "SUBJECT 'test'"）
                返回：符合条件的邮件UID列表。
        """
        if not self.connection or self.config.protocol != "IMAP":
            return []

        try:
            # 优先使用UTF-8 字符集，失败则回退到默认
            status, messages = self.connection.uid('SEARCH', *criteria)
            if status == "OK":
                msg_ids = messages[0].split()
                print(f'msg_ids:{msg_ids}')
                return [int(msg_id) for msg_id in msg_ids]
            return []
        except Exception as e:
            logger.warning(f"Search with charset '{charset}' failed: {str(e)}; retrying without charset")
            try:
                status, messages = self.connection.search(None, *criteria)
                if status == "OK":
                    msg_ids = messages[0].split()
                    return [int(msg_id) for msg_id in msg_ids]
                return []
            except Exception as e2:
                logger.error(f"Error searching emails with criteria '{criteria}': {str(e2)}")
                return []

    def get_email(self, msg_id: int) -> Optional[EmailMessage]:
        """
            根据邮件ID获取邮件
                msg_id (int): 邮件ID
                返回：EmailMessage邮件消息对象，失败时返回None
        """
        if not self.connection:
            return None

        try:
            if self.config.protocol == "IMAP":
                return self._get_imap_email(msg_id)
            elif self.config.protocol == "POP3":
                return self._get_pop3_email(msg_id)
            return None
        except Exception as e:
            logger.error(f"Error retrieving email {msg_id}: {str(e)}")
            return None

    def _get_imap_email(self, msg_id: int) -> Optional[EmailMessage]:
        """
            使用IMAP协议检索邮件
                msg_id (int): 邮件ID
                返回: EmailMessage邮件消息对象
        """
        status, msg_data = self.connection.uid('FETCH', str(msg_id), "(RFC822)")
        if status != "OK":
            return None

        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)
        return self._parse_email_message(email_message)

    def _get_pop3_email(self, msg_id: int) -> Optional[EmailMessage]:
        """
            使用POP3协议检索邮件
                msg_id (int): 邮件ID（基于1的索引）
                返回: EmailMessage邮件消息对象
        """
        msg_lines, octets = self.connection.retr(msg_id)
        raw_email = b'\n'.join(msg_lines)
        email_message = email.message_from_bytes(raw_email)
        return self._parse_email_message(email_message)

    def _parse_email_message(self, email_message: Message) -> EmailMessage:
        """
            解析邮件内容
                email_message (Message): 邮件消息
        """
        # 主题
        subject = self._decode_header_value(email_message.get("Subject", ""))

        # 发件人
        sender = self._decode_header_value(email_message.get("From", ""))

        # 收件人
        to_header = email_message.get("To", "")
        recipients = [self._decode_header_value(addr) for addr in to_header.split(",")] if to_header else []

        # 日期
        date_str = email_message.get("Date", "")
        try:
            date = datetime.strptime(date_str[:-6], "%a, %d %b %Y %H:%M:%S") if date_str else datetime.now()
        except:
            date = datetime.now()

        # 正文和附件
        body = ""
        html_body = ""
        attachments = []

        #  如果邮件是multipart，就遍历所有part
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Content-Disposition包含attachment：当附件处理。
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                        payload = part.get_payload(decode=True)
                        attachments.append({
                            "filename": filename,
                            "content": payload,
                            "content_type": content_type
                        })
                    continue

                # text/plain：解析为纯文本正文。
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors="ignore")
                    except Exception:
                        body = part.get_payload()

                # text/html：解析为HTML正文。
                elif content_type == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html_body = part.get_payload(decode=True).decode(charset, errors="ignore")
                    except Exception:
                        html_body = part.get_payload()

        # 如果不是multipart，就直接根据content_type解析单体正文。
        else:
            content_type = email_message.get_content_type()
            charset = email_message.get_content_charset() or "utf-8"
            # text/plain：解析为纯文本正文。
            if content_type == "text/plain":
                try:
                    body = email_message.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    body = email_message.get_payload()
            # text/html：解析为HTML正文。
            elif content_type == "text/html":
                try:
                    html_body = email_message.get_payload(decode=True).decode(charset, errors="ignore")
                except Exception:
                    html_body = email_message.get_payload()

        # 最后返回一个EmailMessage对象
        return EmailMessage(
            subject=subject,
            sender=sender,
            recipients=recipients,
            date=date,
            body=body,
            html_body=html_body,
            attachments=attachments
        )

    def _decode_header_value(self, header_value: str) -> str:
        """
            解码邮件头：用来处理邮件头里的编码问题
                header_value: Encoded header value
        """
        if not header_value:
            return ""

        # 把它拆成多个片段，然后按对应encoding解码
        # 如果解码失败，就回退到UTF-8并忽略非法字符
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_string += part.decode(encoding)
                    except Exception:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string

    def __enter__(self):
        """ 进入with时自动连接 """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ 退出时自动断开连接 """
        self.disconnect()


# 测试使用:
if __name__ == "__main__":
    # IMAP测试

    # 创建163邮箱IMAP配置。
    config = EmailConfig(
        host="imap.163.com",
        port=993,
        username="niejeff@163.com",  # 邮箱
        password="XFpFWCYbrHzy2yyx",  # 授权码
        protocol="IMAP"
    )
    # 连接邮箱
    with EmailReader(config) as reader:
        # 选择INBOX
        reader.select_folder("INBOX")
        criteria = ["ALL"]  # 条件是ALL
        email_ids = reader.search_emails(criteria )

        # 获取最新一封邮件: 打印主题、发件人和正文前 100 个字符。
        for email_id in email_ids:
            if email_id:
                latest_email = reader.get_email(email_id)
                if latest_email:
                    print(f"Subject: {latest_email.subject}")
                    print(f"From: {latest_email.sender}")
                    print(f"Body: {latest_email.body[:100]}...")



