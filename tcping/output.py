"""Форматирование и вывод результатов."""

import json
import sys
from typing import List, Optional, TextIO
from datetime import datetime

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


def format_duration(seconds: float) -> str:
    # Форматирует длительность в миллисекундах.
    if seconds is None:
        return "N/A"
    milliseconds = seconds * 1000
    return f"{milliseconds:.2f}ms"


def print_result(result: PingResult, file: TextIO = None) -> None:
    # Выводит результат одного пинга.
    if JSON_MODE:
        return  # В JSON режиме результаты выводятся только в конце через print_stats

    if file is None:
        file = sys.stdout

    if result.success:
        time_str = format_duration(result.duration)
        line = f"Connected to {result.host}:{result.port} - time={time_str}"
    else:
        line = f"Failed to connect to {result.host}:{result.port} - {result.error_message}"

        # В отладочном режиме добавляем timestamp
    if DEBUG_MODE:
        timestamp = result.timestamp.strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] {line}"

    print(line, file=file)


def print_stats(stats: Stats, file: TextIO = None) -> None:
    # Выводит статистику по серии пингов.
    if file is None:
        file = sys.stdout

    if JSON_MODE:
        json_output = generate_json(stats, stats.results if VERBOSE_MODE else None)
        print(json_output, file=file)
        return

        # Обычный текстовый вывод
    print(file=file)
    print(f"--- {stats.host}:{stats.port} ping statistics ---", file=file)
    print(f"{stats.sent} packets transmitted, {stats.received} received, "
          f"{stats.loss_percent:.1f}% loss", file=file)

    if stats.received > 0:
        min_str = format_duration(stats.min_time)
        avg_str = format_duration(stats.avg_time)
        max_str = format_duration(stats.max_time)

        print(f"round-trip min/avg/max = {min_str}/{avg_str}/{max_str}", file=file)

        # В verbose режиме добавляем стандартное отклонение
        if VERBOSE_MODE and stats.std_dev is not None:
            std_str = format_duration(stats.std_dev)
            print(f"std dev = {std_str}", file=file)


def generate_json(stats: Stats, results: Optional[List[PingResult]] = None) -> str:
    # Генерирует JSON представление статистики и опционально результатов.
    output = {
        "host": stats.host,
        "port": stats.port,
        "statistics": {
            "sent": stats.sent,
            "received": stats.received,
            "lost": stats.lost,
            "loss_percent": round(stats.loss_percent, 2),
            "min_time_ms": round(stats.min_time * 1000, 2) if stats.min_time is not None else None,
            "avg_time_ms": round(stats.avg_time * 1000, 2) if stats.avg_time is not None else None,
            "max_time_ms": round(stats.max_time * 1000, 2) if stats.max_time is not None else None,
            "std_dev_ms": round(stats.std_dev * 1000, 2) if stats.std_dev is not None else None,
        }
    }

    # Если есть результаты и verbose режим – добавляем их
    if results and VERBOSE_MODE:
        output["results"] = []
        for r in results:
            result_dict = {
                "success": r.success,
                "timestamp": r.timestamp.isoformat(),
            }
            if r.success:
                result_dict["duration_ms"] = round(r.duration * 1000, 2)
            else:
                result_dict["error"] = r.error_message
            output["results"].append(result_dict)

    return json.dumps(output, indent=2, ensure_ascii=False)


def print_legend() -> None:
    # Выводит легенду обозначений при verbose режиме
    if VERBOSE_MODE and not JSON_MODE:
        print("\nLegend:")
        print("  ✓ - successful connection")
        print("  ✗ - failed connection")
        print("  ! - timeout")
