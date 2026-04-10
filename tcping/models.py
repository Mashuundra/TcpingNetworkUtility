"""Структуры данных для TCP ping."""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PingResult:
    """
    Результат одной попытки TCP-соединения.

    Attributes:
        success: Успешно ли соединение
        host: Целевой хост (IP или домен)
        port: Целевой порт
        duration: Время соединения в секундах (None при ошибке)
        error_message: Сообщение об ошибке (None при успехе)
        timestamp: Время попытки (автоматически)
    """

    success: bool
    host: str
    port: int
    duration: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def is_timeout(self) -> bool:
        """Возвращает True, если ошибка связана с таймаутом."""
        if self.success or not self.error_message:
            return False
        return "timeout" in self.error_message.lower()

    def __str__(self) -> str:
        """Строковое представление для логов."""
        if self.success:
            return (
                f"Connected to {self.host}:{self.port} in {self.duration * 1000:.2f}ms"
            )
        return f"Failed to connect to {self.host}:{self.port} - {self.error_message}"


@dataclass
class Stats:
    """
    Статистика по серии пингов.

    Attributes:
        host: Целевой хост
        port: Целевой порт
        sent: Отправлено попыток
        received: Получено успешных ответов
        lost: Потеряно попыток
        loss_percent: Процент потерь
        min_time: Минимальное время ответа (сек)
        avg_time: Среднее время ответа (сек)
        max_time: Максимальное время ответа (сек)
        std_dev: Стандартное отклонение (опционально)
        results: Все результаты попыток (опционально, для детального вывода)
    """

    host: str
    port: int
    sent: int
    received: int
    lost: int
    loss_percent: float
    min_time: Optional[float] = None
    avg_time: Optional[float] = None
    max_time: Optional[float] = None
    std_dev: Optional[float] = None
    results: Optional[List[PingResult]] = None

    @classmethod
    def from_results(cls, host: str, port: int, results: List[PingResult]) -> "Stats":
        """
        Создает статистику из списка результатов.

        Args:
            host: Целевой хост
            port: Целевой порт
            results: Список результатов пингов

        Returns:
            Stats: Рассчитанная статистика

        Raises:
            ValueError: Если results пустой
        """
        if not results:
            raise ValueError("Cannot create stats from empty results list")

        sent = len(results)
        successful = [r for r in results if r.success]
        received = len(successful)
        lost = sent - received

        # Расчет процента потерь
        loss_percent = (lost / sent) * 100 if sent > 0 else 0

        # Расчет временных показателей (только для успешных попыток)
        min_time = None
        max_time = None
        avg_time = None
        std_dev = None

        if successful:
            durations = [r.duration for r in successful if r.duration is not None]
            if durations:
                min_time = min(durations)
                max_time = max(durations)
                avg_time = sum(durations) / len(durations)
                avg_time = round(avg_time, 10)  # округление до 10 знаков
                if len(durations) > 1:
                    try:
                        std_dev = statistics.stdev(durations)
                    except statistics.StatisticsError:
                        std_dev = None

        return cls(
            host=host,
            port=port,
            sent=sent,
            received=received,
            lost=lost,
            loss_percent=round(loss_percent, 2),
            min_time=min_time,
            avg_time=avg_time,
            max_time=max_time,
            std_dev=std_dev,
            results=results if results else None,
        )

    def to_dict(self) -> dict:
        """Преобразует в словарь для JSON сериализации."""
        return {
            "host": self.host,
            "port": self.port,
            "sent": self.sent,
            "received": self.received,
            "lost": self.lost,
            "loss_percent": round(self.loss_percent, 2),
            "min_time_ms": round(self.min_time * 1000, 2) if self.min_time else None,
            "avg_time_ms": round(self.avg_time * 1000, 2) if self.avg_time else None,
            "max_time_ms": round(self.max_time * 1000, 2) if self.max_time else None,
            "std_dev_ms": round(self.std_dev * 1000, 2) if self.std_dev else None,
        }

    def __str__(self) -> str:
        """Строковое представление статистики."""
        result = f"--- {self.host}:{self.port} ping statistics ---\n"
        result += f"{self.sent} packets transmitted, {self.received} received, "
        result += f"{self.loss_percent}% loss\n"

        if self.received > 0:
            result += f"round-trip min/avg/max = "
            result += f"{self.min_time * 1000:.2f}/{self.avg_time * 1000:.2f}/{self.max_time * 1000:.2f} ms"
            if self.std_dev:
                result += f" (std-dev = {self.std_dev * 1000:.2f} ms)"

        return result
