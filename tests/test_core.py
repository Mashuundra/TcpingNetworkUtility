"""Модульные тесты для логики TCP пинга."""

import socket
from unittest.mock import MagicMock, patch

from tcping.core import TCPinger
from tcping.models import PingResult


class TestTCPingerPingOnce:
    """Тесты для метода ping_once."""

    def setup_method(self):
        """Создаёт экземпляр TCPinger перед каждым тестом."""
        self.pinger = TCPinger(timeout=5.0)

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_success(self, mock_create_connection):
        """Проверка успешного соединения."""
        mock_socket = MagicMock()
        mock_create_connection.return_value.__enter__.return_value = mock_socket

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is True
        assert result.host == "google.com"
        assert result.port == 80
        assert result.duration is not None
        assert result.error_message is None
        assert result.is_timeout() is False

        mock_create_connection.assert_called_once_with(("google.com", 80), timeout=5.0)

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_timeout(self, mock_create_connection):
        """Проверка обработки таймаута."""
        mock_create_connection.side_effect = socket.timeout()

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert result.duration is None
        assert "timeout" in result.error_message.lower()
        assert result.is_timeout() is True

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_connection_refused(self, mock_create_connection):
        """Проверка обработки отказа в соединении."""
        mock_create_connection.side_effect = ConnectionRefusedError()

        result = self.pinger.ping_once("localhost", 9999)

        assert result.success is False
        assert result.duration is None
        assert "connection refused" in result.error_message.lower()
        assert result.is_timeout() is False

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_dns_error(self, mock_create_connection):
        """Проверка обработки ошибки DNS."""
        mock_create_connection.side_effect = socket.gaierror("Name does not resolve")

        result = self.pinger.ping_once("nonexistent.domain.xyz", 80)

        assert result.success is False
        assert result.duration is None
        assert "dns resolution failed" in result.error_message.lower()

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_network_error(self, mock_create_connection):
        """Проверка обработки общей сетевой ошибки."""
        mock_create_connection.side_effect = socket.error("Network unreachable")

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert result.duration is None
        assert "network error" in result.error_message.lower()
        assert result.is_timeout() is False

    @patch("tcping.core.socket.create_connection")
    def test_ping_once_unexpected_error(self, mock_create_connection):
        """Проверка обработки неожиданной ошибки."""
        mock_create_connection.side_effect = RuntimeError("Something went wrong")

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert result.duration is None
        assert "unexpected error" in result.error_message.lower()


class TestTCPingerPingMany:
    """Тесты для метода ping_many."""

    def setup_method(self):
        """Создаёт экземпляр TCPinger перед каждым тестом."""
        self.pinger = TCPinger(timeout=5.0)

    @patch("tcping.core.TCPinger.ping_once")
    def test_ping_many_count(self, mock_ping_once):
        """Проверка количества попыток."""
        mock_ping_once.return_value = PingResult(
            success=True, host="google.com", port=80, duration=0.045
        )

        results = self.pinger.ping_many("google.com", 80, count=5, interval=0.1)

        assert mock_ping_once.call_count == 5
        assert len(results) == 5

    @patch("tcping.core.TCPinger.ping_once")
    @patch("tcping.core.time.sleep")
    def test_ping_many_interval(self, mock_sleep, mock_ping_once):
        """Проверка интервалов между попытками."""
        mock_ping_once.return_value = PingResult(
            success=True, host="google.com", port=80, duration=0.045
        )

        self.pinger.ping_many("google.com", 80, count=3, interval=0.5)

        # Проверяем, что sleep вызывался между попытками
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)

    @patch("tcping.core.TCPinger.ping_once")
    def test_ping_many_no_interval_after_last(self, mock_ping_once):
        """Проверка: после последней попытки интервал не ждём."""
        mock_ping_once.return_value = PingResult(
            success=True, host="google.com", port=80, duration=0.045
        )

        with patch("tcping.core.time.sleep") as mock_sleep:
            self.pinger.ping_many("google.com", 80, count=1, interval=0.5)

            mock_sleep.assert_not_called()

    @patch("tcping.core.TCPinger.ping_once")
    def test_ping_many_mixed_results(self, mock_ping_once):
        """Проверка серии со смешанными результатами."""
        mock_ping_once.side_effect = [
            PingResult(success=True, host="google.com", port=80, duration=0.045),
            PingResult(
                success=False, host="google.com", port=80, error_message="timeout"
            ),
            PingResult(success=True, host="google.com", port=80, duration=0.050),
        ]

        results = self.pinger.ping_many("google.com", 80, count=3, interval=0.1)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


class TestTCPingerInit:
    """Тесты для инициализации TCPinger."""

    def test_default_timeout(self):
        """Проверка таймаута по умолчанию."""
        pinger = TCPinger()
        assert pinger.timeout == 5.0

    def test_custom_timeout(self):
        """Проверка кастомного таймаута."""
        pinger = TCPinger(timeout=3.0)
        assert pinger.timeout == 3.0


class TestTCPingerPingHostsFromFile:
    """Тесты для метода ping_hosts_from_file."""

    def setup_method(self):
        """Создаёт экземпляр TCPinger перед каждым тестом."""
        self.pinger = TCPinger(timeout=5.0)

    @patch("tcping.cli.parse_hosts_file")
    @patch("tcping.core.TCPinger.ping_many")
    def test_ping_hosts_from_file(self, mock_ping_many, mock_parse_hosts_file):
        """Проверка пинга списка хостов из файла."""
        mock_parse_hosts_file.return_value = [
            ("google.com", 80),
            ("ya.ru", 443),
        ]

        mock_ping_many.side_effect = [
            [PingResult(success=True, host="google.com", port=80, duration=0.045)],
            [PingResult(success=True, host="ya.ru", port=443, duration=0.050)],
        ]

        result = self.pinger.ping_hosts_from_file("hosts.txt", count=1, interval=0.5)

        mock_parse_hosts_file.assert_called_once_with("hosts.txt")
        assert mock_ping_many.call_count == 2

        assert len(result) == 2
        assert ("google.com", 80) in result
        assert ("ya.ru", 443) in result
