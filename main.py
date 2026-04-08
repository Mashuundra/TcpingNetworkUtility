"""
Точка входа в приложение tcping.
Связывает парсинг аргументов (cli), сетевую логику (core) и вывод (output).
Обрабатывает глобальные ошибки, переключает отладочный режим по флагу --debug.
"""
import sys
import traceback
from typing import List, Tuple

from tcping.cli import parse_args
from tcping.core import TCPinger
from tcping.models import PingResult, Stats
from tcping.output import print_result, print_stats, set_output_mode
from tcping.exceptions import TCpingError, ConfigurationError, HostsFileError


def process_single_target(host: str, port: int, args) -> Tuple[List[PingResult], Stats]:
    # Выполняет серию пингов для одной цели
    pinger = TCPinger(timeout=args.timeout)
    results = pinger.ping_many(host, port, count=args.count, interval=args.interval)
    stats = Stats.from_results(host, port, results)
    return results, stats


def process_packet_mode(args) -> None:
    # Пакетный режим: обрабатывает несколько целей из файла.
    from tcping.cli import parse_hosts_file

    try:
        targets = parse_hosts_file(args.hosts_file)
    except HostsFileError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if not targets:
        print("Ошибка: файл не содержит корректных записей", file=sys.stderr)
        sys.exit(1)

    for host, port in targets:
        if not args.json:
            print(f"\n--- {host}:{port} tcping statistics ---")

        try:
            results, stats = process_single_target(host, port, args)

            if not args.json:
                # Выводим результаты каждой попытки
                for result in results:
                    print_result(result)
                print_stats(stats)
            else:
                # В JSON режиме выводим всё вместе
                from tcping.output import generate_json
                print(generate_json(stats, results if args.verbose else None))

        except Exception as e:
            print(f"Ошибка при обработке {host}:{port}: {e}", file=sys.stderr)
            if args.debug:
                traceback.print_exc()
            continue


def main():
    args = parse_args()

    # Устанавливаем режимы вывода
    set_output_mode(verbose=args.verbose, json_mode=args.json, debug=args.debug)

    try:
        # Проверка конфликтующих аргументов
        if args.hosts_file and (args.host or args.port):
            print("Ошибка: нельзя указывать одновременно --file и хост с портом", file=sys.stderr)
            sys.exit(1)

        # Пакетный режим (из файла)
        if args.hosts_file:
            process_packet_mode(args)

        # Одиночный режим
        elif args.host and args.port:
            results, stats = process_single_target(args.host, args.port, args)

            # Выводим результаты каждой попытки
            for result in results:
                print_result(result)

            # Выводим статистику
            print_stats(stats)

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
        print("\nПрервано пользователем", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        print(f"Внутренняя ошибка: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        else:
            print("Для подробностей запустите с ключом --debug", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
