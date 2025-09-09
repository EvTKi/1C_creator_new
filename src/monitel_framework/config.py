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
            # Сохраняем дефолтный конфиг
            self._save_config(default_config)
            return default_config

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            # Сливаем с дефолтами
            return self._merge_with_defaults(user_config)
        except Exception as e:
            raise Exception(f"Ошибка загрузки конфигурации: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию."""
        return {
            "app": {
                "name": "CSV-to-RDF Converter",
                "version": "1.0.0"
            },
            "io": {
                "input_dir": "input",
                "output_dir": "output",
                "log_dir": "logs",
                "exclude_files": ["Sample.csv"],
                "default_encoding": "utf-8-sig",
                "allowed_encodings": ["utf-8-sig", "utf-8", "cp1251", "windows-1251"]
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s]: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file": None
            },
            "csv": {
                "headers": {
                    "path": "НаименованиеКонтейнераОборудования",
                    "uid": "uid",
                    "cck_code": "ОбъектРемонтаКодККС"
                },
                "delimiter": "auto"
            },
            "xml": {
                "namespaces": {
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "md": "http://iec.ch/TC57/61970-552/ModelDescription/1#",
                    "cim": "http://iec.ch/TC57/2014/CIM-schema-cim16#",
                    "cim17": "http://iec.ch/TC57/CIM100#",
                    "me": "http://monitel.com/2014/schema-cim16#",
                    "rf": "http://gost.ru/2019/schema-cim01#",
                    "rh": "http://rushydro.ru/2015/schema-cim16#",
                    "so": "http://so-ups.ru/2015/schema-cim16#"
                },
                "model": {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "created": "2025-01-01T00:00:00.0000000Z",
                    "version": "ver:1.0.0",
                    "name": "CIM16"
                },
                "modified_output": {
                    "enabled": True,
                    "format": "xlsx",  # или "csv"
                    "suffix": "_modified",
                    "include_status_column": True  # только для CSV
                }
            }
        }

    def _merge_with_defaults(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Рекурсивно объединяет пользовательскую конфигурацию с дефолтной."""
        from copy import deepcopy
        merged = deepcopy(self._get_default_config())

        def merge(a: dict, b: dict):
            for key, value in b.items():
                if key in a and isinstance(a[key], dict) and isinstance(value, dict):
                    merge(a[key], value)
                else:
                    a[key] = value
            return a

        return merge(merged, user_config)

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Сохраняет конфигурацию в файл."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Ошибка сохранения конфигурации: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Получает значение по пути к ключу."""
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any) -> None:
        """Устанавливает значение по пути к ключу."""
        keys = key_path.split('.')
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        self._save_config(self._config)

    def reload(self) -> None:
        """Перезагружает конфигурацию из файла."""
        self._config = self._load_config()

    @property
    def config(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию."""
        return self._config.copy()
