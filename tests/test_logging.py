"""
Тесты для системы логирования
"""
import unittest
import tempfile
import os
import logging
from src.monitel_framework.logging import (
    LoggerConfig,
    UILogHandler,
    LoggerManager,
    FileLogHandler
)


class TestLoggerConfig(unittest.TestCase):
    def test_config_creation(self):
        """Проверка создания конфигурации логгера"""
        config = LoggerConfig(
            level=logging.DEBUG,
            format_string="%(levelname)s: %(message)s",
            date_format="%H:%M:%S"
        )
        self.assertEqual(config.level, logging.DEBUG)
        self.assertIsNotNone(config.formatter)


class TestUILogHandler(unittest.TestCase):
    def setUp(self):
        self.messages = []

    def ui_callback(self, msg):
        self.messages.append(msg)

    def test_ui_handler_emits_message(self):
        """Проверка, что UILogHandler вызывает callback"""
        handler = UILogHandler(callback=self.ui_callback)
        logger = logging.getLogger("test_ui")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        logger.info("Test message")
        handler.close()  # Закрываем обработчик

        self.assertGreater(len(self.messages), 0)
        self.assertIn("INFO", self.messages[0])
        self.assertIn("Test message", self.messages[0])


class TestFileLogHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        # Закрываем все логгеры перед удалением
        logging.shutdown()
        self.temp_dir.cleanup()

    def test_file_handler_creates_dir_and_writes(self):
        """Проверка, что FileLogHandler создаёт папку и пишет в файл"""
        log_path = os.path.join(self.temp_dir.name, "logs", "test.log")
        handler = FileLogHandler(log_path)
        logger = logging.getLogger("test_file")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        logger.info("File log test")
        handler.close()  # Важно: закрыть файл

        # Проверка: файл создан
        self.assertTrue(os.path.exists(log_path))

        # Проверка: сообщение записано
        with open(log_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("File log test", content)


class TestLoggerManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = LoggerConfig(level=logging.DEBUG)

    def tearDown(self):
        logging.shutdown()  # Закрываем все обработчики
        self.temp_dir.cleanup()

    def test_create_logger_with_file_and_ui(self):
        """Проверка создания логгера с файлом и UI"""
        manager = LoggerManager(self.config)
        log_path = os.path.join(self.temp_dir.name, "test.log")

        logger = manager.create_logger(
            name="test",
            log_file_path=log_path,
            ui_callback=lambda msg: None
        )

        logger.info("Test log entry")
        
        # Закрываем обработчики
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # Проверка записи в файл
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r", encoding="utf-8") as f:
            self.assertIn("Test log entry", f.read())

    def test_cleanup_all_loggers(self):
        """Проверка очистки логгеров"""
        manager = LoggerManager(self.config)
        manager.create_logger("temp")
        self.assertEqual(len(manager.loggers), 1)

        manager.cleanup_all_loggers()
        self.assertEqual(len(manager.loggers), 0)


if __name__ == "__main__":
    unittest.main()