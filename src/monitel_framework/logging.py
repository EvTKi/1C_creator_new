"""
Модуль: Система логирования для monitel_framework.

Поддерживает:
- Конфигурируемые уровни и форматы
- Запись в файл
- Вывод в GUI через callback
- Централизованное управление через LogManager
"""

import logging
import logging.handlers
from typing import Optional, Callable, Dict, Any
from pathlib import Path


class LoggerConfig:
    """Конфигурация формата и уровня логирования."""
    def __init__(
        self,
        level: int = logging.INFO,
        format_string: str = "%(asctime)s [%(levelname)s]: %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S"
    ):
        self.level = level
        self.format_string = format_string
        self.date_format = date_format
        self.formatter = logging.Formatter(fmt=format_string, datefmt=date_format)


class FileLogHandler(logging.FileHandler):
    """Обработчик для записи логов в файл."""
    def __init__(self, filename: str, mode: str = 'a', encoding: str = 'utf-8', delay: bool = False):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, mode, encoding, delay)


class UILogHandler(logging.Handler):
    """Обработчик для передачи логов в GUI."""
    def __init__(
        self,
        callback: Callable[[str], None],
        level: int = logging.INFO,
        format_string: str = "%(asctime)s [%(levelname)s]: %(message)s",
        date_format: str = "%Y-%m-%d %H:%M:%S"
    ):
        super().__init__(level)
        self.callback = callback
        self.formatter = logging.Formatter(fmt=format_string, datefmt=date_format)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


class LoggerManager:
    """Менеджер логгеров — централизованное создание и управление."""
    def __init__(self, default_config: LoggerConfig):
        self.default_config = default_config
        self.loggers: Dict[str, logging.Logger] = {}

    def create_logger(
        self,
        name: str,
        log_file_path: Optional[str] = None,
        ui_callback: Optional[Callable[[str], None]] = None,
        config: Optional[LoggerConfig] = None
    ) -> logging.Logger:
        config = config or self.default_config
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.setLevel(config.level)
        logger.propagate = False

        console_handler = logging.StreamHandler()
        console_handler.setLevel(config.level)
        console_handler.setFormatter(config.formatter)
        logger.addHandler(console_handler)

        if log_file_path:
            file_handler = FileLogHandler(log_file_path, mode="a", encoding="utf-8")
            file_handler.setLevel(config.level)
            file_handler.setFormatter(config.formatter)
            logger.addHandler(file_handler)

        if ui_callback:
            ui_handler = UILogHandler(
                callback=ui_callback,
                level=config.level,
                format_string=config.format_string,
                date_format=config.date_format
            )
            logger.addHandler(ui_handler)

        self.loggers[name] = logger
        return logger

    def cleanup_all_loggers(self):
        """Очистка всех обработчиков."""
        for logger in self.loggers.values():
            logger.handlers.clear()
        self.loggers.clear()


class LogManager:
    """Синглтон для глобального доступа к менеджеру логгеров."""
    _instance = None
    _manager: Optional[LoggerManager] = None

    def __new__(cls) -> 'LogManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _ensure_manager(cls) -> None:
        if cls._manager is None:
            default_config = LoggerConfig(
                level=logging.INFO,
                format_string="%(asctime)s [%(levelname)s]: %(message)s",
                date_format="%Y-%m-%d %H:%M:%S"
            )
            cls._manager = LoggerManager(default_config)

    @classmethod
    def get_logger(
        cls,
        name: str,
        log_file_path: Optional[str] = None,
        ui_callback: Optional[Callable[[str], None]] = None
    ) -> logging.Logger:
        cls._ensure_manager()
        assert cls._manager is not None
        return cls._manager.create_logger(name, log_file_path, ui_callback)

    @classmethod
    def get_manager(cls) -> LoggerManager:
        cls._ensure_manager()
        assert cls._manager is not None
        return cls._manager