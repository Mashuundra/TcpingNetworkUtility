"""
Точка входа в приложение tcping.
Связывает парсинг аргументов (cli), сетевую логику (core) и вывод (output).
Обрабатывает глобальные ошибки, переключает отладочный режим по флагу --debug.
"""

import sys
import time
import traceback
from typing import List, Tuple

from tcping.cli import parse_args
from tcping.core import TCPinger
from tcping.exceptions import ConfigurationError, HostsFileError, TCpingError
from tcping.models import PingResult, Stats
from tcping.output import print_result, print_stats, set_output_mode


def process_single_target_stream(host: str, port: int, args, knock_ports: List[int] = None) -> Tuple[
    List[PingResult], Stats]:
    """Выполняет серию пингов с мгновенным выводом каждой попытки."""
    pinger = TCPinger(timeout=args.timeout)

    def stream_callback(result: PingResult) -> None:
        if not args.json:
            print_result(result)

    results = pinger.ping_many(
        host, port,
        count=args.count,
        interval=args.interval,
        knock_ports=knock_ports,
        stream_callback=stream_callback
    )
    stats = Stats.from_results(host, port, results)
    return results, stats


def process_single_target(host: str, port: int, args, knock_ports: List[int] = None) -> Tuple[List[PingResult], Stats]:
    """Выполняет серию пингов без мгновенного вывода (для JSON)."""
    pinger = TCPinger(timeout=args.timeout)
    results = pinger.ping_many(host, port, count=args.count, interval=args.interval, knock_ports=knock_ports)
    stats = Stats.from_results(host, port, results)
    return results, stats


def process_packet_mode(args) -> None:
    """Пакетный режим: обрабатывает несколько целей из файла."""
    from tcping.cli import parse_hosts_file

    try:
        targets = parse_hosts_file(args.hosts_file)
    except HostsFileError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if not targets:
        print("Ошибка: файл не содержит корректных записей", file=sys.stderr)
        sys.exit(1)

    knock_ports = getattr(args, 'knock', None)

    for host, port in targets:
        if not args.json:
            print(f"\n--- {host}:{port} tcping statistics ---")

        try:
            if not args.json:
                results, stats = process_single_target_stream(host, port, args, knock_ports)
                print_stats(stats)
            else:
                results, stats = process_single_target(host, port, args, knock_ports)
                from tcping.output import generate_json
                print(generate_json(stats, results if args.verbose else None))

        except Exception as e:
            print(f"Ошибка при обработке {host}:{port}: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            continue


def process_targets_mode(args) -> None:
    """Режим нескольких IP/портов из командной строки."""
    targets = getattr(args, 'targets', [])
    if not targets:
        return

    knock_ports = getattr(args, 'knock', None)

    for host, port in targets:
        if not args.json:
            print(f"\n--- {host}:{port} tcping statistics ---")

        try:
            if not args.json:
                results, stats = process_single_target_stream(host, port, args, knock_ports)
                print_stats(stats)
            else:
                results, stats = process_single_target(host, port, args, knock_ports)
                from tcping.output import generate_json
                print(generate_json(stats, results if args.verbose else None))

        except Exception as e:
            print(f"Ошибка при обработке {host}:{port}: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            continue


def main():
    try:
        args = parse_args()
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"Ошибка парсинга аргументов: {e}", file=sys.stderr)
        sys.exit(1)

    set_output_mode(verbose=args.verbose, json_mode=args.json, debug=args.debug)

    # Watchdog режим
    watch_mode = getattr(args, "watch", False)
    watch_interval = getattr(args, "watch_interval", 5)

    while True:
        try:
            # Пакетный режим (из файла)
            if args.hosts_file:
                process_packet_mode(args)

            # Режим нескольких IP/портов
            elif hasattr(args, 'targets') and args.targets:
                process_targets_mode(args)

            # Одиночный режим
            elif args.host and args.port:
                knock_ports = getattr(args, 'knock', None)
                if not args.json:
                    results, stats = process_single_target_stream(args.host, args.port, args, knock_ports)
                    print_stats(stats)
                else:
                    results, stats = process_single_target(args.host, args.port, args, knock_ports)
                    from tcping.output import generate_json
                    print(generate_json(stats, results if args.verbose else None))

            else:
                print("Ошибка: укажите хост и порт или используйте --file", file=sys.stderr)
                print("Для справки используйте: python main.py --help", file=sys.stderr)
                sys.exit(1)

        except ConfigurationError as e:
            print(f"Ошибка конфигурации: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            sys.exit(1)

        except TCpingError as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            sys.exit(1)

        except KeyboardInterrupt:
            if watch_mode:
                print("\nWatchdog stopped by user", file=sys.stderr)
                sys.exit(0)
            else:
                print("\nПрервано пользователем", file=sys.stderr)
                sys.exit(130)

        except Exception as e:
            print(f"Внутренняя ошибка: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            else:
                print("Для подробностей запустите с ключом --debug", file=sys.stderr)
            sys.exit(1)

        if not watch_mode:
            break

        print(f"\n--- Waiting {watch_interval} seconds ---\n")
        time.sleep(watch_interval)


if __name__ == "__main__":
    main()
