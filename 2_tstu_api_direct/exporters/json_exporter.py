# JsonExporter.py Модуль сохранения расписания в формат JSON
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: сериализация структуры расписания в текстовый файл формата JSON

import json


class JsonScheduleExporter:
    """
    Класс отвечает за сериализацию объекта расписания в файл JSON.
    """

    def __init__(self):
        """
        Конструктор экспортера JSON.
        """
        pass
    # end of __init__

    def export(self, pGroupSchedule, pFilePath):
        """
        Сохранение структуры данных в файл.

        Входные параметры:
            pGroupSchedule (GroupSchedule): объект расписания.
            pFilePath (str): целевой путь сохранения файла (.json).
        """
        dataMap = pGroupSchedule.toDictionary()
        with open(pFilePath, "w", encoding="utf-8") as fileDescriptor:
            json.dump(dataMap, fileDescriptor, ensure_ascii=False, indent=2)
        # end of with open
    # end of export

# end of class JsonScheduleExporter
# end of JsonExporter.py
