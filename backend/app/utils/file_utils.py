""""""
import hashlib
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
import logging

from fastapi import UploadFile

logger = logging.getLogger(__name__)


'''
    file_utils.py 是文件处理工具模块，主要用于上传文件保存、文件哈希、MIME类型判断、文件名清理、安全删除/复制，以及基于目录的文件管理。
    
    这个文件是后端文件系统操作的工具箱，主要服务于上传、保存、读取、删除和管理本地文件。
        我们把常见文件操作集中封装，避免业务代码里重复处理目录创建、文件名清理、哈希计算和异常捕获。
'''


def get_file_hash(file_content: bytes) -> str:
    """
        文件哈希：
            接收文件二进制内容， 返回SHA-256哈希
            这个哈希可以用于判断文件是否重复、记录文件指纹、校验文件内容是否变化。
    """
    return hashlib.sha256(file_content).hexdigest()


def get_file_mime_type(filename: str) -> str:
    """
        MIME类型判断
            根据文件名扩展名猜MIME类型，如果猜不出来，就返回通用二进制类型
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def ensure_directory(directory: Path) -> None:
    """
        确保目录存在
            如果不存在则创建目录
                parents=True 表示父目录不存在也一起创建。
                exist_ok=True 表示目录已存在时不报错。
    """
    directory.mkdir(parents=True, exist_ok=True)


async def save_uploaded_file(
    upload_file: UploadFile,
    destination: Path,
    max_size: int = 10 * 1024 * 1024  # 10MB default
) -> tuple[str, int]:
    """
        保存上传文件: 用于保存 FastAPI 上传的文件
            这个函数适合上传简历、文档、附件时使用。
    """
    # 确保目标目录存在
    ensure_directory(destination.parent)

    # 读取上传文件全部内容
    content = await upload_file.read()
    file_size = len(content)

    # 计算文件大小
    if file_size > max_size:
        raise ValueError(f"File size {file_size} exceeds maximum {max_size}")

    # 如果超过最大限制，抛出ValueError
    file_hash = get_file_hash(content)

    # 以二进制方式写入磁盘
    with open(destination, "wb") as f:
        f.write(content)

    logger.info(f"File saved: {destination} (size: {file_size}, hash: {file_hash})")

    return file_hash, file_size


def delete_file_safe(file_path: Path) -> bool:
    """
        安全删除文件，并返回是否成功
        逻辑是：
            文件存在：删除并返回True。
            文件不存在：记录warning，返回False。
            删除出错：记录error，返回False。
        不会把异常继续抛给调用方，适合“尽力删除”的场景。
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {file_path}")
            return True
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False


def copy_file_safe(source: Path, destination: Path) -> bool:
    """
        安全复制文件
    """
    try:
        ensure_directory(destination.parent)  # 先确保目标目录存在
        shutil.copy2(source, destination)  # copy2 会尽量保留源文件的元数据，比如修改时间
        logger.info(f"File copied: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Error copying file {source} to {destination}: {e}")
        return False


def get_file_size(file_path: Path) -> int:
    """
        获取文件大小
    """
    try:
        return file_path.stat().st_size
    except Exception:
        return 0


def is_file_type_allowed(filename: str, allowed_types: list[str]) -> bool:
    """
        检查文件类型是否允许
    """
    if not filename:
        return False

    extension = Path(filename).suffix.lower()
    return extension in [ext.lower() for ext in allowed_types]


def sanitize_filename(filename: str) -> str:
    """
        清理文件名: 用于把用户上传的文件名变得更安全
            这个函数可以降低路径穿越、非法文件名、系统不兼容字符等问题。
    """
    # 把危险字符替换成下划线
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # 去掉开头和结尾的空格、点号
    filename = filename.strip(' .')

    # 如果文件名为空，改成：unnamed_file
    if not filename:
        filename = "unnamed_file"

    # 如果长度超过255，就截断文件名，但保留扩展名
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    return filename


def get_unique_filename(directory: Path, filename: str) -> str:
    """
        生成唯一文件名：用于避免覆盖已有文件
            例如：目录里已经有“简历.pdf”，则会尝试使用：resume_1.pdf，resume_2.pdf，resume_3.pdf等。
    """
    base_path = directory / filename

    if not base_path.exists():
        return filename

    name, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_path = directory / new_filename

        if not new_path.exists():
            return new_filename

        counter += 1




class FileManager:
    """
        FileManager：文件管理类
    """

    def __init__(self, base_directory: Path):
        """
            保存基础目录，并确保目录存在。
        """
        self.base_directory = Path(base_directory)
        ensure_directory(self.base_directory)

    def get_file_path(self, relative_path: str) -> Path:
        """
            把相对路径转换成完整路径
        """
        return self.base_directory / relative_path

    def save_file(self, content: bytes, relative_path: str) -> Path:
        """
            保存二进制内容到相对路径。
        """
        file_path = self.get_file_path(relative_path)
        ensure_directory(file_path.parent)

        with open(file_path, "wb") as f:
            f.write(content)

        return file_path

    def read_file(self, relative_path: str) -> bytes:
        """
            读取相对路径文件的二进制内容。
        """
        file_path = self.get_file_path(relative_path)

        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, relative_path: str) -> bool:
        """
            删除相对路径文件，内部调用delete_file_safe()。
        """
        file_path = self.get_file_path(relative_path)
        return delete_file_safe(file_path)

    def file_exists(self, relative_path: str) -> bool:
        """
            判断文件是否存在
        """
        file_path = self.get_file_path(relative_path)
        return file_path.exists()

    def list_files(self, relative_directory: str = "") -> list[str]:
        """
            列出某个相对目录下的直接文件，并返回相对于base_directory的路径列表。
        """
        directory = self.get_file_path(relative_directory)

        if not directory.exists() or not directory.is_dir():
            return []

        files = []
        for item in directory.iterdir():
            if item.is_file():
                files.append(str(item.relative_to(self.base_directory)))

        return sorted(files)




