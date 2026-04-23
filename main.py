"""
Точка входа в приложение tcping.
"""

import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from tcping.cli import parse_args, parse_targets
from tcping.core import TCPinger
from tcping.exceptions import ConfigurationError, HostsFileError, TCpingError
from tcping.models import PingResult, Stats
from tcping.output import print_result, print_stats, set_output_mode


@dataclass
class ServiceCheckResult:
    """Результат проверки сервиса."""
    host: str
    port: int
    success: bool
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    stats: Optional[Stats] = None


def check_single_service(
    host: str,
    port: int,
    timeout: float,
    knock_ports: Optional[List[int]] = None
) -> ServiceCheckResult:
    """Проверяет один сервис (одна попытка для мониторинга)."""
    pinger = TCPinger(timeout=timeout)
    result = pinger.ping_once(host, port, knock_ports=knock_ports)

    return ServiceCheckResult(
        host=host,
        port=port,
        success=result.success,
        response_time_ms=result.duration * 1000 if result.duration else None,
        error_message=result.error_message,
    )


def check_services_parallel(
    targets: List[Tuple[str, int]],
    timeout: float,
    knock_ports: Optional[List[int]] = None,
    max_workers: int = 4
) -> List[ServiceCheckResult]:
    """Параллельная проверка нескольких сервисов."""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_single_service, host, port, timeout, knock_ports): (host, port)
            for host, port in targets
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                host, port = futures[future]
                results.append(ServiceCheckResult(
                    host=host,
                    port=port,
                    success=False,
                    error_message=str(e)
                ))

    return results


def run_standard_test(args, targets: List[Tuple[str, int]]):
    """Запускает стандартное тестирование (с полной статистикой)."""
    knock_ports = getattr(args, 'knock_ports', None)

    for host, port in targets:
        if not args.json:
            print(f"\n--- {host}:{port} tcping statistics ---")

        pinger = TCPinger(timeout=args.timeout)

        if not args.json:
            # Потоковый вывод
            def callback(result: PingResult):
                print_result(result)

            results = pinger.ping_many(
                host, port,
                count=args.count,
                interval=args.interval,
                knock_ports=knock_ports,
                stream_callback=callback
            )
            stats = Stats.from_results(host, port, results)
            print_stats(stats)
        else:
            # JSON вывод
            results = pinger.ping_many(
                host, port,
                count=args.count,
                interval=args.interval,
                knock_ports=knock_ports
            )
            stats = Stats.from_results(host, port, results)
            from tcping.output import generate_json
            print(generate_json(stats, results if args.verbose else None))


def run_watchdog_mode(args, targets: List[Tuple[str, int]]):
    """Запускает режим мониторинга с уведомлениями."""
    from tcping.notifications import Notifier, ServiceStatus

    # Инициализация уведомлений
    notifier = None
    if args.email:
        notifier = Notifier(
            to_email=args.email,
            from_email=args.email_from,
            password=args.email_password,
            smtp_server=args.smtp_server,
            smtp_port=args.smtp_port
        )

    knock_ports = getattr(args, 'knock_ports', None)
    check_count = 0

    print(f"Starting watchdog mode monitoring {len(targets)} service(s)")
    print(f"   Check interval: {args.watch_interval} seconds")
    if args.email:
        print(f"   Email notifications: {args.email}")
    if args.parallel:
        print(f"   Parallel mode: {args.max_workers} workers")
    print("\nPress Ctrl+C to stop\n")

    while True:
        check_count += 1
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{timestamp}] Check #{check_count}")

        # Проверка сервисов
        start_time = time.time()

        if args.parallel:
            results = check_services_parallel(
                targets, args.timeout, knock_ports, args.max_workers
            )
        else:
            results = []
            for host, port in targets:
                result = check_single_service(host, port, args.timeout, knock_ports)
                results.append(result)

        elapsed = time.time() - start_time

        # Вывод результатов
        healthy = sum(1 for r in results if r.success)

        print(f"   Results: {healthy}/{len(targets)} healthy (took {elapsed:.2f}s)")

        for r in results:
            status = "✅" if r.success else "❌"
            time_str = f"{r.response_time_ms:.2f}ms" if r.response_time_ms else "N/A"
            print(f"   {status} {r.host}:{r.port} - {time_str}")
            if not r.success and r.error_message:
                print(f"      Error: {r.error_message}")

        # Отправка уведомлений
        if notifier:
            statuses = [
                ServiceStatus(
                    host=r.host,
                    port=r.port,
                    is_healthy=r.success,
                    error_message=r.error_message,
                    response_time_ms=r.response_time_ms
                )
                for r in results
            ]

            if check_count == 1:
                notifier.send_initial_report(statuses)
            else:
                notifier.send_service_status(statuses)

        print()
        time.sleep(args.watch_interval)


def main():
    try:
        args = parse_args()
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"Ошибка парсинга аргументов: {e}", file=sys.stderr)
        sys.exit(1)

    set_output_mode(verbose=args.verbose, json_mode=args.json, debug=args.debug)

    # Определяем цели для проверки
    targets = []

    try:
        if args.hosts_file:
            from tcping.cli import parse_hosts_file
            targets = parse_hosts_file(args.hosts_file)
        elif args.targets:
            targets = parse_targets(args.targets)
        elif args.host and args.port:
            targets = [(args.host, args.port)]
        else:
            print("Ошибка: укажите хост и порт, --hosts-file или --targets", file=sys.stderr)
            print("Для справки используйте: python main.py --help", file=sys.stderr)
            sys.exit(1)
    except (ConfigurationError, HostsFileError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.watch:
            # Режим мониторинга
            run_watchdog_mode(args, targets)
        else:
            # Стандартный режим
            run_standard_test(args, targets)

    except KeyboardInterrupt:
        print("\n\n Interrupted by user", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
