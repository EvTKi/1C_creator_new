"""
Monitel Framework - набор утилит для работы с конфигурацией, файлами и логированием.
"""

from .config import ConfigManager
from .files import FileManager, CLIManager
from .logging import LoggerManager, LoggerConfig, LogManager
from .utils import resource_path, validate_uuid

__version__ = "0.1.0"
__all__ = [
    'ConfigManager',
    'FileManager', 'CLIManager',
    'LoggerManager', 'LoggerConfig', 'LogManager',
    'resource_path', 'validate_uuid'
]