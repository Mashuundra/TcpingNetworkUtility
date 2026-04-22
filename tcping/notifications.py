"""Email уведомления для мониторинга сервисов."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ServiceStatus:
    """Статус сервиса для уведомлений."""

    host: str
    port: int
    is_healthy: bool
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        """Init."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Notifier:
    """Класс для отправки уведомлений."""

    def __init__(
            self,
            to_email: str,
            from_email: str,
            password: str,
            smtp_server: str = "smtp.gmail.com",
            smtp_port: int = 587,
            debug: bool = False
    ):
        self.to_email = to_email
        self.from_email = from_email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.debug = debug

        # Для отслеживания предыдущих состояний
        self._last_status: Dict[tuple, bool] = {}
        self._failure_count: Dict[tuple, int] = defaultdict(int)

    def send_notification(
            self,
            subject: str,
            body: str,
            is_html: bool = False
    ) -> bool:
        """Отправляет email уведомление."""
        if self.debug:
            print("\n" + "=" * 60)
            print(f"EMAIL (DEBUG MODE)")
            print(f"To: {self.to_email}")
            print(f"Subject: {subject}")
            print(f"Body preview: {body[:300]}...")
            print("=" * 60 + "\n")
            return True

        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject

            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def send_service_status(
            self,
            statuses: List[ServiceStatus],
            is_initial: bool = False
    ) -> None:
        """Отправляет уведомление о статусе сервисов."""
        if not statuses:
            return

        healthy = [s for s in statuses if s.is_healthy]
        unhealthy = [s for s in statuses if not s.is_healthy]

        # Отправляем только при изменении статуса или для критических проблем
        notifications_to_send = []

        for status in statuses:
            key = (status.host, status.port)
            prev_healthy = self._last_status.get(key)

            # Статус изменился
            if prev_healthy is not None and prev_healthy != status.is_healthy:
                notifications_to_send.append(status)
                if not status.is_healthy:
                    self._failure_count[key] += 1
                else:
                    self._failure_count[key] = 0
            # Сервис все еще недоступен (каждые 3 проверки)
            elif not status.is_healthy and self._failure_count[key] % 3 == 0:
                notifications_to_send.append(status)
                self._failure_count[key] += 1
            # Первое уведомление
            elif prev_healthy is None and not is_initial:
                notifications_to_send.append(status)

            self._last_status[key] = status.is_healthy

        if not notifications_to_send:
            return

        # Формируем письмо
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if unhealthy and not healthy:
            subject = f"⚠️ ALL SERVICES DOWN - {timestamp}"
        elif unhealthy:
            subject = f"⚠️ Service Alert - {len(unhealthy)} service(s) down - {timestamp}"
        else:
            subject = f"✅ Services Recovered - {timestamp}"

        # HTML тело письма
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .healthy {{ color: green; }}
                .unhealthy {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>TCP Ping Monitor Report</h2>
            <p><strong>Time:</strong> {timestamp}</p>

            <h3>Summary</h3>
            <ul>
                <li> Healthy: {len(healthy)}</li>
                <li> Unhealthy: {len(unhealthy)}</li>
                <li> Total: {len(statuses)}</li>
            </ul>
        """

        if unhealthy:
            html_body += """
            <h3>⚠️ Services with Issues</h3>
            <table>
                <tr><th>Host</th><th>Port</th><th>Error</th><th>Time</th></tr>
            """
            for s in unhealthy:
                error = s.error_message or "Unknown error"
                time_str = s.timestamp.strftime("%H:%M:%S")
                html_body += f"""
                <tr class="unhealthy">
                    <td>{s.host}</td><td>{s.port}</td><td>{error}</td><td>{time_str}</td>
                </tr>
                """
            html_body += "</table>"

        if healthy and unhealthy:
            html_body += """
            <h3>✅ Healthy Services</h3>
            <table>
                <tr><th>Host</th><th>Port</th><th>Response Time</th></tr>
            """
            for s in healthy[:10]:  # Ограничиваем для краткости
                time_str = f"{s.response_time_ms:.2f}ms" if s.response_time_ms else "N/A"
                html_body += f"""
                <tr class="healthy">
                    <td>{s.host}</td><td>{s.port}</td><td>{time_str}</td>
                </tr>
                """
            if len(healthy) > 10:
                html_body += f"<tr><td colspan='3'>... and {len(healthy) - 10} more</td></tr>"
            html_body += "</table>"

        html_body += """
            <hr>
            <p><small>TCP Ping Monitor - Continuous monitoring active</small></p>
        </body>
        </html>
        """

        self.send_notification(subject, html_body, is_html=True)

    def send_initial_report(self, statuses: List[ServiceStatus]) -> None:
        """Отправляет начальный отчет о состоянии сервисов."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        healthy = sum(1 for s in statuses if s.is_healthy)

        subject = f" Service Monitor Started - {healthy}/{len(statuses)} healthy - {timestamp}"

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .healthy {{ color: green; }}
                .unhealthy {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>🚀 TCP Ping Monitor Started</h2>
            <p><strong>Time:</strong> {timestamp}</p>
            <p><strong>Initial Status:</strong> {healthy}/{len(statuses)} services healthy</p>

            <h3>All Services Status</h3>
            <table>
                <tr><th>Host</th><th>Port</th><th>Status</th><th>Response Time</th><th>Error</th></tr>
        """

        for s in statuses:
            status_class = "healthy" if s.is_healthy else "unhealthy"
            status_text = "✅ OK" if s.is_healthy else "❌ FAIL"
            time_str = f"{s.response_time_ms:.2f}ms" if s.response_time_ms else "N/A"
            error_str = s.error_message or "-"
            html_body += f"""
                <tr class="{status_class}">
                    <td>{s.host}</td><td>{s.port}</td>
                    <td>{status_text}</td><td>{time_str}</td>
                    <td>{error_str}</td>
                </tr>
            """

        html_body += """
            </table>
            <p><small>You will receive notifications when service status changes.</small></p>
        </body>
        </html>
        """

        self.send_notification(subject, html_body, is_html=True)
