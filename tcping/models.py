"""Структуры данных для TCP ping."""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


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
        return 'timeout' in self.error_message.lower()

    def __str__(self) -> str:
        """Строковое представление для логов."""
        if self.success:
            return f"Connected to {self.host}:{self.port} in {self.duration * 1000:.2f}ms"
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
    def from_results(cls, host: str, port: int, results: List[PingResult]) -> 'Stats':
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

        # TODO: Реализовать расчет статистики
        # - Подсчитать успешные попытки
        # - Вычислить min/avg/max из duration успешных
        # - Рассчитать процент потерь
        # - Опционально: std_dev
        pass

    def to_dict(self) -> dict:
        """Преобразует в словарь для JSON сериализации."""
        return {
            'host': self.host,
            'port': self.port,
            'sent': self.sent,
            'received': self.received,
            'lost': self.lost,
            'loss_percent': round(self.loss_percent, 2),
            'min_time_ms': round(self.min_time * 1000, 2) if self.min_time else None,
            'avg_time_ms': round(self.avg_time * 1000, 2) if self.avg_time else None,
            'max_time_ms': round(self.max_time * 1000, 2) if self.max_time else None,
            'std_dev_ms': round(self.std_dev * 1000, 2) if self.std_dev else None,
        }