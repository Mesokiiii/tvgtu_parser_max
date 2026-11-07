# Main.py Точка входа модуля авторизации, выбора групп и парсинга через мессенджер MAX
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Разработчик ФИТ Добавлена поддержка выбора групп (в т.ч. магистратуры) и интерактивный CLI
# Назначение: конфигурирование зависимостей и запуск в консольном или серверном режиме

import os
import sys
from core.session_manager import SessionManager
from core.auth_client import MaxAuthClient
from core.schedule_client import MaxScheduleClient
from exporters.excel_exporter import MaxExcelExporter
from exporters.json_exporter import MaxJsonExporter
from web.http_server import WebControlServer

DEFAULT_PORT = 8080


def ExecuteMain():
    """
    Основная процедура инициализации зависимостей и маршрутизации запуска.
    """
    baseDir = os.path.dirname(os.path.abspath(__file__))
    tokensPath = os.path.join(baseDir, "data", "tokens.json")
    cachedSchedulePath = os.path.join(baseDir, "data", "cached_schedule_pin.json")
    webDirPath = os.path.join(baseDir, "web")

    # Инициализация доменных сервисов с внедрением зависимостей
    authClt = MaxAuthClient()
    sessionMgr = SessionManager(tokensPath, pAuthClient=authClt)
    scheduleClt = MaxScheduleClient(sessionMgr, authClt)
    excelExp = MaxExcelExporter()
    jsonExp = MaxJsonExporter()

    # 1. Режим вывода каталога доступных групп (включая магистратуру)
    if "--list-groups" in sys.argv:
        listIndex = sys.argv.index("--list-groups")
        filterLevel = ""
        if listIndex + 1 < len(sys.argv) and not sys.argv[listIndex + 1].startswith("--"):
            filterArg = sys.argv[listIndex + 1].lower()
            if "магистр" in filterArg or filterArg == "м":
                filterLevel = "М"
            elif "бакалавр" in filterArg or filterArg == "б":
                filterLevel = "Б"
            elif "специал" in filterArg or filterArg == "с":
                filterLevel = "С"
            elif "колледж" in filterArg or "спо" in filterArg:
                filterLevel = "СПО"
            elif "аспирант" in filterArg or filterArg == "а":
                filterLevel = "А"
            # end of if filterArg
        # end of if listIndex + 1

        matchedGroups = sessionMgr.searchGroups(pLevel=filterLevel)
        levelTitle = {
            "М": "Магистратура",
            "Б": "Бакалавриат",
            "С": "Специалитет",
            "СПО": "Колледж (СПО)",
            "А": "Аспирантура"
        }.get(filterLevel, "Все уровни подготовки")

        print(f"Каталог академических групп ТвГТУ ({levelTitle}, найдено: {len(matchedGroups)}):")
        for idx, grp in enumerate(matchedGroups[:40], 1):
            print(f"  {idx:2d}. {grp['name']:<20} (ID в MAX: {grp['id']})")
        # end of for idx, grp
        if len(matchedGroups) > 40:
            print(f"  ... и еще {len(matchedGroups) - 40} групп. Используйте поиск по подстроке.")
        # end of if len(matchedGroups)
        return
    # end of if "--list-groups"

    # 2. Режим явного указания или смены целевой группы через CLI
    if "--group" in sys.argv:
        groupIndex = sys.argv.index("--group")
        if groupIndex + 1 < len(sys.argv):
            targetGroupQuery = sys.argv[groupIndex + 1]
            foundGroup = sessionMgr.findGroupByName(targetGroupQuery)
            if foundGroup:
                sessionMgr.setTargetGroup(foundGroup["id"], foundGroup["name"])
                print(f"Целевая группа успешно установлена: {foundGroup['name']} (ID: {foundGroup['id']})")
            else:
                if targetGroupQuery.isdigit():
                    sessionMgr.setTargetGroup(int(targetGroupQuery), f"Группа_{targetGroupQuery}")
                    print(f"Установлен числовой ID группы: {targetGroupQuery}")
                else:
                    sessionMgr.setTargetGroup(sessionMgr.getTargetGroupId(), targetGroupQuery)
                    print(f"Установлено наименование группы: {targetGroupQuery}")
                # end of if targetGroupQuery.isdigit()
            # end of if foundGroup
        else:
            print("Ошибка: укажите шифр группы после флага --group (например, --group М.ПИН.РИС.25.09).")
            return
        # end of if groupIndex + 1

        if "--fetch" not in sys.argv:
            return
        # end of if "--fetch"
    # end of if "--group"

    # 3. Интерактивный режим консольного выбора группы
    if "--select-group" in sys.argv:
        print("\n--- Интерактивный выбор учебной группы ТвГТУ ---")
        print("1. Бакалавриат (префикс 'Б.')")
        print("2. Магистратура (префикс 'М.')")
        print("3. Специалитет (префикс 'С.')")
        print("4. Колледж / СПО (префикс 'СПО.')")
        print("5. Все группы")
        levelChoice = input("Выберите категорию (1-5, по умолчанию 2 - Магистратура): ").strip() or "2"
        levelCodeMap = {"1": "Б", "2": "М", "3": "С", "4": "СПО", "5": ""}
        selectedLevel = levelCodeMap.get(levelChoice, "М")

        queryStr = input("Введите поисковый запрос (или Enter для списка): ").strip()
        candidates = sessionMgr.searchGroups(pQuery=queryStr, pLevel=selectedLevel)

        if not candidates:
            print("Группы по вашему запросу не найдены.")
            return
        # end of if not candidates

        print(f"\nНайдено групп: {len(candidates)}")
        for i, grp in enumerate(candidates[:20], 1):
            print(f"  {i}. {grp['name']} (ID: {grp['id']})")
        # end of for i, grp

        pick = input(f"Выберите номер группы (1-{min(len(candidates), 20)}): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= min(len(candidates), 20):
            selectedItem = candidates[int(pick) - 1]
            sessionMgr.setTargetGroup(selectedItem["id"], selectedItem["name"])
            print(f"Выбрана и сохранена группа: {selectedItem['name']} (ID: {selectedItem['id']})\n")
        else:
            print("Выбор отменен.")
            return
        # end of if pick.isdigit()
    # end of if "--select-group"

    # 4. Режим поиска расписания преподавателя
    if "--teacher" in sys.argv:
        teacherIndex = sys.argv.index("--teacher")
        if teacherIndex + 1 < len(sys.argv):
            teacherQuery = sys.argv[teacherIndex + 1]
        else:
            print("Ошибка: укажите фамилию преподавателя после --teacher.")
            return
        # end of if teacherIndex + 1

        teacherDays = scheduleClt.fetchTeacherSchedule(teacherQuery, pFallbackFilePath=cachedSchedulePath)
        title = f"Преподаватель_{teacherQuery.replace(' ', '_')}"
        outputTeachersDir = os.path.join(baseDir, "output", "teachers")
        os.makedirs(outputTeachersDir, exist_ok=True)
        excelFilePath = os.path.join(outputTeachersDir, f"{title}.xlsx")
        jsonFilePath = os.path.join(outputTeachersDir, f"{title}.json")

        excelExp.export(teacherDays, f"Преподаватель {teacherQuery}", excelFilePath)
        jsonExp.export(teacherDays, jsonFilePath)

        totalLessons = sum(sum(len(s.get("events", [])) for s in d.get("slots", [])) for d in teacherDays)
        print(f"Поиск расписания преподавателя '{teacherQuery}' в MAX завершен.")
        print(f"Найдено занятий: {totalLessons}")
        print(f"Файл Excel: {excelFilePath}")
        print(f"Файл JSON: {jsonFilePath}")
        return
    # end of if "--teacher"

    # 5. Режим прямого скачивания расписания группы из командной строки
    if "--fetch" in sys.argv:
        try:
            targetGrpId = sessionMgr.getTargetGroupId()
            targetGrpName = sessionMgr.getTargetGroupName()
            scheduleDays = scheduleClt.fetchSchedule(pGroupId=targetGrpId, pFallbackFilePath=cachedSchedulePath)
            
            cleanGroupName = targetGrpName.replace("/", "_").replace("\\", "_")
            outputGroupsDir = os.path.join(baseDir, "output", "groups")
            os.makedirs(outputGroupsDir, exist_ok=True)
            excelFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.xlsx")
            jsonFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.json")

            excelExp.export(scheduleDays, targetGrpName, excelFilePath)
            jsonExp.export(scheduleDays, jsonFilePath)

            print(f"Экспорт расписания MAX для группы '{targetGrpName}' завершен.")
            print(f"Файл Excel: {excelFilePath}")
            print(f"Файл JSON: {jsonFilePath}")
        except Exception as executionError:
            print(f"Ошибка при выгрузке расписания: {executionError}")
        # end of try
        return
    # end of if "--fetch"

    # 6. Режим ручного обновления токена из консоли
    if "--refresh" in sys.argv:
        try:
            refreshToken = sessionMgr.getRefreshToken()
            newAuth = authClt.refreshAccessToken(refreshToken)
            sessionMgr.save({"auth_token": newAuth})
            print(f"Токен успешно обновлен: {newAuth[:20]}...")
        except Exception as refreshError:
            print(f"Ошибка обновления токена: {refreshError}")
        # end of try
        return
    # end of if "--refresh"

    # 7. Режим по умолчанию: запуск локального веб-сервера управления
    controlServer = WebControlServer(
        pPort=DEFAULT_PORT,
        pSessionManager=sessionMgr,
        pAuthClient=authClt,
        pScheduleClient=scheduleClt,
        pExcelExporter=excelExp,
        pJsonExporter=jsonExp,
        pWebDir=webDirPath
    )
    controlServer.start()
# end of ExecuteMain


if __name__ == "__main__":
    ExecuteMain()
# end of Main.py
