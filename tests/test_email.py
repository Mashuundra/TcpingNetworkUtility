import smtplib
import socket

# Проверка SMTP подключения без отправки
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(("smtp.gmail.com", 587))
    sock.send(b"HELO test\r\n")
    response = sock.recv(1024)
    print(f"SMTP server response: {response}")
    sock.close()
    print("SMTP connection successful")
except Exception as e:
    print(f"SMTP connection failed: {e}")
