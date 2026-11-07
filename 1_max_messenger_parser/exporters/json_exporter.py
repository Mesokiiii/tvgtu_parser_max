# JsonExporter.py Модуль экспорта расписания в формат JSON
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: сохранение массива расписания в текстовый файл формата JSON

import json


class MaxJsonExporter:
    """
    Класс отвечает за сериализацию расписания в файл JSON.
    """

    def __init__(self):
        """
        Конструктор экспортера.
        """
        pass
    # end of __init__

    def export(self, pScheduleData, pOutputFilePath):
        """
        Сохранение структуры данных в файл.

        Входные параметры:
            pScheduleData (list or dict): структура данных расписания.
            pOutputFilePath (str): путь сохранения файла (.json).
        """
        with open(pOutputFilePath, "w", encoding="utf-8") as fileDescriptor:
            json.dump(pScheduleData, fileDescriptor, ensure_ascii=False, indent=2)
        # end of with open
    # end of export

# end of class MaxJsonExporter
# end of JsonExporter.py
