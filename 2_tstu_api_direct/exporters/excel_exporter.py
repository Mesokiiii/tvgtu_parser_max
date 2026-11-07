# ExcelExporter.py Модуль экспорта расписания в формат Microsoft Excel
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: генерация стилизованного отчета расписания занятий с цветовой маркировкой недель

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ExcelScheduleExporter:
    """
    Класс формирует электронную таблицу Excel на основе объекта расписания.
    Инкапсулирует стилизацию ячеек, цветовую маркировку четности недель и настройку макета.
    """

    def __init__(self):
        """
        Конструктор экспортера.
        """
        pass
    # end of __init__

    def export(self, pGroupSchedule, pFilePath):
        """
        Генерация файла рабочей книги Excel.

        Входные параметры:
            pGroupSchedule (GroupSchedule): объект расписания учебной группы.
            pFilePath (str): целевой путь сохранения файла (.xlsx).
        """
        workbookInstance = openpyxl.Workbook()
        worksheetInstance = workbookInstance.active
        groupTitle = pGroupSchedule.groupName or "Группа"
        worksheetInstance.title = f"Расписание {groupTitle}"[:31]
        worksheetInstance.views.sheetView[0].showGridLines = True

        # Стилистическое оформление шрифтов
        titleFont = Font(name="Calibri", size=14, bold=True, color="1F497D")
        subFont = Font(name="Calibri", size=10, italic=True, color="595959")
        dayHeaderFont = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        columnHeaderFont = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        dataFont = Font(name="Calibri", size=10)
        boldFont = Font(name="Calibri", size=10, bold=True)

        borderSide = Side(border_style="thin", color="D9D9D9")
        tableBorder = Border(left=borderSide, right=borderSide, top=borderSide, bottom=borderSide)

        # Цветовые заливки блоков
        dayHeaderFill = PatternFill("solid", fgColor="2C3E50")
        columnHeaderFill = PatternFill("solid", fgColor="34495E")

        fillRedWeek = PatternFill("solid", fgColor="FFD9D9")
        fillBlueWeek = PatternFill("solid", fgColor="D9E8FB")
        fillBothWeeks = PatternFill("solid", fgColor="F2F2F2")

        alignCenter = Alignment(horizontal="center", vertical="center", wrap_text=True)
        alignLeft = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Формирование шапки документа
        worksheetInstance.merge_cells("A1:H1")
        worksheetInstance["A1"] = "Тверской государственный технический университет"
        worksheetInstance["A1"].font = titleFont

        worksheetInstance.merge_cells("A2:H2")
        worksheetInstance["A2"] = f"Расписание занятий: {groupTitle}"
        worksheetInstance["A2"].font = subFont

        # Блок легенды обозначений
        worksheetInstance["A3"] = "Обозначения:"
        worksheetInstance["A3"].font = boldFont
        worksheetInstance["B3"] = "Красная неделя"
        worksheetInstance["B3"].fill = fillRedWeek
        worksheetInstance["B3"].alignment = alignCenter
        worksheetInstance["C3"] = "Синяя неделя"
        worksheetInstance["C3"].fill = fillBlueWeek
        worksheetInstance["C3"].alignment = alignCenter
        worksheetInstance["D3"] = "Обе недели"
        worksheetInstance["D3"].fill = fillBothWeeks
        worksheetInstance["D3"].alignment = alignCenter

        rowIndex = 5
        tableHeaders = ["Время", "Неделя", "Тип", "Дисциплина", "Аудитория", "Преподаватель", "Группа", "Подгруппа"]

        for dayTitle, lessonsList in pGroupSchedule.daysMap.items():
            if not lessonsList:
                continue
            # end of if not lessonsList

            # Заголовок дня недели
            worksheetInstance.merge_cells(start_row=rowIndex, start_column=1, end_row=rowIndex, end_column=8)
            dayCell = worksheetInstance.cell(row=rowIndex, column=1, value=dayTitle.upper())
            dayCell.font = dayHeaderFont
            dayCell.fill = dayHeaderFill
            dayCell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            worksheetInstance.row_dimensions[rowIndex].height = 22
            rowIndex += 1

            # Заголовки столбцов таблицы
            for colIdx, headerTitle in enumerate(tableHeaders, 1):
                hdrCell = worksheetInstance.cell(row=rowIndex, column=colIdx, value=headerTitle)
                hdrCell.font = columnHeaderFont
                hdrCell.fill = columnHeaderFill
                hdrCell.alignment = alignCenter
                hdrCell.border = tableBorder
            # end of for colIdx
            worksheetInstance.row_dimensions[rowIndex].height = 20
            rowIndex += 1

            # Построчный вывод занятий
            for lesson in lessonsList:
                if lesson.weekType == "RED":
                    weekText = "Красная"
                    currentFill = fillRedWeek
                elif lesson.weekType == "BLUE":
                    weekText = "Синяя"
                    currentFill = fillBlueWeek
                else:
                    weekText = "Обе недели"
                    currentFill = fillBothWeeks
                # end of if lesson.weekType

                worksheetInstance.cell(row=rowIndex, column=1, value=lesson.time).alignment = alignCenter
                worksheetInstance.cell(row=rowIndex, column=2, value=weekText).alignment = alignCenter
                worksheetInstance.cell(row=rowIndex, column=3, value=lesson.lessonType).alignment = alignCenter
                worksheetInstance.cell(row=rowIndex, column=4, value=lesson.subject).alignment = alignLeft
                worksheetInstance.cell(row=rowIndex, column=5, value=lesson.classroom).alignment = alignCenter
                worksheetInstance.cell(row=rowIndex, column=6, value=lesson.teacher).alignment = alignLeft
                worksheetInstance.cell(row=rowIndex, column=7, value=getattr(lesson, "group", "Б.ПИН.ИИ.25.16")).alignment = alignCenter
                worksheetInstance.cell(row=rowIndex, column=8, value=lesson.subgroup or "Вся группа").alignment = alignCenter

                for colIdx in range(1, 9):
                    dataCell = worksheetInstance.cell(row=rowIndex, column=colIdx)
                    dataCell.font = dataFont
                    dataCell.fill = currentFill
                    dataCell.border = tableBorder
                # end of for colIdx

                worksheetInstance.row_dimensions[rowIndex].height = 26
                rowIndex += 1
            # end of for lesson

            rowIndex += 1
        # end of for dayTitle, lessonsList

        # Задание оптимальной ширины столбцов
        columnWidths = {1: 12, 2: 14, 3: 15, 4: 50, 5: 14, 6: 28, 7: 24, 8: 15}
        for colNumber, widthValue in columnWidths.items():
            worksheetInstance.column_dimensions[get_column_letter(colNumber)].width = widthValue
        # end of for colNumber

        workbookInstance.save(pFilePath)
    # end of export

# end of class ExcelScheduleExporter
# end of ExcelExporter.py
