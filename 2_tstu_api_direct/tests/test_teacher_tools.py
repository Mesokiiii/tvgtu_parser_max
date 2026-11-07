# test_teacher_tools.py
# Тестирование аналитических и фильтрационных инструментов преподавателя

import os
import sys
import datetime
import openpyxl
import pytest

currentDir = os.path.dirname(os.path.abspath(__file__))
parentDir = os.path.dirname(currentDir)
if parentDir not in sys.path:
    sys.path.insert(0, parentDir)

from models.lesson import Lesson, GroupSchedule
from parsers.teacher_tools import TeacherTools


class TestTeacherTools:

    @pytest.fixture
    def teacher_schedule(self):
        s = GroupSchedule("Преподаватель Созонов Михаил Константинович", "TEACHER")
        # Вторник: 2 пары с окном в 40 минут
        s.addLesson("Вторник", Lesson("09:45", "RED", "Лекция", "Методы оптимизации", "Вц-221", "Созонов М.К.", pGroupName="Б.ПИН.ИИ.25.16"))
        s.addLesson("Вторник", Lesson("12:00", "RED", "Практика", "Методы ИИ", "Вц-221", "Созонов М.К.", pGroupName="Б.ПИН.ИИ.25.16"))

        # Четверг: пара на синей неделе
        s.addLesson("Четверг", Lesson("14:00", "BLUE", "Лабораторная", "Управление проектами", "Вц-225", "Созонов М.К.", pGroupName="М.ПИН.РИС.25.09"))

        # Суббота: пара еженедельно
        s.addLesson("Суббота", Lesson("10:15", "BOTH", "Лекция", "Архитектура ИС", "Вц-205", "Созонов М.К.", pGroupName="Б.ПИН.ИИ.25.16"))
        return s

    def test_calculate_workload(self, teacher_schedule):
        stats = TeacherTools.calculateWorkload(teacher_schedule)
        assert stats["total_unique_lessons"] == 4
        # Красная неделя: 2 во вторник + 1 в субботу = 3
        assert stats["classes_red_week"] == 3
        # Синяя неделя: 1 в четверг + 1 в субботу = 2
        assert stats["classes_blue_week"] == 2
        # Среднее число пар в неделю: (3 + 2) / 2 = 2.5
        assert stats["classes_weekly_avg"] == 2.5
        assert stats["academic_hours_week"] == 5.0
        assert stats["academic_hours_semester"] == 85.0

        # Формы занятий
        assert stats["by_type"]["Лекция"] == 2
        assert stats["by_type"]["Практика"] == 1
        assert stats["by_type"]["Лабораторная"] == 1

        # Окна между парами во вторник (09:45+95 мин = 11:20; следующая в 12:00 -> окно 40 мин)
        assert len(stats["gaps"]) == 1
        assert stats["gaps"][0]["duration_minutes"] == 40

    def test_check_conflicts(self):
        conflictSchedule = GroupSchedule("Преподаватель Тест", "TEACHER")
        # Два разных занятия во вторник в 10:00 в разных аудиториях на красной неделе
        conflictSchedule.addLesson("Вторник", Lesson("10:00", "RED", "Лекция", "Базы данных", "Вц-201", "Тест"))
        conflictSchedule.addLesson("Вторник", Lesson("10:00", "RED", "Лабораторная", "Сети", "ХТ-301", "Тест"))

        conflicts = TeacherTools.checkConflicts(conflictSchedule)
        assert len(conflicts) >= 1
        assert any(c["type"] == "HARD_CONFLICT" for c in conflicts)

    def test_free_days(self, teacher_schedule):
        freeInfo = TeacherTools.getFreeDays(teacher_schedule)
        # Понедельник, Среда, Пятница полностью свободны
        assert "Понедельник" in freeInfo["fully_free"]
        assert "Среда" in freeInfo["fully_free"]
        assert "Пятница" in freeInfo["fully_free"]

        # Четверг свободен на красной неделе
        assert "Четверг" in freeInfo["free_red_week"]
        # Вторник свободен на синей неделе
        assert "Вторник" in freeInfo["free_blue_week"]

    def test_upcoming_lesson(self, teacher_schedule):
        # Эмулируем вторник 09:00 утра (перед первой парой)
        mockDt = datetime.datetime(2026, 9, 1, 9, 0)
        upcoming = TeacherTools.getUpcomingLesson(teacher_schedule, mockDt)
        assert upcoming is not None
        assert upcoming["is_today"] is True
        assert upcoming["lesson"].time == "09:45"
        assert upcoming["starts_in_minutes"] == 45

    def test_filter_schedule_by_day_and_week(self, teacher_schedule):
        # Фильтр по дню: Вторник
        tuesdayFiltered = TeacherTools.filterSchedule(teacher_schedule, pDayFilter="Вторник")
        assert len(tuesdayFiltered.daysMap) == 1
        assert "Вторник" in tuesdayFiltered.daysMap
        assert len(tuesdayFiltered.daysMap["Вторник"]) == 2

        # Фильтр по синей неделе (BLUE): должно остаться 2 пары (Четверг 14:00 и Суббота 10:15)
        blueFiltered = TeacherTools.filterSchedule(teacher_schedule, pWeekFilter="blue")
        totalBlue = sum(len(l) for l in blueFiltered.daysMap.values())
        assert totalBlue == 2

    def test_filter_schedule_by_building(self, teacher_schedule):
        # Все пары в корпусе Вц
        vcFiltered = TeacherTools.filterSchedule(teacher_schedule, pBuildingFilter="Вц")
        totalVc = sum(len(l) for l in vcFiltered.daysMap.values())
        assert totalVc == 4

        # В корпусе ХТ пар нет
        htFiltered = TeacherTools.filterSchedule(teacher_schedule, pBuildingFilter="ХТ")
        totalHt = sum(len(l) for l in htFiltered.daysMap.values())
        assert totalHt == 0

    def test_attendance_roster_generation(self, teacher_schedule, tmp_path):
        outXlsx = str(tmp_path / "Ведомость_БРС_Тест.xlsx")
        TeacherTools.generateAttendanceRoster(
            teacher_schedule,
            outXlsx,
            pSemesterStartDate="2026-09-01",
            pSemesterEndDate="2027-01-31"
        )
        assert os.path.exists(outXlsx)
        wb = openpyxl.load_workbook(outXlsx)
        # Проверяем, что для каждой группы создан отдельный лист
        assert "Б.ПИН.ИИ.25.16" in wb.sheetnames
        assert "М.ПИН.РИС.25.09" in wb.sheetnames
        ws = wb["Б.ПИН.ИИ.25.16"]
        assert ws.cell(row=1, column=1).value == "ТВЕРСКОЙ ГОСУДАРСТВЕННЫЙ ТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ"
        assert ws.cell(row=5, column=1).value == "№"
        assert ws.cell(row=5, column=2).value == "Ф.И.О. Студента"
        # Проверяем, что есть календарные колонки с датами
        assert ws.max_column > 5

    def test_render_formats(self, teacher_schedule):
        tableStr = TeacherTools.renderAsciiTable(teacher_schedule)
        assert "╔═" in tableStr
        assert "Вторник" in tableStr

        compactStr = TeacherTools.renderCompactList(teacher_schedule)
        assert "● Вторник:" in compactStr

        mdStr = TeacherTools.renderMarkdown(teacher_schedule)
        assert "| День | Время |" in mdStr

        cardStr = TeacherTools.renderTeacherCard(teacher_schedule)
        assert "ПРЕПОДАВАТЕЛЬ:" in cardStr
        assert "Педагогическая нагрузка:" in cardStr
