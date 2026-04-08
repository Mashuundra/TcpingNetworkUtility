"""Кастомные исключения для TCP ping."""


class TCpingError(Exception):
    """Базовое исключение для всех ошибок tcping."""
    pass


class ConfigurationError(TCpingError):
    """Ошибка конфигурации (неверные параметры, конфликтующие аргументы)."""
    pass


class NetworkError(TCpingError):
    """Ошибка сети (недоступный хост, сброс соединения)."""
    pass


class TimeoutError(NetworkError):
    """Таймаут соединения."""
    pass


class ResolveError(NetworkError):
    """Ошибка разрешения DNS имени."""
    pass


class InvalidPortError(ConfigurationError):
    """Некорректный номер порта (не в диапазоне 1-65535)."""
    pass


class HostsFileError(ConfigurationError):
    """Ошибка чтения файла с хостами."""
    pass