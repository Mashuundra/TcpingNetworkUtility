# email_check.py - простой скрипт для проверки
from tcping.notifications import Notifier, ServiceStatus

print("Создаем notifier в debug режиме...")
notifier = Notifier(
    to_email="test@example.com",
    from_email="monitor@example.com",
    password="anything",
    smtp_server="localhost",
    smtp_port=8025,
    debug=True
)

print("Создаем тестовый статус...")
status = ServiceStatus(
    host="google.com",
    port=80,
    is_healthy=True,
    response_time_ms=45.23
)

print("Отправляем email...")
notifier.send_initial_report([status])
print("Готово!")
