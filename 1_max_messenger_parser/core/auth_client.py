# AuthClient.py Сетевой клиент обновления и первичной аутентификации токенов доступа API расписания
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Разработчик ФИТ Добавление первичной авторизации по WebAppData
# Назначение: взаимодействие с маршрутами /v1/auth и /v1/auth/refresh для получения и пролонгации сессии

import urllib.parse
import requests


class MaxAuthClient:
    """
    Класс отвечает за первичную авторизацию по параметрам WebAppData и обновление токена auth_token.
    """

    LOGIN_URL = "https://schedule.vk-apps.com/v1/auth"
    REFRESH_URL = "https://schedule.vk-apps.com/v1/auth/refresh"
    
    # Сервер schedule.vk-apps.com проверяет соответствие заголовков Origin и Referer
    # для предотвращения несанкционированных междоменных запросов (CORS).
    HTTP_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://digital-uni-schedule.vk-apps.com",
        "Referer": "https://digital-uni-schedule.vk-apps.com/"
    }

    def __init__(self, pTimeoutSeconds=15):
        """
        Конструктор клиента аутентификации.

        Входные параметры:
            pTimeoutSeconds (int): предельное время ожидания ответа.
        """
        self.timeoutSeconds = pTimeoutSeconds
    # end of __init__

    def authenticate(self, pWebAppDataOrUrl):
        """
        Первичная аутентификация по строке параметров запуска мини-приложения (WebAppData / init_data).
        Выполняет обращение к шлюзу /v1/auth и возвращает пару JWT-токенов (auth_token и refresh_token).

        Входные параметры:
            pWebAppDataOrUrl (str): сырая строка WebAppData либо полный URL мини-приложения из фрейма.
        Выходное значение:
            dict: словарь с ключами auth_token и refresh_token.
        """
        if not pWebAppDataOrUrl or not str(pWebAppDataOrUrl).strip():
            raise ValueError("Параметры WebAppData не могут быть пустыми")
        # end of if not pWebAppDataOrUrl

        rawString = str(pWebAppDataOrUrl).strip()

        # Если передан полный URL с фрагментом (#WebAppData=...)
        if "#" in rawString:
            rawString = rawString.split("#", 1)[1]
        # end of if "#" in rawString

        # Извлечение чистого параметра WebAppData
        webAppDataValue = rawString
        if "WebAppData=" in rawString:
            parsedQuery = urllib.parse.parse_qs(rawString)
            if "WebAppData" in parsedQuery and parsedQuery["WebAppData"]:
                webAppDataValue = parsedQuery["WebAppData"][0]
            # end of if "WebAppData"
        # end of if "WebAppData=" in rawString

        requestPayload = {
            "init_data": webAppDataValue,
            "timezone": "Europe/Moscow"
        }
        requestHeaders = dict(self.HTTP_HEADERS)
        requestHeaders["Origin"] = "https://digital-uni-schedule.cdn-vk.ru"
        requestHeaders["Referer"] = "https://digital-uni-schedule.cdn-vk.ru/"

        try:
            try:
                response = requests.post(
                    self.LOGIN_URL,
                    json=requestPayload,
                    headers=requestHeaders,
                    timeout=self.timeoutSeconds
                )
            except requests.exceptions.SSLError:
                # Резервный вызов при отсутствии национального корневого сертификата
                response = requests.post(
                    self.LOGIN_URL,
                    json=requestPayload,
                    headers=requestHeaders,
                    timeout=self.timeoutSeconds,
                    verify=False
                )
            # end of try SSLError

            if response.status_code in (200, 201):
                responseData = response.json()
                return {
                    "auth_token": responseData.get("auth_token", ""),
                    "refresh_token": responseData.get("refresh_token", "")
                }
            # end of if response.status_code

            if "token_expired" in response.text:
                raise PermissionError("Срок действия параметров WebAppData истек (токен действителен ~15-20 минут). Пожалуйста, откройте мини-приложение в боте MAX заново и скопируйте свежую ссылку.")
            # end of if token_expired

            raise PermissionError(f"Ошибка обмена WebAppData на токены (код {response.status_code}): {response.text}")
        except requests.exceptions.RequestException as networkError:
            raise ConnectionError(f"Сетевой сбой при обращении к серверу аутентификации MAX: {networkError}")
        # end of try
    # end of authenticate

    def refreshAccessToken(self, pRefreshToken):
        """
        Отправка запроса на получение свежего auth_token по действующему refresh_token.

        Входные параметры:
            pRefreshToken (str): долгосрочный сессионный токен.
        Выходное значение:
            str: новый рабочий токен auth_token (срок действия 10 минут).
        """
        if not pRefreshToken:
            raise ValueError("Токен refresh_token не может быть пустым")
        # end of if not pRefreshToken

        requestPayload = {"refresh_token": pRefreshToken}
        response = requests.post(
            self.REFRESH_URL,
            json=requestPayload,
            headers=self.HTTP_HEADERS,
            timeout=self.timeoutSeconds
        )

        if response.status_code == 200:
            responseData = response.json()
            newAuthToken = responseData.get("auth_token")
            if newAuthToken:
                return newAuthToken
            # end of if newAuthToken
        # end of if response.status_code == 200

        # Сервер возвращает 401, если 12-часовой лимит истек или сессия была сброшена в мессенджере
        raise PermissionError(f"Ошибка обновления токена (код {response.status_code}): {response.text}")
    # end of refreshAccessToken

# end of class MaxAuthClient
# end of AuthClient.py
