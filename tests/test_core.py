"""Модульные тесты для логики TCP пинга."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from tcping.core import TCPinger
from tcping.models import PingResult


class TestTCPingerPingOnce:
    """Тесты для метода ping_once."""

    def setup_method(self):
        """Создаёт экземпляр TCPinger перед каждым тестом."""
        self.pinger = TCPinger(timeout=5.0)

    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_success_ipv4(self, mock_resolve_host, mock_syn_scan):
        """Проверка успешного соединения через IPv4."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_syn_scan.return_value = (True, 0.045, None)

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is True
        assert result.host == "google.com"
        assert result.port == 80
        assert result.duration == 0.045
        assert result.error_message is None

    @patch("tcping.core.TCPinger._syn_scan_ipv6")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_success_ipv6(self, mock_resolve_host, mock_syn_scan):
        """Проверка успешного соединения через IPv6."""
        mock_resolve_host.return_value = [("::1", socket.AF_INET6)]
        mock_syn_scan.return_value = (True, 0.045, None)

        result = self.pinger.ping_once("localhost", 80)

        assert result.success is True
        assert result.duration == 0.045

    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_dns_error(self, mock_resolve_host):
        """Проверка обработки ошибки DNS."""
        mock_resolve_host.return_value = []

        result = self.pinger.ping_once("nonexistent.domain.xyz", 80)

        assert result.success is False
        assert result.duration is None
        assert "DNS resolution failed" in result.error_message

    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_timeout(self, mock_resolve_host, mock_syn_scan):
        """Проверка обработки таймаута."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_syn_scan.return_value = (False, None, "timeout after 5.0s")

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert result.duration is None
        assert "timeout" in result.error_message.lower()

    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_connection_refused(self, mock_resolve_host, mock_syn_scan):
        """Проверка обработки отказа в соединении."""
        mock_resolve_host.return_value = [("127.0.0.1", socket.AF_INET)]
        mock_syn_scan.return_value = (False, None, "connection refused")

        result = self.pinger.ping_once("localhost", 9999)

        assert result.success is False
        assert "connection refused" in result.error_message.lower()

    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_network_error(self, mock_resolve_host, mock_syn_scan):
        """Проверка обработки общей сетевой ошибки."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_syn_scan.return_value = (False, None, "network error: unreachable")

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert "network error" in result.error_message.lower()

    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_unexpected_error(self, mock_resolve_host, mock_syn_scan):
        """Проверка обработки неожиданной ошибки."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_syn_scan.return_value = (False, None, "unexpected error: something wrong")

        result = self.pinger.ping_once("google.com", 80)

        assert result.success is False
        assert "unexpected error" in result.error_message.lower()

    @patch("tcping.core.TCPinger.knock")
    @patch("tcping.core.TCPinger._syn_scan_ipv4")
    @patch("tcping.core.TCPinger._resolve_host")
    def test_ping_once_with_knocking(self, mock_resolve_host, mock_syn_scan, mock_knock):
        """Проверка port knocking перед сканированием."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_syn_scan.return_value = (True, 0.045, None)

        result = self.pinger.ping_once("google.com", 80, knock_ports=[1000, 2000, 3000])

        mock_knock.assert_called_once_with("google.com", [1000, 2000, 3000])
        assert result.success is True


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

    @patch("tcping.core.TCPinger.ping_once")
    def test_ping_many_with_knock_ports(self, mock_ping_once):
        """Проверка передачи knock_ports в ping_once."""
        mock_ping_once.return_value = PingResult(
            success=True, host="google.com", port=80, duration=0.045
        )

        self.pinger.ping_many("google.com", 80, count=2, interval=0.1, knock_ports=[1000, 2000])

        # Проверяем, что knock_ports был передан в каждый вызов ping_once
        for call in mock_ping_once.call_args_list:
            kwargs = call[1]
            assert kwargs.get('knock_ports') == [1000, 2000]

    @patch("tcping.core.TCPinger.ping_once")
    def test_ping_many_stream_callback(self, mock_ping_once):
        """Проверка вызова stream_callback после каждой попытки."""
        mock_ping_once.return_value = PingResult(
            success=True, host="google.com", port=80, duration=0.045
        )

        callback = MagicMock()
        self.pinger.ping_many("google.com", 80, count=3, interval=0.1, stream_callback=callback)

        assert callback.call_count == 3


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
    """Тесты ping_hosts_from_file."""

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


class TestTCPingerKnock:
    """Тесты для метода knock."""

    def setup_method(self):
        self.pinger = TCPinger(timeout=5.0)

    @patch("tcping.core.TCPinger._resolve_host")
    @patch("tcping.core.TCPinger._send_syn")
    @patch("tcping.core.time.sleep")
    def test_knock_success(self, mock_sleep, mock_send_syn, mock_resolve_host):
        """Проверка успешного port knocking."""
        mock_resolve_host.return_value = [("8.8.8.8", socket.AF_INET)]
        mock_send_syn.return_value = True

        result = self.pinger.knock("google.com", [1000, 2000, 3000], delay=0.1)

        assert result is True
        assert mock_send_syn.call_count == 3
        assert mock_sleep.call_count == 3

    @patch("tcping.core.TCPinger._resolve_host")
    def test_knock_dns_error(self, mock_resolve_host):
        """Проверка ошибки DNS при knocking."""
        mock_resolve_host.return_value = []

        result = self.pinger.knock("nonexistent.xyz", [1000, 2000])

        assert result is False


class TestTCPingerSendSyn:
    """Тесты для метода _send_syn."""

    def setup_method(self):
        """Инициализирует экземпляр TCPinger перед каждым тестом."""
        self.pinger = TCPinger(timeout=5.0)

    @patch("socket.socket")
    def test_send_syn_ipv4_success(self, mock_socket_class):
        """Проверка отправки SYN через IPv4."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = self.pinger._send_syn("8.8.8.8", 80, socket.AF_INET)

        assert result is True
        mock_sock.sendto.assert_called_once()

    @patch("socket.socket")
    def test_send_syn_ipv6_success(self, mock_socket_class):
        """Проверка отправки SYN через IPv6."""
        mock_sock = MagicMock()
        mock_socket_class.return_value = mock_sock

        result = self.pinger._send_syn("::1", 80, socket.AF_INET6)

        assert result is True
        mock_sock.sendto.assert_called_once()
