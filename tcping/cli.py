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
        "  python main.py ya.ru 443 --timeout 3 --verbose\n"
        "  python main.py --targets google.com:80,github.com:443 --watch\n"
        "  python main.py --targets google.com:80 --knock 1000,2000,3000",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Режимы работы
    parser.add_argument("host", nargs="?", help="Target host (IP or domain name)")

    parser.add_argument(
        "--hosts-file",
        "-f",
        type=Path,
        help='File with list of hosts (one per line: "host port")',
    )

    parser.add_argument("port", nargs="?", type=int, help="Target port (1-65535)")

    parser.add_argument(
        "--targets",
        "-T",
        type=str,
        help='Multiple targets: "host1:port1,host2:port2,..." or file with targets',
    )

    # Port knocking
    parser.add_argument(
        "--knock",
        "-k",
        type=str,
        help='Port knocking sequence: "port1,port2,port3" (comma-separated)',
    )

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

    # Watchdog режим
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watchdog mode - monitor services continuously",
    )

    parser.add_argument(
        "--watch-interval",
        "-wi",
        type=int,
        default=60,
        help="Watchdog check interval in seconds (default: 60)",
    )

    # Email уведомления
    parser.add_argument(
        "--email",
        "-e",
        type=str,
        help="Email address for notifications",
    )

    parser.add_argument(
        "--smtp-server",
        type=str,
        default="smtp.gmail.com",
        help="SMTP server (default: smtp.gmail.com)",
    )

    parser.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        help="SMTP port (default: 587)",
    )

    parser.add_argument(
        "--email-from",
        type=str,
        help="Sender email address",
    )

    parser.add_argument(
        "--email-password",
        type=str,
        help="Sender email password or app password",
    )

    # Параллельное тестирование
    parser.add_argument(
        "--parallel",
        "-p",
        action="store_true",
        help="Run tests in parallel mode",
    )

    parser.add_argument(
        "--max-workers",
        "-mw",
        type=int,
        default=4,
        help="Maximum number of parallel workers (default: 4)",
    )

    # Парсим аргументы
    parsed_args = parser.parse_args(args)

    # Дополнительная валидация
    _validate_args(parsed_args)

    return parsed_args


def _validate_args(args: argparse.Namespace) -> None:
    """Валидация аргументов после парсинга."""
    # Проверка что указан либо хост+порт, либо файл, либо targets
    has_host = args.host is not None
    has_port = args.port is not None
    has_file = args.hosts_file is not None
    has_targets = args.targets is not None

    if not (has_file or has_targets or (has_host and has_port)):
        raise ConfigurationError(
            "Specify host and port, --hosts-file, or --targets"
        )

    # Проверка конфликтов
    if sum([has_file, has_targets, (has_host and has_port)]) > 1:
        raise ConfigurationError(
            "Cannot specify multiple input sources simultaneously"
        )

    if has_host and has_port:
        validate_port(args.port)

    # Проверка режима с файлом
    if args.hosts_file:
        if not args.hosts_file.exists():
            raise HostsFileError(f"Hosts file not found: {args.hosts_file}")
        if not args.hosts_file.is_file():
            raise HostsFileError(f"Path is not a file: {args.hosts_file}")

    # Проверка targets
    if has_targets:
        if args.targets.endswith('.txt'):
            target_path = Path(args.targets)
            if not target_path.exists():
                raise HostsFileError(f"Targets file not found: {target_path}")
        # Валидация будет в parse_targets

    # Парсим port knocking
    if args.knock:
        try:
            ports = [int(p.strip()) for p in args.knock.split(',')]
            for port in ports:
                validate_port(port)
            args.knock_ports = ports
        except ValueError:
            raise ConfigurationError(f"Invalid knock ports: {args.knock}")

    # Проверка email настроек
    if args.email:
        if not args.email_from or not args.email_password:
            raise ConfigurationError(
                "Email notifications require --email-from and --email-password"
            )

    # Проверка числовых параметров
    validate_count(args.count)
    validate_interval(args.interval)
    validate_timeout(args.timeout)


def parse_targets(targets_str: str) -> List[Tuple[str, int]]:
    """Парсит строку с несколькими целями."""
    targets = []

    if targets_str.endswith('.txt'):
        # Чтение из файла
        path = Path(targets_str)
        if not path.exists():
            raise HostsFileError(f"Targets file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                target = _parse_target_line(line, line_num)
                if target:
                    targets.append(target)
    else:
        # Парсим строку с целями через запятую
        parts = targets_str.split(',')
        for part in parts:
            if ':' not in part:
                raise ConfigurationError(f"Invalid target format: {part}")
            host, port_str = part.split(':', 1)
            try:
                port = int(port_str)
                validate_port(port)
                targets.append((host, port))
            except ValueError:
                raise ConfigurationError(f"Invalid port in target: {part}")

    if not targets:
        raise ConfigurationError("No valid targets specified")

    return targets


def _parse_target_line(line: str, line_num: int) -> Optional[Tuple[str, int]]:
    """Парсит одну строку из файла целей."""
    # Формат: host port или host:port
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
        return (host, port)
    except ValueError:
        raise HostsFileError(f"Invalid port at line {line_num}: {port_str}")


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
