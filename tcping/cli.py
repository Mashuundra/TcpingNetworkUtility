"""Парсинг командной строки."""

import argparse
from typing import List, Optional, Tuple
from pathlib import Path


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Парсит аргументы командной строки.

    Args:
        args: Список аргументов (None = sys.argv[1:])

    Returns:
        Namespace с атрибутами:
        - host: str | None - целевой хост
        - port: int | None - целевой порт
        - hosts_file: Path | None - путь к файлу с хостами
        - count: int - количество попыток (по умолчанию 4)
        - interval: float - интервал между попытками в секундах (по умолчанию 1.0)
        - timeout: float - таймаут соединения в секундах (по умолчанию 5.0)
        - debug: bool - режим отладки
        - json: bool - вывод в JSON формате
        - verbose: bool - подробный вывод

    Raises:
        ConfigurationError: При конфликтующих или некорректных параметрах
        InvalidPortError: При невалидном порте
        HostsFileError: При проблемах с файлом хостов
    """
    pass


def validate_port(port: int) -> None:
    """
    Проверяет корректность порта.

    Args:
        port: Номер порта

    Raises:
        InvalidPortError: Если порт не в диапазоне 1-65535
    """
    pass


def validate_count(count: int) -> None:
    """
    Проверяет количество попыток.

    Args:
        count: Количество попыток

    Raises:
        ConfigurationError: Если count < 1
    """
    pass


def validate_interval(interval: float) -> None:
    """
    Проверяет интервал между попытками.

    Args:
        interval: Интервал в секундах

    Raises:
        ConfigurationError: Если interval <= 0
    """
    pass


def parse_hosts_file(file_path: Path) -> List[Tuple[str, int]]:
    """
    Парсит файл со списком хостов.

    Формат файла: каждая строка содержит "хост порт"
    Строки начинающиеся с # игнорируются.

    Args:
        file_path: Путь к файлу

    Returns:
        List[Tuple[str, int]]: Список пар (хост, порт)

    Raises:
        HostsFileError: Если файл не найден, нет прав доступа или некорректный формат
    """
    pass