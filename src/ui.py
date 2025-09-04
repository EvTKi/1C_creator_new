"""
Модуль: GUI для конвертера CSV → RDF/XML (CIM16)
Современный интерфейс с поддержкой логирования в файл и GUI.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List

# PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QFileDialog, QFrame, QScrollArea,
        QCheckBox, QPlainTextEdit, QGroupBox, QProgressBar
    )
    from PyQt6.QtCore import Qt, QObject, pyqtSignal
    from PyQt6.QtGui import QPalette, QColor, QFont, QTextCursor
    from PyQt6.QtCore import QProcess
except ImportError as e:
    raise ImportError("Требуется PyQt6. Установите: pip install PyQt6") from e

# Фреймворк
try:
    from monitel_framework.config import ConfigManager
    from monitel_framework.files import FileManager
    from monitel_framework.logging import (
        UILogHandler, LoggerConfig, LoggerManager, FileLogHandler
    )
except ImportError:
    from .monitel_framework.config import ConfigManager
    from .monitel_framework.files import FileManager
    from .monitel_framework.logging import (
        UILogHandler, LoggerConfig, LoggerManager, FileLogHandler
    )

# Логика приложения
try:
    from main import process_file
except ImportError:
    # Если запускается из .exe или src
    try:
        from .main import process_file
    except ImportError:
        raise ImportError("Не удалось импортировать process_file из main.py")
from hierarchy_parser import HierarchyParser
from xml_generator import XMLGenerator


class LogSignal(QObject):
    """Сигнал для потокобезопасной передачи логов."""
    message = pyqtSignal(str)


class LogHandlerWidget(UILogHandler):
    """Обработчик логов, отправляющий сообщения в GUI."""
    def __init__(self, signal: LogSignal, level: int = logging.INFO):
        super().__init__(callback=self._dummy_callback, level=level)
        self.signal = signal
        self.setLevel(level)

    def _dummy_callback(self, msg: str) -> None:
        pass

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.signal.message.emit(msg + "\n")
        except Exception:
            self.handleError(record)


class MainWindow(QMainWindow):
    """
    Основное окно приложения с улучшенным визуальным стилем.
    """

    def __init__(self):
        super().__init__()
        self.config = ConfigManager("config.json")
        self.logger_manager: Optional[LoggerManager] = None
        self.logger: Optional[logging.Logger] = None
        self.file_checkboxes: List[QCheckBox] = []

        self._setup_ui()
        self._setup_logging()
        self._apply_modern_style()

    def _setup_ui(self) -> None:
        """Создание интерфейса."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Настройки ===
        settings_group = QGroupBox("⚙️ Настройки")
        settings_layout = QVBoxLayout()

        # UID
        uid_layout = QHBoxLayout()
        uid_layout.addWidget(QLabel("UID корня:"))
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("Введите UID корневого объекта...")
        uid_layout.addWidget(self.uid_input)
        settings_layout.addLayout(uid_layout)

        # Папка CSV
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("CSV папка:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Выберите папку с CSV файлами...")
        dir_layout.addWidget(self.dir_input)

        self.browse_btn = QPushButton("📁 Выбрать папку")
        self.browse_btn.setObjectName("browse_button")
        self.browse_btn.setMinimumHeight(40)
        self.browse_btn.setStyleSheet("""
            QPushButton#browse_button {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                padding: 10px 15px;
            }
            QPushButton#browse_button:hover {
                background-color: #138496;
            }
            QPushButton#browse_button:pressed {
                background-color: #117a8b;
            }
        """)
        self.browse_btn.setToolTip("Выбрать папку")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_btn)
        settings_layout.addLayout(dir_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # === Список файлов ===
        files_group = QGroupBox("📋 Файлы для обработки")
        files_layout = QVBoxLayout()

        self.files_scroll = QScrollArea()
        self.files_scroll.setWidgetResizable(True)
        self.files_widget = QWidget()
        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setSpacing(5)
        self.files_layout.setContentsMargins(10, 10, 10, 10)
        self.files_scroll.setWidget(self.files_widget)
        files_layout.addWidget(self.files_scroll)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # === Прогресс-бар ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Готово: %p%")
        layout.addWidget(self.progress_bar)

        # === Кнопки ===
        btn_layout = QHBoxLayout()

        self.run_btn = QPushButton("▶️ Запуск")
        self.run_btn.setObjectName("run_button")
        self.run_btn.setFixedSize(100, 30)
        self.run_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.run_btn)

        self.open_folder_btn = QPushButton("📁 Папка")
        self.open_folder_btn.setObjectName("folder_button")
        self.open_folder_btn.setFixedSize(100, 30)
        self.open_folder_btn.clicked.connect(self.open_results_folder)
        btn_layout.addWidget(self.open_folder_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # === Лог (увеличенная область) ===
        log_group = QGroupBox("📝 Лог операций")
        log_layout = QVBoxLayout()

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(250)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)

        # === Статус ===
        self.status_label = QLabel("🟢 Готов к работе")
        layout.addWidget(self.status_label)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def _apply_modern_style(self) -> None:
        """Применяет современный стиль."""
        colors = {
            "bg": "#1e1e1e",
            "fg": "#dcdcdc",
            "accent": "#007acc",
            "accent_hover": "#005a9e",
            "border": "#3c3c3c",
            "scroll_bg": "#2d2d2d",
            "log_bg": "#1e1e1e",
            "log_text": "#dcdcdc",
            "checkbox_bg": "#2d2d2d",
            "checkbox_border": "#404040"
        }
        font_size = 10

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['bg']};
                color: {colors['fg']};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {font_size}pt;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {colors['border']};
                border-radius: 8px;
                margin-top: 20px;
                padding: 15px;
                background-color: #{int(sum([int(c,16) for c in colors['bg'][1::2]])/3):02x}{int(sum([int(c,16) for c in colors['bg'][2::2]])/3):02x}{int(sum([int(c,16) for c in colors['bg'][3::2]])/3):02x};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background: {colors['bg']};
                color: {colors['accent']};
            }}
            QLabel {{
                color: {colors['fg']};
                font-weight: 500;
            }}
            QLineEdit {{
                padding: 12px;
                border: 1px solid {colors['border']};
                border-radius: 8px;
                background-color: #{int(sum([int(c,16) for c in colors['bg'][1::2]])/3):02x}{int(sum([int(c,16) for c in colors['bg'][2::2]])/3):02x}{int(sum([int(c,16) for c in colors['bg'][3::2]])/3):02x};
                color: {colors['fg']};
            }}
            QPushButton {{
                padding: 6px 10px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 9pt;
                min-height: 24px;
            }}
            QPushButton#run_button, QPushButton#folder_button {{
                background-color: {colors['accent']};
                color: white;
                border: none;
            }}
            QPushButton#run_button:hover, QPushButton#folder_button:hover {{
                background-color: {colors['accent_hover']};
            }}
            QCheckBox {{
                padding: 8px 12px;
                border-bottom: 1px solid {colors['border']};
                border-radius: 6px;
                margin: 2px;
                background-color: {colors['checkbox_bg']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors['border']};
                border-radius: 6px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['accent']};
                border-color: {colors['accent']};
            }}
            QPlainTextEdit {{
                background-color: {colors['log_bg']};
                color: {colors['log_text']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }}
            QProgressBar {{
                border: 1px solid {colors['border']};
                border-radius: 8px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['accent']};
                border-radius: 8px;
            }}
        """)

    def browse_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с CSV")
        if folder:
            self.dir_input.setText(folder)
            self.populate_file_list()

    def populate_file_list(self) -> None:
        for checkbox in self.file_checkboxes:
            checkbox.setParent(None)
        self.file_checkboxes.clear()

        folder = self.dir_input.text()
        if not folder or not Path(folder).is_dir():
            return

        try:
            files = [
                f for f in Path(folder).iterdir()
                if f.is_file() and f.suffix.lower() == '.csv' and f.name.lower() != 'sample.csv'
            ]
            files = sorted(files, key=lambda x: x.name)
        except Exception as e:
            self.logger.error(f"Ошибка чтения папки: {e}")
            return

        if not files:
            no_files_label = QLabel("📁 Нет подходящих CSV-файлов")
            no_files_label.setStyleSheet(f"color: #dc3545; font-style: italic;")
            self.files_layout.addWidget(no_files_label)
            self.file_checkboxes.append(no_files_label)
            return

        for file_path in files:
            checkbox = QCheckBox(file_path.name)
            checkbox.setChecked(True)
            self.files_layout.addWidget(checkbox)
            self.file_checkboxes.append(checkbox)

        self.logger.info(f"Найдено файлов: {len(files)}")

    def _setup_logging(self) -> None:
        log_level = getattr(logging, self.config.get("logging.level", "INFO"))
        log_format = self.config.get("logging.format", "%(asctime)s [%(levelname)s]: %(message)s")
        date_format = self.config.get("logging.date_format", "%Y-%m-%d %H:%M:%S")

        log_config = LoggerConfig(level=log_level, format_string=log_format, date_format=date_format)
        self.logger_manager = LoggerManager(log_config)

        base_dir = Path.cwd()
        log_dir_name = self.config.get("io.log_dir", "log")
        log_dir_path = base_dir / log_dir_name
        log_dir_path.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        gui_log_path = log_dir_path / f"gui_{date_str}.log"

        self.logger = self.logger_manager.create_logger("gui", ui_callback=lambda msg: None)
        assert self.logger is not None, "Failed to create logger"
        self.logger.setLevel(log_level)

        self.log_signal = LogSignal()
        self.log_signal.message.connect(self.append_log)

        ui_handler = LogHandlerWidget(self.log_signal, level=log_level)
        ui_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(ui_handler)

        file_handler = FileLogHandler(gui_log_path, mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(file_handler)

        # self.logger.debug("✅ DEBUG-режим активирован")
        self.logger.info("GUI запущен. Ожидание ввода...")

    def append_log(self, message: str) -> None:
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertPlainText(message)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def start_conversion(self) -> None:
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
        QApplication.processEvents()

        try:
            base_dir = Path.cwd()
            log_dir_name = self.config.get("io.log_dir", "log")
            log_dir_path = base_dir / log_dir_name
            log_dir_path.mkdir(parents=True, exist_ok=True)

            # --- ✅ Добавляем FileHandler к существующему logger ---
            from datetime import datetime
            date_str = datetime.now().strftime("%Y-%m-%d")
            gui_log_path = log_dir_path / f"gui_{date_str}.log"

            file_handler = FileLogHandler(gui_log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(self.logger.level)
            file_handler.setFormatter(self.logger.handlers[0].formatter)
            self.logger.addHandler(file_handler)

            self.logger.info("=== ЗАПУСК ОБРАБОТКИ ===")
            # ---

            file_manager = FileManager(base_directory=csv_dir, log_directory=log_dir_name)
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
                self.process_file(csv_path, folder_uid, log_dir_path)
                self.progress_bar.setValue(i)
                QApplication.processEvents()

            self.logger.info("✅ Готово. Все файлы обработаны.")
            self.status_label.setText("🟢 Готово")
            self.progress_bar.setValue(total)

        except Exception as e:
            self.logger.error(f"❌ Ошибка: {e}", exc_info=True)
            self.status_label.setText("🔴 Ошибка")
        finally:
            self.run_btn.setEnabled(True)
    
    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        """Обрабатывает файл, используя логику из main.py."""
        from datetime import datetime
        try:
            # --- 🔥 Создаём отдельный логгер для этого файла ---
            date_str = datetime.now().strftime("%Y-%m-%d")
            csv_log_path = log_dir_path / f"{csv_path.stem}_{date_str}.log"

            file_logger = self.logger_manager.create_logger(
                name=f"processor.{csv_path.stem}",
                log_file_path=csv_log_path
            )
            file_logger.setLevel(self.logger.level)  # Наследуем уровень GUI
            # ---

            # Передаём логгер в main.process_file
            process_file(csv_path, parent_uid, self.config, logger=file_logger)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке {csv_path.name}: {e}", exc_info=True)
    
    def open_results_folder(self) -> None:
        folder = self.dir_input.text()
        if not folder or not Path(folder).is_dir():
            self.logger.info("Папка не выбрана или не найдена.")
            return

        try:
            if sys.platform.startswith('win'):
                import os
                os.startfile(folder)
            elif sys.platform.startswith('darwin'):
                QProcess.startDetached('open', [folder])
            else:
                QProcess.startDetached('xdg-open', [folder])
            self.logger.info(f"Открыта папка: {folder}")
        except Exception as e:
            self.logger.error(f"Не удалось открыть папку: {e}")

    def closeEvent(self, event) -> None:
        if self.logger_manager:
            self.logger_manager.cleanup_all_loggers()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()