"""Тесты для моделей данных."""

from datetime import datetime

import pytest

from tcping.models import PingResult, Stats


def test_ping_result_success():
    """Тест создания успешного результата."""
    result = PingResult(success=True, host="google.com", port=80, duration=0.123)

    assert result.success is True
    assert result.host == "google.com"
    assert result.port == 80
    assert result.duration == 0.123
    assert result.error_message is None
    assert isinstance(result.timestamp, datetime)
    assert result.is_timeout() is False


def test_ping_result_failure():
    """Тест создания неудачного результата."""
    result = PingResult(
        success=False, host="localhost", port=9999, error_message="Connection refused"
    )

    assert result.success is False
    assert result.duration is None
    assert result.error_message == "Connection refused"
    assert result.is_timeout() is False


def test_ping_result_timeout():
    """Тест определения таймаута."""
    result = PingResult(
        success=False, host="google.com", port=80, error_message="Connection timeout"
    )

    assert result.is_timeout() is True


def test_ping_result_str():
    """Тест строкового представления."""
    success_result = PingResult(
        success=True, host="google.com", port=80, duration=0.045
    )
    assert "45.00ms" in str(success_result)

    fail_result = PingResult(
        success=False, host="localhost", port=9999, error_message="Refused"
    )
    assert "Refused" in str(fail_result)


def test_stats_from_results_empty():
    """Тест создания статистики из пустого списка."""
    with pytest.raises(ValueError, match="Cannot create stats from empty results list"):
        Stats.from_results("google.com", 80, [])


def test_stats_from_results_all_success():
    """Тест статистики со всеми успешными попытками."""
    results = [
        PingResult(success=True, host="google.com", port=80, duration=0.1),
        PingResult(success=True, host="google.com", port=80, duration=0.2),
        PingResult(success=True, host="google.com", port=80, duration=0.3),
    ]

    stats = Stats.from_results("google.com", 80, results)

    assert stats.sent == 3
    assert stats.received == 3
    assert stats.lost == 0
    assert stats.loss_percent == 0.0
    assert stats.min_time == 0.1
    assert stats.max_time == 0.3
    assert stats.avg_time == 0.2


def test_stats_from_results_with_loss():
    """Тест статистики с потерями."""
    results = [
        PingResult(success=True, host="google.com", port=80, duration=0.1),
        PingResult(success=False, host="google.com", port=80, error_message="Timeout"),
        PingResult(success=True, host="google.com", port=80, duration=0.3),
        PingResult(success=False, host="google.com", port=80, error_message="Refused"),
    ]

    stats = Stats.from_results("google.com", 80, results)

    assert stats.sent == 4
    assert stats.received == 2
    assert stats.lost == 2
    assert stats.loss_percent == 50.0
    assert stats.min_time == 0.1
    assert stats.max_time == 0.3
    assert stats.avg_time == 0.2


def test_stats_to_dict():
    """Тест преобразования в словарь."""
    results = [
        PingResult(success=True, host="google.com", port=80, duration=0.1),
        PingResult(success=True, host="google.com", port=80, duration=0.2),
    ]

    stats = Stats.from_results("google.com", 80, results)
    stats_dict = stats.to_dict()

    assert stats_dict["host"] == "google.com"
    assert stats_dict["port"] == 80
    assert stats_dict["sent"] == 2
    assert stats_dict["received"] == 2
    assert stats_dict["loss_percent"] == 0.0
    assert "min_time_ms" in stats_dict
    assert "avg_time_ms" in stats_dict
    assert "max_time_ms" in stats_dict


def test_stats_str():
    """Тест строкового представления статистики."""
    results = [
        PingResult(success=True, host="google.com", port=80, duration=0.1),
        PingResult(success=True, host="google.com", port=80, duration=0.2),
    ]

    stats = Stats.from_results("google.com", 80, results)
    str_output = str(stats)

    assert "google.com:80" in str_output
    assert "2 packets transmitted" in str_output
    assert "0.0% loss" in str_output
