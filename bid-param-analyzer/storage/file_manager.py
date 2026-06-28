"""
文件临时存储管理

管理招标文件的上传、存储和自动清理。
"""
import os
import time
from datetime import datetime, timedelta

from config.settings import TEMP_FILE_DIR, TEMP_FILE_TTL_HOURS


def save_uploaded_file(file_path: str, task_id: str) -> str:
    """
    将上传文件保存到临时目录，按任务 ID 组织。
    """
    os.makedirs(TEMP_FILE_DIR, exist_ok=True)

    task_dir = os.path.join(TEMP_FILE_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    dest = os.path.join(task_dir, filename)

    if os.path.abspath(file_path) != os.path.abspath(dest):
        with open(file_path, "rb") as src:
            with open(dest, "wb") as dst:
                dst.write(src.read())

    return dest


def cleanup_expired_files() -> int:
    """
    清理超过 TTL 的临时文件。
    """
    if not os.path.isdir(TEMP_FILE_DIR):
        return 0

    cutoff = time.time() - TEMP_FILE_TTL_HOURS * 3600
    cleaned = 0

    for task_dir in os.listdir(TEMP_FILE_DIR):
        task_path = os.path.join(TEMP_FILE_DIR, task_dir)
        if not os.path.isdir(task_path):
            continue

        try:
            mtime = os.path.getmtime(task_path)
            if mtime < cutoff:
                for root, dirs, files in os.walk(task_path, topdown=False):
                    for f in files:
                        os.unlink(os.path.join(root, f))
                    for d in dirs:
                        os.rmdir(os.path.join(root, d))
                os.rmdir(task_path)
                cleaned += 1
        except OSError:
            pass

    return cleaned


def clear_task_files(task_id: str) -> bool:
    """
    用户主动清除指定任务的临时文件。
    """
    task_dir = os.path.join(TEMP_FILE_DIR, task_id)
    if not os.path.isdir(task_dir):
        return False

    try:
        for root, dirs, files in os.walk(task_dir, topdown=False):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        os.rmdir(task_dir)
        return True
    except OSError:
        return False
