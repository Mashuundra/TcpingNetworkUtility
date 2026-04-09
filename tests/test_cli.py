"""Тесты для парсинга командной строки."""
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from tcping.cli import (
    parse_args, validate_port, validate_count,
    validate_interval, validate_timeout, parse_hosts_file
)
from tcping.exceptions import ConfigurationError, InvalidPortError, HostsFileError


def test_parse_args_single_host():
    """Тест парсинга аргументов с одним хостом."""
    args = parse_args(['google.com', '80'])

    assert args.host == 'google.com'
    assert args.port == 80
    assert args.count == 4
    assert args.interval == 1.0
    assert args.timeout == 5.0
    assert args.debug is False
    assert args.json is False
    assert args.verbose is False


def test_parse_args_with_options():
    """Тест парсинга аргументов с опциями."""
    args = parse_args([
        'google.com', '443',
        '--count', '10',
        '--interval', '0.5',
        '--timeout', '3',
        '--verbose',
        '--debug'
    ])

    assert args.host == 'google.com'
    assert args.port == 443
    assert args.count == 10
    assert args.interval == 0.5
    assert args.timeout == 3.0
    assert args.verbose is True
    assert args.debug is True


def test_parse_args_missing_port():
    """Тест ошибки при отсутствии порта."""
    with pytest.raises(ConfigurationError, match="Port is required"):
        parse_args(['google.com'])


def test_validate_port_valid():
    """Тест валидных портов."""
    validate_port(1)
    validate_port(80)
    validate_port(443)
    validate_port(65535)


def test_validate_port_invalid():
    """Тест невалидных портов."""
    with pytest.raises(InvalidPortError):
        validate_port(0)
    with pytest.raises(InvalidPortError):
        validate_port(65536)
    with pytest.raises(InvalidPortError):
        validate_port(-1)


def test_validate_count_valid():
    """Тест валидного количества попыток."""
    validate_count(1)
    validate_count(10)
    validate_count(100)


def test_validate_count_invalid():
    """Тест невалидного количества попыток."""
    with pytest.raises(ConfigurationError, match="Count must be at least 1"):
        validate_count(0)
    with pytest.raises(ConfigurationError, match="Count must be at least 1"):
        validate_count(-5)


def test_validate_interval_valid():
    """Тест валидного интервала."""
    validate_interval(0.1)
    validate_interval(1.0)
    validate_interval(5.5)


def test_validate_interval_invalid():
    """Тест невалидного интервала."""
    with pytest.raises(ConfigurationError, match="Interval must be greater than 0"):
        validate_interval(0)
    with pytest.raises(ConfigurationError, match="Interval must be greater than 0"):
        validate_interval(-1.0)


def test_validate_timeout_valid():
    """Тест валидного таймаута."""
    validate_timeout(0.5)
    validate_timeout(5.0)
    validate_timeout(30.0)


def test_validate_timeout_invalid():
    """Тест невалидного таймаута."""
    with pytest.raises(ConfigurationError, match="Timeout must be greater than 0"):
        validate_timeout(0)
    with pytest.raises(ConfigurationError, match="Timeout must be greater than 0"):
        validate_timeout(-2.0)


def test_parse_hosts_file_valid():
    """Тест парсинга валидного файла с хостами."""
    with NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("google.com 80\n")
        f.write("ya.ru 443\n")
        f.write("# This is a comment\n")
        f.write("github.com:22\n")
        f.write("  localhost   8080  \n")
        temp_file = Path(f.name)

    try:
        hosts = parse_hosts_file(temp_file)
        assert len(hosts) == 4
        assert ('google.com', 80) in hosts
        assert ('ya.ru', 443) in hosts
        assert ('github.com', 22) in hosts
        assert ('localhost', 8080) in hosts
    finally:
        temp_file.unlink()


def test_parse_hosts_file_not_found():
    """Тест ошибки при отсутствии файла."""
    with pytest.raises(HostsFileError, match="File not found"):
        parse_hosts_file(Path("/nonexistent/file.txt"))


def test_parse_hosts_file_invalid_format():
    """Тест ошибки при неверном формате."""
    with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("invalid_line\n")
        temp_file = Path(f.name)

    try:
        with pytest.raises(HostsFileError, match="Invalid format"):
            parse_hosts_file(temp_file)
    finally:
        temp_file.unlink()


def test_parse_hosts_file_invalid_port():
    """Тест ошибки при неверном порте."""
    with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("google.com 99999\n")
        temp_file = Path(f.name)

    try:
        with pytest.raises(HostsFileError, match="Invalid port"):
            parse_hosts_file(temp_file)
    finally:
        temp_file.unlink()
