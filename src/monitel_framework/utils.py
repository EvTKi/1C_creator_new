"""
Вспомогательные утилиты для фреймворка.
"""

import sys
import os
from pathlib import Path
import re
from typing import Optional

def resource_path(relative_path: str) -> str:
    """
    Получение правильного пути к ресурсу, работает как для скрипта, так и для .exe.

    Args:
        relative_path: относительный путь к ресурсу

    Returns:
        str: абсолютный путь к ресурсу
    """
    try:
        # PyInstaller создает атрибут _MEIPASS во время выполнения
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def validate_uuid(uuid_string: str) -> bool:
    """
    Проверяет валидность UUID.

    Args:
        uuid_string: строка для проверки

    Returns:
        bool: True если UUID валиден
    """
    uuid_regex = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_regex.match(uuid_string))

def ensure_directory(directory_path: str) -> str:
    """
    Создает директорию если она не существует.

    Args:
        directory_path: путь к директории

    Returns:
        str: путь к созданной директории
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)

def get_file_size(file_path: str) -> Optional[int]:
    """
    Получает размер файла в байтах.

    Args:
        file_path: путь к файлу

    Returns:
        int: размер файла в байтах или None если файл не существует
    """
    path = Path(file_path)
    if path.exists() and path.is_file():
        return path.stat().st_size
    return None