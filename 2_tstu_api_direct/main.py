# Main.py Консольная точка входа прямого модуля расписания ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Расширенный CLI для преподавателей: аналитика нагрузки, фильтрация, проверка коллизий, ведомости и Radicale
# Назначение: загрузка, экспорт, фильтрация и синхронизация расписания академических групп и преподавателей

import os
import sys
import json
import time

# Обеспечиваем немедленный вывод логов без буферизации
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

from schedule_service import TstuScheduleService
from parsers.teacher_tools import TeacherTools


def _getArgValue(pFlagName: str, pDefault=None):
    """Извлечение значения строкового флага командной строки."""
    if pFlagName in sys.argv:
        idx = sys.argv.index(pFlagName)
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--"):
            return sys.argv[idx + 1]
    return pDefault


def _getBoolEnv(pEnvName: str, pDefault: bool = True) -> bool:
    """Извлечение булевой переменной окружения."""
    val = os.environ.get(pEnvName)
    if val is None:
        return pDefault
    return val.strip().lower() in ("true", "1", "yes", "y", "on")


def PrintUsage():
    """Вывод подробной справки по всем флагам и режимам."""
    helpText = """
════════════════════════════════════════════════════════════════════════════════
    КОМАНДНЫЙ ИНТЕРФЕЙС РАСПИСАНИЯ ТвГТУ (ПРЯМОЙ ШЛЮЗ + RADICALE CALDAV)
════════════════════════════════════════════════════════════════════════════════

ИСПОЛЬЗОВАНИЕ:
  python main.py [ОПЦИИ] [ШИФР_ГРУППЫ]

БАЗОВЫЕ РЕЖИМЫ ВЫБОРА:
  --group <ШИФР>             Указать учебную группу (магистр 'М.', бакалавр 'Б.', спец. 'С.')
  --teacher <ФИО>            Поиск расписания преподавателя (например: 'Созонов', 'Пиджакова')
  --sozonov, --sozontov, --me Быстрый шорткат для расписания М.К. Созонова
  --list-groups [ФИЛЬТР]     Каталог всех 438 групп (фильтры: 'м', 'б', 'с', 'спо')
  --select-group             Интерактивный консольный выбор группы
  --teachers-list            Список всех преподавателей университета

СУПЕР-ФИШКИ ДЛЯ ПРЕПОДАВАТЕЛЯ (ФИЛЬТРАЦИЯ И РАСПОРЯДОК):
  --today                    Показать пары только на СЕГОДНЯ
  --tomorrow                 Показать пары только на ЗАВТРА
  --day <ДЕНЬ>               Показать пары на день (Понедельник, Вторник, Среда...)
  --current-week             Расписание на ТЕКУЩУЮ календарную неделю семестра
  --week <red|blue>          Фильтр по четности (красная / нечетная или синяя / четная)
  --building <КОРПУС>        Фильтр по учебному корпусу (например: 'Вц', 'Ц', 'ХТ', 'Уч')
  --next, --upcoming         Показать ближайшую следующую пару и сколько минут осталось

АНАЛИТИКА, НАГРУЗКА И ВЕДОМОСТИ:
  --workload, --stats        Полный расчет педагогической нагрузки (пары, акад. часы, % лекций/лаб/практик, окна)
  --conflicts, --check-conflicts Проверка расписания на коллизии, накладки и резкие смены корпусов
  --free-days                Список методических и научных дней (свободных от занятий)
  --card, --summary          Красивая визитная карточка преподавателя со сводкой
  --attendance-sheet, --roster Сгенерировать готовый журнал посещаемости и баллов БРС в Excel (.xlsx)

ФОРМАТЫ ТЕРМИНАЛЬНОГО ВЫВОДА:
  --format <table>           Красивая псевдографическая ASCII-таблица (по умолчанию)
  --format <compact>         Компактный строчный список
  --format <markdown>        Таблица в формате Markdown для заметок (Obsidian / Notion)
  --format <json>            Машиночитаемый JSON в stdout
  --quiet                    Подавить вывод таблицы расписания (только экспорт в файлы)

ЭКСПОРТ В RADICALE И КАЛЕНДАРИ (iCalendar / CalDAV):
  --radicale-url <URL>       Адрес сервера Radicale (по умолч.: 'http://localhost:5232')
  --radicale-user <USER>     Пользователь CalDAV (по умолч.: 'tstu')
  --radicale-pass <PASS>     Пароль CalDAV
  --radicale-cal <NAME>      Имя коллекции календаря (по умолч.: 'schedule')
  --alarm <МИНУТЫ>           Напоминание перед каждой парой в календаре (VALARM, напр.: 15)
  --sync-radicale            Принудительно отправить события на CalDAV-сервер
  --no-radicale              Отключить отправку в Radicale
  --no-ics                   Отключить локальный файл .ics
  --no-excel                 Отключить файл Excel (.xlsx)
  --no-json                  Отключить файл JSON
  --semester-start <ДАТА>    Начало семестра (ГГГГ-ММ-ДД, по умолч.: '2026-09-01')
  --semester-end <ДАТА>      Конец семестра (ГГГГ-ММ-ДД, по умолч.: '2027-01-31')

ВЕБ-ПРОСМОТРЩИК И DOCKER:
  --serve, --server          Запустить встроенный веб-сервер и web_viewer.html
  --port <ПОРТ>              Порт веб-сервера (по умолчанию: 8081)
  --interval <СЕК>           Период фоновой синхронизации в Docker-контейнере (сек)

ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (.env):
  SCHEDULE_GROUP, SCHEDULE_TEACHER, RADICALE_URL, RADICALE_USER, RADICALE_PASSWORD,
  RADICALE_CALENDAR, EXPORT_RADICALE, EXPORT_ICS, EXPORT_EXCEL, EXPORT_JSON,
  SEMESTER_START_DATE, SEMESTER_END_DATE, TEACHER_ALARM, RUN_SERVER, PORT, SYNC_INTERVAL
"""
    print(helpText)


