"""
Модуль: monitel_framework.ui_base
Базовый класс для GUI-приложений в рамках Monitel Framework.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List, Union, cast

# PyQt6
try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QFileDialog, QScrollArea,
        QCheckBox, QPlainTextEdit, QGroupBox, QProgressBar
    )
    from PyQt6.QtCore import Qt, QObject, pyqtSignal, QProcess
    from PyQt6.QtGui import QPalette, QColor, QFont, QTextCursor
except ImportError as e:
    raise ImportError("Требуется PyQt6. Установите: pip install PyQt6") from e

# Фреймворк
from .config import ConfigManager
from .files import FileManager
from .logging import LoggerConfig, LoggerManager, UILogHandler, FileLogHandler


class LogSignal(QObject):
    """Сигнал для потокобезопасной передачи логов в GUI."""
    message = pyqtSignal(str)


class BaseMainWindow(QMainWindow):
    """Базовое окно приложения с общей структурой и логированием."""

    def __init__(self, config_file: str = "config.json"):
        super().__init__()
        print("🔧 BaseMainWindow.__init__ вызван")
        
        # Аннотации для UI-элементов
        self.uid_input: QLineEdit
        self.dir_input: QLineEdit
        self.browse_btn: QPushButton
        self.files_scroll: QScrollArea
        self.files_widget: QWidget
        self.files_layout: QVBoxLayout
        self.progress_bar: QProgressBar
        self.run_btn: QPushButton
        self.open_folder_btn: QPushButton
        self.status_label: QLabel
        self.log_text: QPlainTextEdit
        
        self.config = ConfigManager(config_file)
        self.logger_manager: Optional[LoggerManager] = None
        self.logger: Optional[logging.Logger] = None
        self.file_checkboxes: List[Union[QCheckBox, QLabel]] = []
        self.log_dir_path: Optional[Path] = None

        # Сначала настраиваем UI, потом логирование
        self._setup_ui()
        self._setup_logging()
        self._apply_modern_style()

        assert self.logger is not None, "Logger не должен быть None"
        self.logger.info("GUI запущен. Ожидание ввода...")

    def _setup_logging(self) -> None:
        """Настраивает систему логирования для GUI."""
        log_level = getattr(logging, self.config.get("logging.level", "INFO"))
        log_format = self.config.get("logging.format", "%(asctime)s [%(levelname)s]: %(message)s")
        date_format = self.config.get("logging.date_format", "%Y-%m-%d %H:%M:%S")

        log_config = LoggerConfig(level=log_level, format_string=log_format, date_format=date_format)
        self.logger_manager = LoggerManager(log_config)

        base_dir = Path.cwd()
        log_dir_name = self.config.get("io.log_dir", "log")
        assert isinstance(log_dir_name, str), "io.log_dir должен быть строкой"

        self.log_dir_path = base_dir / log_dir_name
        self.log_dir_path.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        gui_log_path = self.log_dir_path / f"gui_{date_str}.log"

        self.logger = self.logger_manager.create_logger("gui", ui_callback=lambda msg: None)
        assert self.logger is not None, "Failed to create logger"
        self.logger.setLevel(log_level)

        self.log_signal = LogSignal()

        def log_callback(msg: str) -> None:
            """Обёртка для передачи лога через сигнал."""
            self.log_signal.message.emit(msg)

        self.log_signal.message.connect(self.append_log)

        ui_handler = UILogHandler(callback=log_callback, level=log_level)
        ui_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(ui_handler)

        file_handler = FileLogHandler(str(gui_log_path), mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(file_handler)

    def _setup_ui(self) -> None:
        """Создаёт стандартный интерфейс."""
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
        self.uid_input.setPlaceholderText("Введите UID...")
        uid_layout.addWidget(self.uid_input)
        settings_layout.addLayout(uid_layout)

        # Папка CSV
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("CSV папка:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Выберите папку...")
        dir_layout.addWidget(self.dir_input)

        self.browse_btn = QPushButton("📁 Выбрать папку")
        self.browse_btn.setObjectName("browse_button")
        self.browse_btn.setMinimumHeight(40)
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

        # === Лог ===
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
        """Применяет современный стиль (тёмная тема) к интерфейсу."""
        colors = {
            "bg": "#1e1e1e",
            "fg": "#dcdcdc",
            "accent": "#007acc",
            "accent_hover": "#005a9e",
            "border": "#3c3c3c",
            "scroll_bg": "#2d2d2d",
            "log_bg": "#1e1e1e",
            "log_text": "#dcdcdc",
        }
        font_size = 10

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {colors['bg']}; color: {colors['fg']}; font-size: {font_size}pt; }}
            QGroupBox {{ border: 1px solid {colors['border']}; border-radius: 8px; margin-top: 20px; padding: 15px; }}
            QLabel {{ color: {colors['fg']}; }}
            QLineEdit {{ padding: 12px; border: 1px solid {colors['border']}; border-radius: 8px; }}
            QPushButton {{ padding: 6px 10px; border-radius: 8px; font-weight: bold; }}
            QPushButton#run_button, QPushButton#folder_button {{
                background-color: {colors['accent']}; color: white; border: none;
            }}
            QPushButton#run_button:hover, QPushButton#folder_button:hover {{
                background-color: {colors['accent_hover']};
            }}
            QPlainTextEdit {{
                background-color: {colors['log_bg']}; color: {colors['log_text']};
                border: 1px solid {colors['border']}; border-radius: 8px;
                font-family: 'Consolas', monospace; font-size: 9pt;
            }}
            QProgressBar::chunk {{ background-color: {colors['accent']}; }}
        """)

    def browse_directory(self) -> None:
        """Открывает диалог выбора папки с CSV-файлами."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с CSV")
        if folder:
            self.dir_input.setText(folder)
            self.populate_file_list()

    def populate_file_list(self) -> None:
        """Заполняет список доступных CSV-файлов в выбранной папке."""
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
            assert self.logger is not None
            self.logger.error(f"Ошибка чтения папки: {e}")
            return

        if not files:
            no_files_label = QLabel("📁 Нет подходящих CSV-файлов")
            no_files_label.setStyleSheet("color: #dc3545; font-style: italic;")
            self.files_layout.addWidget(no_files_label)
            self.file_checkboxes.append(no_files_label)
            return

        for file_path in files:
            checkbox = QCheckBox(file_path.name)
            checkbox.setChecked(True)
            self.files_layout.addWidget(checkbox)
            self.file_checkboxes.append(checkbox)

        assert self.logger is not None
        self.logger.info(f"Найдено файлов: {len(files)}")

    def append_log(self, message: str) -> None:
        """Добавляет сообщение в текстовое поле лога с автопрокруткой."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertPlainText(message + "\n")
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def start_conversion(self) -> None:
        """Запускает процесс конвертации файлов."""
        raise NotImplementedError("start_conversion() должен быть реализован в подклассе")

    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        """Обрабатывает один CSV-файл."""
        raise NotImplementedError("process_file() должен быть реализован в подклассе")

    def open_results_folder(self) -> None:
        """Открывает папку с результатами в проводнике."""
        folder = self.dir_input.text()
        if not folder or not Path(folder).is_dir():
            assert self.logger is not None
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
            assert self.logger is not None
            self.logger.info(f"Открыта папка: {folder}")
        except Exception as e:
            assert self.logger is not None
            self.logger.error(f"Не удалось открыть папку: {e}")

    def closeEvent(self, event) -> None:
        """Обработчик закрытия окна — очищает логгеры."""
        if self.logger_manager:
            self.logger_manager.cleanup_all_loggers()
        super().closeEvent(event)