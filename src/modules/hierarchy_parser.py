"""
Парсер иерархии с поддержкой внешних UID как виртуальных контейнеров.

Объект с uid НЕ создаётся, но его uid используется как ParentObject для детей.
Логирование делегируется внешнему логгеру для согласованности с системой.
"""

from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import csv
import logging
from collections import defaultdict


class HierarchyParser:
    """
    Парсер иерархических данных из CSV с поддержкой виртуальных контейнеров.

    Виртуальные контейнеры (строки с uid) не порождают объекты в XML,
    но их uid используется как родитель для дочерних элементов.
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Инициализация парсера иерархии.

        Args:
            file_path (str, optional): Путь к CSV-файлу.
            config (dict, optional): Конфигурация (например, имена колонок).
            logger (logging.Logger, optional): Логгер для вывода сообщений.
                Если не указан — используется стандартный.
        """
        self.file_path = Path(file_path) if file_path else None
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.paths_with_uid = set()
        self.path_to_uid = {}  # путь → uid (виртуальные контейнеры)

    def _normalize_path(self, path: Tuple[str, ...]) -> Tuple[str, ...]:
        """
        Нормализует путь, удаляя повторяющиеся последовательные элементы.

        Пример: ('A', 'B', 'B', 'C') -> ('A', 'B', 'C')

        Args:
            path (tuple): Кортеж с элементами пути.

        Returns:
            tuple: Нормализованный путь.
        """
        if not path:
            return path
        normalized = [path[0]]
        for i in range(1, len(path)):
            if path[i] != normalized[-1]:
                normalized.append(path[i])
        return tuple(normalized)

    def _read_lines(self) -> List[Tuple[str, str, str]]:
        """
        Читает строки из CSV-файла или возвращает тестовые данные.

        Returns:
            list: Список кортежей (путь, uid, cck_code).

        Raises:
            Exception: Если не удалось прочитать файл ни в одной кодировке.
        """
        if self.file_path and self.file_path.exists():
            self.logger.info(f"Чтение данных из файла: {self.file_path}")

            # Получаем имена колонок из конфига
            csv_headers = self.config.get("csv", {}).get("headers", {})
            path_header = csv_headers.get("path", "НаименованиеКонтейнераОборудования")
            uid_header = csv_headers.get("uid", "uid")
            cck_header = csv_headers.get("cck_code", "ОбъектРемонтаКодККС")

            encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']
            data = []
            last_error = None

            for encoding in encodings:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        sample = f.read(1024)
                        f.seek(0)
                        delimiter = ';' if ';' in sample else '\t' if '\t' in sample else ','

                        reader = csv.DictReader(f, delimiter=delimiter)

                        if path_header not in reader.fieldnames:
                            raise ValueError(f"В CSV отсутствует поле пути: '{path_header}'")

                        for i, row in enumerate(reader):
                            path = row.get(path_header, '').strip()
                            uid = row.get(uid_header, '').strip()
                            cck_code = row.get(cck_header, '').strip() if cck_header else ""

                            if path:
                                parts = tuple(p.strip() for p in path.split('\\') if p.strip())
                                normalized_parts = self._normalize_path(parts)
                                data.append((path, uid, cck_code))

                    self.logger.debug(f"Прочитано {len(data)} строк из файла")
                    return data

                except UnicodeDecodeError as e:
                    last_error = e
                    self.logger.debug(f"Не удалось прочитать в кодировке {encoding}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Ошибка чтения файла: {e}", exc_info=True)
                    raise

            if last_error:
                msg = f"Не удалось прочитать файл в известных кодировках: {encodings}"
                self.logger.error(msg)
                raise Exception(msg)
            else:
                raise Exception("Не удалось прочитать файл: неизвестная ошибка")

        else:
            self.logger.warning("Файл не найден. Используются тестовые данные.")
            return [
                ("A\\", "", ""),
                ("A\\B", "123-456", ""),
                ("A\\B\\C", "", ""),
                ("A\\B\\C\\D", "", ""),
            ]

    def parse(self) -> Tuple[
        List[Tuple[str, ...]],  # paths для создания
        Dict[Tuple[str, ...], List[str]],  # external_children: parent → [uid]
        Dict[Tuple[str, ...], str],  # cck_map
        Dict[Tuple[str, ...], str]  # parent_uid_map: child_path → parent_uid
    ]:
        """
        Парсит CSV и возвращает структурированные данные для генерации XML.

        Returns:
            tuple: (paths_to_create, external_children, cck_map, parent_uid_map)
        """
        lines = self._read_lines()

        path_to_uid = {}
        path_to_cck = {}
        all_paths = []

        for line, uid, cck_code in lines:
            parts = tuple(p.strip() for p in line.split('\\') if p.strip())
            normalized_parts = self._normalize_path(parts)
            if normalized_parts:
                all_paths.append(normalized_parts)
                if uid:
                    path_to_uid[normalized_parts] = uid
                if cck_code:
                    path_to_cck[normalized_parts] = cck_code

        self.path_to_uid = path_to_uid
        self.logger.debug(f"Найдено виртуальных контейнеров: {len(path_to_uid)}")

        paths_to_create = set()
        external_children = defaultdict(list)
        parent_uid_map = {}

        # 1. Добавляем все пути
        for path in all_paths:
            paths_to_create.add(path)

        # 2. Добавляем предков для полной иерархии
        for path in list(paths_to_create):
            for i in range(1, len(path)):
                ancestor = path[:i]
                normalized_ancestor = self._normalize_path(ancestor)
                if normalized_ancestor not in path_to_uid:
                    paths_to_create.add(normalized_ancestor)

        # 3. Обрабатываем виртуальные контейнеры
        for virtual_path, uid in path_to_uid.items():
            if len(virtual_path) > 1:
                parent_path = virtual_path[:-1]
                normalized_parent = self._normalize_path(parent_path)
                if normalized_parent not in path_to_uid:
                    external_children[normalized_parent].append(uid)

            for child_path in all_paths:
                if (len(child_path) == len(virtual_path) + 1 and
                        child_path[:len(virtual_path)] == virtual_path):
                    parent_uid_map[child_path] = uid

        # 4. Удаляем виртуальные контейнеры из создания
        for virtual_path in path_to_uid.keys():
            paths_to_create.discard(virtual_path)

        self.logger.info(f"Окончательно путей для создания: {len(paths_to_create)}")
        return (
            sorted(list(paths_to_create)),
            dict(external_children),
            path_to_cck,
            parent_uid_map
        )