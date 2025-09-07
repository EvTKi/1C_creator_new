# Руководство разработчика: monitel_framework

Версия: 1.0  
Дата: 2025  
Разработчик: Monitel Team

Это руководство поможет вам использовать и расширять `monitel_framework` —
ваш собственный фреймворк для создания GUI-приложений на Python с поддержкой логирования,
конфигурации и современного стиля.

---

## 🧱 1. Как создать новое приложение на BaseMainWindow

`BaseMainWindow` — базовый класс для всех GUI-приложений в `monitel_framework`.

### Шаги:

1. Убедитесь, что `monitel_framework` доступен в `PYTHONPATH`
2. Создайте файл `ui.py`
3. Унаследуйтесь от `BaseMainWindow`
4. Реализуйте обязательные методы

### Пример:

```python
from monitel_framework import BaseMainWindow

class MyConverter(BaseMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мой конвертер")
        self.resize(800, 600)

    def start_conversion(self):
        # Ваша логика запуска
        self.logger.info("Запуск обработки...")
        # ...

    def process_file(self, csv_path, parent_uid, log_dir_path):
        # Обработка одного файла
        self.logger.info(f"Обработка: {csv_path.name}")
        # ...
```

> ⚠️ Обязательно вызывайте `super().__init__()` — иначе UI не создастся.

---

## ⚙️ 2. Как расширить ConfigManager

`ConfigManager` загружает настройки из `config.json`.

### Возможности:

- Чтение значений: `config.get("key", "default")`
- Автосохранение (опционально)
- Валидация структуры

### Пример расширения:

```python
from monitel_framework.config import ConfigManager

class ExtendedConfig(ConfigManager):
    def get_input_folder(self):
        return self.get("io.input_folder", "input")

    def get_output_format(self):
        return self.get("format.type", "rdf_xml")

    def validate(self):
        required = ["io.log_dir", "logging.level"]
        for key in required:
            if not self.get(key):
                raise ValueError(f"Отсутствует обязательный параметр: {key}")
```

Использование:

```python
config = ExtendedConfig("config.json")
config.validate()
folder = config.get_input_folder()
```

---

## 📝 3. Как добавить свой обработчик логов

`monitel_framework.logging` поддерживает:

- Логирование в GUI (`UILogHandler`)
- Логирование в файл (`FileLogHandler`)
- Пользовательские обработчики

### Пример: Email-логгер

```python
import logging
import smtplib
from email.mime.text import MIMEText

class EmailLogHandler(logging.Handler):
    def __init__(self, smtp_server, port, login, password, recipients, level=logging.ERROR):
        super().__init__(level)
        self.smtp_server = smtp_server
        self.port = port
        self.login = login
        self.password = password
        self.recipients = recipients

    def emit(self, record):
        try:
            msg = MIMEText(self.format(record))
            msg["Subject"] = f"[ERROR] {record.name}"
            msg["From"] = self.login
            msg["To"] = ", ".join(self.recipients)

            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.login, self.password)
                server.send_message(msg)
        except Exception as e:
            print(f"Не удалось отправить email: {e}")
```

Подключение:

```python
handler = EmailLogHandler(
    smtp_server="smtp.gmail.com",
    port=587,
    login="bot@company.com",
    password="xxx",
    recipients=["admin@company.com"]
)
logger.addHandler(handler)
```

---

## 🔁 4. Примеры наследования и переопределения

### Переопределение интерфейса

```python
class CustomMainWindow(BaseMainWindow):
    def _setup_ui(self):
        super()._setup_ui()
        # Добавляем свою кнопку
        extra_btn = QPushButton("🔍 Дополнительно")
        extra_btn.clicked.connect(self.on_extra)
        self.layout().addWidget(extra_btn)

    def on_extra(self):
        self.logger.info("Нажата дополнительная кнопка")
```

Переопределение логики

```python
class MyTool(BaseMainWindow):
    def start_conversion(self):
        if not self.custom_validation():
            self.logger.error("❌ Проверка не пройдена")
            return
        super().start_conversion()  # или своя логика

    def custom_validation(self):
        return len(self.uid_input.text()) > 5
```

---

## 📁 5. Структура логов

### Файловая структура:

```
log/
├── gui_2025-09-05.log        ← общий лог GUI
├── file1_2025-09-05.log      ← лог обработки конкретного файла
└── file2_2025-09-05.log
```

Формат сообщения:

```
2025-09-05 10:30:45 [INFO]: Начало обработки: data.csv
2025-09-05 10:30:45 [DEBUG]: Чтение строки 0
2025-09-05 10:30:46 [ERROR]: Ошибка парсинга: invalid UID
```

### Уровни логирования:

- `DEBUG` — отладочная информация
- `INFO` — обычные действия
- `WARNING` — потенциальные проблемы
- `ERROR` — критические ошибки

---

## ✅ 6. Рекомендации по стилю кода

Следуйте этим правилам для единообразия:

### 1. Докстринги — Google Style

```python
def process_file(self, csv_path: Path, parent_uid: str, log_dir_path: Path) -> None:
    """Обрабатывает один CSV-файл.

    Args:
        csv_path (Path): Путь к CSV-файлу
        parent_uid (str): UID корневого объекта
        log_dir_path (Path): Путь к папке логов
    """
```

### 2. Именование

- Классы: `PascalCase`
- Методы: `snake_case`
- Переменные: `snake_case`
- Константы: `UPPER_CASE`

### 3. Аннотации типов

```python
self.log_text: QPlainTextEdit
self.file_checkboxes: List[Union[QCheckBox, QLabel]]
```

### 4. Pylance

- Не игнорируйте `reportOptionalMemberAccess`
- Используйте `assert self.logger is not None`

---

## 🎨 7. Примеры модификации визуальной составляющей

### Изменение стиля (CSS)

```python
def _apply_modern_style(self):
    super()._apply_modern_style()
    extra_css = """
        QPushButton#run_button {
            background-color: #d35400;
            border-radius: 15px;
        }
        QPushButton#run_button:hover {
            background-color: #e67e22;
        }
    """
    self.setStyleSheet(self.styleSheet() + extra_css)
```

Добавление темы "ночная"

```python
def _apply_night_theme(self):
    colors = {
        "bg": "#0d1b2a",
        "fg": "#e0e1dd",
        "accent": "#778da9",
        "log_bg": "#1b263b"
    }
    # ... применить через setStyleSheet
```

Добавление анимации прогресс-бара

```python
from PyQt6.QtCore import QPropertyAnimation

anim = QPropertyAnimation(self.progress_bar, b"value")
anim.setDuration(500)
anim.setStartValue(0)
anim.setEndValue(100)
anim.start()
```

Добавление тени у окна (только в Windows/Linux)

```python
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

shadow = QGraphicsDropShadowEffect()
shadow.setBlurRadius(15)
shadow.setColor(QColor(0, 0, 0, 80))
shadow.setOffset(0, 0)
self.centralWidget().setGraphicsEffect(shadow)
```

## 📌 Заключение

`monitel_framework` создан для:

- Быстрого старта новых проектов
- Единого стиля и логирования
- Простого расширения

Используйте его как основу для:

- Конвертеров
- Админ-панелей
- Инструментов обработки данных
- Систем мониторинга

---

## 📞 Поддержка

📧 [gornovzena99@gmail.com](mailto:gornovzena99@gmail.com)  
🌐 [github.com/EvTKi/1C_creator_new](https://github.com/EvTKi/1C_creator_new)
