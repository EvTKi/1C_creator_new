"""
Фикстуры для всех тестов
"""
import pytest
import tempfile
import os
import json


@pytest.fixture
def temp_config():
    """Временный config.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        config_data = {
            "io": {"log_dir": "log"},
            "logging": {"level": "DEBUG"}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)
        yield config_path, tmpdir