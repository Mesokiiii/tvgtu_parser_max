# Main.py Консольная точка входа прямого модуля расписания ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Разработчик ФИТ Добавлена поддержка выбора групп (в т.ч. магистратуры), каталога и интерактивного меню
# Назначение: консольный запуск загрузки расписания групп и преподавателей

import os
import sys
from schedule_service import TstuScheduleService


def ExecuteMain():
    """
    Основная процедура консольного запуска программы.
    Выполняет инициализацию сервиса расписания, обработку параметров вызова и экспорт отчетов.
    """
    serviceInstance = TstuScheduleService()
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    groupsCachePath = os.path.join(currentDirectory, "data", "groups_list.json")
    defaultGroup = "Б.ПИН.ИИ.25.16"
    fallbackJsonPath = os.path.join(currentDirectory, "output", "groups", f"schedule_{defaultGroup}.json")

    # 1. Режим вывода каталога доступных групп (включая магистратуру)
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
            # end of if filterArg
        # end of if listIndex + 1

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
        # end of if filterLevel

        print(f"Каталог академических групп ТвГТУ ({levelName}, найдено: {len(matched)}):")
        for idx, grp in enumerate(matched[:40], 1):
            print(f"  {idx:2d}. {grp:<20} (ID шлюза: {serviceInstance.cachedGroupsMap[grp]})")
        # end of for idx, grp
        if len(matched) > 40:
            print(f"  ... и еще {len(matched) - 40} групп. Используйте поиск по подстроке.")
        # end of if len(matched)
        return
    # end of if "--list-groups"

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
        # end of if not candidates

        print(f"\nНайдено групп: {len(candidates)}")
        for i, grp in enumerate(candidates[:20], 1):
            print(f"  {i}. {grp} (ID: {serviceInstance.cachedGroupsMap[grp]})")
        # end of for i, grp

        pick = input(f"Выберите номер группы (1-{min(len(candidates), 20)}): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= min(len(candidates), 20):
            targetGroupName = candidates[int(pick) - 1]
            print(f"Выбрана группа: {targetGroupName}\n")
        else:
            print("Выбор отменен.")
            return
        # end of if pick.isdigit()
    else:
        # Определение целевой группы через флаг --group или позиционный аргумент
        if "--group" in sys.argv:
            grpIdx = sys.argv.index("--group")
            if grpIdx + 1 < len(sys.argv):
                targetGroupName = sys.argv[grpIdx + 1]
            else:
                print("Ошибка: укажите шифр группы после флага --group.")
                return
            # end of if grpIdx + 1
        elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            targetGroupName = sys.argv[1]
        else:
            targetGroupName = defaultGroup
        # end of if "--group"
    # end of if "--select-group"

    # 3. Режим вывода списка преподавателей
    if "--teachers-list" in sys.argv:
        teachers = serviceInstance.getAvailableTeachers(
            pGroupNameOrId=targetGroupName,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=fallbackJsonPath
        )
        print(f"Список преподавателей, ведущих занятия в ТвГТУ ({targetGroupName}, всего: {len(teachers)}):")
        for idx, t in enumerate(teachers, 1):
            print(f"  {idx:2d}. {t}")
        # end of for idx, t
        return
    # end of if "--teachers-list"

    # 4. Режим запуска локального веб-сервера и открытия интерфейса
    if "--serve" in sys.argv or "--server" in sys.argv:
        import http.server
        import socketserver
        import webbrowser
        portNumber = 8081
        os.chdir(currentDirectory)
        serverHandler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", portNumber), serverHandler) as httpDaemon:
            print(f"Сервер интерактивного расписания запущен: http://localhost:{portNumber}/web_viewer.html")
            webbrowser.open(f"http://localhost:{portNumber}/web_viewer.html")
            try:
                httpDaemon.serve_forever()
            except KeyboardInterrupt:
                print("\nСервер остановлен.")
        return
    # end of if "--serve"

    # 5. Режим открытия интерактивного веб-просмотрщика в браузере
    if "--viewer" in sys.argv or "--web" in sys.argv:
        import webbrowser
        viewerHtmlPath = os.path.join(currentDirectory, "web_viewer.html")
        print(f"Открытие интерактивного интерфейса: {viewerHtmlPath}")
        webbrowser.open(f"file:///{viewerHtmlPath.replace(os.sep, '/')}")
        return
    # end of if "--viewer"

    # 6. Режим поиска расписания конкретного преподавателя
    if "--teacher" in sys.argv:
        teacherIndex = sys.argv.index("--teacher")
        if teacherIndex + 1 < len(sys.argv):
            teacherQuery = sys.argv[teacherIndex + 1]
        else:
            print("Ошибка: после ключа --teacher необходимо указать фамилию или ФИО преподавателя.")
            return
        # end of if teacherIndex + 1

        teacherSchedule = serviceInstance.fetchTeacherSchedule(
            pTeacherQuery=teacherQuery,
            pGroupNameOrId=targetGroupName,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=fallbackJsonPath
        )

        outputTeachersDir = os.path.join(currentDirectory, "output", "teachers")
        os.makedirs(outputTeachersDir, exist_ok=True)
        sanitizedName = teacherSchedule.groupName.replace(" ", "_")
        jsonFilePath = os.path.join(outputTeachersDir, f"{sanitizedName}.json")
        excelFilePath = os.path.join(outputTeachersDir, f"{sanitizedName}.xlsx")

        serviceInstance.saveToJson(teacherSchedule, jsonFilePath)
        serviceInstance.saveToExcel(teacherSchedule, excelFilePath)

        totalLessons = sum(len(items) for items in teacherSchedule.daysMap.values())
        print(f"Поиск расписания преподавателя '{teacherQuery}' завершен.")
        print(f"Найдено занятий в сетке: {totalLessons}")
        print(f"Файл данных JSON: {jsonFilePath}")
        print(f"Файл таблицы Excel: {excelFilePath}")
        return
    # end of if "--teacher"

    # 7. Режим расписания учебной группы
    outputGroupsDir = os.path.join(currentDirectory, "output", "groups")
    os.makedirs(outputGroupsDir, exist_ok=True)
    targetFallback = os.path.join(outputGroupsDir, f"schedule_{targetGroupName}.json")

    try:
        scheduleObject = serviceInstance.fetchSchedule(
            pGroupNameOrId=targetGroupName,
            pCacheFilePath=groupsCachePath,
            pFallbackJsonPath=targetFallback
        )
    except Exception as executionError:
        print(f"Ошибка при загрузке расписания: {executionError}")
        return
    # end of try

    groupTitle = scheduleObject.groupName
    cleanGroupName = groupTitle.replace("/", "_").replace("\\", "_")
    jsonFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.json")
    excelFilePath = os.path.join(outputGroupsDir, f"schedule_{cleanGroupName}.xlsx")

    serviceInstance.saveToJson(scheduleObject, jsonFilePath)
    serviceInstance.saveToExcel(scheduleObject, excelFilePath)

    totalLessons = sum(len(items) for items in scheduleObject.daysMap.values())
    print(f"Загрузка и парсинг завершены успешно.")
    print(f"Целевая группа: {groupTitle} (ID в шлюзе: {scheduleObject.groupId})")
    print(f"Всего занятий в расписании: {totalLessons}")
    print(f"Файл данных JSON: {jsonFilePath}")
    print(f"Файл таблицы Excel: {excelFilePath}")
# end of ExecuteMain


if __name__ == "__main__":
    ExecuteMain()
# end of Main.py
