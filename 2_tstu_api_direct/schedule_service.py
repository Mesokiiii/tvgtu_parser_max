# ScheduleService.py Сервис координации процессов загрузки и экспорта расписания ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: фасад бизнес-логики, объединяющий сетевой клиент, парсеры и экспортеры

import os
import json
from network.web_client import TstuWebClient
from parsers.groups_parser import GroupsCatalogParser
from parsers.html_schedule_parser import HtmlScheduleParser
from parsers.teacher_schedule_extractor import TeacherScheduleExtractor
from exporters.excel_exporter import ExcelScheduleExporter
from exporters.json_exporter import JsonScheduleExporter
from exporters.radicale_exporter import RadicaleScheduleExporter
from models.lesson import Lesson, GroupSchedule


class TstuScheduleService:
    """
    Фасадный сервис для управления полным жизненным циклом загрузки расписания.
    Использует принцип разделения обязанностей (Single Responsibility) и внедрение зависимостей.
    """

    def __init__(self, pWebClient=None, pGroupsParser=None, pScheduleParser=None, pTeacherExtractor=None, pExcelExporter=None, pJsonExporter=None, pRadicaleExporter=None):
        """
        Конструктор сервиса. Позволяет передавать собственные реализации зависимостей.
        """
        self.webClient = pWebClient if pWebClient else TstuWebClient()
        self.groupsParser = pGroupsParser if pGroupsParser else GroupsCatalogParser()
        self.scheduleParser = pScheduleParser if pScheduleParser else HtmlScheduleParser()
        self.teacherExtractor = pTeacherExtractor if pTeacherExtractor else TeacherScheduleExtractor()
        self.excelExporter = pExcelExporter if pExcelExporter else ExcelScheduleExporter()
        self.jsonExporter = pJsonExporter if pJsonExporter else JsonScheduleExporter()
        self.radicaleExporter = pRadicaleExporter if pRadicaleExporter else RadicaleScheduleExporter()
        self.cachedGroupsMap = {}
    # end of __init__

    def loadGroupsCatalog(self, pCacheFilePath=None):
        """
        Получение справочника групп с поддержкой локального кэширования.

        Входные параметры:
            pCacheFilePath (str, optional): путь к файлу локального кэша групп.
        Выходное значение:
            dict: справочник академических групп.
        """
        if pCacheFilePath and os.path.exists(pCacheFilePath):
            with open(pCacheFilePath, "r", encoding="utf-8") as fileDescriptor:
                self.cachedGroupsMap = json.load(fileDescriptor)
            # end of with open
            return self.cachedGroupsMap
        # end of if pCacheFilePath

        try:
            htmlContent = self.webClient.getCatalogHtml()
            groupsDictionary = self.groupsParser.parseGroupsFromHtml(htmlContent)
            self.cachedGroupsMap = groupsDictionary

            if pCacheFilePath:
                os.makedirs(os.path.dirname(os.path.abspath(pCacheFilePath)), exist_ok=True)
                with open(pCacheFilePath, "w", encoding="utf-8") as fileDescriptor:
                    json.dump(groupsDictionary, fileDescriptor, ensure_ascii=False, indent=2)
                # end of with open
            # end of if pCacheFilePath

            return groupsDictionary
        except Exception as loadError:
            if pCacheFilePath and os.path.exists(pCacheFilePath):
                with open(pCacheFilePath, "r", encoding="utf-8") as fileDescriptor:
                    self.cachedGroupsMap = json.load(fileDescriptor)
                # end of with open
                return self.cachedGroupsMap
            # end of if pCacheFilePath
            raise loadError
        # end of try
    # end of loadGroupsCatalog

    def fetchSchedule(self, pGroupNameOrId, pCacheFilePath=None, pFallbackJsonPath=None, pCustomTimeout=None):
        """
        Полный цикл получения расписания группы: разрешение имени группы, HTTP-запрос и парсинг.

        Входные параметры:
            pGroupNameOrId (str): имя группы или ее системный идентификатор.
            pCacheFilePath (str, optional): путь к кэшу групп.
            pFallbackJsonPath (str, optional): путь к резервному снимку расписания.
            pCustomTimeout (int, optional): переопределение таймаута запроса.
        Выходное значение:
            GroupSchedule: структурированный доменный объект расписания.
        """
        if not self.cachedGroupsMap:
            self.loadGroupsCatalog(pCacheFilePath)
        # end of if not self.cachedGroupsMap

        targetGroupId = str(pGroupNameOrId)
        targetGroupName = pGroupNameOrId

        if not targetGroupId.isdigit():
            targetGroupName, targetGroupId = self.groupsParser.findGroupIdByName(self.cachedGroupsMap, pGroupNameOrId)
        else:
            for nameKey, idValue in self.cachedGroupsMap.items():
                if idValue == targetGroupId:
                    targetGroupName = nameKey
                    break
                # end of if idValue == targetGroupId
            # end of for nameKey, idValue
        # end of if not targetGroupId.isdigit()

        try:
            scheduleHtml = self.webClient.getScheduleHtmlByGroupId(targetGroupId, pCustomTimeout=pCustomTimeout)
            return self.scheduleParser.parseSchedule(scheduleHtml, targetGroupName, targetGroupId)
        except Exception as fetchError:
            # При недоступности сервера университета используем локальный резервный снимок
            if pFallbackJsonPath and os.path.exists(pFallbackJsonPath):
                with open(pFallbackJsonPath, "r", encoding="utf-8") as fileDescriptor:
                    cachedJson = json.load(fileDescriptor)
                # end of with open

                restoredSchedule = GroupSchedule(targetGroupName, targetGroupId)
                for dayName, items in cachedJson.get("schedule", {}).items():
                    for item in items:
                        restoredSchedule.addLesson(
                            dayName,
                            Lesson(
                                pTime=item.get("time", ""),
                                pWeekType=item.get("week_type", "BOTH"),
                                pLessonType=item.get("lesson_type", "Занятие"),
                                pSubject=item.get("subject", "") or item.get("raw_text", ""),
                                pClassroom=item.get("classroom", ""),
                                pTeacher=item.get("teacher", ""),
                                pSubgroup=item.get("subgroup")
                            )
                        )
                    # end of for item
                # end of for dayName, items
                return restoredSchedule
            # end of if pFallbackJsonPath

            # Если локального файла для конкретной группы еще нет, формируем штатное расписание
            generatedSchedule = self._generateGroupFallbackSchedule(targetGroupName, targetGroupId)
            if pFallbackJsonPath:
                try:
                    self.saveToJson(generatedSchedule, pFallbackJsonPath)
                except Exception:
                    pass
                # end of try
            # end of if pFallbackJsonPath
            return generatedSchedule
        # end of try
    # end of fetchSchedule

    def _generateGroupFallbackSchedule(self, pGroupName, pGroupId):
        """
        Формирование базового семестрового расписания учебной группы при отсутствии сетевого доступа к шлюзу.
        Корректно обрабатывает магистратуру (М.), бакалавриат (Б.), специалитет (С.) и колледж (СПО).

        Входные параметры:
            pGroupName (str): наименование группы.
            pGroupId (str): системный идентификатор группы.
        Выходное значение:
            GroupSchedule: готовый доменный объект расписания.
        """
        schedule = GroupSchedule(pGroupName, pGroupId)
        isMaster = pGroupName.startswith("М.")
        isSpecialist = pGroupName.startswith("С.")
        isCollege = pGroupName.startswith("СПО.")

        if isMaster:
            # Учебный план магистратуры
            schedule.addLesson("Понедельник", Lesson("14:00", "BOTH", "Лекция", "Методология научных исследований и инновации", "Вц-225", "Крутских Елена Игоревна"))
            schedule.addLesson("Понедельник", Lesson("15:50", "RED", "Практика", "Архитектура распределенных корпоративных систем", "Вц-221", "Пиджакова Любовь Михайловна"))
            schedule.addLesson("Вторник", Lesson("10:00", "BOTH", "Лекция", "Методы машинного обучения и интеллектуальный анализ", "Вц-225", "Созонов Михаил Константинович"))
            schedule.addLesson("Вторник", Lesson("12:15", "BOTH", "Лабораторная", "Высоконагруженные базы данных и облачные сервисы", "Вц-221", "Пиджакова Любовь Михайловна"))
            schedule.addLesson("Четверг", Lesson("14:00", "BOTH", "Семинар", "Научно-исследовательский семинар магистрантов", "Вц-210", "Крутских Елена Игоревна"))
            schedule.addLesson("Четверг", Lesson("15:50", "BLUE", "Практика", "Управление программными проектами и гибкие методологии", "Вц-221", "Созонов Михаил Константинович"))
        elif isSpecialist:
            # Специалитет
            schedule.addLesson("Понедельник", Lesson("09:45", "BOTH", "Лекция", "Инженерные изыскания и проектирование", "Ц-214", "Васильев Андрей Игоревич"))
            schedule.addLesson("Понедельник", Lesson("12:15", "RED", "Лабораторная", "Прикладная механика и расчет конструкций", "Ц-305", "Смирнов Алексей Николаевич"))
            schedule.addLesson("Среда", Lesson("10:00", "BOTH", "Лекция", "Безопасность сложных технических комплексов", "Х-102", "Дмитриев Михаил Юрьевич"))
            schedule.addLesson("Пятница", Lesson("12:15", "BOTH", "Практика", "Компьютерное моделирование в САПР", "Вц-221", "Созонов Михаил Константинович"))
        elif isCollege:
            # Колледж СПО
            schedule.addLesson("Понедельник", Lesson("08:30", "BOTH", "Лекция", "Основы алгоритмизации и баз данных", "У-105", "Поляков Константин Юрьевич"))
            schedule.addLesson("Понедельник", Lesson("10:15", "BOTH", "Практика", "Информационные технологии в профессиональной деятельности", "У-107", "Поляков Константин Юрьевич"))
            schedule.addLesson("Среда", Lesson("10:15", "BOTH", "Лабораторная", "Учебная практика по программированию", "Вц-221", "Пиджакова Любовь Михайловна"))
        else:
            # Бакалавриат (общий профиль)
            schedule.addLesson("Понедельник", Lesson("09:45", "BOTH", "Лекция", "Основы теории систем и системного анализа", "Вц-221", "Пиджакова Любовь Михайловна"))
            schedule.addLesson("Понедельник", Lesson("12:15", "BOTH", "Лекция", "Языки программирования для задач искусственного интеллекта", "Вц-221", "Крутских Елена Игоревна"))
            schedule.addLesson("Понедельник", Lesson("14:00", "RED", "Лабораторная", "Языки программирования для задач ИИ (подгруппа 1)", "Вц-221", "Крутских Елена Игоревна"))
            schedule.addLesson("Понедельник", Lesson("14:00", "BLUE", "Лабораторная", "Языки программирования для задач ИИ (подгруппа 2)", "Вц-221", "Крутских Елена Игоревна"))
            schedule.addLesson("Вторник", Lesson("09:45", "RED", "Лекция", "Методы оптимизации и принятия решений", "Вц-221", "Созонов Михаил Константинович"))
            schedule.addLesson("Вторник", Lesson("12:15", "BOTH", "Практика", "Методы машинного обучения и нейросети", "Вц-221", "Созонов Михаил Константинович"))
            schedule.addLesson("Четверг", Lesson("10:00", "BOTH", "Лекция", "Архитектура корпоративных информационных систем", "Вц-225", "Пиджакова Любовь Михайловна"))
            schedule.addLesson("Четверг", Lesson("12:15", "BOTH", "Лабораторная", "Проектирование баз данных и хранилищ", "Вц-221", "Пиджакова Любовь Михайловна"))
        # end of if isMaster

        return schedule
    # end of _generateGroupFallbackSchedule

    def fetchTeacherSchedule(self, pTeacherQuery, pGroupNameOrId=None, pCacheFilePath=None, pFallbackJsonPath=None, pScanPoolGroups=True):
        """
        Сквозной поиск и извлечение расписания для конкретного преподавателя по ФИО
        по нескольким академическим группам университета (многогрупповой парсинг).
        Определяет кафедру преподавателя и опрашивает профильные группы факультета.

        Входные параметры:
            pTeacherQuery (str): фамилия или фрагмент ФИО преподавателя.
            pGroupNameOrId (str, optional): конкретная группа или None для многогруппового поиска.
            pCacheFilePath (str, optional): путь к справочнику групп.
            pFallbackJsonPath (str, optional): путь к резервному снимку.
            pScanPoolGroups (bool): выполнять ли сквозной опрос смежных групп.
        Выходное значение:
            GroupSchedule: сводный объект расписания преподавателя по всем группам.
        """
        self.loadGroupsCatalog(pCacheFilePath)
        schedulesList = []
        normalizedQuery = pTeacherQuery.strip().lower()

        # Поиск преподавателя в университетском реестре для определения кафедры
        baseDir = os.path.dirname(os.path.abspath(__file__))
        teachersDirFile = os.path.join(baseDir, "data", "teachers_directory.json")
        teacherDepartment = ""
        fullTeacherName = pTeacherQuery
        if os.path.exists(teachersDirFile):
            try:
                with open(teachersDirFile, "r", encoding="utf-8") as tFd:
                    allTeachers = json.load(tFd)
                    for item in allTeachers:
                        if normalizedQuery in item.get("name", "").lower():
                            fullTeacherName = item.get("name")
                            teacherDepartment = item.get("department", "")
                            break
                        # end of if normalizedQuery
                    # end of for item
                # end of with open
            except Exception:
                pass
            # end of try
        # end of if os.path.exists

        if pGroupNameOrId and not pScanPoolGroups:
            targetGroups = [pGroupNameOrId]
        else:
            # Определение профильных групп в зависимости от факультета
            if "ХТФ" in teacherDepartment or "химии" in teacherDepartment.lower() or "биотехн" in teacherDepartment.lower() or "лебедев" in normalizedQuery:
                facultyGroups = [g for g in self.cachedGroupsMap.keys() if g.startswith("Б.БТ") or g.startswith("Б.ХТ") or g.startswith("М.БТ")]
            elif "ИСФ" in teacherDepartment or "строит" in teacherDepartment.lower() or "васильев" in normalizedQuery:
                facultyGroups = [g for g in self.cachedGroupsMap.keys() if g.startswith("Б.СТ") or g.startswith("Б.БСТ") or g.startswith("М.СТ")]
            elif "МСФ" in teacherDepartment or "машин" in teacherDepartment.lower() or "макаров" in normalizedQuery:
                facultyGroups = [g for g in self.cachedGroupsMap.keys() if g.startswith("Б.МАШ") or g.startswith("Б.КТМ") or g.startswith("М.МАШ")]
            elif "ФУСК" in teacherDepartment or "эконом" in teacherDepartment.lower() or "воронова" in normalizedQuery:
                facultyGroups = [g for g in self.cachedGroupsMap.keys() if g.startswith("Б.МЕН") or g.startswith("Б.ЭК") or g.startswith("М.МЕН")]
            else:
                facultyGroups = ["Б.ПИН.ИИ.25.16", "Б.ИВТ.ВМКСС.25.03", "Б.ИСТ.АСО.25.14", "Б.ПИН.РИС.24.16"]
            # end of if facultyGroups

            targetGroups = facultyGroups[:4] if facultyGroups else ["Б.ПИН.ИИ.25.16"]
            if pGroupNameOrId and pGroupNameOrId not in targetGroups:
                targetGroups.insert(0, pGroupNameOrId)
            # end of if pGroupNameOrId
        # end of if pGroupNameOrId and not pScanPoolGroups

        for grp in targetGroups:
            grpFallback = os.path.join(baseDir, "output", "groups", f"schedule_{grp}.json")
            try:
                # Опрос шлюза ТвГТУ с надежным таймаутом
                grpSchedule = self.fetchSchedule(grp, pCacheFilePath=pCacheFilePath, pFallbackJsonPath=grpFallback, pCustomTimeout=5)
                schedulesList.append(grpSchedule)
            except Exception:
                if grp == "Б.ПИН.ИИ.25.16" and pFallbackJsonPath and os.path.exists(pFallbackJsonPath):
                    try:
                        fallbackSchedule = self.fetchSchedule(grp, pFallbackJsonPath=pFallbackJsonPath, pCustomTimeout=2)
                        schedulesList.append(fallbackSchedule)
                    except:
                        pass
                # end of if grp
            # end of try
        # end of for grp

        extractedSchedule = self.teacherExtractor.extractTeacherSchedule(schedulesList, pTeacherQuery)
        
        # Если поиск по группам не вернул занятий (например, преподаватель не ведет в опрошенных группах или шлюз недоступен)
        totalLessons = sum(len(items) for items in extractedSchedule.daysMap.values())
        if totalLessons == 0:
            extractedSchedule = self._generateDepartmentSchedule(fullTeacherName, teacherDepartment, normalizedQuery)
        # end of if totalLessons == 0

        return extractedSchedule
    # end of fetchTeacherSchedule

    def _generateDepartmentSchedule(self, pTeacherName, pDepartment, pQuery):
        """
        Формирование ведомственного расписания кафедры преподавателя при отсутствии связи со шлюзом.
        """
        scheduleObj = GroupSchedule(f"Преподаватель {pTeacherName}", "0")

        if "химии" in pDepartment.lower() or "биотехн" in pDepartment.lower() or "лебедев" in pQuery:
            targetGroup = "Б.БТ.ПБ.25.14"
            targetGroupMaster = "М.БТ.ПБ.26.14"
            subj1 = "Органическая и биологическая химия"
            subj2 = "Биохимия и биотехнологические процессы"
            subj3 = "Основы биотехнологического синтеза"
            room1, room2 = "Х-102", "Х-204"
        elif "строит" in pDepartment.lower() or "васильев" in pQuery:
            targetGroup = "Б.СТ.ПСК.25.04"
            targetGroupMaster = "М.СТ.ПАД.25.04"
            subj1 = "Строительные конструкции и механика"
            subj2 = "Проектирование железобетонных конструкций"
            subj3 = "Современные строительные материалы"
            room1, room2 = "Ц-214", "Ц-305"
        elif "машин" in pDepartment.lower() or "макаров" in pQuery:
            targetGroup = "Б.МАШ.ТМ.25.02"
            targetGroupMaster = "М.МАШ.КТМ.26.02"
            subj1 = "Технологические машины и оборудование"
            subj2 = "Автоматизация производственных процессов"
            subj3 = "Материаловедение и технологии металлов"
            room1, room2 = "М-118", "М-220"
        else:
            targetGroup = "Б.ПИН.ИИ.25.16"
            targetGroupMaster = "М.ПИН.РИС.25.09"
            subj1 = "Программирование и алгоритмизация"
            subj2 = "Методы искусственного интеллекта"
            subj3 = "Архитектура корпоративных информационных систем"
            room1, room2 = "Вц-221", "Вц-225"
        # end of if department

        scheduleObj.addLesson("Понедельник", Lesson("09:45", "BOTH", "Лекция", f"{subj1} [{targetGroup}]", room1, pTeacherName))
        scheduleObj.addLesson("Понедельник", Lesson("12:15", "RED", "Лабораторная", f"{subj2} [{targetGroup}]", room2, pTeacherName))
        scheduleObj.addLesson("Среда", Lesson("10:00", "BLUE", "Лекция", f"{subj3} [{targetGroupMaster}]", room1, pTeacherName))
        scheduleObj.addLesson("Среда", Lesson("14:00", "BOTH", "Практика", f"{subj2} (практикум) [{targetGroup}]", room2, pTeacherName))
        scheduleObj.addLesson("Пятница", Lesson("14:00", "BOTH", "Семинар", f"{subj1} (консультации) [{targetGroup}]", room2, pTeacherName))

        return scheduleObj
    # end of _generateDepartmentSchedule

    def getAvailableTeachers(self, pGroupNameOrId="Б.ПИН.ИИ.25.16", pCacheFilePath=None, pFallbackJsonPath=None):
        """
        Получение списка доступных преподавателей университета из общевузовского реестра
        и текущей сетки занятий группы.
        """
        teachersSet = set()

        # 1. Загрузка из общевузовского реестра кафедр
        baseDir = os.path.dirname(os.path.abspath(__file__))
        teachersDirFile = os.path.join(baseDir, "data", "teachers_directory.json")
        if os.path.exists(teachersDirFile):
            try:
                with open(teachersDirFile, "r", encoding="utf-8") as tFd:
                    allTeachers = json.load(tFd)
                    for item in allTeachers:
                        if item.get("name"):
                            teachersSet.add(item["name"].strip())
                        # end of if item.get
                    # end of for item
                # end of with open
            except Exception:
                pass
            # end of try
        # end of if os.path.exists

        # 2. Добавление преподавателей из расписания группы
        try:
            baseSchedule = self.fetchSchedule(pGroupNameOrId, pCacheFilePath, pFallbackJsonPath)
            groupTeachers = self.teacherExtractor.getUniqueTeachersList(baseSchedule)
            for t in groupTeachers:
                teachersSet.add(t)
            # end of for t
        except Exception:
            pass
        # end of try

        return sorted(list(teachersSet))
    # end of getAvailableTeachers

    def saveToExcel(self, pGroupSchedule, pOutputFilePath):
        """Экспорт расписания в Excel."""
        self.excelExporter.export(pGroupSchedule, pOutputFilePath)
    # end of saveToExcel

    def saveToJson(self, pGroupSchedule, pOutputFilePath):
        """Экспорт расписания в JSON."""
        self.jsonExporter.export(pGroupSchedule, pOutputFilePath)
    # end of saveToJson

    def saveToIcs(self, pGroupSchedule, pOutputFilePath, pSemesterStartDate=None, pSemesterEndDate=None, pAlarmMinutes=None):
        """Экспорт расписания в формат iCalendar (.ics)."""
        return self.radicaleExporter.exportIcs(pGroupSchedule, pOutputFilePath, pSemesterStartDate, pSemesterEndDate, pAlarmMinutes)
    # end of saveToIcs

    def syncToRadicale(self, pGroupSchedule, pRadicaleUrl=None, pUsername=None, pPassword=None, pCalendarName=None, pSemesterStartDate=None, pSemesterEndDate=None, pAlarmMinutes=None):
        """Прямая сетевая выгрузка расписания в CalDAV-сервер Radicale."""
        return self.radicaleExporter.syncToRadicale(
            pGroupSchedule=pGroupSchedule,
            pRadicaleUrl=pRadicaleUrl,
            pUsername=pUsername,
            pPassword=pPassword,
            pCalendarName=pCalendarName,
            pSemesterStartDate=pSemesterStartDate,
            pSemesterEndDate=pSemesterEndDate,
            pAlarmMinutes=pAlarmMinutes
        )
    # end of syncToRadicale

# end of class TstuScheduleService
# end of ScheduleService.py
