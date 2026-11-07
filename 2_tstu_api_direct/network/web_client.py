# WebClient.py Модуль сетевого взаимодействия с веб-сервером ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: выполнение безопасных HTTP-запросов к веб-серверу университета

import time
import requests
import urllib3

# Сервер университета использует внутренний SSL-сертификат, который может не проходить
# стандартную проверку доверенными центрами сертификации операционной системы.
# Для стабильного выполнения запросов отключаем предупреждения библиотеки urllib3.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TstuWebClient:
    """
    Сетевой клиент для загрузки веб-страниц шлюза расписания ТвГТУ.
    Отвечает исключительно за сетевой транспорт и обработку сетевых ошибок.
    """

    BASE_URL = "https://new.tstu.tver.ru/api/tver_polytech_bot/schedule_groups/"
    
    # Стандартный заголовок браузера необходим, чтобы сервер вуза не отклонял запросы
    # встроенного скрипта по признаку отсутствия идентификатора клиента (User-Agent).
    HTTP_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    def __init__(self, pTimeoutSeconds=10, pMaxRetries=2):
        """
        Конструктор сетевого клиента.

        Входные параметры:
            pTimeoutSeconds (int): время ожидания ответа от сервера в секундах.
            pMaxRetries (int): количество повторных попыток при сетевых сбоях.
        """
        self.timeoutSeconds = pTimeoutSeconds
        self.maxRetries = pMaxRetries
    # end of __init__

    def getCatalogHtml(self):
        """
        Загрузка исходной HTML-страницы со списком групп университета.

        Выходное значение:
            str: исходный HTML-код страницы.
        """
        lastException = None
        for attemptIndex in range(self.maxRetries):
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=self.HTTP_HEADERS,
                    verify=False,
                    timeout=self.timeoutSeconds
                )
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as networkError:
                lastException = networkError
                time.sleep(1)
            # end of try
        # end of for attemptIndex

        raise ConnectionError(f"Ошибка соединения с веб-сервером ТвГТУ: {lastException}")
    # end of getCatalogHtml

    def getScheduleHtmlByGroupId(self, pGroupId, pCustomTimeout=None):
        """
        Загрузка страницы с таблицей расписания для конкретного идентификатора группы.

        Входные параметры:
            pGroupId (str): числовой системный идентификатор группы (например, '1851').
            pCustomTimeout (int, optional): переопределение времени ожидания ответа.
        Выходное значение:
            str: исходный HTML-код страницы с таблицей занятий.
        """
        requestUrl = f"{self.BASE_URL}?schedule_site_group={pGroupId}"
        effectiveTimeout = pCustomTimeout if pCustomTimeout is not None else self.timeoutSeconds
        retriesCount = 1 if pCustomTimeout is not None else self.maxRetries
        lastException = None

        for attemptIndex in range(retriesCount):
            try:
                response = requests.get(
                    requestUrl,
                    headers=self.HTTP_HEADERS,
                    verify=False,
                    timeout=effectiveTimeout
                )
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as networkError:
                lastException = networkError
                time.sleep(0.5)
            # end of try
        # end of for attemptIndex

        raise ConnectionError(f"Не удалось получить расписание для группы {pGroupId}: {lastException}")
    # end of getScheduleHtmlByGroupId

# end of class TstuWebClient
# end of WebClient.py
