"""
Модуль генерации RDF/XML по иерархическим данным.

Ответственность:
- Построение XML на основе путей, UID, ККС и виртуальных контейнеров
- Поддержка CIM16, включая AssetContainer и GenericPSR
- Генерация UUID, управление иерархией и ссылками

Новые правила для ККС:
- AssetContainer: <me:IdentifiedObject.mRIDStr>{ККС}</me:IdentifiedObject.mRIDStr>
- GenericPSR: <rh:PowerSystemResource.ccsCode>{ККС}</rh:PowerSystemResource.ccsCode>
"""

from typing import List, Tuple, Dict, Set, Any, Optional
from uuid import uuid4
import logging
from collections import defaultdict
from queue import Queue


class XMLGenerator:
    """
    Генератор RDF/XML для иерархии оборудования.

    Преобразует структуру путей в XML с учётом:
    - Пространств имён
    - Виртуальных контейнеров (через ParentObject)
    - ККС (по новым правилам)
    - Связей ParentObject и ChildObjects
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Инициализация генератора XML.

        Args:
            config (dict, optional): Конфигурация генерации.
            logger (logging.Logger, optional): Логгер для вывода сообщений.
        """
        self.config = config or {}
        xml_config = self.config.get("xml", {})
        self.logger = logger or logging.getLogger(__name__)

        self.namespaces = xml_config.get("namespaces", {
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "md": "http://iec.ch/TC57/61970-552/ModelDescription/1#",
            "cim": "http://iec.ch/TC57/2014/CIM-schema-cim16#",
            "cim17": "http://iec.ch/TC57/CIM100#",
            "me": "http://monitel.com/2014/schema-cim16#",
            "rf": "http://gost.ru/2019/schema-cim01#",
            "rh": "http://rushydro.ru/2015/schema-cim16#",
            "so": "http://so-ups.ru/2015/schema-cim16#"
        })

        model = xml_config.get("model", {})
        self.model_id = f"#_{model.get('id', '00000000-0000-0000-0000-000000000000')}"
        self.model_created = model.get(
            'created', '2025-01-01T00:00:00.0000000Z')
        self.model_version = model.get('version', 'ver:1.0.0')
        self.model_name = model.get('name', 'CIM16')

        self.logger.info("XMLGenerator инициализирован")

    def _generate_id(self, path: Tuple[str, ...]) -> str:
        """
        Генерирует уникальный ID на основе UUID4.

        Args:
            path (tuple): Путь к объекту.

        Returns:
            str: ID в формате "#_uuid".
        """
        uid = uuid4()
        self.logger.debug(f"Генерация UUID4 для пути {path}: {uid}")
        return f"#_{uid}"

    def generate(
        self,
        paths: List[Tuple[str, ...]],
        external_children: Dict[Tuple[str, ...], List[str]],
        parent_uid: str,
        cck_map: Dict[Tuple[str, ...], str],
        parent_uid_map: Dict[Tuple[str, ...], str],
        virtual_containers: Optional[Set[Tuple[str, ...]]] = None
    ) -> Tuple[str, Dict[Tuple[str, ...], str]]:
        """
        Основной метод генерации XML.
        Returns:
            tuple: (xml_content: str, path_to_generated_id: Dict[Tuple[str, ...], str])
        """
        self.logger.info("Начало генерации XML")
        if not paths:
            raise ValueError("Нет данных для генерации")

        cck_map = cck_map or {}
        parent_uid_map = parent_uid_map or {}
        virtual_containers = virtual_containers or set()

        # --- Собираем ВСЕ уникальные узлы из всех путей ---
        all_nodes = set()
        for path in paths:
            for i in range(1, len(path) + 1):
                all_nodes.add(path[:i])

        # --- Построение дерева (восстанавливаем children_map и parent_map) ---
        children_map = defaultdict(list)
        parent_map = {}
        for path in paths:
            for i in range(1, len(path)):
                parent = tuple(path[:i])
                child = tuple(path[:i+1])
                if parent in all_nodes and child in all_nodes:
                    if child not in children_map[parent]:
                        children_map[parent].append(child)
                    parent_map[child] = parent

        # Генерация ID для ВСЕХ узлов
        id_map = {node: self._generate_id(node) for node in all_nodes}

        # --- Генерация XML ---
        lines = []
        lines.append('<?xml version="1.0" encoding="utf-8"?>')
        lines.append('<?iec61970-552 version="2.0"?>')
        lines.append('<?floatExporter 1?>')

        # Открывающий тег RDF
        rdf_open = '<rdf:RDF'
        for prefix, uri in self.namespaces.items():
            rdf_open += f' xmlns:{prefix}="{uri}"'
        rdf_open += '>'
        lines.append(rdf_open)

        # FullModel
        lines.append(f'  <md:FullModel rdf:about="{self.model_id}">')
        lines.append(
            f'    <md:Model.created>{self.model_created}</md:Model.created>')
        lines.append(
            f'    <md:Model.version>{self.model_version}</md:Model.version>')
        lines.append(f'    <me:Model.name>{self.model_name}</me:Model.name>')
        lines.append('  </md:FullModel>')

        # Генерация объектов
        processed = set()
        q = Queue()
        for path in paths:
            q.put(path)

        while not q.empty():
            current = q.get()
            if current in processed:
                continue
            processed.add(current)
            current_id = id_map[current]
            is_leaf = (
                current not in children_map or not children_map[current])
            if len(current) == 1:
                element_type = "cim:AssetContainer"
            elif is_leaf:
                element_type = "me:GenericPSR"
            else:
                element_type = "cim:AssetContainer"

            lines.append(f'  <{element_type} rdf:about="{current_id}">')
            lines.append(
                f'    <cim:IdentifiedObject.name>{current[-1]}</cim:IdentifiedObject.name>')

            # ParentObject
            if len(current) == 1:
                parent_resource = parent_uid
            else:
                if current in parent_uid_map:
                    parent_resource = f"#_{parent_uid_map[current]}"
                elif current in parent_map and parent_map[current] in id_map:
                    parent_resource = id_map[parent_map[current]]
                else:
                    parent_resource = parent_uid
            lines.append(
                f'    <me:IdentifiedObject.ParentObject rdf:resource="#_{parent_resource}" />')

            # Связи Assets
            if element_type == "cim:AssetContainer":
                lines.append(
                    f'    <cim:Asset.AssetContainer rdf:resource="#_{parent_resource}" />')
            elif element_type == "me:GenericPSR":
                lines.append(
                    f'    <cim:PowerSystemResource.Assets rdf:resource="#_{parent_resource}" />')

            # Запись ККС
            if current in cck_map and cck_map[current]:
                kks_code = cck_map[current]
                if element_type == "cim:AssetContainer":
                    lines.append(
                        f'    <me:IdentifiedObject.mRIDStr>{kks_code}</me:IdentifiedObject.mRIDStr>')
                elif element_type == "me:GenericPSR":
                    lines.append(
                        f'    <rh:PowerSystemResource.ccsCode>{kks_code}</rh:PowerSystemResource.ccsCode>')

            # ChildObjects (только для AssetContainer)
            if element_type == "cim:AssetContainer":
                added_children = set()
                if current in children_map:
                    for child in children_map[current]:
                        if child in id_map:
                            child_id = id_map[child]
                            if child_id not in added_children:
                                lines.append(
                                    f'    <me:IdentifiedObject.ChildObjects rdf:resource="#_{child_id}" />')
                                added_children.add(child_id)
                                q.put(child)
            lines.append(f'  </{element_type}>')

        lines.append('</rdf:RDF>')
        self.logger.info("Генерация XML завершена")

        # Возвращаем XML и маппинг ВСЕХ узлов
        xml_content = '\n'.join(lines)
        path_to_generated_id = {
            path: id_str for path, id_str in id_map.items()}

        return xml_content, path_to_generated_id
