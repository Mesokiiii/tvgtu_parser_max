# RadicaleExporter.py Модуль экспорта расписания в формат CalDAV / iCalendar (Radicale)
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: генерация календаря iCalendar (.ics) и выгрузка расписания в CalDAV-сервер Radicale

import os
import re
import datetime
import hashlib
from typing import Dict, Any, Optional, Tuple, List
import requests


class RadicaleScheduleExporter:
    """
    Экспортер расписания учебных занятий ТвГТУ в формат iCalendar (RFC 5545)
    и прямая интеграция с CalDAV-сервером Radicale.

    Поддерживает:
      - Генерацию файлов .ics для импорта в любые календари (Apple, Google, Outlook, Thunderbird);
      - Корректный расчет четных (синих) и нечетных (красных) недель семестра;
      - Формирование правил повторения RRULE (еженедельно или раз в две недели);
      - Прямую сетевую выгрузку по протоколу CalDAV (HTTP PUT/MKCALENDAR) на сервер Radicale;
      - Настройку параметров через переменные окружения и аргументы вызова.
    """

    DAYS_MAP = {
        "понедельник": 0,
        "вторник": 1,
        "среда": 2,
        "четверг": 3,
        "пятница": 4,
        "суббота": 5,
        "воскресенье": 6
    }

    # Временная зона университета (Москва, UTC+3)
    TIMEZONE_ID = "Europe/Moscow"

    def __init__(self, pDefaultDurationMinutes: int = 95):
        """
        Конструктор экспортера.

        Входные параметры:
            pDefaultDurationMinutes (int): продолжительность академической пары в минутах (по умолчанию 95 мин).
        """
        self.defaultDurationMinutes = pDefaultDurationMinutes
    # end of __init__

    def cleanSubjectTitle(self, pRawSubject: str, pClassroom: str = "", pTeacher: str = "") -> str:
        """
        Очистка наименования предмета от технических маркеров аудитории, преподавателя и типа.

        Входные параметры:
            pRawSubject (str): исходная строка из ячейки расписания.
            pClassroom (str): номер аудитории.
            pTeacher (str): ФИО преподавателя.
        Выходное значение:
            str: лаконичное наименование учебной дисциплины.
        """
        if not pRawSubject:
            return "Занятие"
        # end of if not pRawSubject

        cleaned = pRawSubject
        if pClassroom:
            cleaned = cleaned.replace(pClassroom, "")
        # end of if pClassroom
        if pTeacher:
            cleaned = cleaned.replace(pTeacher, "")
        # end of if pTeacher

        # Удаление меток форм обучения и подгрупп
        cleaned = re.sub(r'\(.*?\)', '', cleaned)
        cleaned = re.sub(r'\[.*?\]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Удаление остаточных обозначений аудиторий типа Вц-205, ХТ-102, Ц-214
        cleaned = re.sub(r'\b[А-Яа-яA-Za-z]{1,4}-\d{3}[а-яА-Я]?\b', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned if cleaned else pRawSubject.strip()
    # end of cleanSubjectTitle

    def _determineSemesterDates(self, pStartDate: Optional[str] = None, pEndDate: Optional[str] = None) -> Tuple[datetime.date, datetime.date]:
        """
        Определение граничных дат учебного семестра (по умолчанию осенний или весенний семестр).

        Выходное значение:
            Tuple[date, date]: (дата начала семестра, дата окончания семестра).
        """
        today = datetime.date.today()

        if pStartDate:
            try:
                startDate = datetime.date.fromisoformat(pStartDate)
            except ValueError:
                startDate = None
        else:
            startDate = None

        if pEndDate:
            try:
                endDate = datetime.date.fromisoformat(pEndDate)
            except ValueError:
                endDate = None
        else:
            endDate = None

        if not startDate:
            # Если дата не задана, определяем текущий семестр
            # Месяцы 8..12 - осенний семестр текущего года (с 1 сентября по 31 января)
            # Месяц 1 - продолжение осеннего семестра предыдущего года
            # Месяцы 2..7 - весенний семестр текущего года (с 9 февраля по 30 июня)
            if today.month >= 8:
                startDate = datetime.date(today.year, 9, 1)
            elif today.month == 1:
                startDate = datetime.date(today.year - 1, 9, 1)
            else:
                startDate = datetime.date(today.year, 2, 9)
        # end of if not startDate

        if not endDate:
            if startDate.month == 9:
                endDate = datetime.date(startDate.year + 1, 1, 31)
            else:
                endDate = datetime.date(startDate.year, 6, 30)
        # end of if not endDate

        return startDate, endDate
    # end of _determineSemesterDates

    def _parseLessonTime(self, pTimeString: str) -> Tuple[int, int, int, int]:
        """
        Извлечение часов и минут начала и окончания занятия.

        Выходное значение:
            Tuple[int, int, int, int]: (startHour, startMin, endHour, endMin)
        """
        times = re.findall(r'(\d{1,2}):(\d{2})', pTimeString)
        if not times:
            return 8, 30, 10, 5
        # end of if not times

        startH, startM = int(times[0][0]), int(times[0][1])

        if len(times) >= 2:
            endH, endM = int(times[1][0]), int(times[1][1])
        else:
            startTotal = startH * 60 + startM
            endTotal = startTotal + self.defaultDurationMinutes
            endH = (endTotal // 60) % 24
            endM = endTotal % 60
        # end of if len(times) >= 2

        return startH, startM, endH, endM
    # end of _parseLessonTime

    def _calculateFirstOccurrence(self, pDayName: str, pWeekType: str, pSemesterStart: datetime.date) -> datetime.date:
        """
        Вычисление точной даты первого занятия с учетом четности недели (красная/синяя).

        Логика:
          Семестр начинается на 1-й (нечетной / красной) неделе.
          Красная неделя (RED) -> занятие на 1-й неделе семестра.
          Синяя неделя (BLUE) -> занятие на 2-й неделе семестра.
          Обе недели (BOTH) -> еженедельно, начиная с 1-й недели.
        """
        dayKey = pDayName.strip().lower()
        targetWeekday = self.DAYS_MAP.get(dayKey, 0)

        # Находим понедельник первой недели семестра
        week1Monday = pSemesterStart - datetime.timedelta(days=pSemesterStart.weekday())

        weekTypeUpper = (pWeekType or "BOTH").upper()

        if weekTypeUpper == "BLUE":
            # Вторая неделя (четная)
            firstDate = week1Monday + datetime.timedelta(days=7 + targetWeekday)
        else:
            # Первая неделя (нечетная) или обе
            firstDate = week1Monday + datetime.timedelta(days=targetWeekday)
            if firstDate < pSemesterStart:
                # Если 1 сентября пришлось на середину недели (например, вторник),
                # то понедельник первой недели уже прошел -> переносим на следующий цикл
                if weekTypeUpper == "RED":
                    firstDate += datetime.timedelta(days=14)
                else:
                    firstDate += datetime.timedelta(days=7)
                # end of if weekTypeUpper
            # end of if firstDate < pSemesterStart
        # end of if weekTypeUpper

        return firstDate
    # end of _calculateFirstOccurrence

    TRANSLIT_TABLE = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
        'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
        'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
        'я': 'ya'
    }

    def _slugify(self, pText: str) -> str:
        """Транслитерация и формирование безопасного ASCII-идентификатора."""
        res = []
        for ch in pText.lower():
            if ch in self.TRANSLIT_TABLE:
                res.append(self.TRANSLIT_TABLE[ch])
            elif ch.isalnum() or ch in ('-', '_'):
                res.append(ch)
            else:
                res.append('_')
        slug = "".join(res).strip('_')
        return re.sub(r'_+', '_', slug)[:25] or "item"

    def _generateUid(self, pLesson, pDayName: str, pGroupOrTeacher: str) -> str:
        """
        Генерация стабильного уникального идентификатора UID для iCalendar / CalDAV.
        """
        rawKey = f"{pGroupOrTeacher}_{pDayName}_{pLesson.time}_{pLesson.weekType}_{pLesson.subject}_{pLesson.classroom}"
        keyHash = hashlib.sha256(rawKey.encode("utf-8")).hexdigest()[:16]
        slug = self._slugify(pGroupOrTeacher)
        return f"tstu-{slug}-{keyHash}@tstu.tver.ru"
    # end of _generateUid

    def _formatIcalText(self, pText: str) -> str:
        """
        Экранирование спецсимволов по стандарту RFC 5545.
        """
        if not pText:
            return ""
        escaped = pText.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        escaped = escaped.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
        return escaped
    # end of _formatIcalText

    def buildVEvent(self, pLesson, pDayName: str, pSemesterStart: datetime.date, pSemesterEnd: datetime.date, pGroupTitle: str, pAlarmMinutes: Optional[int] = None) -> str:
        """
        Построение текстового блока VEVENT для одного учебного занятия.

        Выходное значение:
            str: компонент VEVENT.
        """
        firstDate = self._calculateFirstOccurrence(pDayName, pLesson.weekType, pSemesterStart)
        startH, startM, endH, endM = self._parseLessonTime(pLesson.time)

        dtStartStr = f"{firstDate.strftime('%Y%m%d')}T{startH:02d}{startM:02d}00"
        dtEndStr = f"{firstDate.strftime('%Y%m%d')}T{endH:02d}{endM:02d}00"
        untilStr = f"{pSemesterEnd.strftime('%Y%m%d')}T235959Z"
        dtstampStr = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        cleanSubject = self.cleanSubjectTitle(pLesson.subject, pLesson.classroom, pLesson.teacher)
        lessonTypeStr = pLesson.lessonType or "Занятие"

        # Заголовок события в календаре
        if pLesson.subgroup:
            summary = f"[{lessonTypeStr}] {cleanSubject} ({pLesson.subgroup})"
        else:
            summary = f"[{lessonTypeStr}] {cleanSubject}"
        # end of if pLesson.subgroup

        # Текстовое описание занятия
        weekDesc = "Еженедельно"
        if (pLesson.weekType or "").upper() == "RED":
            weekDesc = "Красная неделя (нечетная)"
        elif (pLesson.weekType or "").upper() == "BLUE":
            weekDesc = "Синяя неделя (четная)"

        descriptionParts = [
            f"Дисциплина: {cleanSubject}",
            f"Форма занятия: {lessonTypeStr}",
            f"Преподаватель: {pLesson.teacher or 'Не указан'}",
            f"Аудитория: {pLesson.classroom or 'Не указана'}",
            f"Группа: {pLesson.group or pGroupTitle}",
            f"Чередование: {weekDesc}"
        ]
        if pLesson.subgroup:
            descriptionParts.append(f"Подгруппа: {pLesson.subgroup}")

        descriptionText = "\\n".join(descriptionParts)

        # Определение правила повторения (RRULE)
        weekTypeUpper = (pLesson.weekType or "BOTH").upper()
        if weekTypeUpper in ("RED", "BLUE"):
            rrule = f"FREQ=WEEKLY;INTERVAL=2;UNTIL={untilStr}"
        else:
            rrule = f"FREQ=WEEKLY;INTERVAL=1;UNTIL={untilStr}"

        uid = self._generateUid(pLesson, pDayName, pGroupTitle)
        location = self._formatIcalText(pLesson.classroom or "")

        lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstampStr}",
            f"DTSTART;TZID={self.TIMEZONE_ID}:{dtStartStr}",
            f"DTEND;TZID={self.TIMEZONE_ID}:{dtEndStr}",
            f"RRULE:{rrule}",
            f"SUMMARY:{self._formatIcalText(summary)}",
            f"DESCRIPTION:{descriptionText}",
            f"LOCATION:{location}",
            f"CATEGORIES:{self._formatIcalText(lessonTypeStr)}",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE"
        ]

        # Добавление напоминания (VALARM) при указании времени срабатывания
        if pAlarmMinutes and pAlarmMinutes > 0:
            lines.extend([
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{self._formatIcalText(summary)}",
                f"TRIGGER:-PT{int(pAlarmMinutes)}M",
                "END:VALARM"
            ])

        lines.append("END:VEVENT")
        return "\r\n".join(lines)
    # end of buildVEvent

    def generateIcsContent(self, pGroupSchedule, pSemesterStartDate: Optional[str] = None, pSemesterEndDate: Optional[str] = None, pAlarmMinutes: Optional[int] = None) -> str:
        """
        Формирование полного содержимого файла .ics (VCALENDAR) для расписания.

        Выходное значение:
            str: текст календаря в формате iCalendar (RFC 5545).
        """
        semStart, semEnd = self._determineSemesterDates(pSemesterStartDate, pSemesterEndDate)
        groupTitle = getattr(pGroupSchedule, "groupName", "Расписание") or "Расписание"

        vevents = []
        daysMap = getattr(pGroupSchedule, "daysMap", {})
        for dayName, lessonsList in daysMap.items():
            for lessonObj in lessonsList:
                vevent = self.buildVEvent(lessonObj, dayName, semStart, semEnd, groupTitle, pAlarmMinutes=pAlarmMinutes)
                vevents.append(vevent)
            # end of for lessonObj
        # end of for dayName, lessonsList

        # Блок описания московской временной зоны (MSK)
        vtimezone = "\r\n".join([
            "BEGIN:VTIMEZONE",
            f"TZID:{self.TIMEZONE_ID}",
            f"X-LIC-LOCATION:{self.TIMEZONE_ID}",
            "BEGIN:STANDARD",
            "TZOFFSETFROM:+0300",
            "TZOFFSETTO:+0300",
            "TZNAME:MSK",
            "DTSTART:19700101T000000",
            "END:STANDARD",
            "END:VTIMEZONE"
        ])

        header = "\r\n".join([
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//TvGTU//Schedule Service Direct v2.0//RU",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{self._formatIcalText(f'Расписание {groupTitle}')}",
            f"X-WR-TIMEZONE:{self.TIMEZONE_ID}"
        ])

        allBlocks = [header, vtimezone] + vevents + ["END:VCALENDAR\r\n"]
        return "\r\n".join(allBlocks)
    # end of generateIcsContent

    def exportIcs(self, pGroupSchedule, pOutputFilePath: str, pSemesterStartDate: Optional[str] = None, pSemesterEndDate: Optional[str] = None, pAlarmMinutes: Optional[int] = None) -> str:
        """
        Сохранение расписания в локальный файл формата .ics.

        Входные параметры:
            pGroupSchedule (GroupSchedule): объект расписания.
            pOutputFilePath (str): путь для сохранения файла (.ics).
            pSemesterStartDate (str, optional): дата начала семестра (ГГГГ-ММ-ДД).
            pSemesterEndDate (str, optional): дата окончания семестра (ГГГГ-ММ-ДД).
            pAlarmMinutes (int, optional): время предварительного напоминания в минутах (VALARM).
        Выходное значение:
            str: абсолютный путь к созданному файлу.
        """
        icsText = self.generateIcsContent(pGroupSchedule, pSemesterStartDate, pSemesterEndDate, pAlarmMinutes=pAlarmMinutes)
        os.makedirs(os.path.dirname(os.path.abspath(pOutputFilePath)), exist_ok=True)

        with open(pOutputFilePath, "w", encoding="utf-8", newline="") as fd:
            fd.write(icsText)
        # end of with open

        return os.path.abspath(pOutputFilePath)
    # end of exportIcs

    def syncToRadicale(
        self,
        pGroupSchedule,
        pRadicaleUrl: Optional[str] = None,
        pUsername: Optional[str] = None,
        pPassword: Optional[str] = None,
        pCalendarName: Optional[str] = None,
        pSemesterStartDate: Optional[str] = None,
        pSemesterEndDate: Optional[str] = None,
        pAlarmMinutes: Optional[int] = None,
        pTimeoutSeconds: int = 10
    ) -> Dict[str, Any]:
        """
        Прямая выгрузка расписания в CalDAV-сервер Radicale по протоколу HTTP (PUT / MKCALENDAR).

        Входные параметры:
            pGroupSchedule (GroupSchedule): объект расписания.
            pRadicaleUrl (str, optional): базовый адрес Radicale (из аргумента или RADICALE_URL).
            pUsername (str, optional): имя пользователя CalDAV (по умолчанию из RADICALE_USER или 'tstu').
            pPassword (str, optional): пароль CalDAV (из RADICALE_PASSWORD).
            pCalendarName (str, optional): имя календаря/коллекции (из RADICALE_CALENDAR или 'schedule').
            pSemesterStartDate (str, optional): начало семестра.
            pSemesterEndDate (str, optional): конец семестра.
            pTimeoutSeconds (int): сетевой таймаут запроса.

        Выходное значение:
            Dict[str, Any]: отчет о результатах синхронизации {success, synced_count, total_events, collection_url, message, error}.
        """
        radicaleUrl = (pRadicaleUrl or os.environ.get("RADICALE_URL") or "http://localhost:5232").rstrip("/")
        username = pUsername or os.environ.get("RADICALE_USER") or "tstu"
        password = pPassword or os.environ.get("RADICALE_PASSWORD") or ""
        calendarName = pCalendarName or os.environ.get("RADICALE_CALENDAR") or "schedule"

        # Формирование URL коллекции CalDAV: http://host:port/username/calendarName/
        collectionUrl = f"{radicaleUrl}/{username}/{calendarName}/"

        auth = (username, password) if (username and password) else None

        resultSummary = {
            "success": False,
            "synced_count": 0,
            "total_events": 0,
            "collection_url": collectionUrl,
            "message": "",
            "error": None
        }

        semStart, semEnd = self._determineSemesterDates(pSemesterStartDate, pSemesterEndDate)
        groupTitle = getattr(pGroupSchedule, "groupName", "Расписание") or "Расписание"

        # 1. Попытка создания коллекции календаря через MKCOL / MKCALENDAR
        try:
            mkcalXml = f"""<?xml version="1.0" encoding="utf-8" ?>
<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:set>
    <D:prop>
      <D:displayname>Расписание {groupTitle}</D:displayname>
      <C:calendar-description>Учебное расписание ТвГТУ ({groupTitle})</C:calendar-description>
      <C:supported-calendar-component-set>
        <C:comp name="VEVENT"/>
      </C:supported-calendar-component-set>
    </D:prop>
  </D:set>
</C:mkcalendar>"""
            headers = {"Content-Type": "application/xml; charset=utf-8"}
            requests.request("MKCALENDAR", collectionUrl, data=mkcalXml.encode("utf-8"), headers=headers, auth=auth, timeout=pTimeoutSeconds)
            # Статусы 201 (создан), 405 (уже существует), 409 являются допустимыми
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as netErr:
            resultSummary["error"] = f"Сервер Radicale по адресу '{radicaleUrl}' недоступен: {netErr}"
            resultSummary["message"] = (
                f"[Radicale] Предупреждение: CalDAV-сервер Radicale ({radicaleUrl}) в данный момент недоступен. "
                f"События сохранены в локальный .ics файл для последующего импорта."
            )
            return resultSummary
        except Exception:
            # При отсутствии явной поддержки MKCALENDAR пробуем обычный MKCOL
            try:
                requests.request("MKCOL", collectionUrl, auth=auth, timeout=pTimeoutSeconds)
            except Exception:
                pass
            # end of try
        # end of try

        # 2. Формирование отдельных событий VEVENT и загрузка через HTTP PUT
        daysMap = getattr(pGroupSchedule, "daysMap", {})
        allEvents = []
        for dayName, lessonsList in daysMap.items():
            for lessonObj in lessonsList:
                allEvents.append((dayName, lessonObj))
            # end of for lessonObj
        # end of for dayName, lessonsList

        resultSummary["total_events"] = len(allEvents)

        if not allEvents:
            resultSummary["success"] = True
            resultSummary["message"] = "Расписание не содержит занятий для выгрузки."
            return resultSummary
        # end of if not allEvents

        syncedCount = 0
        connectionFailed = False

        for dayName, lessonObj in allEvents:
            uid = self._generateUid(lessonObj, dayName, groupTitle)
            veventBody = self.buildVEvent(lessonObj, dayName, semStart, semEnd, groupTitle, pAlarmMinutes=pAlarmMinutes)

            # Оборачиваем VEVENT в минимальный VCALENDAR для отправки по CalDAV
            eventIcs = "\r\n".join([
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//TvGTU//Schedule Service Direct//RU",
                "CALSCALE:GREGORIAN",
                "BEGIN:VTIMEZONE",
                f"TZID:{self.TIMEZONE_ID}",
                "BEGIN:STANDARD",
                "TZOFFSETFROM:+0300",
                "TZOFFSETTO:+0300",
                "TZNAME:MSK",
                "DTSTART:19700101T000000",
                "END:STANDARD",
                "END:VTIMEZONE",
                veventBody,
                "END:VCALENDAR\r\n"
            ])

            eventPutUrl = f"{collectionUrl}{uid}.ics"
            putHeaders = {"Content-Type": "text/calendar; charset=utf-8"}

            try:
                putResp = requests.put(eventPutUrl, data=eventIcs.encode("utf-8"), headers=putHeaders, auth=auth, timeout=pTimeoutSeconds)
                if putResp.status_code in (200, 201, 204):
                    syncedCount += 1
                else:
                    # Сервер ответил ошибкой
                    pass
                # end of if putResp.status_code
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as netErr:
                connectionFailed = True
                resultSummary["error"] = f"Сервер Radicale по адресу '{radicaleUrl}' недоступен: {netErr}"
                break
            except Exception as otherErr:
                resultSummary["error"] = f"Ошибка загрузки занятия '{uid}': {otherErr}"
            # end of try
        # end of for dayName, lessonObj

        resultSummary["synced_count"] = syncedCount

        if connectionFailed:
            resultSummary["success"] = False
            resultSummary["message"] = (
                f"[Radicale] Предупреждение: CalDAV-сервер Radicale ({radicaleUrl}) в данный момент недоступен. "
                f"События сохранены в локальный .ics файл для последующего импорта."
            )
        elif syncedCount > 0:
            resultSummary["success"] = True
            resultSummary["message"] = (
                f"[Radicale] Успешно синхронизировано {syncedCount} из {len(allEvents)} занятий в CalDAV-коллекцию: {collectionUrl}"
            )
        else:
            resultSummary["success"] = False
            resultSummary["message"] = f"[Radicale] Не удалось выгрузить занятия в коллекцию {collectionUrl}. Проверьте авторизацию и права доступа."
        # end of if connectionFailed

        return resultSummary
    # end of syncToRadicale

# end of class RadicaleScheduleExporter
# end of RadicaleExporter.py
