# Dockerfile для сервиса расписания ТвГТУ (Вариант 2 - Прямой доступ к шлюзу ТвГТУ)
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)

FROM python:3.11-slim

# Установка рабочей директории в контейнере
WORKDIR /app

# Настройка вывода Python без буферизации для мгновенного отображения логов в Docker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода приложения
COPY . .

# Создание каталогов выгрузки отчетов
RUN mkdir -p output/groups output/teachers data

# Переменные окружения по умолчанию
ENV SCHEDULE_GROUP="Б.ПИН.ИИ.25.16" \
    SCHEDULE_TEACHER="" \
    RADICALE_URL="" \
    RADICALE_USER="tstu" \
    RADICALE_PASSWORD="" \
    RADICALE_CALENDAR="schedule" \
    EXPORT_RADICALE="false" \
    EXPORT_ICS="true" \
    EXPORT_EXCEL="true" \
    EXPORT_JSON="true" \
    SEMESTER_START_DATE="2026-09-01" \
    SEMESTER_END_DATE="2027-01-31" \
    PORT=8081 \
    RUN_SERVER="false" \
    SYNC_INTERVAL=0

# Порт для встроенного веб-сервера интерактивного расписания
EXPOSE 8081

# Точка входа в приложение
ENTRYPOINT ["python", "main.py"]
