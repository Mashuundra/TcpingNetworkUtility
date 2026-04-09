# tcping — TCP ping утилита

Утилита для измерения времени установки TCP-соединения с указанным хостом и портом.  
Аналог классического `ping`, но для TCP.


## Содержание
- [Архитектура проекта](#архитектура-проекта)
- [CLI модуль](#cli-модуль)
- [Core модуль](#core-модуль)
- [Models и Exceptions](#models-и-exceptions)
- [Output модуль](#output-модуль)
- [Пакетный режим](#пакетный-режим)
- [Запуск тестов](#запуск-тестов)
- [Авторы](#авторы)
- [Ссылки](#ссылки)

# Архитектура проекта

tcping/

├── main.py # Точка входа

├── tcping/

│ ├── cli.py # CLI и валидация

│ ├── core.py # TCP-пинг логика

│ ├── models.py # Данные и статистика

│ ├── output.py # Форматирование вывода

│ └── exceptions.py # Исключения

├── tests/ # Тесты

├── examples/

│ └── hosts.txt # Пример пакетного режима

└── requirements.txt # Зависимости



## CLI модуль

Отвечает за разбор аргументов и ввод пользователя.

### Основные возможности:

- парсинг аргументов (`argparse`)
- валидация порта, таймаута и количества запросов
- чтение файла с хостами

### Пример запуска:

python main.py google.com 80 --count 5 --timeout 2 --verbose



## Core модуль

Содержит основную логику TCP-пинга.

установка TCP-соединения
измерение времени ответа
обработка сетевых ошибок
возвращает результат в виде PingResult



## Models и Exceptions
models.py
PingResult — результат одного запроса
Stats — агрегированная статистика
exceptions.py

### Иерархия ошибок:
TCPingError
├── ConfigurationError
└── NetworkError



## Output модуль
Отвечает за вывод результатов.

### Поддерживает:
обычный текстовый режим
подробный (--verbose)
JSON (--json)
debug (--debug)

### Пример вывода:
Connected to google.com:80 - time=45.23ms



## Пакетный режим
Позволяет обрабатывать список хостов из файла.

### Пример hosts.txt:
google.com 80
ya.ru 443
8.8.8.8 53

### Запуск:
python main.py --hosts-file examples/hosts.txt --count 3



# Запуск тестов

### Установка зависимостей:
pip install -r requirements.txt

### Запуск тестов:
pytest tests/ -v

### С покрытием:
pytest --cov=tcping --cov-fail-under=80


## Авторы

Власова Мария, Усманова Алина

## Ссылки

https://github.com/Mashuundra/TcpingNetworkUtility