def RunScheduleCycle(serviceInstance, pTargetGroup, pTargetTeacher, pConfig, currentDirectory, groupsCachePath):
    """
    Выполнение одного цикла загрузки, обработки, фильтрации и экспорта расписания.
    """
    semStart = pConfig["semester_start"]
    semEnd = pConfig["semester_end"]
    alarmMin = pConfig.get("alarm_minutes")

    # 1. Режим преподавателя
    if pTargetTeacher:
        fallbackJsonPath = os.path.join(currentDirectory, "output", "groups", f"schedule_{pTargetGroup}.json")
        fullSchedule = serviceInstance.fetchTeacherSchedule(
            pTeacherQuery=pTargetTeacher,
            pGroupNameOrId=pTargetGroup,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=fallbackJsonPath
        )

        teacherTitle = fullSchedule.groupName
        print(f"\n🎓 Персональный модуль преподавателя: {teacherTitle}")

        # Фича: Визитная карточка преподавателя
        if pConfig.get("show_card"):
            print("\n" + TeacherTools.renderTeacherCard(fullSchedule))

        # Фича: Расчет педагогической нагрузки и окон
        if pConfig.get("show_workload"):
            stats = TeacherTools.calculateWorkload(fullSchedule)
            print("\n" + "═" * 70)
            print(f"📊 ПЕДАГОГИЧЕСКАЯ НАГРУЗКА: {teacherTitle}")
            print("═" * 70)
            print(f"  • Всего пар в сетке расписания:   {stats['total_unique_lessons']}")
            print(f"  • Пар на нечетной (красной) нед.:  {stats['classes_red_week']}")
            print(f"  • Пар на четной (синей) неделе:    {stats['classes_blue_week']}")
            print(f"  • Средняя нагрузка в неделю:       {stats['classes_weekly_avg']} пар ({stats['academic_hours_week']} акад. час.)")
            print(f"  • Нагрузка за семестр (~17 нед.):  {stats['academic_hours_semester']} акад. час.")
            print("\n  Распределение по формам занятий:")
            for lt, cnt in stats["by_type"].items():
                print(f"    - {lt:<20}: {cnt} пар ({round(cnt / stats['total_unique_lessons'] * 100)}%)")
            print("\n  Закрепленные академические группы:")
            for grp, cnt in stats["by_group"].items():
                print(f"    - {grp:<20}: {cnt} пар в неделю")
            print("\n  Используемые аудитории:")
            for room, cnt in stats["by_classroom"].items():
                print(f"    - {room:<20}: {cnt} занятий")

            if stats["gaps"]:
                print("\n  ⚠️ Обнаруженные окна между парами в течение дня:")
                for gap in stats["gaps"]:
                    print(f"    - {gap['day']}: перерыв {gap['duration_minutes']} мин между парами ({gap['after']} и {gap['before']})")
            else:
                print("\n  ✓ Окон между парами не обнаружено (компактное расписание).")
            print("═" * 70)

        # Фича: Проверка коллизий
        if pConfig.get("check_conflicts"):
            conflicts = TeacherTools.checkConflicts(fullSchedule)
            print("\n" + "═" * 70)
            print(f"🔍 АУДИТ КОЛЛИЗИЙ И НАКЛАДОК: {teacherTitle}")
            print("═" * 70)
            if not conflicts:
                print("  ✓ Коллизий не обнаружено! Расписание составлено корректно, пересечений нет.")
            else:
                for c in conflicts:
                    if c["type"] == "HARD_CONFLICT":
                        print(f"  ❌ НАКЛАДКА ({c['day']} {c['time']}, неделя {c['week']}):")
                        print(f"     Пара 1: {c['lesson1']}")
                        print(f"     Пара 2: {c['lesson2']}")
                        print(f"     {c['description']}")
                    elif c["type"] == "CAMPUS_HOP":
                        print(f"  ⚠️ БЫСТРАЯ СМЕНА КОРПУСА ({c['day']} {c['time']}):")
                        print(f"     {c['description']}")
            print("═" * 70)

        # Фича: Методические (свободные) дни
        if pConfig.get("show_free_days"):
            freeInfo = TeacherTools.getFreeDays(fullSchedule)
            print("\n" + "═" * 70)
            print(f"🏖️ МЕТОДИЧЕСКИЕ И НАУЧНЫЕ ДНИ: {teacherTitle}")
            print("═" * 70)
            if freeInfo["fully_free"]:
                print(f"  • Полностью свободные дни (нет пар): {', '.join(freeInfo['fully_free'])}")
            else:
                print("  • Полностью свободных рабочих дней в сетке нет.")
            if freeInfo["free_red_week"]:
                print(f"  • Свободен на красной неделе:        {', '.join(freeInfo['free_red_week'])}")
            if freeInfo["free_blue_week"]:
                print(f"  • Свободен на синей неделе:          {', '.join(freeInfo['free_blue_week'])}")
            print("═" * 70)

        # Фича: Ближайшая пара
        if pConfig.get("show_upcoming"):
            upcoming = TeacherTools.getUpcomingLesson(fullSchedule)
            print("\n" + "═" * 70)
            print(f"⏰ БЛИЖАЙШЕЕ ЗАНЯТИЕ:")
            print("═" * 70)
            if upcoming:
                print(f"  👉 {upcoming['description']}")
            else:
                print("  В сетке расписания занятий не найдено.")
            print("═" * 70)

        # Фича: Журнал посещаемости и успеваемости БРС в Excel
        if pConfig.get("generate_roster"):
            rosterDir = os.path.join(currentDirectory, "output", "teachers")
            sanitizedTeacher = fullSchedule.groupName.replace(" ", "_").replace("/", "_")
            rosterPath = os.path.join(rosterDir, f"Ведомость_БРС_{sanitizedTeacher}.xlsx")
            TeacherTools.generateAttendanceRoster(fullSchedule, rosterPath, semStart, semEnd)
            print(f"📋 Сформирован журнал посещаемости и ведомость БРС (Excel): {rosterPath}")

        # Применение фильтров (сегодня / завтра / день / четность / корпус)
        displaySchedule = TeacherTools.filterSchedule(
            fullSchedule,
            pDayFilter=pConfig.get("day_filter"),
            pWeekFilter=pConfig.get("week_filter"),
            pBuildingFilter=pConfig.get("building_filter"),
            pSemesterStartDate=semStart
        )

        # Вывод расписания в терминал
        if not pConfig.get("quiet"):
            formatType = pConfig.get("format", "table")
            print("\n" + f"📅 Расписание занятий ({teacherTitle}):")
            if pConfig.get("day_filter"):
                print(f"   [Фильтр по дню]: {pConfig.get('day_filter')}")
            if pConfig.get("week_filter"):
                print(f"   [Фильтр по неделе]: {pConfig.get('week_filter')}")
            if pConfig.get("building_filter"):
                print(f"   [Фильтр по корпусу]: {pConfig.get('building_filter')}")

            if formatType == "compact":
                print(TeacherTools.renderCompactList(displaySchedule))
            elif formatType == "markdown":
                print(TeacherTools.renderMarkdown(displaySchedule))
            elif formatType == "json":
                print(json.dumps(displaySchedule.toDictionary(), ensure_ascii=False, indent=2))
            else:
                print(TeacherTools.renderAsciiTable(displaySchedule))

        # Экспорт в файлы
        outputTeachersDir = os.path.join(currentDirectory, "output", "teachers")
        os.makedirs(outputTeachersDir, exist_ok=True)
        sanitizedName = fullSchedule.groupName.replace(" ", "_").replace("/", "_")
        jsonFilePath = os.path.join(outputTeachersDir, f"{sanitizedName}.json")
        excelFilePath = os.path.join(outputTeachersDir, f"{sanitizedName}.xlsx")
        icsFilePath = os.path.join(outputTeachersDir, f"{sanitizedName}.ics")

        if pConfig["export_json"]:
            serviceInstance.saveToJson(fullSchedule, jsonFilePath)
        if pConfig["export_excel"]:
            serviceInstance.saveToExcel(fullSchedule, excelFilePath)
        if pConfig["export_ics"]:
            serviceInstance.saveToIcs(fullSchedule, icsFilePath, semStart, semEnd, pAlarmMinutes=alarmMin)

        totalLessons = sum(len(items) for items in fullSchedule.daysMap.values())
        print(f"\n💾 Экспорт файлов для '{teacherTitle}' (всего пар: {totalLessons}):")
        if pConfig["export_json"]:
            print(f"  • JSON:     {jsonFilePath}")
        if pConfig["export_excel"]:
            print(f"  • Excel:    {excelFilePath}")
        if pConfig["export_ics"]:
            alarmNote = f" (с напоминанием за {alarmMin} мин)" if alarmMin else ""
            print(f"  • iCal .ics:{icsFilePath}{alarmNote}")

        # Синхронизация с сервером Radicale
        if pConfig["export_radicale"]:
            syncReport = serviceInstance.syncToRadicale(
                pGroupSchedule=fullSchedule,
                pRadicaleUrl=pConfig["radicale_url"],
                pUsername=pConfig["radicale_user"],
                pPassword=pConfig["radicale_pass"],
                pCalendarName=pConfig["radicale_cal"],
                pSemesterStartDate=semStart,
                pSemesterEndDate=semEnd,
                pAlarmMinutes=alarmMin
            )
            print(f"  • {syncReport['message']}")
        return

    # 2. Режим академической группы
    outputGroupsDir = os.path.join(currentDirectory, "output", "groups")
    os.makedirs(outputGroupsDir, exist_ok=True)
    targetFallback = os.path.join(outputGroupsDir, f"schedule_{pTargetGroup}.json")

    try:
        scheduleObject = serviceInstance.fetchSchedule(
            pGroupNameOrId=pTargetGroup,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=targetFallback
        )
    except Exception as executionError:
        print(f"Ошибка при загрузке расписания: {executionError}")
        return

    groupTitle = scheduleObject.groupName

    # Фильтры для группы
    displaySchedule = TeacherTools.filterSchedule(
        scheduleObject,
        pDayFilter=pConfig.get("day_filter"),
        pWeekFilter=pConfig.get("week_filter"),
        pBuildingFilter=pConfig.get("building_filter"),
        pSemesterStartDate=semStart
    )

    if not pConfig.get("quiet"):
        formatType = pConfig.get("format", "table")
        print(f"\n📅 Расписание занятий группы {groupTitle}:")
        if formatType == "compact":
            print(TeacherTools.renderCompactList(displaySchedule))
        elif formatType == "markdown":
            print(TeacherTools.renderMarkdown(displaySchedule))
        elif formatType == "json":
            print(json.dumps(displaySchedule.toDictionary(), ensure_ascii=False, indent=2))
        else:
            print(TeacherTools.renderAsciiTable(displaySchedule))

    cleanGroupName = groupTitle.replace("/", "_").replace("\\", "_")
    jsonFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.json")
    excelFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.xlsx")
    icsFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.ics")

    if pConfig["export_json"]:
        serviceInstance.saveToJson(scheduleObject, jsonFilePath)
    if pConfig["export_excel"]:
        serviceInstance.saveToExcel(scheduleObject, excelFilePath)
    if pConfig["export_ics"]:
        serviceInstance.saveToIcs(scheduleObject, icsFilePath, semStart, semEnd, pAlarmMinutes=alarmMin)

    totalLessons = sum(len(items) for items in scheduleObject.daysMap.values())
    print(f"\n💾 Экспорт файлов группы {groupTitle} (всего пар: {totalLessons}):")
    if pConfig["export_json"]:
        print(f"  • JSON:     {jsonFilePath}")
    if pConfig["export_excel"]:
        print(f"  • Excel:    {excelFilePath}")
    if pConfig["export_ics"]:
        alarmNote = f" (с напоминанием за {alarmMin} мин)" if alarmMin else ""
        print(f"  • iCal .ics:{icsFilePath}{alarmNote}")

    # Синхронизация с сервером Radicale
    if pConfig["export_radicale"]:
        syncReport = serviceInstance.syncToRadicale(
            pGroupSchedule=scheduleObject,
            pRadicaleUrl=pConfig["radicale_url"],
            pUsername=pConfig["radicale_user"],
            pPassword=pConfig["radicale_pass"],
            pCalendarName=pConfig["radicale_cal"],
            pSemesterStartDate=semStart,
            pSemesterEndDate=semEnd,
            pAlarmMinutes=alarmMin
        )
        print(f"  • {syncReport['message']}")


