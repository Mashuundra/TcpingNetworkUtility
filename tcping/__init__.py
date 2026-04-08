"""TCP Ping утилита для измерения доступности TCP портов."""

from tcping.core import TCPinger
from tcping.models import PingResult, Stats
from tcping.exceptions import (
    TCpingError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
    ResolveError
)

__all__ = [
    'TCPinger',
    'PingResult',
    'Stats',
    'TCpingError',
    'ConfigurationError',
    'NetworkError',
    'TimeoutError',
    'ResolveError'
]
