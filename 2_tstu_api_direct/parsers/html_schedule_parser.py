# HtmlScheduleParser.py Модуль синтаксического анализа таблицы расписания занятий
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: парсинг HTML-таблицы расписания, классификация четности недель и создание моделей Lesson

import re
from bs4 import BeautifulSoup
from models.lesson import Lesson, GroupSchedule


class HtmlScheduleParser:
    """
    Класс отвечает за синтаксический анализ структуры HTML-таблицы расписания.
    Извлекает дни недели, временные слоты, аудитории, преподавателей и цветовые недели.
    """

    DAYS_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    def __init__(self):
        """
        Конструктор парсера HTML-расписания.
        """
        pass
    # end of __init__

    def parseSchedule(self, pHtmlContent, pGroupName, pGroupId):
        """
        Преобразование сырого HTML-кода страницы в доменный объект GroupSchedule.

        Входные параметры:
            pHtmlContent (str): HTML-код страницы с расписанием.
            pGroupName (str): наименование группы.
            pGroupId (str): идентификатор группы.
        Выходное значение:
            GroupSchedule: структурированное расписание группы.
        """
        soupInstance = BeautifulSoup(pHtmlContent, "html.parser")
        tableTag = soupInstance.find("table", class_="table")
        scheduleResult = GroupSchedule(pGroupName, pGroupId)

        if not tableTag:
            # Если для группы еще не заведено расписание на семестр
            return scheduleResult
        # end of if not tableTag

        currentActiveDay = None
        currentActiveTime = None

        # В таблице ТвГТУ дни недели объединяют строки. Первая строка дня содержит 3 ячейки:
        # [День недели, Время, Содержимое пары].
        # Последующие строки того же дня содержат 2 ячейки [Время, Пара] или 1 ячейку [Вторая пара на другое чередование недель].
        for rowTag in tableTag.find_all("tr"):
            cellTags = rowTag.find_all("td")
            if not cellTags:
                continue
            # end of if not cellTags

            cellTexts = [td.get_text(separator=" ", strip=True) for td in cellTags]
            firstCellText = cellTexts[0]

            # Проверяем, открывает ли данная строка новый день недели
            detectedDay = next((d for d in self.DAYS_ORDER if d in firstCellText), None)

            if detectedDay:
                currentActiveDay = detectedDay
                if len(cellTags) >= 2 and re.match(r"^\d{2}:\d{2}", cellTexts[1]):
                    currentActiveTime = cellTexts[1]
                # end of if len(cellTags) >= 2
                if len(cellTags) >= 3:
                    lessonObj = self._extractLessonFromCell(cellTags[2], currentActiveTime, pGroupName)
                    if lessonObj:
                        scheduleResult.addLesson(currentActiveDay, lessonObj)
                    # end of if lessonObj
                # end of if len(cellTags) >= 3
            else:
                # Строка продолжается в рамках текущего дня
                if len(cellTags) >= 2 and re.match(r"^\d{2}:\d{2}", cellTexts[0]):
                    currentActiveTime = cellTexts[0]
                    lessonObj = self._extractLessonFromCell(cellTags[1], currentActiveTime, pGroupName)
                    if lessonObj:
                        scheduleResult.addLesson(currentActiveDay, lessonObj)
                    # end of if lessonObj
                elif len(cellTags) == 1 and currentActiveDay:
                    # Случай, когда в один временной слот укладываются два разных занятия
                    # для красной и синей недель (вторая строка содержит только 1 ячейку)
                    lessonObj = self._extractLessonFromCell(cellTags[0], currentActiveTime, pGroupName)
                    if lessonObj:
                        scheduleResult.addLesson(currentActiveDay, lessonObj)
                    # end of if lessonObj
                # end of if len(cellTags) >= 2
            # end of if detectedDay
        # end of for rowTag

        return scheduleResult
    # end of parseSchedule

    def _extractLessonFromCell(self, pTdTag, pTimeValue, pGroupName="Б.ПИН.ИИ.25.16"):
        """
        Вспомогательный метод декомпозиции ячейки занятия на составляющие сущности.

        Входные параметры:
            pTdTag (bs4.element.Tag): DOM-элемент ячейки td.
            pTimeValue (str): строковое время пары (например, '10:15').
        Выходное значение:
            Lesson: объект занятия либо None, если ячейка пуста.
        """
        rawText = pTdTag.get_text(separator=" ", strip=True)
        if not rawText:
            return None
        # end of if not rawText

        # Определение типа недели по CSS-классам фреймворка Bootstrap:
        # table-danger (красный фон) = Красная неделя (нечетная)
        # table-primary (синий фон) = Синяя неделя (четная)
        # отсутствие специального класса = занятие проводится каждую неделю
        cssClasses = pTdTag.get("class", [])
        if "table-danger" in cssClasses:
            weekCategory = "RED"
        elif "table-primary" in cssClasses:
            weekCategory = "BLUE"
        else:
            weekCategory = "BOTH"
        # end of if "table-danger" in cssClasses

        # Определение формы проведения занятия
        lessonForm = "Занятие"
        if "Лекция" in rawText:
            lessonForm = "Лекция"
        elif "Лабораторная" in rawText:
            lessonForm = "Лабораторная"
        elif "Практическое" in rawText or "Практика" in rawText:
            lessonForm = "Практика"
        # end of if "Лекция" in rawText

        # Извлечение номера подгруппы (при наличии)
        subgroupInfo = None
        subgroupMatch = re.search(r'\(подгруппа\s*(\d+)\)', rawText, re.IGNORECASE)
        if subgroupMatch:
            subgroupInfo = f"Подгруппа {subgroupMatch.group(1)}"
        # end of if subgroupMatch

        # Регулярное выражение для поиска аудитории ТвГТУ:
        # Корпуса: Вц (Вычислительный центр), Уч (Учебный), Ц (Центральный), ХТ (Химико-технологический)
        # Номер: дефис и 3 цифры (например: Вц-205, ХТ-112, Ц-217)
        roomMatch = re.search(r'([А-Яа-яA-Za-z]{1,4}-\d{3}[а-яА-Я]?(?:;\s*[А-Яа-яA-Za-z]{1,4}-\d{3}[а-яА-Я]?)*)', rawText)
        classroomString = roomMatch.group(1) if roomMatch else ""

        # Извлечение ФИО преподавателя: шаблон ищет Фамилию Имя Отчество с заглавных букв
        teacherMatch = re.search(r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})', rawText)
        teacherString = teacherMatch.group(1) if teacherMatch else ""

        return Lesson(
            pTime=pTimeValue,
            pWeekType=weekCategory,
            pLessonType=lessonForm,
            pSubject=rawText,
            pClassroom=classroomString,
            pTeacher=teacherString,
            pSubgroup=subgroupInfo,
            pGroupName=pGroupName
        )
    # end of _extractLessonFromCell

# end of class HtmlScheduleParser
# end of HtmlScheduleParser.py
