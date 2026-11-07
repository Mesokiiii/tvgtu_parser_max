# teacher_tools.py Инструменты аналитики, фильтрации и подготовки отчетов для преподавателей
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: педагогическая нагрузка, фильтрация (сегодня/завтра/четность), поиск окон, ведомости и терминальный вывод

import os
import re
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, List, Any, Optional, Tuple
from models.lesson import Lesson, GroupSchedule


class TeacherTools:
    """
    Набор инструментов для преподавателя ТвГТУ:
      - Расчет педагогической нагрузки (часы, формы занятий, распределение по группам);
      - Фильтрация расписания (сегодня, завтра, конкретный день, четная/нечетная неделя);
      - Определение ближайшей пары и свободных (методических) дней;
      - Поиск "окон" (перерывов) между парами в расписании;
      - Генерация журнала посещаемости / ведомости БРС в формате Excel;
      - Форматирование расписания в терминале (таблица, компактный вид, Markdown, карточка).
    """

    DAYS_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    DAY_EN_TO_RU = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }

    @staticmethod
    def getCurrentWeekParity(pSemesterStartDate: str = "2026-09-01", pCurrentDate: Optional[datetime.date] = None) -> Tuple[str, int]:
        """
        Определение четности текущей календарной недели учебного семестра.

        Выходное значение:
            Tuple[str, int]: ('RED' или 'BLUE', номер недели в семестре 1..N).
        """
        today = pCurrentDate if pCurrentDate else datetime.date.today()
        try:
            semStart = datetime.date.fromisoformat(pSemesterStartDate)
        except Exception:
            semStart = datetime.date(today.year, 9, 1) if today.month >= 8 else datetime.date(today.year, 2, 9)

        # Понедельник первой недели семестра
        week1Monday = semStart - datetime.timedelta(days=semStart.weekday())
        daysDiff = (today - week1Monday).days
        if daysDiff < 0:
            return "RED", 1

        weekNumber = (daysDiff // 7) + 1
        # Нечетная неделя = RED (красная), четная = BLUE (синяя)
        parity = "RED" if (weekNumber % 2 == 1) else "BLUE"
        return parity, weekNumber

    @classmethod
    def filterSchedule(
        cls,
        pSchedule: GroupSchedule,
        pDayFilter: Optional[str] = None,
        pWeekFilter: Optional[str] = None,
        pBuildingFilter: Optional[str] = None,
        pSemesterStartDate: str = "2026-09-01"
    ) -> GroupSchedule:
        """
        Фильтрация расписания по дню недели, четности недели и корпусу.
        """
        filtered = GroupSchedule(pGroupName=pSchedule.groupName, pGroupId=pSchedule.groupId)

        targetDay = None
        if pDayFilter:
            normDay = pDayFilter.strip().lower()
            todayDate = datetime.date.today()
            if normDay in ("today", "сегодня"):
                targetDay = cls.DAY_EN_TO_RU.get(todayDate.weekday())
            elif normDay in ("tomorrow", "завтра"):
                targetDay = cls.DAY_EN_TO_RU.get((todayDate.weekday() + 1) % 7)
            else:
                for d in cls.DAYS_ORDER:
                    if normDay in d.lower():
                        targetDay = d
                        break

        targetWeek = None
        if pWeekFilter:
            normWeek = pWeekFilter.strip().lower()
            if normWeek in ("current", "текущая", "сейчас"):
                targetWeek, _ = cls.getCurrentWeekParity(pSemesterStartDate)
            elif normWeek in ("red", "красная", "нечетная", "1"):
                targetWeek = "RED"
            elif normWeek in ("blue", "синяя", "четная", "2"):
                targetWeek = "BLUE"

        normBuilding = pBuildingFilter.strip().lower() if pBuildingFilter else None

        for dayName, lessonsList in pSchedule.daysMap.items():
            if targetDay and dayName.lower() != targetDay.lower():
                continue

            for lesson in lessonsList:
                # Фильтр по четности недели
                if targetWeek:
                    lessonWeek = (lesson.weekType or "BOTH").upper()
                    if lessonWeek != "BOTH" and lessonWeek != targetWeek:
                        continue

                # Фильтр по корпусу
                if normBuilding:
                    room = (lesson.classroom or "").lower()
                    if normBuilding not in room:
                        continue

                filtered.addLesson(dayName, lesson)

        return filtered

    @staticmethod
    def calculateWorkload(pSchedule: GroupSchedule) -> Dict[str, Any]:
        """
        Расчет полной педагогической нагрузки преподавателя.
        """
        redCount = 0
        blueCount = 0
        bothCount = 0

        byType: Dict[str, int] = {}
        byGroup: Dict[str, int] = {}
        byClassroom: Dict[str, int] = {}
        byDay: Dict[str, int] = {}
        gaps: List[Dict[str, Any]] = []

        allLessons = []
        for dayName, lessons in pSchedule.daysMap.items():
            byDay[dayName] = len(lessons)
            # Сортировка пар по времени для выявления "окон"
            sortedLessons = sorted(lessons, key=lambda l: l.time)
            for idx in range(len(sortedLessons) - 1):
                curLesson = sortedLessons[idx]
                nextLesson = sortedLessons[idx + 1]
                # Проверяем, могут ли эти пары идти в один день (одинаковое чередование или BOTH)
                curWeek = (curLesson.weekType or "BOTH").upper()
                nextWeek = (nextLesson.weekType or "BOTH").upper()
                if curWeek == "BOTH" or nextWeek == "BOTH" or curWeek == nextWeek:
                    curH, curM = map(int, re.findall(r'\d+', curLesson.time)[:2])
                    nextH, nextM = map(int, re.findall(r'\d+', nextLesson.time)[:2])
                    curEndMinutes = curH * 60 + curM + 95
                    nextStartMinutes = nextH * 60 + nextM
                    gapDuration = nextStartMinutes - curEndMinutes
                    if gapDuration >= 20:
                        gaps.append({
                            "day": dayName,
                            "after": f"{curLesson.time} ({curLesson.subject[:25]}...)",
                            "before": f"{nextLesson.time} ({nextLesson.subject[:25]}...)",
                            "duration_minutes": gapDuration
                        })

            for lesson in lessons:
                allLessons.append(lesson)
                wt = (lesson.weekType or "BOTH").upper()
                if wt == "RED":
                    redCount += 1
                elif wt == "BLUE":
                    blueCount += 1
                else:
                    bothCount += 1

                lt = lesson.lessonType or "Занятие"
                byType[lt] = byType.get(lt, 0) + 1

                grp = lesson.group or "Основная группа"
                for g in [g.strip() for g in grp.split(",") if g.strip()]:
                    byGroup[g] = byGroup.get(g, 0) + 1

                room = lesson.classroom or "Аудитория не указана"
                byClassroom[room] = byClassroom.get(room, 0) + 1

        totalClassesRedWeek = bothCount + redCount
        totalClassesBlueWeek = bothCount + blueCount
        avgClassesPerWeek = (totalClassesRedWeek + totalClassesBlueWeek) / 2.0
        academicHoursPerWeek = avgClassesPerWeek * 2.0
        semesterHours = academicHoursPerWeek * 17.0  # 17 учебных недель в семестре

        return {
            "total_unique_lessons": len(allLessons),
            "classes_red_week": totalClassesRedWeek,
            "classes_blue_week": totalClassesBlueWeek,
            "classes_weekly_avg": round(avgClassesPerWeek, 1),
            "academic_hours_week": round(academicHoursPerWeek, 1),
            "academic_hours_semester": round(semesterHours, 1),
            "by_type": byType,
            "by_group": byGroup,
            "by_classroom": byClassroom,
            "by_day": byDay,
            "gaps": gaps
        }

    @classmethod
    def checkConflicts(cls, pSchedule: GroupSchedule) -> List[Dict[str, Any]]:
        """
        Проверка расписания преподавателя на предмет коллизий и накладок.
        """
        conflicts = []
        for dayName, lessons in pSchedule.daysMap.items():
            for i in range(len(lessons)):
                for j in range(i + 1, len(lessons)):
                    l1, l2 = lessons[i], lessons[j]
                    if l1.time == l2.time:
                        w1 = (l1.weekType or "BOTH").upper()
                        w2 = (l2.weekType or "BOTH").upper()
                        # Конфликт только если недели пересекаются
                        if w1 == "BOTH" or w2 == "BOTH" or w1 == w2:
                            # Если предмет и аудитория разные — это жесткая коллизия
                            if l1.classroom != l2.classroom or l1.subject != l2.subject:
                                conflicts.append({
                                    "type": "HARD_CONFLICT",
                                    "day": dayName,
                                    "time": l1.time,
                                    "week": f"{w1} / {w2}",
                                    "lesson1": f"[{l1.lessonType}] {l1.subject} ({l1.classroom})",
                                    "lesson2": f"[{l2.lessonType}] {l2.subject} ({l2.classroom})",
                                    "description": f"В одно и то же время ({l1.time}) назначены два разных занятия в разных аудиториях!"
                                })

            # Проверка резкой смены корпусов при коротком перерыве
            sortedLessons = sorted(lessons, key=lambda l: l.time)
            for i in range(len(sortedLessons) - 1):
                l1, l2 = sortedLessons[i], sortedLessons[i + 1]
                w1 = (l1.weekType or "BOTH").upper()
                w2 = (l2.weekType or "BOTH").upper()
                if w1 == "BOTH" or w2 == "BOTH" or w1 == w2:
                    b1 = l1.classroom.split("-")[0] if "-" in l1.classroom else ""
                    b2 = l2.classroom.split("-")[0] if "-" in l2.classroom else ""
                    if b1 and b2 and b1 != b2:
                        conflicts.append({
                            "type": "CAMPUS_HOP",
                            "day": dayName,
                            "time": f"{l1.time} -> {l2.time}",
                            "description": f"Смена учебного корпуса: из '{b1}' ({l1.classroom}) в '{b2}' ({l2.classroom})."
                        })

        return conflicts

    @classmethod
    def getFreeDays(cls, pSchedule: GroupSchedule) -> Dict[str, List[str]]:
        """
        Определение методических и свободных дней преподавателя.
        """
        fullyFree = []
        freeRedWeek = []
        freeBlueWeek = []

        for day in cls.DAYS_ORDER:
            lessons = pSchedule.daysMap.get(day, [])
            if not lessons:
                fullyFree.append(day)
                continue

            hasRed = any((l.weekType or "BOTH").upper() in ("RED", "BOTH") for l in lessons)
            hasBlue = any((l.weekType or "BOTH").upper() in ("BLUE", "BOTH") for l in lessons)

            if not hasRed:
                freeRedWeek.append(day)
            if not hasBlue:
                freeBlueWeek.append(day)

        return {
            "fully_free": fullyFree,
            "free_red_week": freeRedWeek,
            "free_blue_week": freeBlueWeek
        }

    @classmethod
    def getUpcomingLesson(cls, pSchedule: GroupSchedule, pCurrentDatetime: Optional[datetime.datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Поиск ближайшего предстоящего занятия преподавателя.
        """
        now = pCurrentDatetime if pCurrentDatetime else datetime.datetime.now()
        currentWeekday = now.weekday()
        currentMinutes = now.hour * 60 + now.minute

        # Проверяем оставшиеся занятия на сегодня
        todayName = cls.DAY_EN_TO_RU.get(currentWeekday)
        todayLessons = pSchedule.daysMap.get(todayName, [])
        for lesson in sorted(todayLessons, key=lambda l: l.time):
            h, m = map(int, re.findall(r'\d+', lesson.time)[:2])
            lessonStartMinutes = h * 60 + m
            if lessonStartMinutes >= currentMinutes:
                diff = lessonStartMinutes - currentMinutes
                return {
                    "is_today": True,
                    "day": todayName,
                    "lesson": lesson,
                    "starts_in_minutes": diff,
                    "description": f"Сегодня в {lesson.time} (через {diff} мин): [{lesson.lessonType}] {lesson.subject} (ауд. {lesson.classroom})"
                }

        # Если на сегодня занятий больше нет, ищем ближайший следующий день (до 7 дней вперед)
        for dayOffset in range(1, 8):
            nextWeekday = (currentWeekday + dayOffset) % 7
            dayName = cls.DAY_EN_TO_RU.get(nextWeekday)
            dayLessons = pSchedule.daysMap.get(dayName, [])
            if dayLessons:
                earliest = sorted(dayLessons, key=lambda l: l.time)[0]
                if dayOffset == 1:
                    dayLabel = "Завтра"
                elif dayOffset == 7:
                    dayLabel = f"В следующую субботу" if dayName == "Суббота" else f"В следующий {dayName.lower()}"
                else:
                    dayLabel = f"В {dayName.lower()}"
                return {
                    "is_today": False,
                    "day": dayName,
                    "lesson": earliest,
                    "starts_in_minutes": None,
                    "description": f"{dayLabel} в {earliest.time}: [{earliest.lessonType}] {earliest.subject} (ауд. {earliest.classroom})"
                }

        return None

    @staticmethod
    def renderAsciiTable(pSchedule: GroupSchedule, pTitle: Optional[str] = None) -> str:
        """
        Отрисовка расписания в виде красивой терминальной псевдографической таблицы.
        """
        lines = []
        title = pTitle or pSchedule.groupName or "Расписание занятий"
        headerBorder = "═" * 84
        lines.append(f"╔{headerBorder}╗")
        lines.append(f"║ {title.center(82)} ║")
        lines.append(f"╠══════════════╦════════╦══════════════╦══════════════════════════════════════╦══════════════╣")
        lines.append(f"║ День недели  ║ Время  ║ Неделя       ║ Дисциплина и форма занятия           ║ Ауд. / Группа║")
        lines.append(f"╠══════════════╬════════╬══════════════╬══════════════════════════════════════╬══════════════╣")

        hasLessons = False
        dayOrder = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        for day in dayOrder:
            lessons = pSchedule.daysMap.get(day, [])
            if not lessons:
                continue
            hasLessons = True
            for idx, item in enumerate(sorted(lessons, key=lambda l: l.time)):
                dayCol = day if idx == 0 else ""
                timeCol = item.time[:6]
                weekDesc = "Еженедельно"
                wt = (item.weekType or "BOTH").upper()
                if wt == "RED":
                    weekDesc = "Красная (неч)"
                elif wt == "BLUE":
                    weekDesc = "Синяя (чет)"

                subjClean = item.subject
                for removeMarker in [item.classroom, item.teacher]:
                    if removeMarker:
                        subjClean = subjClean.replace(removeMarker, "")
                subjClean = re.sub(r'\(.*?\)', '', subjClean).strip()
                typeAndSubj = f"[{item.lessonType or 'Пара'}] {subjClean}"[:36]

                locAndGroup = f"{item.classroom or '-'} | {item.group[:6]}"[:12]

                lines.append(f"║ {dayCol:<12} ║ {timeCol:<6} ║ {weekDesc:<12} ║ {typeAndSubj:<36} ║ {locAndGroup:<12} ║")

            lines.append(f"╠──────────────╫────────╫──────────────╫──────────────────────────────────────╫──────────────╣")

        if not hasLessons:
            lines.append(f"║ {'Занятий по заданным фильтрам не найдено.'.center(82)} ║")
            lines.append(f"╚{headerBorder}╝")
        else:
            lines[-1] = f"╚{headerBorder}╝"

        return "\n".join(lines)

    @staticmethod
    def renderCompactList(pSchedule: GroupSchedule) -> str:
        """
        Компактный строковый вывод пар списком.
        """
        lines = []
        for day in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]:
            lessons = pSchedule.daysMap.get(day, [])
            if not lessons:
                continue
            lines.append(f"● {day}:")
            for item in sorted(lessons, key=lambda l: l.time):
                wt = (item.weekType or "BOTH").upper()
                weekTag = "[КРАСНАЯ]" if wt == "RED" else ("[СИНЯЯ]" if wt == "BLUE" else "[ВСЕ]")
                lines.append(f"   • {item.time} {weekTag} [{item.lessonType}] {item.subject[:45]} — ауд. {item.classroom} ({item.group})")
        return "\n".join(lines) if lines else "Занятия не найдены."

    @staticmethod
    def renderMarkdown(pSchedule: GroupSchedule) -> str:
        """
        Генерация отчета в формате Markdown для вставки в заметки / Notion.
        """
        lines = [
            f"# {pSchedule.groupName}",
            "",
            "| День | Время | Неделя | Форма | Дисциплина | Аудитория | Группа |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]
        for day in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]:
            for item in sorted(pSchedule.daysMap.get(day, []), key=lambda l: l.time):
                lines.append(f"| {day} | {item.time} | {item.weekType} | {item.lessonType} | {item.subject} | {item.classroom} | {item.group} |")
        return "\n".join(lines)

    @classmethod
    def renderTeacherCard(cls, pSchedule: GroupSchedule, pDepartment: Optional[str] = None) -> str:
        """
        Визитная карточка преподавателя со сводкой нагрузки.
        """
        stats = cls.calculateWorkload(pSchedule)
        freeDays = cls.getFreeDays(pSchedule)
        dept = pDepartment or "Факультет информационных технологий (ФИТ)"
        teacherName = pSchedule.groupName.replace("Преподаватель ", "")

        lines = [
            "┌────────────────────────────────────────────────────────────────────────┐",
            f"│  ПРЕПОДАВАТЕЛЬ: {teacherName:<53} │",
            f"│  Кафедра:       {dept:<53} │",
            "├────────────────────────────────────────────────────────────────────────┤",
            f"│  Педагогическая нагрузка:                                              │",
            f"│    • Всего пар в расписании:      {stats['total_unique_lessons']:<38} │",
            f"│    • Пар на красной неделе:       {stats['classes_red_week']:<38} │",
            f"│    • Пар на синей неделе:         {stats['classes_blue_week']:<38} │",
            f"│    • Акад. часов в неделю (ср.):  {stats['academic_hours_week']:<38} │",
            f"│    • Акад. часов в семестре:      {stats['academic_hours_semester']:<38} │",
            "├────────────────────────────────────────────────────────────────────────┤",
            f"│  Формы занятий:                                                        │",
        ]
        for lt, cnt in stats["by_type"].items():
            lines.append(f"│    • {lt:<25}: {cnt:<42} │")

        lines.append("├────────────────────────────────────────────────────────────────────────┤")
        lines.append("│  Закрепленные академические группы:                                    │")
        groupsStr = ", ".join(stats["by_group"].keys())[:68]
        lines.append(f"│    {groupsStr:<68} │")

        lines.append("├────────────────────────────────────────────────────────────────────────┤")
        freeStr = ", ".join(freeDays["fully_free"]) if freeDays["fully_free"] else "Нет свободных дней"
        lines.append(f"│  Методические (свободные) дни: {freeStr:<39} │")
        lines.append("└────────────────────────────────────────────────────────────────────────┘")

        return "\n".join(lines)

    @classmethod
    def generateAttendanceRoster(
        cls,
        pSchedule: GroupSchedule,
        pOutputFilePath: str,
        pSemesterStartDate: str = "2026-09-01",
        pSemesterEndDate: str = "2027-01-31"
    ) -> str:
        """
        Генерация готовой таблицы посещаемости и баллов БРС (Excel .xlsx)
        с календарными датами всех занятий преподавателя на семестр.
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # удаляем дефолтный лист

        semStart = datetime.date.fromisoformat(pSemesterStartDate)
        semEnd = datetime.date.fromisoformat(pSemesterEndDate)
        week1Monday = semStart - datetime.timedelta(days=semStart.weekday())

        dayMap = {"понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3, "пятница": 4, "суббота": 5}

        # Собираем группы преподавателя
        teacherName = pSchedule.groupName.replace("Преподаватель ", "")
        groupsMap: Dict[str, List[Tuple[str, Lesson]]] = {}
        for dayName, lessons in pSchedule.daysMap.items():
            for lesson in lessons:
                for grp in [g.strip() for g in (lesson.group or "Общая группа").split(",") if g.strip()]:
                    if grp not in groupsMap:
                        groupsMap[grp] = []
                    groupsMap[grp].append((dayName, lesson))

        if not groupsMap:
            groupsMap["Группа"] = []

        headerFill = PatternFill("solid", fgColor="1F497D")
        headerFont = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        titleFont = Font(name="Calibri", size=13, bold=True, color="1F497D")
        thinBorder = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9")
        )

        for grpName, grpLessons in groupsMap.items():
            ws = wb.create_sheet(title=grpName[:30].replace("/", "_"))
            ws.views.sheetView[0].showGridLines = True

            # Заголовок
            ws.cell(row=1, column=1, value="ТВЕРСКОЙ ГОСУДАРСТВЕННЫЙ ТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ").font = titleFont
            ws.cell(row=2, column=1, value=f"ЖУРНАЛ УЧЕТА ПОСЕЩАЕМОСТИ И УСПЕВАЕМОСТИ (БРС)").font = Font(name="Calibri", size=11, bold=True)
            ws.cell(row=3, column=1, value=f"Преподаватель: {teacherName}  |  Группа: {grpName}  |  Семестр: {semStart.year}/{semStart.year+1}").font = Font(name="Calibri", size=10, italic=True)

            # Вычисление всех дат занятий этой группы на семестр
            lessonDates: List[Tuple[datetime.date, Lesson]] = []
            for dayName, lesson in grpLessons:
                dayIdx = dayMap.get(dayName.lower(), 0)
                wt = (lesson.weekType or "BOTH").upper()
                curMonday = week1Monday
                weekNum = 1
                while curMonday <= semEnd:
                    eventDate = curMonday + datetime.timedelta(days=dayIdx)
                    if semStart <= eventDate <= semEnd:
                        isRed = (weekNum % 2 == 1)
                        if wt == "BOTH" or (wt == "RED" and isRed) or (wt == "BLUE" and not isRed):
                            lessonDates.append((eventDate, lesson))
                    curMonday += datetime.timedelta(days=7)
                    weekNum += 1

            lessonDates = sorted(lessonDates, key=lambda x: (x[0], x[1].time))

            # Формирование шапки таблицы
            rowHeaders = 5
            headers = ["№", "Ф.И.О. Студента"]
            for lDate, lItem in lessonDates:
                headers.append(f"{lDate.strftime('%d.%m')}\n{lItem.time}\n{lItem.lessonType[:3]}.")
            headers.extend(["Посещ.", "БРС", "Итог"])

            for colIdx, hText in enumerate(headers, 1):
                cell = ws.cell(row=rowHeaders, column=colIdx, value=hText)
                cell.fill = headerFill
                cell.font = headerFont
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thinBorder

            ws.row_dimensions[rowHeaders].height = 42

            # Строки студентов (шаблон на 25 позиций)
            for r in range(1, 26):
                rowIdx = rowHeaders + r
                ws.cell(row=rowIdx, column=1, value=r).alignment = Alignment(horizontal="center")
                ws.cell(row=rowIdx, column=2, value=f"Студент {r:02d}")
                for c in range(3, len(headers) + 1):
                    ws.cell(row=rowIdx, column=c, value="").alignment = Alignment(horizontal="center")
                for c in range(1, len(headers) + 1):
                    ws.cell(row=rowIdx, column=c).border = thinBorder

            # Настройка ширины колонок
            ws.column_dimensions["A"].width = 5
            ws.column_dimensions["B"].width = 28
            for cIdx in range(3, len(headers) - 2):
                colLetter = get_column_letter(cIdx)
                ws.column_dimensions[colLetter].width = 9
            ws.column_dimensions[get_column_letter(len(headers) - 2)].width = 9
            ws.column_dimensions[get_column_letter(len(headers) - 1)].width = 8
            ws.column_dimensions[get_column_letter(len(headers))].width = 10

        os.makedirs(os.path.dirname(os.path.abspath(pOutputFilePath)), exist_ok=True)
        wb.save(pOutputFilePath)
        return pOutputFilePath
