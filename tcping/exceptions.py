"""Кастомные исключения для TCP ping."""


class TCpingError(Exception):
    """Базовое исключение для всех ошибок tcping."""


class ConfigurationError(TCpingError):
    """Ошибка конфигурации (неверные параметры, конфликтующие аргументы)."""


class NetworkError(TCpingError):
    """Ошибка сети (недоступный хост, сброс соединения)."""


class TimeoutError(NetworkError):
    """Таймаут соединения."""


class ResolveError(NetworkError):
    """Ошибка разрешения DNS имени."""


class InvalidPortError(ConfigurationError):
    """Некорректный номер порта (не в диапазоне 1-65535)."""


class HostsFileError(ConfigurationError):
    """Ошибка чтения файла с хостами."""
