"""
Точка входа CLI приложения.
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

# Специфичные модули приложения
from hierarchy_parser import HierarchyParser
from xml_generator import XMLGenerator


def process_file(
    csv_path: Path,
    parent_uid: str,
    config: ConfigManager,
    logger: logging.Logger
) -> None:
    """
    Обрабатывает один CSV-файл: парсинг → генерация XML.

    Использует переданный логгер для вывода всех сообщений (включая DEBUG).

    Args:
        csv_path (Path): Путь к CSV-файлу
        parent_uid (str): UID корневого контейнера
        config (ConfigManager): Конфигурация приложения
        logger (logging.Logger): Логгер для вывода (GUI + файл)
    """
    try:
        parser = HierarchyParser(str(csv_path), config.config, logger=logger)
        paths, external_children, cck_map, parent_uid_map = parser.parse()
        logger.info(f"Загружено путей: {len(paths)}")

        if not paths:
            logger.error("Нет данных для обработки")
            return

        generator = XMLGenerator(config.config, logger=logger)
        xml_content = generator.generate(
            paths=paths,
            external_children=external_children,
            parent_uid=parent_uid,
            cck_map=cck_map,
            parent_uid_map=parent_uid_map,
            virtual_containers=set(getattr(parser, 'path_to_uid', {}).keys())
        )
        logger.info("Генерация XML успешна")

        output_path = csv_path.with_suffix(".xml")
        if output_path.exists():
            output_path.unlink()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        logger.info(f"Файл сохранён: {output_path}")

    except Exception as e:
        logger.error(f"Ошибка при обработке {csv_path.name}: {e}", exc_info=True)

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