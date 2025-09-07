"""
GUI для конвертера CSV → RDF/XML (CIM16)
Использует BaseMainWindow из monitel_framework.
"""

import sys
from pathlib import Path

# 🔥 Принудительная очистка кэша
to_remove = [k for k in sys.modules.keys() if k.startswith('monitel_framework')]
for k in to_remove:
    print(f"🧹 Удалён из кэша: {k}")
    del sys.modules[k]

# Добавляем src в путь
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import logging

# PyQt6
from PyQt6.QtWidgets import QApplication

# Фреймворк
try:
    from monitel_framework import BaseMainWindow, ConfigManager
    from monitel_framework.files import FileManager
except ImportError as e:
    raise ImportError(f"Не удалось импортировать из monitel_framework: {e}") from e

# Логика приложения
try:
    from main import process_file as main_process_file
except ImportError:
    from .main import process_file as main_process_file


class MainWindow(BaseMainWindow):
    """Конкретная реализация GUI для конвертера CSV → RDF/XML."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Конвертер CSV → RDF/XML")
        self.resize(800, 600)

    def start_conversion(self) -> None:
        folder_uid = self.uid_input.text().strip()
        csv_dir = self.dir_input.text().strip()

        if not folder_uid:
            assert self.logger is not None
            self.logger.error("❌ Не указан UID папки.")
            return

        if not csv_dir:
            assert self.logger is not None
            self.logger.error("❌ Не указана папка с CSV.")
            return

        self.status_label.setText("🔄 Обработка...")
        self.run_btn.setEnabled(False)
        sys.stdout.flush()

        try:
            file_manager = FileManager(base_directory=csv_dir)
            if not file_manager.validate_directory():
                assert self.logger is not None
                self.logger.error(f"❌ Папка не найдена: {csv_dir}")
                return

            exclude_files = self.config.get("io.exclude_files", ["Sample.csv"])
            csv_files = file_manager.get_csv_files(exclude_files=exclude_files)

            if not csv_files:
                assert self.logger is not None
                self.logger.error("❌ Нет подходящих CSV-файлов.")
                return

            total = len(csv_files)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)

            assert self.log_dir_path is not None, "log_dir_path не установлен"
            log_dir_path = self.log_dir_path

            for i, filename in enumerate(csv_files, 1):
                csv_path = file_manager.base_directory / filename
                assert self.logger is not None
                self.logger.info(f"--- [{i}/{total}] Обработка: {filename} ---")
                self.process_file(csv_path, folder_uid, log_dir_path)
                self.progress_bar.setValue(i)

            assert self.logger is not None
            self.logger.info("✅ Готово. Все файлы обработаны.")
            self.status_label.setText("🟢 Готово")
            self.progress_bar.setValue(total)

        except Exception as e:
            assert self.logger is not None
            self.logger.error(f"❌ Ошибка: {e}", exc_info=True)
            self.status_label.setText("🔴 Ошибка")
        finally:
            self.run_btn.setEnabled(True)

    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        try:
            from monitel_framework.logging import LoggerManager, LoggerConfig
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            csv_log_path = log_dir_path / f"{csv_path.stem}_{date_str}.log"

            log_level = getattr(logging, self.config.get("logging.level", "INFO"))
            log_config = LoggerConfig(level=log_level)
            file_logger = LoggerManager(log_config).create_logger(
                name=f"processor.{csv_path.stem}",
                log_file_path=str(csv_log_path)
            )
            file_logger.setLevel(log_level)

            main_process_file(csv_path, parent_uid, self.config, logger=file_logger)

        except Exception as e:
            assert self.logger is not None
            self.logger.error(f"Ошибка: {e}", exc_info=True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()