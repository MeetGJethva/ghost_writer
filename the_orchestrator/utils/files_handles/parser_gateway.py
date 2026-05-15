from .parser_factory import ParserFactory


import filetype
from pathlib import Path
from typing import Optional, Union

class MimeDeterminer:
    """Handles identification of MIME types via magic bytes and extensions."""
    
    # Mapping for common extensions where magic bytes might fail or be generic
    EXTENSION_MAP = {
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".odt": "application/vnd.oasis.opendocument.text",
        ".ods": "application/vnd.oasis.opendocument.spreadsheet",
        ".zip": "application/zip",
        ".mp4": "video/mp4",
        ".avi": "video/avi",
        ".mpeg": "video/mpeg",
        ".csv": "text/csv",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "text/plain",
    }

    @classmethod
    def determine(cls, file_data: bytes, file_path: Optional[Union[Path, str]] = None) -> Optional[str]:
        """
        Detects MIME type. 
        Priority: 1. Magic Bytes -> 2. File Extension -> 3. None
        """
        # 1. Try guessing by content (Magic Bytes)
        kind = filetype.guess(file_data)
        mime = kind.mime if kind else None

        # 2. Fallback to extension if magic bytes fail or are too generic (like zip/octet-stream)
        if mime is None or mime == "application/zip":
            if file_path:
                ext = Path(file_path).suffix.lower()
                mime = cls.EXTENSION_MAP.get(ext, mime)

        # 3. Last resort check: if it's valid UTF-8 text but wasn't caught
        if mime is None:
            try:
                file_data.decode('utf-8')
                mime = "text/plain"
            except UnicodeDecodeError:
                pass

        return mime


async def process_file(file_data=None, llm=None, vision=None, file_path=None, logger=None, query: str = None):
    mime = MimeDeterminer.determine(file_data, file_path)
    
    try:
        parser = ParserFactory.get_parser(mime)
        ocr_result = await parser.parse(file_path=file_path, llm=llm, file_data=file_data, user_query=query, vision=vision)
    except ValueError as e:
        raise TypeError(f"Unsupported file: {e}")

    return ocr_result