def ExecuteMain():
    """
    Основная процедура консольного запуска программы.
    Выполняет инициализацию сервиса расписания, обработку параметров вызова и экспорт отчетов.
    """
    if "-h" in sys.argv or "--help" in sys.argv:
        PrintUsage()
        return

    serviceInstance = TstuScheduleService()
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    groupsCachePath = os.path.join(currentDirectory, "data", "groups_list.json")

    # Чтение переменных окружения
    envDefaultGroup = os.environ.get("SCHEDULE_GROUP") or os.environ.get("GROUP_NAME") or "Б.ПИН.ИИ.25.16"
    envTeacher = os.environ.get("SCHEDULE_TEACHER") or os.environ.get("TEACHER_NAME")

    radicaleUrlEnv = os.environ.get("RADICALE_URL")
    radicaleUserEnv = os.environ.get("RADICALE_USER", "tstu")
    radicalePassEnv = os.environ.get("RADICALE_PASSWORD", "")
    radicaleCalEnv = os.environ.get("RADICALE_CALENDAR", "schedule")

    # 1. Режим вывода каталога доступных групп
    if "--list-groups" in sys.argv:
        serviceInstance.loadGroupsCatalog(groupsCachePath)
        listIndex = sys.argv.index("--list-groups")
        filterLevel = ""
        if listIndex + 1 < len(sys.argv) and not sys.argv[listIndex + 1].startswith("--"):
            filterArg = sys.argv[listIndex + 1].lower()
            if "магистр" in filterArg or filterArg == "м":
                filterLevel = "М."
            elif "бакалавр" in filterArg or filterArg == "б":
                filterLevel = "Б."
            elif "специал" in filterArg or filterArg == "с":
                filterLevel = "С."
            elif "колледж" in filterArg or "спо" in filterArg:
                filterLevel = "СПО."
            elif "аспирант" in filterArg or filterArg == "а":
                filterLevel = "А."

        matched = [g for g in serviceInstance.cachedGroupsMap.keys() if g.startswith(filterLevel)]
        levelName = "Все уровни подготовки"
        if filterLevel == "М.":
            levelName = "Магистратура"
        elif filterLevel == "Б.":
            levelName = "Бакалавриат"
        elif filterLevel == "С.":
            levelName = "Специалитет"
        elif filterLevel == "СПО.":
            levelName = "Колледж (СПО)"
        elif filterLevel == "А.":
            levelName = "Аспирантура"

        print(f"Каталог академических групп ТвГТУ ({levelName}, найдено: {len(matched)}):")
        for idx, grp in enumerate(matched[:40], 1):
            print(f"  {idx:2d}. {grp:<20} (ID шлюза: {serviceInstance.cachedGroupsMap[grp]})")
        if len(matched) > 40:
            print(f"  ... и еще {len(matched) - 40} групп. Используйте поиск по подстроке.")
        return

    # 2. Интерактивный режим консольного выбора группы
    if "--select-group" in sys.argv:
        serviceInstance.loadGroupsCatalog(groupsCachePath)
        print("\n--- Интерактивный выбор учебной группы ТвГТУ (Вариант 2) ---")
        print("1. Бакалавриат (префикс 'Б.')")
        print("2. Магистратура (префикс 'М.')")
        print("3. Специалитет (префикс 'С.')")
        print("4. Колледж / СПО (префикс 'СПО.')")
        print("5. Все группы")
        levelChoice = input("Выберите категорию (1-5, по умолчанию 2 - Магистратура): ").strip() or "2"
        prefixMap = {"1": "Б.", "2": "М.", "3": "С.", "4": "СПО.", "5": ""}
        selectedPrefix = prefixMap.get(levelChoice, "М.")

        queryStr = input("Введите поисковый запрос (или Enter для списка): ").strip().lower()
        candidates = [g for g in serviceInstance.cachedGroupsMap.keys() if g.startswith(selectedPrefix) and (not queryStr or queryStr in g.lower())]

        if not candidates:
            print("Группы по вашему запросу не найдены.")
            return

        print(f"\nНайдено групп: {len(candidates)}")
        for i, grp in enumerate(candidates[:20], 1):
            print(f"  {i}. {grp} (ID: {serviceInstance.cachedGroupsMap[grp]})")

        pick = input(f"Выберите номер группы (1-{min(len(candidates), 20)}): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= min(len(candidates), 20):
            targetGroupName = candidates[int(pick) - 1]
            print(f"Выбрана группа: {targetGroupName}\n")
        else:
            print("Выбор отменен.")
            return
    else:
        # Определение группы через --group, позиционный аргумент или переменную окружения
        if "--group" in sys.argv:
            targetGroupName = _getArgValue("--group", envDefaultGroup)
        elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            targetGroupName = sys.argv[1]
        else:
            targetGroupName = envDefaultGroup

    # 3. Определение преподавателя (аргументы, шорткаты или переменная окружения)
    targetTeacher = None
    if "--sozonov" in sys.argv or "--sozontov" in sys.argv or "--me" in sys.argv:
        targetTeacher = "Созонов"
    elif "--teacher" in sys.argv:
        targetTeacher = _getArgValue("--teacher")
        if not targetTeacher:
            print("Ошибка: после ключа --teacher необходимо указать фамилию или ФИО преподавателя.")
            return
    elif envTeacher:
        targetTeacher = envTeacher

    # 4. Режим вывода списка преподавателей
    if "--teachers-list" in sys.argv:
        fallbackJsonPath = os.path.join(currentDirectory, "output", "groups", f"schedule_{targetGroupName}.json")
        teachers = serviceInstance.getAvailableTeachers(
            pGroupNameOrId=targetGroupName,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=fallbackJsonPath
        )
        print(f"Список преподавателей, ведущих занятия в ТвГТУ ({targetGroupName}, всего: {len(teachers)}):")
        for idx, t in enumerate(teachers, 1):
            print(f"  {idx:2d}. {t}")
        return

    # 5. Режим открытия просмотрщика в браузере
    if "--viewer" in sys.argv or "--web" in sys.argv:
        import webbrowser
        viewerHtmlPath = os.path.join(currentDirectory, "web_viewer.html")
        print(f"Открытие интерактивного интерфейса: {viewerHtmlPath}")
        webbrowser.open(f"file:///{viewerHtmlPath.replace(os.sep, '/')}")
        return

    # 6. Режим запуска локального веб-сервера
    portNumber = int(_getArgValue("--port", os.environ.get("PORT") or os.environ.get("SERVE_PORT") or 8081))
    if "--serve" in sys.argv or "--server" in sys.argv or _getBoolEnv("RUN_SERVER", False) or _getBoolEnv("SERVE_MODE", False):
        import http.server
        import socketserver
        os.chdir(currentDirectory)
        serverHandler = http.server.SimpleHTTPRequestHandler
        serverHandler.extensions_map.update({
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".ics": "text/calendar",
        })
        with socketserver.TCPServer(("", portNumber), serverHandler) as httpDaemon:
            print(f"Сервер интерактивного расписания запущен: http://0.0.0.0:{portNumber}/web_viewer.html")
            try:
                httpDaemon.serve_forever()
            except KeyboardInterrupt:
                print("\nСервер остановлен.")
        return

    # 7. Конфигурация экспортеров и флагов преподавателя
    exportJson = False if "--no-json" in sys.argv else _getBoolEnv("EXPORT_JSON", True)
    exportExcel = False if "--no-excel" in sys.argv else _getBoolEnv("EXPORT_EXCEL", True)
    exportIcs = False if "--no-ics" in sys.argv else _getBoolEnv("EXPORT_ICS", True)

    radicaleUrl = _getArgValue("--radicale-url", radicaleUrlEnv or "http://localhost:5232")
    radicaleUser = _getArgValue("--radicale-user", radicaleUserEnv)
    radicalePass = _getArgValue("--radicale-pass", radicalePassEnv)
    radicaleCal = _getArgValue("--radicale-cal", radicaleCalEnv)

    if "--no-radicale" in sys.argv:
        exportRadicale = False
    elif "--sync-radicale" in sys.argv:
        exportRadicale = True
    elif "EXPORT_RADICALE" in os.environ:
        exportRadicale = _getBoolEnv("EXPORT_RADICALE", True)
    else:
        exportRadicale = bool(radicaleUrlEnv) or ("--radicale-url" in sys.argv)

    semesterStart = _getArgValue("--semester-start", os.environ.get("SEMESTER_START_DATE") or "2026-09-01")
    semesterEnd = _getArgValue("--semester-end", os.environ.get("SEMESTER_END_DATE") or "2027-01-31")
    syncInterval = int(_getArgValue("--interval", os.environ.get("SYNC_INTERVAL") or 0))

    # Обработка фильтров времени и дней
    dayFilter = None
    if "--today" in sys.argv:
        dayFilter = "today"
    elif "--tomorrow" in sys.argv:
        dayFilter = "tomorrow"
    elif "--day" in sys.argv:
        dayFilter = _getArgValue("--day")
    elif os.environ.get("TEACHER_DAY"):
        dayFilter = os.environ.get("TEACHER_DAY")

    weekFilter = None
    if "--current-week" in sys.argv:
        weekFilter = "current"
    elif "--week" in sys.argv:
        weekFilter = _getArgValue("--week")
    elif os.environ.get("TEACHER_WEEK"):
        weekFilter = os.environ.get("TEACHER_WEEK")

    buildingFilter = _getArgValue("--building")

    # Обработка напоминаний
    alarmMinutes = None
    alarmArg = _getArgValue("--alarm", os.environ.get("TEACHER_ALARM") or os.environ.get("RADICALE_ALARM"))
    if alarmArg and alarmArg.isdigit():
        alarmMinutes = int(alarmArg)

    config = {
        "export_json": exportJson,
        "export_excel": exportExcel,
        "export_ics": exportIcs,
        "export_radicale": exportRadicale,
        "radicale_url": radicaleUrl,
        "radicale_user": radicaleUser,
        "radicale_pass": radicalePass,
        "radicale_cal": radicaleCal,
        "semester_start": semesterStart,
        "semester_end": semesterEnd,
        "alarm_minutes": alarmMinutes,
        "day_filter": dayFilter,
        "week_filter": weekFilter,
        "building_filter": buildingFilter,
        "show_workload": ("--workload" in sys.argv or "--stats" in sys.argv or _getBoolEnv("TEACHER_WORKLOAD", False)),
        "check_conflicts": ("--conflicts" in sys.argv or "--check-conflicts" in sys.argv),
        "show_free_days": ("--free-days" in sys.argv or "--method-days" in sys.argv),
        "show_upcoming": ("--next" in sys.argv or "--upcoming" in sys.argv),
        "show_card": ("--card" in sys.argv or "--summary" in sys.argv),
        "generate_roster": ("--attendance-sheet" in sys.argv or "--roster" in sys.argv or _getBoolEnv("TEACHER_ROSTER", False)),
        "format": _getArgValue("--format", "table"),
        "quiet": ("--quiet" in sys.argv)
    }

    # Выполнение основного цикла
    RunScheduleCycle(serviceInstance, targetGroupName, targetTeacher, config, currentDirectory, groupsCachePath)

    # При наличии интервала синхронизации запускаем периодический цикл (для сервиса в Docker)
    if syncInterval > 0:
        print(f"\nЗапущен фоновый режим периодической синхронизации (интервал: {syncInterval} сек).")
        try:
            while True:
                time.sleep(syncInterval)
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Плановое обновление расписания...")
                RunScheduleCycle(serviceInstance, targetGroupName, targetTeacher, config, currentDirectory, groupsCachePath)
        except KeyboardInterrupt:
            print("\nФоновый процесс синхронизации остановлен.")
# end of ExecuteMain


if __name__ == "__main__":
    ExecuteMain()
# end of Main.py
