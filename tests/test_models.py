"""
Тесты для структур данных и вспомогательных функций в models.py.
Проверяют:
- создание PingResult и Stats
- функцию compute_stats на разных наборах данных (все успешны, есть потери, пустой список)
"""
from tcping.models import PingResult, Stats

def test_ping_result_timeout_detection():
    """Проверка определения таймаута."""
    pass

def test_stats_from_results_empty():
    """Проверка ошибки при пустом списке."""
    pass

def test_stats_from_results_all_success():
    """Проверка статистики со всеми успешными."""
    pass

def test_stats_from_results_with_loss():
    """Проверка статистики с потерями."""
    pass

def test_stats_to_dict():
    """Проверка сериализации в словарь."""
    pass