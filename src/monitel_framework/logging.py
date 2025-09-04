"""
Управление системой логирования.
"""

import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any

class LogHandler(logging.Handler):
    """Базовый класс для кастомных лог handlers."""
    
    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)

class UILogHandler(LogHandler):
    """Handler для вывода логов в интерфейс."""
    
    def __init__(self, callback: Callable[[str], None], 
                 level: int = logging.INFO,
                 format_string: str = "%(asctime)s [%(levelname)s]: %(message)s",
                 date_format: str = "%Y-%m-%d %H:%M:%S"):
        """
        Инициализация UI handler.

        Args:
            callback: функция обратного вызова для UI
            level: уровень логирования
            format_string: формат сообщений
            date_format: формат даты
        """
        super().__init__(level)
        self.callback = callback
        self.formatter = logging.Formatter(format_string, date_format)
    
    def emit(self, record: logging.LogRecord) -> None:
        """Отправляет запись лога в UI."""
        try:
            msg = self.format(record)
            self.callback(msg + "\n")
        except Exception:
            self.handleError(record)

class FileLogHandler(logging.FileHandler):
    """Расширенный FileHandler с дополнительными возможностями."""
    
    def __init__(self, filename: str, mode: str = 'a', encoding: str = 'utf-8'):
        """
        Инициализация файлового handler.

        Args:
            filename: путь к файлу лога
            mode: режим открытия файла
            encoding: кодировка файла
        """
        super().__init__(filename, mode, encoding)


class LoggerConfig:
    """Конфигурация логгера."""
    
    def __init__(self, level: int = logging.INFO,
                 format_string: str = "%(asctime)s [%(levelname)s]: %(message)s",
                 date_format: str = "%Y-%m-%d %H:%M:%S"):
        """
        Инициализация конфигурации.

        Args:
            level: уровень логирования
            format_string: формат сообщений
            date_format: формат даты
        """
        self.level = level
        self.format_string = format_string
        self.date_format = date_format
        self.formatter = logging.Formatter(format_string, date_format)


class LoggerManager:
    """Класс для управления логгерами."""
    
    def __init__(self, default_config: Optional[LoggerConfig] = None):
        """
        Инициализация менеджера логов.

        Args:
            default_config: конфигурация по умолчанию
        """
        self.default_config = default_config or LoggerConfig()
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Настраивает корневой логгер."""
        logging.basicConfig(
            level=self.default_config.level,
            format=self.default_config.format_string,
            datefmt=self.default_config.date_format
        )
    
    def create_logger(self, name: str, log_file_path: Optional[str] = None,
                     ui_callback: Optional[Callable[[str], None]] = None,
                     config: Optional[LoggerConfig] = None) -> logging.Logger:
        """
        Создает и настраивает логгер.

        Args:
            name: имя логгера
            log_file_path: путь к файлу лога (опционально)
            ui_callback: функция обратного вызова для UI (опционально)
            config: конфигурация логгера (опционально)

        Returns:
            logging.Logger: настроенный логгер
        """
        # Если логгер уже существует, возвращаем его
        if name in self.loggers:
            return self.loggers[name]
        
        # Создаем новый логгер
        logger = logging.getLogger(name)
        config = config or self.default_config
        
        # Устанавливаем уровень
        logger.setLevel(config.level)
        
        # Очищаем существующие handlers
        logger.handlers.clear()
        
        # Добавляем консольный handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(config.formatter)
        logger.addHandler(console_handler)
        
        # Добавляем файловый handler если указан путь
        if log_file_path:
            file_handler = FileLogHandler(log_file_path, mode="a", encoding="utf-8")
            file_handler.setFormatter(config.formatter)
            logger.addHandler(file_handler)
        
        # Добавляем UI handler если передан callback
        if ui_callback:
            ui_handler = UILogHandler(
                ui_callback, 
                level=config.level,
                format_string=config.format_string,
                date_format=config.date_format
            )
            ui_handler.setFormatter(config.formatter)
            logger.addHandler(ui_handler)
        
        self.loggers[name] = logger
        return logger
    
    def get_logger(self, name: str) -> Optional[logging.Logger]:
        """
        Получает существующий логгер.

        Args:
            name: имя логгера

        Returns:
            logging.Logger или None если логгер не найден
        """
        return self.loggers.get(name)
    
    def remove_logger(self, name: str) -> bool:
        """
        Удаляет логгер.

        Args:
            name: имя логгера

        Returns:
            bool: True если логгер был удален
        """
        if name in self.loggers:
            logger = self.loggers.pop(name)
            # Очищаем handlers
            logger.handlers.clear()
            return True
        return False
    
    def cleanup_all_loggers(self) -> None:
        """Очищает все логгеры."""
        for logger in self.loggers.values():
            logger.handlers.clear()
        self.loggers.clear()
    
    def update_logger_config(self, name: str, config: LoggerConfig) -> bool:
        """
        Обновляет конфигурацию существующего логгера.

        Args:
            name: имя логгера
            config: новая конфигурация

        Returns:
            bool: True если конфигурация обновлена
        """
        logger = self.get_logger(name)
        if logger:
            logger.setLevel(config.level)
            for handler in logger.handlers:
                handler.setFormatter(config.formatter)
            return True
        return False


class LogManager:
    """Упрощенный интерфейс для управления логами."""
    
    _instance = None
    _manager = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._manager = LoggerManager()
        return cls._instance
    
    @classmethod
    def get_logger(cls, name: str, log_file_path: Optional[str] = None,
                  ui_callback: Optional[Callable[[str], None]] = None) -> logging.Logger:
        """
        Получает или создает логгер.
        """
        if cls._manager is None:
            cls._manager = LoggerManager()
        return cls._manager.create_logger(name, log_file_path, ui_callback)
    
    @classmethod
    def setup_file_logger(cls, log_path: str, name: Optional[str] = None) -> logging.Logger:
        """Настраивает файловый логгер."""
        name = name or f"file_{Path(log_path).stem}"
        if cls._manager is None:
            cls._manager = LoggerManager()
        return cls._manager.create_logger(name, log_file_path=log_path)
    
    @classmethod
    def setup_ui_logger(cls, name: str, ui_callback: Callable[[str], None]) -> logging.Logger:
        """Настраивает UI логгер."""
        if cls._manager is None:
            cls._manager = LoggerManager()
        return cls._manager.create_logger(name, ui_callback=ui_callback)
    
    @classmethod
    def get_manager(cls) -> LoggerManager:
        """Возвращает экземпляр менеджера."""
        if cls._manager is None:
            cls._manager = LoggerManager()
        return cls._manager


# Фабричные функции для удобства
def create_logger_manager(config: Optional[LoggerConfig] = None) -> LoggerManager:
    """Создает менеджер логов."""
    return LoggerManager(config)

def create_logger_config(level: int = logging.INFO,
                        format_string: str = "%(asctime)s [%(levelname)s]: %(message)s",
                        date_format: str = "%Y-%m-%d %H:%M:%S") -> LoggerConfig:
    """Создает конфигурацию логгера."""
    return LoggerConfig(level, format_string, date_format)

def get_simple_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Получает простой логгер для быстрого использования.

    Args:
        name: имя логгера
        log_file: путь к файлу (опционально)

    Returns:
        logging.Logger: логгер
    """
    config = LoggerConfig()
    manager = LoggerManager(config)
    return manager.create_logger(name, log_file)