"""Основная логика TCP пинга."""

import socket
import time
from typing import List

from tcping.models import PingResult


class TCPinger:
    """Класс для выполнения TCP пингов."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout

    def ping_once(self, host: str, port: int) -> PingResult:
        """Выполняет одну попытку TCP соединения."""
        start_time = time.perf_counter()

        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                elapsed = time.perf_counter() - start_time
                return PingResult(
                    success=True,
                    host=host,
                    port=port,
                    duration=elapsed,
                    error_message=None,
                )

        except socket.timeout:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message=f"timeout after {self.timeout}s",
            )

        except socket.gaierror as e:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message=f"DNS resolution failed: {e}",
            )

        except ConnectionRefusedError:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message="connection refused",
            )

        except socket.error as e:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message=f"network error: {e}",
            )

        except Exception as e:
            return PingResult(
                success=False,
                host=host,
                port=port,
                duration=None,
                error_message=f"unexpected error: {e}",
            )

    def ping_many(
        self, host: str, port: int, count: int, interval: float = 1.0
    ) -> List[PingResult]:
        """Выполняет серию TCP соединений с интервалом."""
        results = []

        for i in range(count):
            result = self.ping_once(host, port)
            results.append(result)

            if i < count - 1:
                time.sleep(interval)

        return results

    def ping_hosts_from_file(
        self, hosts_file_path: str, count: int, interval: float
    ) -> dict:
        """Выполняет пинг для списка хостов из файла."""
        from tcping.cli import parse_hosts_file
        from tcping.models import Stats

        targets = parse_hosts_file(hosts_file_path)
        results_dict = {}

        for host, port in targets:
            ping_results = self.ping_many(host, port, count, interval)
            stats = Stats.from_results(host, port, ping_results)
            results_dict[(host, port)] = stats

        return results_dict
