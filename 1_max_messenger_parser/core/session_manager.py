# SessionManager.py Модуль управления сессионными ключами, токенами и выбором группы в MAX
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Разработчик ФИТ Добавлена поддержка выбора групп (включая магистратуру) и распознавание WebAppData
# Назначение: загрузка, валидация, хранение параметров сессии и каталога групп в tokens.json

import os
import re
import json
import base64


class SessionManager:
    """
    Класс инкапсулирует работу с файлом токенов авторизации и каталогом академических групп.
    Обеспечивает чтение, запись, переключение целевой группы и интеллектуальный разбор входных форматов.
    """

    def __init__(self, pConfigFilePath, pAuthClient=None, pGroupsCatalogPath=None):
        """
        Конструктор менеджера сессии.

        Входные параметры:
            pConfigFilePath (str): абсолютный или относительный путь к файлу tokens.json.
            pAuthClient (MaxAuthClient, optional): клиент авторизации для первичного обмена WebAppData.
            pGroupsCatalogPath (str, optional): путь к справочнику всех групп tvgtu_groups.json.
        """
        self.configFilePath = pConfigFilePath
        self.authClient = pAuthClient
        self.tokensCache = self.load()
        
        # Определение пути к каталогу групп
        if pGroupsCatalogPath:
            self.groupsCatalogPath = pGroupsCatalogPath
        else:
            baseDirectory = os.path.dirname(os.path.abspath(pConfigFilePath))
            self.groupsCatalogPath = os.path.join(baseDirectory, "tvgtu_groups.json")
        # end of if pGroupsCatalogPath

        self.groupsCacheList = self.loadGroupsDirectory()
    # end of __init__

    def load(self):
        """
        Чтение параметров сессии из конфигурационного файла.

        Выходное значение:
            dict: словарь параметров (auth_token, refresh_token, group_id и др.).
        """
        if os.path.exists(self.configFilePath):
            try:
                with open(self.configFilePath, "r", encoding="utf-8") as fileDescriptor:
                    return json.load(fileDescriptor)
                # end of with open
            except Exception as readError:
                print(f"Ошибка при чтении файла конфигурации {self.configFilePath}: {readError}")
            # end of try
        # end of if os.path.exists
        return {}
    # end of load

    def loadGroupsDirectory(self):
        """
        Загрузка полного справочника академических групп университета (463 группы).
        Включает бакалавриат (Б.), магистратуру (М.), специалитет (С.), аспирантуру (А.) и колледж (СПО).

        Выходное значение:
            list: массив словарей вида [{"id": 33318, "name": "Б.ПИН.ИИ.25.16"}, ...]
        """
        if os.path.exists(self.groupsCatalogPath):
            try:
                with open(self.groupsCatalogPath, "r", encoding="utf-8") as fileDescriptor:
                    return json.load(fileDescriptor)
                # end of with open
            except Exception as loadError:
                print(f"Ошибка чтения каталога групп {self.groupsCatalogPath}: {loadError}")
            # end of try
        # end of if os.path.exists
        return []
    # end of loadGroupsDirectory

    def save(self, pNewData):
        """
        Обновление параметров сессии и запись на диск.

        Входные параметры:
            pNewData (dict): новые или обновленные параметры сессии.
        """
        self.tokensCache.update(pNewData)
        os.makedirs(os.path.dirname(os.path.abspath(self.configFilePath)), exist_ok=True)
        with open(self.configFilePath, "w", encoding="utf-8") as fileDescriptor:
            json.dump(self.tokensCache, fileDescriptor, ensure_ascii=False, indent=2)
        # end of with open
    # end of save

    def getAuthToken(self):
        """Получение текущего рабочего токена доступа."""
        return self.tokensCache.get("auth_token")
    # end of getAuthToken

    def getRefreshToken(self):
        """Получение токена обновления сессии."""
        return self.tokensCache.get("refresh_token")
    # end of getRefreshToken

    def getTargetGroupId(self):
        """Получение идентификатора учебной группы."""
        return self.tokensCache.get("group_id", 33318)
    # end of getTargetGroupId

    def getTargetGroupName(self):
        """Получение наименования группы."""
        return self.tokensCache.get("group_name", "Б.ПИН.ИИ.25.16")
    # end of getTargetGroupName

    def setTargetGroup(self, pGroupId, pGroupName):
        """
        Установка и фиксация выбранной учебной группы в сессии.

        Входные параметры:
            pGroupId (int): числовой идентификатор группы в MAX.
            pGroupName (str): текстовый шифр группы (например, 'М.ПИН.РИС.25.09').
        """
        self.save({
            "group_id": int(pGroupId),
            "group_name": str(pGroupName).strip()
        })
    # end of setTargetGroup

    def searchGroups(self, pQuery="", pLevel=""):
        """
        Поиск и фильтрация академических групп по текстовому запросу и уровню подготовки.

        Входные параметры:
            pQuery (str): поисковая строка (фрагмент шифра).
            pLevel (str): уровень подготовки ('Б', 'М', 'С', 'СПО', 'А' или пустая строка для всех).
        Выходное значение:
            list: отфильтрованный список словарей групп.
        """
        normalizedQuery = pQuery.strip().lower()
        normalizedLevel = pLevel.strip().upper()

        matchedGroups = []
        for groupItem in self.groupsCacheList:
            groupName = groupItem.get("name", "")
            groupPrefix = groupName.split(".")[0].upper()

            # Фильтрация по уровню подготовки (бакалавриат, магистратура, специалитет, колледж)
            if normalizedLevel and groupPrefix != normalizedLevel:
                continue
            # end of if normalizedLevel

            # Поиск по подстроке
            if not normalizedQuery or normalizedQuery in groupName.lower():
                matchedGroups.append(groupItem)
            # end of if not normalizedQuery
        # end of for groupItem

        return matchedGroups
    # end of searchGroups

    def findGroupByName(self, pGroupNameQuery):
        """
        Поиск группы по точному совпадению или подстроке.

        Входные параметры:
            pGroupNameQuery (str): шифр группы или его фрагмент.
        Выходное значение:
            dict | None: словарь найденной группы или None.
        """
        trimmedQuery = pGroupNameQuery.strip().lower()
        
        # Точное совпадение
        for groupItem in self.groupsCacheList:
            if groupItem.get("name", "").lower() == trimmedQuery:
                return groupItem
            # end of if groupItem
        # end of for groupItem

        # Неточное вхождение
        for groupItem in self.groupsCacheList:
            if trimmedQuery in groupItem.get("name", "").lower():
                return groupItem
            # end of if trimmedQuery
        # end of for groupItem

        return None
    # end of findGroupByName

    def parseAndStoreRawInput(self, pRawInputString, pCustomAuthClient=None):
        """
        Универсальный метод разбора входных данных пользователя.
        Поддерживает:
        1. Полный JSON-объект токенов.
        2. Полный URL iframe мини-приложения (https://digital-uni-schedule...#WebAppData=...).
        3. Сырую строку параметров WebAppData / init_data.
        4. Копию сетевого запроса cURL (curl '...' -H 'authorization: Bearer eyJ...').
        5. Непосредственно токен JWT (начинается с eyJ).
        6. Строку URL с параметром auth_token=...

        Входные параметры:
            pRawInputString (str): сырая строка ввода.
            pCustomAuthClient (MaxAuthClient, optional): клиент авторизации.
        Выходное значение:
            dict: отчет о результатах обработки.
        """
        trimmedString = pRawInputString.strip()
        authClientInstance = pCustomAuthClient if pCustomAuthClient else self.authClient

        # Вариант 1: передан валидный JSON
        if trimmedString.startswith("{") and trimmedString.endswith("}"):
            parsedObject = json.loads(trimmedString)
            self.save(parsedObject)
            return {"status": "success", "message": "Параметры сессии загружены из JSON-конфигурации"}
        # end of if trimmedString.startswith

        # Вариант 2: передан cURL с заголовком Authorization: Bearer
        bearerMatch = re.search(r"Bearer\s+([A-Za-z0-9._-]+)", trimmedString, re.IGNORECASE)
        if bearerMatch:
            token = bearerMatch.group(1)
            self.save({"auth_token": token})
            return {"status": "success", "message": "Токен доступа извлечен из команды cURL"}
        # end of if bearerMatch

        # Вариант 3: передана ссылка с параметром auth_token
        if "auth_token=" in trimmedString:
            tokenMatch = re.search(r"auth_token=([A-Za-z0-9._-]+)", trimmedString)
            if tokenMatch:
                self.save({"auth_token": tokenMatch.group(1)})
                return {"status": "success", "message": "Токен auth_token успешно извлечен из ссылки"}
            # end of if tokenMatch
        # end of if "auth_token=" in trimmedString

        # Вариант 4: передан чистый JWT токен
        if trimmedString.startswith("eyJ"):
            self.save({"auth_token": trimmedString})
            return {"status": "success", "message": "Рабочий токен JWT сохранен"}
        # end of if trimmedString.startswith

        # Вариант 5: передан URL фрейма либо сырая строка WebAppData / init_data
        if "WebAppData=" in trimmedString or "hash=" in trimmedString or "digital-uni-schedule" in trimmedString:
            if authClientInstance:
                try:
                    tokensDict = authClientInstance.authenticate(trimmedString)
                    self.save(tokensDict)
                    return {
                        "status": "success",
                        "message": "Первичная аутентификация в MAX выполнена успешно. Токены зафиксированы на 12 часов."
                    }
                except Exception as authError:
                    # При недоступности сервера фиксируем init_data
                    self.save({"init_data": trimmedString})
                    return {
                        "status": "warning",
                        "message": f"WebAppData сохранен в init_data, но авто-обмен не удался: {authError}"
                    }
                # end of try
            else:
                self.save({"init_data": trimmedString})
                return {"status": "success", "message": "Строка WebAppData сохранена в параметрах сессии"}
            # end of if authClientInstance
        # end of if "WebAppData=" in trimmedString

        # Вариант 6: неизвестный строковый формат
        self.save({"init_data": trimmedString})
        return {"status": "info", "message": "Неизвестный формат сохранен в init_data"}
    # end of parseAndStoreRawInput

# end of class SessionManager
# end of SessionManager.py
