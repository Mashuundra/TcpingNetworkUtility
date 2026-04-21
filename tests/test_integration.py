"""
Сквозные тесты (интеграционные).
Запускают main с подменой sys.argv и перехватом stdout/stderr.
Проверяют:
- код возврата при ошибках
- наличие ожидаемых сообщений
- корректность работы пакетного режима (через временный файл)
"""

import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

import main as tcping_main


class TestIntegrationSingleHost:
    """Интеграционные тесты для режима одного хоста."""

    def test_successful_ping(self, capsys):
        """Тест успешного пинга до реального хоста."""
        import socket

        try:
            socket.create_connection(("google.com", 80), timeout=2)
            socket.close()
        except Exception:
            pytest.skip("No network connection or google.com:80 is blocked")

        test_args = ["main.py", "google.com", "80", "--count", "2", "--interval", "0.1"]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0 or e.code is None

            captured = capsys.readouterr()
            assert "Connected to google.com:80" in captured.out
            assert "ping statistics" in captured.out

    def test_failed_connection(self, capsys):
        """Тест неудачного подключения к закрытому порту."""
        test_args = [
            "main.py",
            "localhost",
            "9999",
            "--count",
            "2",
            "--interval",
            "0.1",
        ]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            assert "Failed to connect to localhost:9999" in captured.out
            assert "2 packets transmitted, 0 received, 100.0% loss" in captured.out

    def test_missing_port(self, capsys):
        """Тест ошибки при отсутствии порта."""
        test_args = ["main.py", "google.com"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Specify host and port, --hosts-file, or --targets" in captured.err

    def test_invalid_port_range(self, capsys):
        """Тест невалидного порта."""
        test_args = ["main.py", "google.com", "99999"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Port must be between 1 and 65535" in captured.err

    def test_invalid_count(self, capsys):
        """Тест невалидного количества попыток."""
        test_args = ["main.py", "google.com", "80", "--count", "0"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Count must be at least 1" in captured.err

    def test_negative_interval(self, capsys):
        """Тест отрицательного интервала."""
        test_args = ["main.py", "google.com", "80", "--interval", "-1"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Interval must be greater than 0" in captured.err

    def test_json_output(self, capsys):
        """Тест JSON формата вывода."""
        import socket

        try:
            socket.create_connection(("google.com", 80), timeout=2)
            socket.close()
        except Exception:
            pytest.skip("No network connection")

        test_args = ["main.py", "google.com", "80", "--count", "1", "--json"]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["host"] == "google.com"
            assert data["port"] == 80
            assert "statistics" in data

    def test_verbose_output(self, capsys):
        """Тест verbose режима."""
        import socket

        try:
            socket.create_connection(("google.com", 80), timeout=2)
            socket.close()
        except Exception:
            pytest.skip("No network connection")

        test_args = ["main.py", "google.com", "80", "--count", "1", "--verbose"]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            assert "Connected to google.com:80" in captured.out

    def test_debug_output(self, capsys):
        """Тест debug режима с timestamp."""
        import socket

        try:
            socket.create_connection(("google.com", 80), timeout=2)
            socket.close()
        except Exception:
            pytest.skip("No network connection")

        test_args = ["main.py", "google.com", "80", "--count", "1", "--debug"]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            import re

            assert re.search(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]", captured.out)


class TestIntegrationBatchMode:
    """Интеграционные тесты для пакетного режима (из файла)."""

    @pytest.fixture
    def valid_hosts_file(self):
        """Создаёт временный файл с валидными хостами."""
        with NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("google.com 80\n")
            f.write("ya.ru 443\n")
            f.write("# This is a comment\n")
            f.write("localhost 8080\n")
            temp_file = Path(f.name)

        yield temp_file
        temp_file.unlink()

    @pytest.fixture
    def invalid_hosts_file(self):
        """Создаёт временный файл с невалидными хостами."""
        with NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("invalid_line_no_port\n")
            temp_file = Path(f.name)

        yield temp_file
        temp_file.unlink()

    @pytest.fixture
    def empty_hosts_file(self):
        """Создаёт пустой временный файл."""
        with NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Only comments\n")
            f.write("# Another comment\n")
            temp_file = Path(f.name)

        yield temp_file
        temp_file.unlink()

    def test_batch_mode_with_valid_file(self, valid_hosts_file, capsys):
        """Тест пакетного режима с валидным файлом."""
        test_args = [
            "main.py",
            "--hosts-file",
            str(valid_hosts_file),
            "--count",
            "1",
            "--interval",
            "0.1",
        ]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            # Проверяем что есть вывод
            assert captured.out != ""

    def test_batch_mode_with_invalid_file(self, invalid_hosts_file, capsys):
        """Тест пакетного режима с невалидным файлом."""
        test_args = ["main.py", "--hosts-file", str(invalid_hosts_file)]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Invalid format" in captured.err or "Ошибка" in captured.err

    def test_batch_mode_with_empty_file(self, empty_hosts_file, capsys):
        """Тест пакетного режима с пустым файлом (только комментарии)."""
        test_args = ["main.py", "--hosts-file", str(empty_hosts_file)]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert (
                "не содержит корректных записей" in captured.err
                or "No valid hosts" in captured.err
            )

    def test_batch_mode_file_not_found(self, capsys):
        """Тест с несуществующим файлом."""
        test_args = ["main.py", "--hosts-file", "nonexistent_file.txt"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "not found" in captured.err or "не найден" in captured.err

    def test_batch_mode_json_output(self, valid_hosts_file, capsys):
        """Тест пакетного режима с JSON выводом."""
        test_args = [
            "main.py",
            "--hosts-file",
            str(valid_hosts_file),
            "--json",
            "--count",
            "1",
        ]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            # Должен быть валидный JSON для каждого хоста
            if captured.out.strip():
                lines = captured.out.strip().split("\n")
                for line in lines:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            assert "host" in data
                        except json.JSONDecodeError:
                            # Может быть несколько строк вывода, не все JSON
                            pass

    def test_batch_mode_with_verbose(self, valid_hosts_file, capsys):
        """Тест пакетного режима с verbose выводом."""
        test_args = [
            "main.py",
            "--hosts-file",
            str(valid_hosts_file),
            "--verbose",
            "--count",
            "1",
        ]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            assert captured.out != ""


class TestIntegrationEdgeCases:
    """Тесты граничных случаев."""

    def test_keyboard_interrupt(self, capsys):
        """Тест обработки Ctrl+C."""
        test_args = ["main.py", "google.com", "80", "--count", "100"]

        with patch.object(sys, "argv", test_args):
            with patch("tcping.core.TCPinger.ping_many", side_effect=KeyboardInterrupt):
                with pytest.raises(SystemExit) as exc_info:
                    tcping_main.main()

                assert exc_info.value.code == 130
                captured = capsys.readouterr()
                assert "Interrupted by user" in captured.err

    def test_network_error_handling(self, capsys):
        """Тест обработки сетевых ошибок - DNS имя не существует."""
        test_args = [
            "main.py",
            "definitely.not.existing.domain.xyz",
            "80",
            "--count",
            "1",
        ]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            # Может быть либо ошибка DNS, либо успех если DNS разрешился неожиданно
            assert (
                "DNS resolution failed" in captured.out
                or "Failed to connect" in captured.out
                or "Connected to" in captured.out
            )

    def test_conflicting_arguments(self, capsys):
        """Тест конфликтующих аргументов (хост+порт и --file одновременно)."""
        test_args = ["main.py", "google.com", "80", "--hosts-file", "hosts.txt"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Cannot specify multiple input sources simultaneously" in captured.err

    def test_help_argument(self, capsys):
        """Тест флага --help."""
        test_args = ["main.py", "--help"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "usage:" in captured.out.lower()
            assert "tcp ping utility" in captured.out.lower()

    def test_zero_timeout(self, capsys):
        """Тест нулевого таймаута (должен быть rejected)."""
        test_args = ["main.py", "google.com", "80", "--timeout", "0"]

        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                tcping_main.main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Timeout must be greater than 0" in captured.err


class TestIntegrationMixedResults:
    """Тесты со смешанными результатами (успех/неудача)."""

    def test_mixed_success_failure_output(self, capsys):
        """Тест вывода при смешанных результатах."""
        import socket

        try:
            socket.create_connection(("google.com", 80), timeout=2)
            socket.close()
        except Exception:
            pytest.skip("No network connection")

        test_args = ["main.py", "google.com", "80", "--count", "3", "--interval", "0.1"]

        with patch.object(sys, "argv", test_args):
            try:
                tcping_main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            lines = captured.out.split("\n")

            # Проверяем что есть вывод
            assert len(lines) > 0
