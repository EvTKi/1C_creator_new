"""
GUI для конвертера CSV → RDF/XML (CIM16)
С расширенным debug-логированием
"""

from PyQt6.QtWidgets import QApplication
import logging
import sys
from pathlib import Path

# 🔥 Принудительная очистка кэша
to_remove = [k for k in sys.modules.keys(
) if k.startswith('monitel_framework')]
for k in to_remove:
    del sys.modules[k]

src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# Фреймворк
try:
    from monitel_framework import BaseMainWindow, ConfigManager
    from monitel_framework.files import FileManager
    from monitel_framework.logging import LoggerManager, LoggerConfig
except Exception as e:
    print(f"❌ Ошибка импорта monitel_framework: {e}")
    raise

# Логика приложения
main_process_file = None


def load_main_module():
    """Загружает main_process_file с отладкой"""
    global main_process_file
    try:
        from main import process_file as mp
        main_process_file = mp
        assert callable(
            main_process_file), "main.process_file не является функцией"
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки main.py: {e}")
        if 'logger' in globals():
            logger.error(f"❌ Не удалось загрузить main.py: {e}")
        return False


class MainWindow(BaseMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧩 Конвертер CSV → RDF/XML (CIM16)")
        self.resize(950, 720)

        # 🔹 Дополнительные отладочные логи
        self.logger.debug("🔧 MainWindow: инициализация завершена")
        self.logger.debug(f"📁 Рабочая директория: {Path.cwd()}")
        self.logger.debug(f"📄 config.json путь: {self.config.config_path}")
        self.logger.debug(f"📂 log_dir_path: {self.log_dir_path}")

        if not load_main_module():
            self.logger.critical(
                "🛑 КРИТИЧЕСКАЯ ОШИБКА: main.py не загружен. Приложение НЕ БУДЕТ работать.")
        else:
            self.logger.info("✅ Модуль main.py успешно загружен")

    def start_conversion(self) -> None:
        try:
            folder_uid = self.uid_input.text().strip()
            csv_dir = self.dir_input.text().strip()

            self.logger.info("🚀 Запуск обработки...")
            self.logger.debug(f"UID: '{folder_uid}'")
            self.logger.debug(f"Папка CSV: '{csv_dir}'")

            if not folder_uid:
                self.logger.error("❌ Не указан UID папки.")
                return

            if not csv_dir:
                self.logger.error("❌ Не указана папка с CSV.")
                return

            if not Path(csv_dir).is_dir():
                self.logger.error(f"❌ Папка не существует: {csv_dir}")
                return

            self.status_label.setText("🔄 Обработка...")
            self.run_btn.setEnabled(False)
            # sys.stdout.flush()

            file_manager = FileManager(base_directory=csv_dir)
            if not file_manager.validate_directory():
                self.logger.error(f"❌ Папка не найдена или пуста: {csv_dir}")
                return

            exclude_files = self.config.get("io.exclude_files", ["Sample.csv"])
            self.logger.debug(f"📋 Исключённые файлы: {exclude_files}")
            csv_files = file_manager.get_csv_files(exclude_files=exclude_files)

            if not csv_files:
                self.logger.error("❌ Нет подходящих CSV-файлов.")
                return

            self.logger.info(f"📦 Найдено файлов: {len(csv_files)}")
            for f in csv_files:
                self.logger.debug(f"📄 Обрабатываемый файл: {f}")

            total = len(csv_files)
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)

            assert self.log_dir_path is not None, "log_dir_path не установлен"
            log_dir_path = self.log_dir_path

            for i, filename in enumerate(csv_files, 1):
                csv_path = file_manager.base_directory / filename
                self.logger.info(
                    f"--- [{i}/{total}] Обработка: {filename} ---")
                self.logger.debug(f"🔍 Путь к файлу: {csv_path}")
                self.logger.debug(
                    f"📝 Лог будет сохранён в: {log_dir_path / f'{csv_path.stem}_*.log'}")

                self.process_file(csv_path, folder_uid, log_dir_path)
                self.progress_bar.setValue(i)

            self.logger.info("✅ Готово. Все файлы обработаны.")
            self.status_label.setText("🟢 Готово")
            self.progress_bar.setValue(total)

        except Exception as e:
            import traceback
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.logger.error(
                f"❌ Ошибка в start_conversion:\n{e}\n{tb}", exc_info=True)
        finally:
            self.run_btn.setEnabled(True)

    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        try:
            if main_process_file is None:
                self.logger.error(
                    "❌ Функция main_process_file не загружена. Проверьте main.py")
                return

            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            csv_log_path = log_dir_path / f"{csv_path.stem}_{date_str}.log"

            log_level = getattr(
                logging, self.config.get("logging.level", "INFO"))
            log_config = LoggerConfig(level=log_level)
            file_logger = LoggerManager(log_config).create_logger(
                name=f"processor.{csv_path.stem}",
                log_file_path=str(csv_log_path)
            )
            file_logger.setLevel(log_level)

            self.logger.debug(f"🖨 Создан логгер для файла: {csv_log_path}")

            main_process_file(csv_path, parent_uid,
                              self.config, logger=file_logger)
            # ✅ Дополнительный лог в GUI
            modified_path = csv_path.parent / \
                f"{csv_path.stem}_modified_*.xlsx"
            # Просто информируем — путь можно уточнить в логах
            self.append_log(
                f"📄 Создан modified файл: {csv_path.stem}_modified_*.xlsx\n")

        except Exception as e:
            import traceback
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.logger.error(
                f"❌ Ошибка в process_file:\n{e}\n{tb}", exc_info=True)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
