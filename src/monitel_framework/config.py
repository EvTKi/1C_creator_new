"""
Управление конфигурацией приложения.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """Менеджер конфигурации без глобального состояния."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Инициализация менеджера конфигурации.

        Args:
            config_path: путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла."""
        if not self.config_path.exists():
            default_config = self._get_default_config()
            self._save_config(default_config)  # Передаем аргумент
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Ошибка загрузки конфигурации: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию."""
        return {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s]: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file": None
            },
            "directories": {
                "input": "input",
                "output": "output", 
                "log": "logs"
            }
        }
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Сохраняет конфигурацию в файл.

        Args:
            config: словарь с конфигурацией для сохранения
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Ошибка сохранения конфигурации: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Получает значение по пути к ключу.

        Args:
            key_path: путь к ключу через точку (например, "logging.level")
            default: значение по умолчанию

        Returns:
            Значение или default
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Устанавливает значение по пути к ключу.

        Args:
            key_path: путь к ключу через точку
            value: значение для установки
        """
        keys = key_path.split('.')
        config = self._config
        
        # Создаем вложенные словари если их нет
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self._save_config(self._config)  # Передаем текущий конфиг
    
    def reload(self) -> None:
        """Перезагружает конфигурацию из файла."""
        self._config = self._load_config()
    
    @property
    def config(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию."""
        return self._config.copy()