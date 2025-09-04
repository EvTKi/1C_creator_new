"""
Управление файлами и директориями.
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

class FileManager:
    """Класс для управления файлами и директориями."""
    
    def __init__(self, base_directory: str = ".", log_directory: str = "logs"):
        """
        Инициализация менеджера файлов.

        Args:
            base_directory: базовая директория для операций
            log_directory: директория для логов
        """
        self.base_directory = Path(base_directory).resolve()
        self.log_directory = log_directory 
    
    def get_csv_files(self, exclude_files: Optional[List[str]] = None) -> List[Path]:
        """
        Получает список CSV файлов в базовой директории.

        Args:
            exclude_files: список файлов для исключения

        Returns:
            List[str]: список имен CSV файлов
        """
        if exclude_files is None:
            exclude_files = ["Sample.csv"]
        exclude_files_lower = [f.lower() for f in exclude_files]
        csv_files = []
        for file_path in self.base_directory.iterdir():
            if (file_path.is_file() and
                file_path.suffix.lower() == '.csv' and
                file_path.name.lower() not in exclude_files_lower):
                csv_files.append(file_path)  # ← Path, а не str
        return sorted(csv_files)
    
    def create_log_directory(self) -> str:
        """
        Создает директорию для логов.

        Returns:
            str: путь к директории логов
        """
        log_dir = self.base_directory / self.log_directory
        log_dir.mkdir(exist_ok=True)
        return str(log_dir)
    
    def get_file_paths(self, filename: str) -> Tuple[Path, Path]:
        """
        Получает полные пути к входному и выходному файлам.

        Args:
            filename: имя файла

        Returns:
            tuple: (путь_к_CSV, путь_к_XML)
        """
        csv_path = self.base_directory / filename
        xml_path = self.base_directory / f"{csv_path.stem}.xml"
        return csv_path, xml_path
    
    def validate_directory(self) -> bool:
        """
        Проверяет существование базовой директории.

        Returns:
            bool: True если директория существует
        """
        return self.base_directory.exists() and self.base_directory.is_dir()
    
    def get_log_path(self, csv_filename: str) -> Path:
        """
        Получает путь к лог-файлу для конкретного CSV файла.

        Args:
            csv_filename: имя CSV файла

        Returns:
            str: путь к лог-файлу
        """
        log_dir = self.base_directory / self.log_directory
        log_dir.mkdir(exist_ok=True)
        
        basename = Path(csv_filename).stem
        date_str = datetime.now().strftime("%Y-%m-%d")
        return log_dir / f"{basename}_{date_str}.log"


class CLIManager:
    """Класс для управления командной строкой."""
    
    @staticmethod
    def get_cli_parameters() -> Tuple[str, str]:
        """
        Получает параметры из командной строки или запрашивает у пользователя.

        Returns:
            tuple: (folder_uid, csv_directory)
        """
        print("="*50)
        print("Пакетный конвертер CSV ➔ XML (поточн. генерация XML)")
        
        if len(sys.argv) >= 3:
            folder_uid = sys.argv[1]
            csv_dir = sys.argv[2]
        else:
            folder_uid = input('Введите UID папки для ролей: ').strip()
            csv_dir = input('Укажите папку с CSV (или . для текущей): ').strip() or '.'
        
        return folder_uid, csv_dir
    
    @staticmethod
    def validate_and_list_files(file_manager: FileManager) -> List[Path]:
        """
        Проверяет директорию и возвращает список файлов.

        Args:
            file_manager: экземпляр FileManager

        Returns:
            List[Path]: список файлов или пустой список если ошибка
        """
        if not file_manager.validate_directory():
            print(f"Папка не найдена: {file_manager.base_directory}")
            return []
        
        csv_files = file_manager.get_csv_files()
        if not csv_files:
            print("Нет подходящих .csv файлов")
            return []
        
        print("Будут обработаны файлы:")
        for f in csv_files:
            print("  ", f)
        print("-"*25)
        
        return csv_files
    
    @staticmethod
    def print_completion_message():
        """Выводит сообщение о завершении работы."""
        print("Готово.")


# Фабричные функции для удобства использования
def create_file_manager(base_directory: str = ".", log_directory: str = "logs") -> FileManager:
    """Создает менеджер файлов."""
    return FileManager(base_directory, log_directory)

def create_cli_manager() -> CLIManager:
    """Создает менеджер CLI."""
    return CLIManager()