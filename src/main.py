"""
Модуль: Основная логика конвертера CSV → RDF/XML (CIM16)

Предоставляет функцию `process_file`, которая:
- Читает CSV-файл
- Парсит иерархию
- Генерирует RDF/XML
- Сохраняет результат

Может использоваться как в CLI, так и из GUI.
"""
import csv
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from uuid import uuid4

# Импорты из фреймворка
try:
    from monitel_framework.config import ConfigManager
    from monitel_framework.files import FileManager, CLIManager
    from monitel_framework.logging import LoggerManager, LoggerConfig
except ImportError:
    from .monitel_framework.files import FileManager, CLIManager
    from .monitel_framework.logging import LoggerManager, LoggerConfig
    from .monitel_framework.config import ConfigManager


import logging
from pathlib import Path
from typing import Optional

# Локальные модули
from monitel_framework.config import ConfigManager
from modules.hierarchy_parser import HierarchyParser
from modules.xml_generator import XMLGenerator


def process_file(
    csv_path: Path,
    parent_uid: str,
    config: ConfigManager,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Обрабатывает один CSV-файл: парсинг → генерация RDF/XML → сохранение.

    Создаёт XML-файл в той же директории, что и исходный CSV.
    Использует переданный логгер или создаёт новый.

    Args:
        csv_path (Path): Путь к входному CSV-файлу
        parent_uid (str): UID корневого объекта для новой иерархии
        config (ConfigManager): Конфигурация приложения
        logger (Optional[logging.Logger]): Логгер для вывода сообщений.
            Если None — будет создан новый с уровнем из config.

    Raises:
        Exception: При ошибках парсинга, генерации или записи файла
    """
    # Если логгер не передан — создаём свой
    if logger is None:
        from monitel_framework.logging import LoggerManager, LoggerConfig
        log_level = getattr(logging, config.get("logging.level", "INFO"))
        log_format = config.get(
            "logging.format", "%(asctime)s [%(levelname)s]: %(message)s")
        date_format = config.get("logging.date_format", "%Y-%m-%d %H:%M:%S")
        log_config = LoggerConfig(
            level=log_level, format_string=log_format, date_format=date_format)
        logger_manager = LoggerManager(log_config)
        logger = logger_manager.create_logger("main")

    # Убеждаемся, что logger не None (для Pylance)
    assert logger is not None, "Логгер не должен быть None после инициализации"

    try:
        logger.info(f"Начало обработки файла: {csv_path.name}")

        # Парсинг CSV
        parser = HierarchyParser(str(csv_path), config.config, logger=logger)
        paths, external_children, cck_map, parent_uid_map = parser.parse()
        logger.info(f"Загружено путей: {len(paths)}")
        if not paths:
            logger.error(
                "❌ Нет данных для обработки — файл пуст или не содержит валидных путей")
            return

        # Генерация XML (теперь возвращает кортеж)
        generator = XMLGenerator(config.config, logger=logger)
        xml_content, path_to_generated_id = generator.generate(
            paths=paths,
            external_children=external_children,
            parent_uid=parent_uid,
            cck_map=cck_map,
            parent_uid_map=parent_uid_map,
            virtual_containers=set(getattr(parser, 'path_to_uid', {}).keys())
        )
        logger.info("✅ Генерация XML завершена")

        # Сохранение XML
        output_path = csv_path.with_suffix(".xml")
        if output_path.exists():
            output_path.unlink()
            logger.debug(f"Удалён существующий файл: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        logger.info(f"✅ Файл успешно сохранён: {output_path}")

        # Создание модифицированного CSV
        _create_modified_csv(csv_path, config, paths,
                             path_to_generated_id, logger)

    except Exception as e:
        logger.error(
            f"❌ Ошибка при обработке {csv_path.name}: {e}", exc_info=True)
        raise


def _create_modified_csv(
    original_csv_path: Path,
    config: ConfigManager,
    all_original_paths: List[str],  # <-- Список исходных строк
    path_to_generated_id: Dict[Tuple[str, ...], str],
    logger: logging.Logger
) -> None:
    """
    Создает модифицированную копию CSV-файла с добавленными сгенерированными UUID.
    Уважает существующие uid из исходного файла.
    """
    modified_csv_path = original_csv_path.with_name(
        f"{original_csv_path.stem}_modified{original_csv_path.suffix}")

    csv_headers = config.get("csv", {}).get("headers", {})
    path_header = csv_headers.get("path", "НаименованиеКонтейнераОборудования")
    uid_header = csv_headers.get("uid", "uid")

    encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']
    used_encoding = 'utf-8-sig'
    delimiter = ','

    original_lines = []
    for encoding in encodings:
        try:
            with open(original_csv_path, 'r', encoding=encoding) as f:
                sample = f.read(1024)
                f.seek(0)
                delimiter = ';' if ';' in sample else '\t' if '\t' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)
                original_lines = list(reader)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if not original_lines:
        logger.warning(
            f"Не удалось определить кодировку для {original_csv_path}, используется utf-8-sig")

    new_lines = []

    for row in original_lines:
        path_str = row.get(path_header, '').strip()
        if path_str:
            parts = tuple(p.strip() for p in path_str.split('\\') if p.strip())
            # Проверяем, есть ли уже UID в этой строке
            existing_uid = row.get(uid_header, '').strip()
            if existing_uid and len(existing_uid) > 0:
                # Если UID существует — оставляем его без изменений
                pass
            else:
                # Если UID отсутствует — используем сгенерированный UUID
                if parts in path_to_generated_id:
                    generated_uid = path_to_generated_id[parts].replace(
                        "#_", "")
                    row[uid_header] = generated_uid
                else:
                    # Если UUID не найден — генерируем новый
                    new_uid = f"{uuid4()}"
                    row[uid_header] = new_uid
                    logger.debug(
                        f"Сгенерирован новый UUID для пути {parts}: {new_uid}")
        new_lines.append(row)

    with open(modified_csv_path, 'w', newline='', encoding=used_encoding) as f:
        if new_lines:
            fieldnames = new_lines[0].keys()
            writer = csv.DictWriter(
                f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(new_lines)

    logger.info(f"✅ Модифицированный CSV сохранён: {modified_csv_path}")


def main():
    """Основная функция CLI-интерфейса."""
    cli_manager = CLIManager()
    folder_uid, csv_dir = cli_manager.get_cli_parameters()

    if not folder_uid:
        print("❌ Не указан UID папки.")
        return

    # --- Загрузка конфигурации ---
    config = ConfigManager("config.json")

    # --- Инициализация менеджера файлов ---
    file_manager = FileManager(
        base_directory=csv_dir or config.get("io.input_dir", "."),
        log_directory=config.get("io.log_dir", "logs")
    )

    if not file_manager.validate_directory():
        print(f"❌ Папка не найдена: {file_manager.base_directory}")
        return

    # --- Получение списка CSV-файлов ---
    exclude_files = config.get("io.exclude_files", ["Sample.csv"])
    csv_files = file_manager.get_csv_files(exclude_files=exclude_files)

    if not csv_files:
        print("❌ Нет подходящих CSV-файлов.")
        return

    print("Будут обработаны:")
    for f in csv_files:
        print(f"  {f}")
    print("-" * 30)

    # --- Создание директории логов ---
    file_manager.create_log_directory()

    # --- Обработка каждого файла ---
    for filename in csv_files:
        csv_path = file_manager.base_directory / filename
        process_file(csv_path, folder_uid, config)

    cli_manager.print_completion_message()


if __name__ == "__main__":
    main()
