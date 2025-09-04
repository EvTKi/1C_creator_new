"""
Точка входа CLI приложения.
"""

import os
import logging
from pathlib import Path

# Импорты из фреймворка - исправленные пути
try:
    # Попробуем импорт как модуль (для разработки)
    from monitel_framework.config import ConfigManager
    from monitel_framework.files import FileManager, CLIManager
    from monitel_framework.logging import LoggerManager, LoggerConfig
except ImportError:
    # Fallback: импорт из текущей директории (для собранного .exe)
    from .monitel_framework.config import ConfigManager
    from .monitel_framework.files import FileManager, CLIManager
    from .monitel_framework.logging import LoggerManager, LoggerConfig

# Специфичные модули приложения
from hierarchy_parser import HierarchyParser
from xml_generator import XMLGenerator

def process_file(csv_path: Path, parent_uid: str, config: ConfigManager):
    """
    Обрабатывает один CSV файл.
    
    Args:
        csv_path: путь к CSV файлу
        parent_uid: UID родительской папки
        config: менеджер конфигурации
    """
    # Создаем логгер
    log_config = LoggerConfig(
        level=getattr(logging, config.get('logging.level', 'INFO')),
        format_string=config.get('logging.format', '%(asctime)s [%(levelname)s]: %(message)s'),
        date_format=config.get('logging.date_format', '%Y-%m-%d %H:%M:%S')
    )
    
    logger_manager = LoggerManager(log_config)
    logger = logger_manager.create_logger(
        "processor",
        log_file_path=config.get('logging.file')
    )
    
    logger.info("=== ЗАПУСК ГЕНЕРАЦИИ RDF/XML ===")
    logger.info(f"Обрабатывается файл: {csv_path}")
    logger.info(f"Родительский UID: {parent_uid}")

    # Парсим CSV
    parser = HierarchyParser(str(csv_path), config.config)
    try:
        paths, external_children, cck_map, parent_uid_map = parser.parse()
        logger.info(f"Загружено путей: {len(paths)}")
    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}", exc_info=True)
        return

    if not paths:
        logger.error("Нет данных для обработки")
        return

    # Генерируем XML
    generator = XMLGenerator(config.config)
    try:
        xml_content = generator.generate(
            paths=paths,
            external_children=external_children,
            parent_uid=parent_uid,
            cck_map=cck_map,
            parent_uid_map=parent_uid_map,
            virtual_containers=set(getattr(parser, 'path_to_uid', {}).keys())
        )
        logger.info("Генерация XML успешна")
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}", exc_info=True)
        return

    # Сохраняем результат
    output_path = csv_path.with_suffix(".xml")
    try:
        if output_path.exists():
            output_path.unlink()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        logger.info(f"Файл сохранён: {output_path}")
        print(f"✅ {csv_path.name} → {output_path.name}")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}", exc_info=True)
        return


def main():
    """Основная функция CLI."""
    # Получаем параметры
    cli_manager = CLIManager()
    folder_uid, csv_dir = cli_manager.get_cli_parameters()
    
    if not folder_uid:
        print("❌ Не указан UID папки.")
        return
    
    # Настраиваем конфигурацию
    config = ConfigManager("config.json")
    
    # Создаем менеджер файлов
    file_manager = FileManager(
        base_directory=csv_dir,
        log_directory=config.get('directories.log', 'logs')
    )
    
    if not file_manager.validate_directory():
        print(f"❌ Папка не найдена: {csv_dir}")
        return
    
    # Получаем список файлов
    csv_files = file_manager.get_csv_files(
        exclude_files=config.get('file_management.exclude_files', ['Sample.csv'])
    )
    
    if not csv_files:
        print("❌ Нет подходящих CSV-файлов.")
        return
    
    print("Будут обработаны:")
    for f in csv_files:
        print(f"  {f}")
    print("-" * 30)
    
    # Создаем директорию логов
    file_manager.create_log_directory()
    
    # Обрабатываем файлы
    for filename in csv_files:
        csv_path = file_manager.base_directory / filename
        process_file(csv_path, folder_uid, config)
    
    cli_manager.print_completion_message()


if __name__ == "__main__":
    main()