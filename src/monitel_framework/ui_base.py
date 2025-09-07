"""
Модуль: monitel_framework.ui_base
Базовый класс для GUI-приложений с поддержкой тем, стиля и логирования.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List, Union

# PyQt6
try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QFileDialog, QScrollArea,
        QCheckBox, QPlainTextEdit, QGroupBox, QProgressBar
    )
    from PyQt6.QtCore import Qt, QObject, pyqtSignal, QProcess
    from PyQt6.QtGui import QFont
except ImportError as e:
    raise ImportError("Требуется PyQt6. Установите: pip install PyQt6") from e

# Фреймворк
from .config import ConfigManager
from .files import FileManager
from .logging import LoggerConfig, LoggerManager, UILogHandler, FileLogHandler


class LogSignal(QObject):
    """Сигнал для потокобезопасной передачи логов."""
    message = pyqtSignal(str)


class BaseMainWindow(QMainWindow):
    """Базовое окно с поддержкой тем, логирования и современного стиля."""

    def __init__(self, config_file: str = "config.json"):
        super().__init__()
        print("🔧 BaseMainWindow.__init__ вызван")

        # Аннотации
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
        self.theme_toggle: QCheckBox

        self.config = ConfigManager(config_file)
        self.logger_manager: Optional[LoggerManager] = None
        self.logger: Optional[logging.Logger] = None
        self.file_checkboxes: List[Union[QCheckBox, QLabel]] = []
        self.log_dir_path: Optional[Path] = None
        self.is_dark_theme = True

        self._setup_ui()
        self._setup_logging()
        self._apply_current_theme()

        assert self.logger is not None
        self.logger.info("GUI запущен. Ожидание ввода...")

    def _setup_ui(self) -> None:
        """Создаёт интерфейс с переключателем темы."""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Настройки ===
        settings_group = QGroupBox("⚙️ Настройки")
        settings_layout = QVBoxLayout()

        uid_layout = QHBoxLayout()
        uid_layout.addWidget(QLabel("UID корня:"))
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("Введите UID...")
        uid_layout.addWidget(self.uid_input)
        settings_layout.addLayout(uid_layout)

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("CSV папка:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Выберите папку...")
        dir_layout.addWidget(self.dir_input)

        self.browse_btn = QPushButton("📁 Выбрать папку")
        self.browse_btn.setObjectName("browse_button")
        self.browse_btn.setMinimumHeight(24)
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
        self.run_btn.setMinimumHeight(24)
        self.run_btn.clicked.connect(self.start_conversion)
        btn_layout.addWidget(self.run_btn)

        self.open_folder_btn = QPushButton("📁 Папка")
        self.open_folder_btn.setObjectName("folder_button")
        self.open_folder_btn.setMinimumHeight(24)
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
        self.log_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)

        # === Тема ===
        theme_layout = QHBoxLayout()
        theme_layout.addStretch()
        self.theme_toggle = QCheckBox("🔆 Светлая тема")
        self.theme_toggle.toggled.connect(self.toggle_theme)
        theme_layout.addWidget(self.theme_toggle)
        layout.addLayout(theme_layout)

        # === Статус ===
        self.status_label = QLabel("🟢 Готов к работе")
        layout.addWidget(self.status_label)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def _setup_logging(self) -> None:
        """Настраивает логирование."""
        log_level = getattr(logging, self.config.get("logging.level", "INFO"))
        log_format = self.config.get("logging.format", "%(asctime)s [%(levelname)s]: %(message)s")
        date_format = self.config.get("logging.date_format", "%Y-%m-%d %H:%M:%S")

        log_config = LoggerConfig(level=log_level, format_string=log_format, date_format=date_format)
        self.logger_manager = LoggerManager(log_config)

        base_dir = Path.cwd()
        log_dir_name = self.config.get("io.log_dir", "log")
        assert isinstance(log_dir_name, str)

        self.log_dir_path = base_dir / log_dir_name
        self.log_dir_path.mkdir(parents=True, exist_ok=True)

        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        gui_log_path = self.log_dir_path / f"gui_{date_str}.log"

        self.logger = self.logger_manager.create_logger("gui", ui_callback=lambda msg: None)
        assert self.logger is not None
        self.logger.setLevel(log_level)

        self.log_signal = LogSignal()
        self.log_signal.message.connect(self.append_log)

        def log_callback(msg: str):
            self.log_signal.message.emit(msg)

        ui_handler = UILogHandler(callback=log_callback, level=log_level)
        ui_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(ui_handler)

        file_handler = FileLogHandler(str(gui_log_path), mode="a", encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_config.formatter)
        self.logger.addHandler(file_handler)

    def _apply_dark_theme(self):
        colors = {
            "bg": "#1a1a1a", "bg_card": "#252526", "fg": "#ffffff",
            "accent": "#007acc", "accent_hover": "#005a9e", "border": "#3c3c3c",
            "scroll": "#2d2d2d", "log_bg": "#1e1e1e", "log_text": "#dcdcdc",
            "folder_btn": "#006699", "folder_btn_hover": "#0088cc"
        }
        self._set_theme_style(colors)

    def _apply_light_theme(self):
        colors = {
            "bg": "#f0f0f0", "bg_card": "#ffffff", "fg": "#333333",
            "accent": "#0056b3", "accent_hover": "#003d82", "border": "#cccccc",
            "scroll": "#e0e0e0", "log_bg": "#f9f9f9", "log_text": "#111111",
            "folder_btn": "#006699", "folder_btn_hover": "#0088cc"
        }
        self._set_theme_style(colors)

    def _set_theme_style(self, colors):
        font_family = "Segoe UI, Arial, sans-serif"
        font_size = 10

        self.setStyleSheet(f"""
            QMainWindow {{ background: {colors['bg']}; color: {colors['fg']}; font-family: '{font_family}'; font-size: {font_size}pt; }}
            QLabel {{ color: {colors['fg']}; font-weight: 500; }}
            QLineEdit {{ padding: 12px; border: 1px solid {colors['border']}; border-radius: 10px; background: {colors['bg_card']}; }}
            QLineEdit:focus {{ border: 2px solid {colors['accent']}; }}
            QGroupBox {{ border: 1px solid {colors['border']}; border-radius: 12px; margin-top: 20px; padding: 15px; background: {colors['bg_card']}; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }}
            QPushButton {{ min-height: 24px; padding: 10px 16px; border-radius: 10px; font-weight: 600; font-size: 11pt; border: none; }}
            QPushButton#run_button {{ background: {colors['accent']}; color: white; }}
            QPushButton#run_button:hover {{ background: {colors['accent_hover']}; transform: scale(1.03); transition: all 0.2s ease; }}
            QPushButton#browse_button {{ background: {colors['folder_btn']}; color: white; }}
            QPushButton#browse_button:hover {{ background: {colors['folder_btn_hover']}; transform: scale(1.03); transition: all 0.2s ease; }}
            QPushButton#folder_button {{ background: #555; color: white; }}
            QPushButton#folder_button:hover {{ background: #777; }}
            QProgressBar::chunk {{ background: {colors['accent']}; border-radius: 4px; }}
            QPlainTextEdit {{ background: {colors['log_bg']}; color: {colors['log_text']}; border: 1px solid {colors['border']}; border-radius: 10px; font-family: 'Consolas', monospace; font-size: 9pt; }}
            QScrollBar:vertical {{ width: 10px; background: {colors['scroll']}; border-radius: 5px; }}
            QScrollBar::handle:vertical {{ background: {colors['border']}; border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: {colors['accent']}; }}
            QCheckBox {{ color: {colors['fg']}; font-weight: 500; }}
        """)
        self.log_text.setStyleSheet(f"background: {colors['log_bg']}; color: {colors['log_text']};")

    def _apply_current_theme(self):
        if self.is_dark_theme:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def toggle_theme(self, checked: bool):
        self.is_dark_theme = not checked
        self._apply_current_theme()

    def append_log(self, message: str) -> None:
        if not hasattr(self, 'log_text') or self.log_text is None:
            return
        text = message.rstrip() + "\n"
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertPlainText(text)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, lambda: self.log_text.ensureCursorVisible())

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
            files = [f for f in Path(folder).iterdir() if f.is_file() and f.suffix.lower() == '.csv' and f.name.lower() != 'sample.csv']
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

    def start_conversion(self) -> None:
        raise NotImplementedError("start_conversion() должен быть реализован в подклассе")

    def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
        raise NotImplementedError("process_file() должен быть реализован в подклассе")

    def open_results_folder(self) -> None:
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
        if self.logger_manager:
            self.logger_manager.cleanup_all_loggers()
        super().closeEvent(event)