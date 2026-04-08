"""Основная логика TCP пинга."""

from typing import List, Optional
from tcping.models import PingResult
from tcping.exceptions import NetworkError, TimeoutError, ResolveError


class TCPinger:
    """
    Класс для выполнения TCP пингов.

    Пример использования:
        pinger = TCPinger(timeout=3.0)
        result = pinger.ping_once('google.com', 80)
        results = pinger.ping_many('github.com', 443, count=5, interval=0.5)
    """

    def __init__(self, timeout: float = 5.0):
        """
        Инициализирует TCPinger.

        Args:
            timeout: Таймаут соединения в секундах (по умолчанию 5.0)
        """
        self.timeout = timeout

    def ping_once(self, host: str, port: int) -> PingResult:
        """
        Выполняет одну попытку TCP соединения.

        Алгоритм:
        1. Засечь время начала (time.perf_counter())
        2. Попытаться создать сокет и подключиться (socket.create_connection)
        3. Засечь время окончания
        4. При успехе вернуть PingResult(success=True, duration=elapsed)
        5. При ошибке вернуть PingResult с соответствующим сообщением
           - socket.timeout -> TimeoutError в error_message
           - socket.gaierror -> ResolveError
           - ConnectionRefusedError -> NetworkError
           - Другие -> NetworkError

        Args:
            host: Целевой хост (IP или домен)
            port: Целевой порт

        Returns:
            PingResult: Результат попытки (всегда возвращает объект, не бросает исключения)
        """
        pass

    def ping_many(self, host: str, port: int, count: int, interval: float = 1.0) -> List[PingResult]:
        """
        Выполняет серию TCP соединений с интервалом.

        Алгоритм:
        1. Инициализировать пустой список results
        2. Для i от 1 до count:
           - Вызвать ping_once(host, port)
           - Добавить результат в список
           - Если не последняя попытка: time.sleep(interval)
        3. Вернуть список результатов

        Args:
            host: Целевой хост
            port: Целевой порт
            count: Количество попыток
            interval: Интервал между попытками в секундах

        Returns:
            List[PingResult]: Список результатов (длина = count)
        """
        pass

    def ping_hosts_from_file(self, hosts_file_path: str, count: int, interval: float) -> dict:
        """
        Выполняет пинг для списка хостов из файла.

        Args:
            hosts_file_path: Путь к файлу с хостами
            count: Количество попыток на хост
            interval: Интервал между попытками

        Returns:
            dict: {host:port: Stats} словарь статистики для каждого хоста
        """
        pass