"""Тесты для форматирования вывода."""

import json
from datetime import datetime

from tcping.models import PingResult, Stats
from tcping.output import (
    set_output_mode,
    format_duration,
    print_result,
    print_stats,
    generate_json,
    print_legend
)


class TestFormatDuration:
    """Тесты для format_duration."""

    def test_format_duration_normal(self):
        """Форматирование нормальной длительности."""
        result = format_duration(0.04567)
        assert result == "45.67ms"

    def test_format_duration_rounding(self):
        """Округление."""
        result = format_duration(0.045)
        assert result == "45.00ms"

    def test_format_duration_none(self):
        """Форматирование None."""
        result = format_duration(None)
        assert result == "N/A"

    def test_format_duration_zero(self):
        """Форматирование нуля."""
        result = format_duration(0)
        assert result == "0.00ms"


class TestPrintResult:
    """Тесты для print_result."""

    def setup_method(self):
        """Сброс режимов перед каждым тестом."""
        set_output_mode(verbose=False, json_mode=False, debug=False)

    def test_print_result_success(self, capsys):
        """Вывод успешного соединения."""
        result = PingResult(
            success=True,
            host="google.com",
            port=80,
            duration=0.04523
        )
        print_result(result)
        captured = capsys.readouterr()
        assert "Connected to google.com:80 - time=45.23ms" in captured.out

    def test_print_result_failure(self, capsys):
        """Вывод неудачного соединения."""
        result = PingResult(
            success=False,
            host="localhost",
            port=9999,
            error_message="connection refused"
        )
        print_result(result)
        captured = capsys.readouterr()
        assert "Failed to connect to localhost:9999 - connection refused" in captured.out

    def test_print_result_debug_mode(self, capsys):
        """Вывод в отладочном режиме с timestamp."""
        set_output_mode(debug=True)
        result = PingResult(
            success=True,
            host="google.com",
            port=80,
            duration=0.04523,
            timestamp=datetime(2024, 1, 15, 14, 30, 25, 123456)
        )
        print_result(result)
        captured = capsys.readouterr()
        assert "[14:30:25.123]" in captured.out
        assert "Connected to google.com:80" in captured.out

    def test_print_result_json_mode_skip(self, capsys):
        """В JSON режиме print_result ничего не выводит."""
        set_output_mode(json_mode=True)
        result = PingResult(success=True, host="google.com", port=80, duration=0.04523)
        print_result(result)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestPrintStats:
    """Тесты для print_stats."""

    def setup_method(self):
        """Сброс режимов перед каждым тестом."""
        set_output_mode(verbose=False, json_mode=False, debug=False)

    def test_print_stats_normal(self, capsys):
        """Вывод статистики в обычном режиме."""
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=3,
            lost=1,
            loss_percent=25.0,
            min_time=0.04218,
            avg_time=0.04377,
            max_time=0.04523
        )
        print_stats(stats)
        captured = capsys.readouterr()

        assert "--- google.com:80 ping statistics ---" in captured.out
        assert "4 packets transmitted, 3 received, 25.0% loss" in captured.out
        assert "round-trip min/avg/max = 42.18ms/43.77ms/45.23ms" in captured.out

    def test_print_stats_no_success(self, capsys):
        """Вывод статистики когда нет успешных попыток."""
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=0,
            lost=4,
            loss_percent=100.0,
            min_time=None,
            avg_time=None,
            max_time=None
        )
        print_stats(stats)
        captured = capsys.readouterr()

        assert "4 packets transmitted, 0 received, 100.0% loss" in captured.out
        assert "round-trip min/avg/max" not in captured.out

    def test_print_stats_verbose_mode_with_stddev(self, capsys):
        """Вывод статистики в verbose режиме со стандартным отклонением."""
        set_output_mode(verbose=True)
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=4,
            lost=0,
            loss_percent=0.0,
            min_time=0.040,
            avg_time=0.050,
            max_time=0.060,
            std_dev=0.008
        )
        print_stats(stats)
        captured = capsys.readouterr()

        assert "std dev = 8.00ms" in captured.out

    def test_print_stats_json_mode(self, capsys):
        """Вывод статистики в JSON режиме."""
        set_output_mode(json_mode=True, verbose=False)
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=4,
            lost=0,
            loss_percent=0.0,
            min_time=0.04218,
            avg_time=0.04377,
            max_time=0.04523,
            std_dev=None
        )
        print_stats(stats)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["host"] == "google.com"
        assert data["port"] == 80
        assert data["statistics"]["sent"] == 4
        assert data["statistics"]["received"] == 4
        assert data["statistics"]["loss_percent"] == 0.0

    def test_print_stats_json_mode_with_results(self, capsys):
        """Вывод статистики в JSON режиме с результатами."""
        set_output_mode(json_mode=True, verbose=True)
        results = [
            PingResult(success=True, host="google.com", port=80, duration=0.04218),
            PingResult(success=False, host="google.com", port=80, error_message="timeout"),
        ]
        stats = Stats.from_results("google.com", 80, results)
        print_stats(stats)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert "results" in data
        assert len(data["results"]) == 2


