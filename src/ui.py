"""
GUI для конвертера CSV → RDF/XML (CIM16)
Использует BaseMainWindow из monitel_framework.
"""

import sys
import logging
from pathlib import Path

# Фреймворк
from monitel_framework import BaseMainWindow, ConfigManager
# Логика приложения
try:
    from main import process_file as main_process_file
except ImportError:
    from .main import process_file as main_process_file
from monitel_framework.files import FileManager


class MainWindow(BaseMainWindow):
    """
    Конкретная реализация GUI для конвертера CSV → RDF/XML.

    Наследует базовую структуру и реализует:
    - Логику запуска обработки
    - Обработку отдельных файлов
    """

    def start_conversion(self) -> None:
        """
        Запускает пакетную обработку выбранных CSV-файлов.

        Для каждого файла:
        - Создаёт отдельный логгер
        - Вызывает main_process_file
        - Обновляет прогресс-бар
        """
        folder_uid = self.uid_input.text().strip()
        csv_dir = self.dir_input.text().strip()

        if not folder_uid:
            self.logger.error("❌ Не указан UID папки.")
            return

        if not csv_dir:
            self.logger.error("❌ Не указана папка с CSV.")
            return

        self.status_label.setText("🔄 Обработка...")
        self.run_btn.setEnabled(False)
        sys.stdout.flush()

        try:
            file_manager = FileManager(base_directory=csv_dir)
            if not file_manager.validate_directory():
                self.logger.error(f"❌ Папка не найдена: {csv_dir}")
                return

            exclude_files = self.config.get("io.exclude_files", ["Sample.csv"])
            csv_files = file_manager.get_csv_files(exclude_files=exclude_files)

            if not csv_files:
                self.logger.error("❌ Нет подходящих CSV-файлов.")
                return

            total = len(csv_files)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)

            for i, filename in enumerate(csv_files, 1):
                csv_path = file_manager.base_directory / filename
                self.logger.info(f"--- [{i}/{total}] Обработка: {filename} ---")
                self.process_file(csv_path, folder_uid, self.log_dir_path)
                self.progress_bar.setValue(i)

            self.logger.info("✅ Готово. Все файлы обработаны.")
            self.status_label.setText("🟢 Готово")
            self.progress_bar.setValue(total)

        except Exception as e:
            self.logger.error(f"❌ Ошибка: {e}", exc_info=True)
            self.status_label.setText("🔴 Ошибка")
        finally:
            self.run_btn.setEnabled(True)

    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        """
        Обрабатывает один CSV-файл с помощью main_process_file.

        Создаёт отдельный логгер с записью в файл: {имя}_YYYY-MM-DD.log

        Args:
            csv_path (Path): Путь к CSV-файлу
            parent_uid (str): UID корневого объекта
            log_dir_path (Path): Путь к папке log
        """
        try:
            from monitel_framework.logging import LoggerManager, LoggerConfig
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            csv_log_path = log_dir_path / f"{csv_path.stem}_{date_str}.log"

            log_level = getattr(logging, self.config.get("logging.level", "INFO"))
            log_config = LoggerConfig(level=log_level)
            file_logger = LoggerManager(log_config).create_logger(
                name=f"processor.{csv_path.stem}",
                log_file_path=csv_log_path
            )
            file_logger.setLevel(log_level)

            main_process_file(csv_path, parent_uid, self.config, logger=file_logger)

        except Exception as e:
            self.logger.error(f"Ошибка: {e}", exc_info=True)


def main():
    """Точка входа для GUI-приложения."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()