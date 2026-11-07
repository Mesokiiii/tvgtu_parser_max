# GroupsParser.py Модуль синтаксического анализа справочника групп ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: извлечение списка академических групп и их системных идентификаторов из HTML-кода

from bs4 import BeautifulSoup


class GroupsCatalogParser:
    """
    Класс выполняет синтаксический анализ выпадающего списка групп на веб-странице.
    Отвечает исключительно за преобразование HTML в структурированный справочник групп.
    """

    def __init__(self):
        """
        Конструктор парсера групп.
        """
        pass
    # end of __init__

    def parseGroupsFromHtml(self, pHtmlContent):
        """
        Извлечение соответствия названий групп и их идентификаторов из тега select.

        Входные параметры:
            pHtmlContent (str): HTML-код страницы со списком групп.
        Выходное значение:
            dict: словарь, где ключ — шифр группы (например, 'Б.ПИН.ИИ.25.16'),
                  значение — системный ID (например, '1851').
        """
        soupInstance = BeautifulSoup(pHtmlContent, "html.parser")
        
        # На странице ТвГТУ выпадающий список групп имеет фиксированный идентификатор schedule_site_group
        selectElement = soupInstance.find("select", id="schedule_site_group")
        if not selectElement:
            raise ValueError("На целевой странице не обнаружен обязательный элемент select#schedule_site_group")
        # end of if not selectElement

        extractedGroups = {}
        for optionTag in selectElement.find_all("option"):
            groupValue = optionTag.get("value", "").strip()
            groupTitle = optionTag.text.strip()
            
            # Пропускаем пустые заглушки по умолчанию вида 'Выберите один из пунктов'
            if groupValue and groupTitle and groupValue != "":
                extractedGroups[groupTitle] = groupValue
            # end of if groupValue and groupTitle
        # end of for optionTag

        return extractedGroups
    # end of parseGroupsFromHtml

    def findGroupIdByName(self, pGroupsMap, pTargetGroupName):
        """
        Поиск числового идентификатора группы в справочнике с поддержкой нестрогого поиска.

        Входные параметры:
            pGroupsMap (dict): словарь групп.
            pTargetGroupName (str): искомое название группы.
        Выходное значение:
            tuple: (точное_название_группы, системный_идентификатор).
        """
        # 1. Попытка точного совпадения
        if pTargetGroupName in pGroupsMap:
            return pTargetGroupName, pGroupsMap[pTargetGroupName]
        # end of if pTargetGroupName in pGroupsMap

        # 2. Нестрогий поиск: регистронезависимое совпадение по подстроке
        normalizedTarget = pTargetGroupName.strip().lower()
        for groupName, groupId in pGroupsMap.items():
            if normalizedTarget in groupName.lower():
                return groupName, groupId
            # end of if normalizedTarget in groupName.lower()
        # end of for groupName, groupId

        raise KeyError(f"Группа с наименованием '{pTargetGroupName}' не найдена в официальном справочнике ТвГТУ")
    # end of findGroupIdByName

# end of class GroupsCatalogParser
# end of GroupsParser.py