class TestGenerateJson:
    """Тесты для generate_json."""

    def setup_method(self):
        """Сброс режимов перед каждым тестом."""
        set_output_mode(verbose=False, json_mode=False, debug=False)

    def test_generate_json_basic(self):
        """Генерация JSON без результатов."""
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=3,
            lost=1,
            loss_percent=25.0,
            min_time=0.04218,
            avg_time=0.04377,
            max_time=0.04523
        )
        result = generate_json(stats)
        data = json.loads(result)

        assert data["host"] == "google.com"
        assert data["port"] == 80
        assert data["statistics"]["sent"] == 4
        assert data["statistics"]["received"] == 3
        assert data["statistics"]["min_time_ms"] == 42.18
        assert data["statistics"]["avg_time_ms"] == 43.77
        assert data["statistics"]["max_time_ms"] == 45.23

    def test_generate_json_with_null_values(self):
        """Генерация JSON с None значениями."""
        stats = Stats(
            host="google.com",
            port=80,
            sent=4,
            received=0,
            lost=4,
            loss_percent=100.0,
            min_time=None,
            avg_time=None,
            max_time=None
        )
        result = generate_json(stats)
        data = json.loads(result)

        assert data["statistics"]["min_time_ms"] is None
        assert data["statistics"]["avg_time_ms"] is None
        assert data["statistics"]["max_time_ms"] is None

    def test_generate_json_with_results_verbose(self):
        """Генерация JSON с результатами в verbose режиме."""
        set_output_mode(verbose=True)
        results = [
            PingResult(success=True, host="google.com", port=80, duration=0.04218),
            PingResult(success=False, host="google.com", port=80, error_message="timeout"),
        ]
        stats = Stats.from_results("google.com", 80, results)
        result = generate_json(stats, results)
        data = json.loads(result)

        assert "results" in data
        assert data["results"][0]["success"] is True
        assert data["results"][0]["duration_ms"] == 42.18
        assert data["results"][1]["success"] is False
        assert data["results"][1]["error"] == "timeout"


class TestPrintLegend:
    """Тесты для print_legend."""

    def setup_method(self):
        """Сброс режимов перед каждым тестом."""
        set_output_mode(verbose=False, json_mode=False)

    def test_print_legend_verbose_mode(self, capsys):
        """Вывод легенды в verbose режиме."""
        set_output_mode(verbose=True, json_mode=False)
        print_legend()
        captured = capsys.readouterr()

        assert "Legend:" in captured.out
        assert "✓ - successful connection" in captured.out

    def test_print_legend_not_verbose(self, capsys):
        """Без verbose режима легенда не выводится."""
        set_output_mode(verbose=False)
        print_legend()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_print_legend_json_mode(self, capsys):
        """В JSON режиме легенда не выводится."""
        set_output_mode(verbose=True, json_mode=True)
        print_legend()
        captured = capsys.readouterr()
        assert captured.out == ""
