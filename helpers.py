"""
通用辅助函数
"""

from fastapi import HTTPException, UploadFile, status

DEFAULT_MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def read_upload_file(file: UploadFile, max_size: int = DEFAULT_MAX_UPLOAD_SIZE) -> bytes:
    """安全读取上传文件：限制大小并给出明确错误"""
    data = file.file.read()
    if len(data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（最大 {max_size // 1024 // 1024} MB）",
        )
    return data
