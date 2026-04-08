"""
Модульные тесты для tcping/core.py.
Используют unittest.mock для подмены socket.create_connection,
чтобы не делать реальных сетевых вызовов.
Проверяют:
- успешное соединение и время
- обработку исключений (таймаут, отказ соединения)
- правильность серии попыток с интервалами
"""

import pytest
from unittest.mock import Mock, patch
from tcping.core import TCPinger
from tcping.models import PingResult


# Обязательные тесты:
def test_ping_once_success():
    """Проверка успешного соединения."""
    pass


def test_ping_once_timeout():
    """Проверка таймаута."""
    pass


def test_ping_once_connection_refused():
    """Проверка отказа в соединении."""
    pass


def test_ping_once_dns_error():
    """Проверка ошибки DNS."""
    pass


def test_ping_many_count():
    """Проверка количества попыток."""
    pass


def test_ping_many_interval():
    """Проверка интервалов между попытками."""
    pass
