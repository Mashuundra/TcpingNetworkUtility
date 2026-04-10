"""Парсинг командной строки."""

import argparse
from pathlib import Path
from typing import List, Optional, Tuple

from tcping.exceptions import (ConfigurationError, HostsFileError,
                               InvalidPortError)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="TCP ping utility - check TCP port availability",
        epilog="Examples:\n"
        "  python main.py google.com 80\n"
        "  python main.py google.com 80 --count 10 --interval 0.5\n"
        "  python main.py --hosts-file hosts.txt --json\n"
        "  python main.py ya.ru 443 --timeout 3 --verbose",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Режимы работы - НЕ делаем группу required, чтобы argparse сам обрабатывал ошибки
    parser.add_argument("host", nargs="?", help="Target host (IP or domain name)")

    parser.add_argument(
        "--hosts-file",
        "-f",
        type=Path,
        help='File with list of hosts (one per line: "host port")',
    )

    parser.add_argument("port", nargs="?", type=int, help="Target port (1-65535)")

    # Опции
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=4,
        help="Number of ping attempts (default: 4)",
    )

    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=1.0,
        help="Interval between attempts in seconds (default: 1.0)",
    )

    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=5.0,
        help="Connection timeout in seconds (default: 5.0)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed error messages",
    )

    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with detailed information",
    )

    # Парсим аргументы - пусть argparse сам обрабатывает ошибки
    parsed_args = parser.parse_args(args)

    # Дополнительная валидация после парсинга
    _validate_args(parsed_args)

    return parsed_args


def _validate_args(args: argparse.Namespace) -> None:
    """Валидация аргументов после парсинга."""
    # Проверка что указан либо хост+порт, либо файл
    has_host = args.host is not None
    has_port = args.port is not None
    has_file = args.hosts_file is not None

    if not has_file and not (has_host and has_port):
        raise ConfigurationError("Either specify host and port, or use --hosts-file")

    # Проверка что не указаны оба режима одновременно
    if has_file and (has_host or has_port):
        raise ConfigurationError("Cannot specify both --hosts-file and host/port")

    if has_host and has_port:
        validate_port(args.port)

    # Проверка режима с файлом
    if args.hosts_file:
        if not args.hosts_file.exists():
            raise HostsFileError(f"Hosts file not found: {args.hosts_file}")
        if not args.hosts_file.is_file():
            raise HostsFileError(f"Path is not a file: {args.hosts_file}")

    # Проверка числовых параметров
    validate_count(args.count)
    validate_interval(args.interval)
    validate_timeout(args.timeout)


def validate_port(port: int) -> None:
    """Проверяет корректность порта."""
    if not isinstance(port, int):
        raise InvalidPortError(f"Port must be an integer, got {type(port).__name__}")

    if port < 1 or port > 65535:
        raise InvalidPortError(f"Port must be between 1 and 65535, got {port}")


def validate_count(count: int) -> None:
    """Проверяет количество попыток."""
    if count < 1:
        raise ConfigurationError(f"Count must be at least 1, got {count}")


def validate_interval(interval: float) -> None:
    """Проверяет интервал между попытками."""
    if interval <= 0:
        raise ConfigurationError(f"Interval must be greater than 0, got {interval}")


def validate_timeout(timeout: float) -> None:
    """Проверяет таймаут соединения."""
    if timeout <= 0:
        raise ConfigurationError(f"Timeout must be greater than 0, got {timeout}")


def parse_hosts_file(file_path: Path) -> List[Tuple[str, int]]:
    """Парсит файл со списком хостов."""
    if not file_path.exists():
        raise HostsFileError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise HostsFileError(f"Not a file: {file_path}")

    hosts = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) == 2:
                    host, port_str = parts
                elif len(parts) == 1 and ":" in parts[0]:
                    host, port_str = parts[0].split(":", 1)
                else:
                    raise HostsFileError(
                        f"Invalid format at line {line_num}: {line}\n"
                        f"Expected: 'host port' or 'host:port'"
                    )

                try:
                    port = int(port_str)
                    validate_port(port)
                    hosts.append((host, port))
                except ValueError:
                    raise HostsFileError(
                        f"Invalid port at line {line_num}: {port_str}\n"
                        f"Port must be an integer"
                    )
                except InvalidPortError as e:
                    raise HostsFileError(f"Invalid port at line {line_num}: {e}")

    except PermissionError:
        raise HostsFileError(f"Permission denied: {file_path}")
    except OSError as e:
        raise HostsFileError(f"Error reading file {file_path}: {e}")

    if not hosts:
        raise HostsFileError(f"No valid hosts found in {file_path}")

    return hosts
