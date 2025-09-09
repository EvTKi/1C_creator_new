"""
Модуль: Основная логика конвертера CSV → RDF/XML (CIM16)

Предоставляет функцию `process_file`, которая:
- Читает CSV-файл
- Парсит иерархию
- Генерирует RDF/XML
- Сохраняет результат
- Экспортирует modified.xlsx/csv с подсветкой старых и новых UID

Может использоваться как в CLI, так и из GUI.
"""

import logging
from pathlib import Path
from typing import Optional

# Импорты из фреймворка
try:
    from monitel_framework.config import ConfigManager
    from monitel_framework.files import FileManager, CLIManager
    from monitel_framework.logging import LoggerManager, LoggerConfig
except ImportError:
    from .monitel_framework.config import ConfigManager
    from .monitel_framework.files import FileManager, CLIManager
    from .monitel_framework.logging import LoggerManager, LoggerConfig

# Локальные модули
from modules.hierarchy_parser import HierarchyParser
from modules.xml_generator import XMLGenerator
from modules.modified_csv_exporter import save_modified_output  # ✅ Новый модуль


def process_file(
    csv_path: Path,
    parent_uid: str,
    config: ConfigManager,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Обрабатывает один CSV-файл: парсинг → генерация RDF/XML → сохранение → экспорт modified.

    Создаёт:
    - XML-файл в той же директории, что и исходный CSV
    - Modified XLSX/CSV с подсветкой старых (зелёных) и новых (чёрных) UID

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

        # --- Парсинг CSV ---
        parser = HierarchyParser(str(csv_path), config.config, logger=logger)
        paths, external_children, cck_map, parent_uid_map = parser.parse()
        logger.info(f"Загружено путей: {len(paths)}")

        if not paths:
            logger.error(
                "❌ Нет данных для обработки — файл пуст или не содержит валидных путей")
            return

        # --- Генерация XML ---
        generator = XMLGenerator(config.config, logger=logger)
        xml_content = generator.generate(
            paths=paths,
            external_children=external_children,
            parent_uid=parent_uid,
            cck_map=cck_map,
            parent_uid_map=parent_uid_map,
            virtual_containers=set(getattr(parser, 'path_to_uid', {}).keys())
        )
        logger.info("✅ Генерация XML завершена")

        # --- Сохранение XML ---
        output_path = csv_path.with_suffix(".xml")
        if output_path.exists():
            output_path.unlink()
            logger.debug(f"Удалён существующий файл: {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        logger.info(f"✅ Файл успешно сохранён: {output_path}")

        # --- Экспорт modified-файла ---
        try:
            # Формируем данные для экспорта
            hierarchy_data = [
                {
                    "path": path,
                    "uid": parent_uid_map.get(path, "") or "",
                    "CCK_code": cck_map.get(path, "")
                }
                for path in paths
            ]

            # ✅ Передаём logger для полного логирования
            modified_path = save_modified_output(
                csv_path=csv_path,
                hierarchy=hierarchy_data,
                config=config.config,
                logger=logger
            )
            if modified_path:
                logger.info(f"📄 Modified файл сохранён: {modified_path}")

        except Exception as e:
            logger.error(
                f"❌ Ошибка при экспорте modified файла: {e}", exc_info=True)

    except Exception as e:
        logger.error(
            f"❌ Ошибка при обработке {csv_path.name}: {e}", exc_info=True)
        raise


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
