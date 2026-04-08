"""Парсинг командной строки."""

import argparse
from pathlib import Path
from typing import List, Optional, Tuple

from tcping.exceptions import ConfigurationError, InvalidPortError, HostsFileError


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Парсит аргументы командной строки.

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
    parser = argparse.ArgumentParser(
        description='TCP ping utility - check TCP port availability',
        epilog='Examples:\n'
               '  python main.py google.com 80\n'
               '  python main.py google.com 80 --count 10 --interval 0.5\n'
               '  python main.py --hosts-file hosts.txt --json\n'
               '  python main.py ya.ru 443 --timeout 3 --verbose',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Режимы работы (группа mutex) пользователь может выбрать только один вариант из нескольких
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        'host',
        nargs='?',
        help='Target host (IP or domain name)'
    )

    group.add_argument(
        '--hosts-file',
        '-f',
        type=Path,
        help='File with list of hosts (one per line: "host port")'
    )

    parser.add_argument(
        'port',
        nargs='?',
        type=int,
        help='Target port (1-65535)'
    )

    # Опции
    parser.add_argument(
        '--count',
        '-c',
        type=int,
        default=4,
        help='Number of ping attempts (default: 4)'
    )

    parser.add_argument(
        '--interval',
        '-i',
        type=float,
        default=1.0,
        help='Interval between attempts in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--timeout',
        '-t',
        type=float,
        default=5.0,
        help='Connection timeout in seconds (default: 5.0)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with detailed error messages'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output with detailed information'
    )

    # Парсим аргументы
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # argparse вызвал sys.exit() при ошибке
        raise ConfigurationError("Invalid command line arguments")

    # Валидация
    _validate_args(parsed_args)

    return parsed_args


def _validate_args(args: argparse.Namespace) -> None:
    """Валидация аргументов после парсинга."""

    # Проверка режима с одним хостом
    if args.host and args.port is None:
        raise ConfigurationError("Port is required when specifying host")

    if args.host and args.port:
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
    """
    Проверяет корректность порта.

    Args:
        port: Номер порта

    Raises:
        InvalidPortError: Если порт не в диапазоне 1-65535
    """
    if not isinstance(port, int):
        raise InvalidPortError(f"Port must be an integer, got {type(port).__name__}")

    if port < 1 or port > 65535:
        raise InvalidPortError(f"Port must be between 1 and 65535, got {port}")


def validate_count(count: int) -> None:
    """
    Проверяет количество попыток.

    Args:
        count: Количество попыток

    Raises:
        ConfigurationError: Если count < 1
    """
    if count < 1:
        raise ConfigurationError(f"Count must be at least 1, got {count}")


def validate_interval(interval: float) -> None:
    """
    Проверяет интервал между попытками.

    Args:
        interval: Интервал в секундах

    Raises:
        ConfigurationError: Если interval <= 0
    """
    if interval <= 0:
        raise ConfigurationError(f"Interval must be greater than 0, got {interval}")


def validate_timeout(timeout: float) -> None:
    """
    Проверяет таймаут соединения.

    Args:
        timeout: Таймаут в секундах

    Raises:
        ConfigurationError: Если timeout <= 0
    """
    if timeout <= 0:
        raise ConfigurationError(f"Timeout must be greater than 0, got {timeout}")


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
    if not file_path.exists():
        raise HostsFileError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise HostsFileError(f"Not a file: {file_path}")

    hosts = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # нумерует строки при чтении файла, начиная с 1
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue

                # Разбираем строку: "host port" или "host:port" или "host port"
                parts = line.split()
                if len(parts) == 2:
                    host, port_str = parts
                elif len(parts) == 1 and ':' in parts[0]:
                    host, port_str = parts[0].split(':', 1)
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
