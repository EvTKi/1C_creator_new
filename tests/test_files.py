"""
Тесты для FileManager и CLIManager
"""
import unittest
import tempfile
import os
from datetime import datetime
from src.monitel_framework.files import FileManager, CLIManager


class TestFileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_manager = FileManager(
            base_directory=self.temp_dir.name,
            log_directory="log"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_log_directory(self):
        """Проверка создания папки log"""
        log_path = self.file_manager.create_log_directory()
        self.assertTrue(os.path.exists(log_path))
        self.assertTrue(os.path.isdir(log_path))

    def test_get_log_path(self):
        """Проверка пути к лог-файлу (с добавлением даты)"""
        # Предполагаем, что get_log_path добавляет дату
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_path = self.file_manager.get_log_path("test.log")
        expected = os.path.join(self.temp_dir.name, "log", f"test_{date_str}.log")
        self.assertEqual(str(log_path), expected)

    def test_validate_directory(self):
        """Проверка валидации директории"""
        self.assertTrue(self.file_manager.validate_directory())

        # Проверка несуществующей директории
        invalid_fm = FileManager("nonexistent_dir", "log")
        self.assertFalse(invalid_fm.validate_directory())

    def test_get_csv_files(self):
        """Проверка поиска CSV-файлов"""
        # Создаём тестовые файлы
        open(os.path.join(self.temp_dir.name, "data.csv"), "w").close()
        open(os.path.join(self.temp_dir.name, "sample.csv"), "w").close()
        open(os.path.join(self.temp_dir.name, "readme.txt"), "w").close()

        files = self.file_manager.get_csv_files(exclude_files=["sample.csv"])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], "data.csv")


class TestCLIManager(unittest.TestCase):
    def test_cli_manager_creation(self):
        """Проверка создания CLIManager"""
        cli = CLIManager()
        self.assertIsNotNone(cli)


if __name__ == "__main__":
    unittest.main()