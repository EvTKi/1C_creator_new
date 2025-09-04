"""
Тесты для ConfigManager
"""
import tempfile
import os
import json
from src.monitel_framework.config import ConfigManager


def test_load_config():
    """Проверка загрузки конфига из файла"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        config_data = {
            "io": {"log_dir": "log"},
            "logging": {"level": "DEBUG"}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        config = ConfigManager(config_path)
        assert config.get("io.log_dir") == "log"
        assert config.get("logging.level") == "DEBUG"


def test_get_with_default():
    """Проверка значения по умолчанию"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w") as f:
            json.dump({}, f)
        config = ConfigManager(config_path)
        assert config.get("unknown.key", "default") == "default"