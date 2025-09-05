"""
Конфигурация pytest для тестирования PyQt6 приложений.
"""

import pytest
import sys
from pathlib import Path

# Добавляем src в путь для импортов
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session", autouse=True)
def setup_qt():
    """Настройка QApplication для тестов."""
    from PyQt6.QtWidgets import QApplication
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


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Очистка тестовых файлов после выполнения тестов."""
    yield
    
    # Удаляем временные файлы
    test_files = [
        Path("test_config.json"),
        Path("test_logs")
    ]
    
    for file_path in test_files:
        if file_path.exists():
            try:
                if file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
            except (PermissionError, OSError):
                # Игнорируем ошибки удаления на Windows
                pass