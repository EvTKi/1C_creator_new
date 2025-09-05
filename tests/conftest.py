"""
Фикстуры для всех тестов
"""
import pytest
import tempfile
import os
import json
import sys
from PyQt6.QtWidgets import QApplication


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
        


@pytest.fixture(scope="session", autouse=True)
def setup_qt():
    """Настройка QApplication для тестов."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def prevent_qt_dialogs(monkeypatch):
    """Предотвращает появление реальных диалоговых окон во время тестов."""
    from PyQt6.QtWidgets import QFileDialog
    
    def mock_get_existing_directory(*args, **kwargs):
        return ""
    
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', mock_get_existing_directory)