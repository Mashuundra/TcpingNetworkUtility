"""Форматирование и вывод результатов."""

from typing import List, Optional, TextIO
from tcping.models import PingResult, Stats


# Глобальные настройки вывода
VERBOSE_MODE = False
JSON_MODE = False
DEBUG_MODE = False


def set_output_mode(verbose: bool = False, json_mode: bool = False, debug: bool = False) -> None:
    """Устанавливает глобальные режимы вывода."""
    global VERBOSE_MODE, JSON_MODE, DEBUG_MODE
    VERBOSE_MODE = verbose
    JSON_MODE = json_mode
    DEBUG_MODE = debug


def print_result(result: PingResult, file: TextIO = None) -> None:
    """
    Выводит результат одного пинга.

    Форматы вывода:
    - Обычный режим: "Connected to google.com:80 - time=45.23ms"
    - Режим ошибки: "Failed to connect to google.com:80 - Connection refused"
    - JSON режим: НЕ ИСПОЛЬЗОВАТЬ (только print_stats для JSON)
    - DEBUG режим: Добавляет timestamp и внутреннюю информацию

    Args:
        result: Результат пинга
        file: Файловый объект для вывода (None = sys.stdout)
    """
    pass


def print_stats(stats: Stats, file: TextIO = None) -> None:
    """
    Выводит статистику по серии пингов.

    Форматы вывода:
    - Обычный режим: Таблица или текстовая сводка
      --- google.com:80 ping statistics ---
      4 packets transmitted, 3 received, 25% loss
      round-trip min/avg/max = 10.2/15.5/23.1 ms

    - JSON режим: Выводит JSON представление статистики
      {"host": "google.com", "port": 80, "sent": 4, ...}

    Args:
        stats: Статистика
        file: Файловый объект для вывода (None = sys.stdout)
    """
    pass


def generate_json(stats: Stats, results: Optional[List[PingResult]] = None) -> str:
    """
    Генерирует JSON представление статистики и опционально результатов.

    Формат JSON:
    {
        "stats": {...},
        "results": [...]  # если verbose режим
    }

    Args:
        stats: Статистика
        results: Список всех результатов (опционально)

    Returns:
        str: JSON строка
    """
    pass


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в миллисекундах.

    Args:
        seconds: Длительность в секундах

    Returns:
        str: Отформатированная строка (например "45.23ms")
    """
    pass


def print_legend() -> None:
    """Выводит легенду обозначений при verbose режиме."""
    pass