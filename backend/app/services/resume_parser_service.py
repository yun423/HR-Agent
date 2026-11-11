"""
简历文件解析服务：用于从各种文件格式中提取文本的简历解析服务
    校验文件格式和大小，支持 txt、pdf、doc、docx 等格式提取文本，并返回文件基本信息，如文件名、大小、hash、MIME 类型。
    是简历评价的前置能力
"""
import logging
import os
import hashlib
import tempfile
from typing import BinaryIO, Tuple, Optional
from uuid import UUID
import mimetypes
from app.utils.text_utils import extract_text_content
from app.utils.file_utils import get_file_mime_type

logger = logging.getLogger(__name__)


class ResumeParserService:
    """用于解析简历文件和提取文本内容的服务"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.doc', '.docx'}
    SUPPORTED_MIME_TYPES = {
        'application/pdf',
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }

    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """验证文件是否符合要求"""
        # 检查文件大小
        if file_size > self.max_file_size:
            return False, f"文件大小超过限制 ({self.max_file_size / 1024 / 1024}MB)"
        
        # 检查文件扩展名
        _, ext = os.path.splitext(filename.lower())
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False, f"不支持的文件格式。支持的格式: {', '.join(self.SUPPORTED_EXTENSIONS)}"
        
        return True, "文件验证通过"

    async def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """从文件中提取文本内容（使用公共提取方法）"""
        try:
            # 统一通过公共方法提取，保持与知识库上传一致
            mime_type = get_file_mime_type(filename)

            # 写入临时文件以复用基于路径的解析逻辑
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name

            try:
                extracted = await extract_text_content(temp_path, mime_type)
                return extracted
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"提取文本内容失败: {e}")
            raise Exception(f"文件解析失败: {str(e)}")

    async def _extract_from_txt(self, file_content: bytes) -> str:
        """从TXT文件提取文本"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'utf-16', 'gbk', 'gb2312', 'big5', 'latin-1']
            
            for encoding in encodings:
                try:
                    return file_content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用utf-8并忽略错误
            return file_content.decode('utf-8', errors='ignore')
            
        except Exception as e:
            logger.error(f"TXT文件解析失败: {e}")
            raise

    async def _extract_from_pdf(self, file_content: bytes) -> str:
        """从PDF文件提取文本"""
        try:
            # 使用PyPDF2或pdfplumber库
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text_content = []
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            
            return '\n'.join(text_content)
            
        except ImportError:
            # 如果没有安装PyPDF2，尝试使用pdfplumber
            try:
                import pdfplumber
                import io
                
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    text_content = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                    
                    return '\n'.join(text_content)
                    
            except ImportError:
                logger.error("PDF解析库未安装，请安装 PyPDF2 或 pdfplumber")
                raise Exception("PDF解析功能不可用，请联系管理员")
                
        except Exception as e:
            logger.error(f"PDF文件解析失败: {e}")
            raise Exception(f"PDF文件解析失败: {str(e)}")

    async def _extract_from_doc(self, file_content: bytes) -> str:
        """从DOC文件提取文本"""
        try:
            # 写入临时文件
            with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                # 优先使用 textract（跨平台，支持DOC）
                try:
                    import textract
                    text_bytes = textract.process(temp_file_path)
                    # 尝试多编码解码，避免中文乱码
                    decoded = None
                    for enc in ['utf-8', 'utf-16', 'gbk', 'gb2312', 'big5', 'latin-1']:
                        try:
                            decoded = text_bytes.decode(enc)
                            break
                        except Exception:
                            continue
                    if decoded is None:
                        decoded = text_bytes.decode('utf-8', errors='ignore')
                    text = decoded.strip()
                    if text:
                        return text
                except ImportError:
                    logger.warning("未安装textract，尝试其他方式解析DOC")
                except Exception as e:
                    logger.warning(f"textract解析DOC失败: {e}")

                # Windows 环境下尝试使用 Word COM 自动化
                try:
                    import win32com.client  # type: ignore
                    word = win32com.client.Dispatch("Word.Application")
                    word.Visible = False
                    doc = word.Documents.Open(temp_file_path)
                    # 保存为临时txt
                    temp_txt_path = temp_file_path + ".txt"
                    wdFormatText = 2
                    doc.SaveAs(temp_txt_path, FileFormat=wdFormatText)
                    doc.Close(False)
                    word.Quit()
                    # 读取时尝试多编码，避免中文乱码
                    text = None
                    for enc in ['utf-8', 'utf-16', 'gbk', 'gb2312', 'big5', 'latin-1']:
                        try:
                            with open(temp_txt_path, "r", encoding=enc) as f:
                                content = f.read().strip()
                                if content:
                                    text = content
                                    break
                        except UnicodeDecodeError:
                            continue
                        except Exception:
                            continue
                    if text is None:
                        with open(temp_txt_path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read().strip()
                    os.unlink(temp_txt_path)
                    if text:
                        return text
                except ImportError:
                    logger.warning("未安装pywin32，跳过Word COM方式")
                except Exception as e:
                    logger.warning(f"Word COM方式解析DOC失败: {e}")

                # 如果系统安装了 antiword，尝试调用（强制UTF-8输出）
                try:
                    import subprocess
                    result = subprocess.run(
                        ["antiword", "-m", "UTF-8", temp_file_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False
                    )
                    # 先按多编码尝试解码stdout
                    text = None
                    for enc in ['utf-8', 'utf-16', 'gbk', 'gb2312', 'big5', 'latin-1']:
                        try:
                            text = result.stdout.decode(enc).strip()
                            if text:
                                break
                        except Exception:
                            continue
                    if text is None:
                        text = result.stdout.decode('utf-8', errors='ignore').strip()
                    if result.returncode == 0 and text:
                        return text
                    else:
                        logger.warning(f"antiword解析失败: {result.stderr.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.warning(f"调用antiword解析DOC失败: {e}")

                # 所有方式失败
                raise Exception("DOC文件解析失败：缺少可用的解析器，请安装textract或pywin32/antiword")

            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"DOC文件解析失败: {e}")
            raise Exception(f"DOC文件解析失败: {str(e)}")

    async def _extract_from_docx(self, file_content: bytes) -> str:
        """从DOCX文件提取文本"""
        try:
            from docx import Document
            import io
            
            # 从字节流创建Document对象
            doc = Document(io.BytesIO(file_content))
            
            # 提取所有段落的文本
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # 提取表格中的文本
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_content.append(cell.text)
            
            return '\n'.join(text_content)
            
        except ImportError:
            logger.error("DOCX解析库未安装，请安装 python-docx")
            raise Exception("DOCX文件解析功能不可用，请联系管理员")
            
        except Exception as e:
            logger.error(f"DOCX文件解析失败: {e}")
            raise Exception(f"DOCX文件解析失败: {str(e)}")

    def get_file_info(self, filename: str, file_content: bytes) -> dict:
        """获取文件基本信息"""
        file_size = len(file_content)
        file_hash = hashlib.sha256(file_content).hexdigest()
        _, ext = os.path.splitext(filename.lower())
        
        return {
            'filename': filename,
            'file_type': ext.lstrip('.'),
            'file_size': file_size,
            'file_hash': file_hash,
            'mime_type': mimetypes.guess_type(filename)[0]
        }