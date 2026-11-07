# test_radicale_exporter.py
# Юнит- и интеграционные тесты модуля radicale_exporter

import os
import sys
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest

# Добавляем родительский каталог в sys.path
currentDir = os.path.dirname(os.path.abspath(__file__))
parentDir = os.path.dirname(currentDir)
if parentDir not in sys.path:
    sys.path.insert(0, parentDir)

from exporters.radicale_exporter import RadicaleScheduleExporter
from models.lesson import Lesson, GroupSchedule


class TestRadicaleExporter:

    @pytest.fixture
    def exporter(self):
        return RadicaleScheduleExporter()

    @pytest.fixture
    def sample_schedule(self):
        schedule = GroupSchedule("Б.ПИН.ИИ.25.16", "1851")
        schedule.addLesson("Понедельник", Lesson(
            pTime="09:45",
            pWeekType="BOTH",
            pLessonType="Лекция",
            pSubject="Основы теории систем (Лекция) Вц-221 Пиджакова Любовь Михайловна",
            pClassroom="Вц-221",
            pTeacher="Пиджакова Любовь Михайловна"
        ))
        schedule.addLesson("Вторник", Lesson(
            pTime="08:30",
            pWeekType="RED",
            pLessonType="Лабораторная",
            pSubject="Дифференциальные уравнения (Лабораторная работа) (подгруппа 1) Вц-205 Пиджакова Любовь Михайловна",
            pClassroom="Вц-205",
            pTeacher="Пиджакова Любовь Михайловна",
            pSubgroup="Подгруппа 1"
        ))
        schedule.addLesson("Вторник", Lesson(
            pTime="10:15",
            pWeekType="BLUE",
            pLessonType="Практика",
            pSubject="Языки программирования для ИИ (Практическое занятие) Вц-221 Крутских Елена Игоревна",
            pClassroom="Вц-221",
            pTeacher="Крутских Елена Игоревна"
        ))
        return schedule

    def test_clean_subject_title(self, exporter):
        raw = "Дифференциальные уравнения для моделирования (Лабораторная работа) (подгруппа 1) Вц-205 Пиджакова Любовь Михайловна"
        cleaned = exporter.cleanSubjectTitle(raw, "Вц-205", "Пиджакова Любовь Михайловна")
        assert "Дифференциальные уравнения для моделирования" in cleaned
        assert "Вц-205" not in cleaned
        assert "Пиджакова" not in cleaned
        assert "(подгруппа 1)" not in cleaned

    def test_slugify_and_uid(self, exporter):
        slug = exporter._slugify("Б.ПИН.ИИ.25.16")
        assert slug == "b_pin_ii_25_16"
        assert all(ord(c) < 128 for c in slug), "Slug must be pure ASCII"

        lesson = Lesson("09:45", "BOTH", "Лекция", "Предмет", "Вц-221", "Учитель")
        uid1 = exporter._generateUid(lesson, "Понедельник", "Б.ПИН.ИИ.25.16")
        uid2 = exporter._generateUid(lesson, "Понедельник", "Б.ПИН.ИИ.25.16")
        assert uid1 == uid2, "UID must be deterministic"
        assert uid1.startswith("tstu-b_pin_ii_25_16-")
        assert uid1.endswith("@tstu.tver.ru")

    def test_determine_semester_dates(self, exporter):
        start, end = exporter._determineSemesterDates("2026-09-01", "2027-01-31")
        assert start == datetime.date(2026, 9, 1)
        assert end == datetime.date(2027, 1, 31)

        # Автоматическое определение семестра
        autoStart, autoEnd = exporter._determineSemesterDates(None, None)
        assert autoStart is not None
        assert autoEnd is not None
        assert autoEnd > autoStart

    def test_parse_lesson_time(self, exporter):
        # Одиночный слот: по умолчанию добавляет 95 минут
        startH, startM, endH, endM = exporter._parseLessonTime("08:30")
        assert (startH, startM) == (8, 30)
        assert (endH, endM) == (10, 5)

        # Диапазон времени
        startH, startM, endH, endM = exporter._parseLessonTime("10:15 - 11:50")
        assert (startH, startM) == (10, 15)
        assert (endH, endM) == (11, 50)

    def test_first_occurrence_parity(self, exporter):
        # 1 сентября 2026 года - это вторник (weekday=1)
        # Первая неделя (RED): понедельник 31 августа, вторник 1 сентября
        semStart = datetime.date(2026, 9, 1)

        # Вторник RED (нечетная) -> должен выпасть ровно на 1 сентября 2026
        redTuesday = exporter._calculateFirstOccurrence("Вторник", "RED", semStart)
        assert redTuesday == datetime.date(2026, 9, 1)

        # Вторник BLUE (четная) -> должен выпасть ровно на 8 сентября 2026
        blueTuesday = exporter._calculateFirstOccurrence("Вторник", "BLUE", semStart)
        assert blueTuesday == datetime.date(2026, 9, 8)

        # Вторник BOTH (еженедельно) -> 1 сентября 2026
        bothTuesday = exporter._calculateFirstOccurrence("Вторник", "BOTH", semStart)
        assert bothTuesday == datetime.date(2026, 9, 1)

    def test_build_vevent(self, exporter):
        lesson = Lesson("08:30", "RED", "Лабораторная", "Физика (Лабораторная)", "Ц-201", "Иванов И.И.", pSubgroup="Подгруппа 1")
        veventStr = exporter.buildVEvent(
            lesson, "Вторник",
            datetime.date(2026, 9, 1),
            datetime.date(2027, 1, 31),
            "Б.ПИН.ИИ.25.16"
        )
        assert "BEGIN:VEVENT" in veventStr
        assert "END:VEVENT" in veventStr
        assert "RRULE:FREQ=WEEKLY;INTERVAL=2;UNTIL=20270131T235959Z" in veventStr
        assert "DTSTART;TZID=Europe/Moscow:20260901T083000" in veventStr
        assert "DTEND;TZID=Europe/Moscow:20260901T100500" in veventStr
        assert "LOCATION:Ц-201" in veventStr
        assert "CATEGORIES:Лабораторная" in veventStr
        assert "Подгруппа 1" in veventStr

    def test_generate_ics_content(self, exporter, sample_schedule):
        content = exporter.generateIcsContent(sample_schedule, "2026-09-01", "2027-01-31")
        assert content.startswith("BEGIN:VCALENDAR")
        assert "VERSION:2.0" in content
        assert "X-WR-CALNAME:Расписание Б.ПИН.ИИ.25.16" in content
        assert "BEGIN:VTIMEZONE" in content
        assert "TZID:Europe/Moscow" in content
        # Проверяем, что созданы все 3 занятия
        assert content.count("BEGIN:VEVENT") == 3
        assert content.count("END:VEVENT") == 3
        assert content.strip().endswith("END:VCALENDAR")

    def test_export_ics_to_file(self, exporter, sample_schedule, tmp_path):
        outPath = str(tmp_path / "test_schedule.ics")
        savedPath = exporter.exportIcs(sample_schedule, outPath, "2026-09-01", "2027-01-31")
        assert os.path.exists(savedPath)
        with open(savedPath, "r", encoding="utf-8") as f:
            data = f.read()
        assert "BEGIN:VCALENDAR" in data
        assert "Основы теории систем" in data

    def test_sync_to_radicale_offline_fast_fail(self, exporter, sample_schedule):
        # Запрос к заведомо закрытому порту должен завершиться быстро и вернуть понятную ошибку
        startTime = datetime.datetime.now()
        report = exporter.syncToRadicale(
            pGroupSchedule=sample_schedule,
            pRadicaleUrl="http://127.0.0.1:59999",
            pTimeoutSeconds=2
        )
        elapsed = (datetime.datetime.now() - startTime).total_seconds()
        assert elapsed < 4.0, "Offline check should fail fast without hanging"
        assert report["success"] is False
        assert "недоступен" in report["message"]
        assert report["synced_count"] == 0

    def test_sync_to_radicale_mock_server(self, exporter, sample_schedule):
        # Создаем локальный mock HTTP-сервер, эмулирующий CalDAV Radicale
        receivedRequests = []

        class MockRadicaleHandler(BaseHTTPRequestHandler):
            def do_MKCALENDAR(self):
                contentLen = int(self.headers.get("Content-Length", 0))
                if contentLen > 0:
                    self.rfile.read(contentLen)
                receivedRequests.append(("MKCALENDAR", self.path))
                self.send_response(201)
                self.end_headers()

            def do_PUT(self):
                contentLen = int(self.headers.get("Content-Length", 0))
                if contentLen > 0:
                    self.rfile.read(contentLen)
                receivedRequests.append(("PUT", self.path))
                self.send_response(201)
                self.end_headers()

            def log_message(self, format, *args):
                pass  # Подавляем вывод логов сервера

        # Подбираем свободный порт
        server = HTTPServer(("127.0.0.1", 0), MockRadicaleHandler)
        serverPort = server.server_port
        serverThread = threading.Thread(target=server.serve_forever, daemon=True)
        serverThread.start()

        mockUrl = f"http://127.0.0.1:{serverPort}"
        try:
            report = exporter.syncToRadicale(
                pGroupSchedule=sample_schedule,
                pRadicaleUrl=mockUrl,
                pUsername="tstu_user",
                pCalendarName="test_cal",
                pSemesterStartDate="2026-09-01",
                pSemesterEndDate="2027-01-31",
                pTimeoutSeconds=3
            )
            print("\nDEBUG REPORT:", report)
            assert report["success"] is True
            assert report["synced_count"] == 3
            assert report["total_events"] == 3
            assert "tstu_user/test_cal" in report["collection_url"]

            # Проверяем, что были отправлены MKCALENDAR и 3 запроса PUT
            methods = [req[0] for req in receivedRequests]
            assert "MKCALENDAR" in methods
            assert methods.count("PUT") == 3
        finally:
            server.shutdown()
            server.server_close()
