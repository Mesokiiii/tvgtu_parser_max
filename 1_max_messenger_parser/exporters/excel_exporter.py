# ExcelExporter.py Модуль экспорта расписания MAX в формат Microsoft Excel
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: формирование стилизованной электронной таблицы расписания с разметкой недель

from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class MaxExcelExporter:
    """
    Класс формирует Excel-документ из структуры данных API цифрового расписания.
    """

    WEEKDAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    def __init__(self):
        """
        Конструктор экспортера.
        """
        pass
    # end of __init__

    def export(self, pScheduleDaysList, pGroupName, pOutputFilePath):
        """
        Генерация файла Excel.

        Входные параметры:
            pScheduleDaysList (list): массив расписания по дням из API.
            pGroupName (str): наименование учебной группы.
            pOutputFilePath (str): путь сохранения таблицы.
        """
        workbookInstance = openpyxl.Workbook()
        worksheetInstance = workbookInstance.active
        worksheetInstance.title = "Расписание MAX"
        worksheetInstance.views.sheetView[0].showGridLines = True

        titleFont = Font(name="Calibri", size=14, bold=True, color="1F497D")
        subFont = Font(name="Calibri", size=10, italic=True, color="595959")
        dayHeaderFont = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        columnHeaderFont = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        dataFont = Font(name="Calibri", size=10)

        borderSide = Side(border_style="thin", color="D9D9D9")
        tableBorder = Border(left=borderSide, right=borderSide, top=borderSide, bottom=borderSide)

        headerFillRed = PatternFill("solid", fgColor="8B0000")
        headerFillBlue = PatternFill("solid", fgColor="1E3A8A")
        columnHeaderFill = PatternFill("solid", fgColor="34495E")

        rowFillRed = PatternFill("solid", fgColor="FFF0F0")
        rowFillBlue = PatternFill("solid", fgColor="F0F6FF")

        alignCenter = Alignment(horizontal="center", vertical="center", wrap_text=True)
        alignLeft = Alignment(horizontal="left", vertical="center", wrap_text=True)

        worksheetInstance.merge_cells("A1:G1")
        worksheetInstance["A1"] = f"ТвГТУ — Расписание: {pGroupName}"
        worksheetInstance["A1"].font = titleFont

        worksheetInstance.merge_cells("A2:G2")
        worksheetInstance["A2"] = "Источник: API цифрового расписания (многогрупповой сквозной опрос)"
        worksheetInstance["A2"].font = subFont

        tableHeaders = ["Дата", "Время", "Неделя", "Дисциплина", "Преподаватель", "Аудитория", "Группа"]
        currentRowIndex = 4

        for dayItem in pScheduleDaysList:
            dateString = dayItem.get("date", "")
            slotsList = dayItem.get("slots", [])
            if not slotsList:
                continue
            # end of if not slotsList

            dateObject = datetime.strptime(dateString, "%Y-%m-%d")
            dayName = self.WEEKDAY_NAMES[dateObject.weekday()]
            
            # Расчет четности по номеру недели в году: нечетная = красная, четная = синяя
            weekNumber = dateObject.isocalendar()[1]
            isOddWeek = (weekNumber % 2 != 0)
            weekDescription = "Красная неделя" if isOddWeek else "Синяя неделя"

            worksheetInstance.merge_cells(start_row=currentRowIndex, start_column=1, end_row=currentRowIndex, end_column=7)
            dayHeaderCell = worksheetInstance.cell(
                row=currentRowIndex,
                column=1,
                value=f"{dayName}, {dateObject.strftime('%d.%m.%Y')} — {weekDescription}"
            )
            dayHeaderCell.font = dayHeaderFont
            dayHeaderCell.fill = headerFillRed if isOddWeek else headerFillBlue
            dayHeaderCell.alignment = alignLeft
            worksheetInstance.row_dimensions[currentRowIndex].height = 22
            currentRowIndex += 1

            for colIdx, headerName in enumerate(tableHeaders, 1):
                colCell = worksheetInstance.cell(row=currentRowIndex, column=colIdx, value=headerName)
                colCell.font = columnHeaderFont
                colCell.fill = columnHeaderFill
                colCell.alignment = alignCenter
                colCell.border = tableBorder
            # end of for colIdx
            worksheetInstance.row_dimensions[currentRowIndex].height = 20
            currentRowIndex += 1

            currentRowFill = rowFillRed if isOddWeek else rowFillBlue

            for slotItem in slotsList:
                timeSpanString = f"{slotItem['time']['start']} - {slotItem['time']['end']}"
                for eventItem in slotItem.get("events", []):
                    subjectTitle = eventItem.get("name", "")
                    rawType = eventItem.get("type", "")
                    typeName = rawType.get("name", "") if isinstance(rawType, dict) else str(rawType)
                    fullSubjectTitle = f"{subjectTitle} ({typeName})" if typeName else subjectTitle

                    teachersList = [t.get("name", "") if isinstance(t, dict) else str(t) for t in eventItem.get("teachers", [])]
                    teachersString = ", ".join(teachersList)

                    roomsList = []
                    for r in eventItem.get("rooms", []):
                        if isinstance(r, dict):
                            bName = r.get("building", {}).get("name", "") if isinstance(r.get("building"), dict) else ""
                            rName = r.get("name", "")
                            roomsList.append(f"{bName} {rName}".strip() if bName else rName)
                        else:
                            roomsList.append(str(r))
                    # end of for r
                    if not roomsList and eventItem.get("room"):
                        rm = eventItem.get("room")
                        roomsList.append(rm.get("name", "") if isinstance(rm, dict) else str(rm))
                    # end of if not roomsList
                    roomsString = ", ".join(roomsList)

                    groupString = eventItem.get("group_name", "Б.ПИН.ИИ.25.16")

                    worksheetInstance.cell(row=currentRowIndex, column=1, value=dateObject.strftime("%d.%m")).alignment = alignCenter
                    worksheetInstance.cell(row=currentRowIndex, column=2, value=timeSpanString).alignment = alignCenter
                    worksheetInstance.cell(row=currentRowIndex, column=3, value="Красная" if isOddWeek else "Синяя").alignment = alignCenter
                    worksheetInstance.cell(row=currentRowIndex, column=4, value=fullSubjectTitle).alignment = alignLeft
                    worksheetInstance.cell(row=currentRowIndex, column=5, value=teachersString).alignment = alignLeft
                    worksheetInstance.cell(row=currentRowIndex, column=6, value=roomsString).alignment = alignCenter
                    worksheetInstance.cell(row=currentRowIndex, column=7, value=groupString).alignment = alignCenter

                    for colIdx in range(1, 8):
                        cellObject = worksheetInstance.cell(row=currentRowIndex, column=colIdx)
                        cellObject.font = dataFont
                        cellObject.fill = currentRowFill
                        cellObject.border = tableBorder
                    # end of for colIdx

                    worksheetInstance.row_dimensions[currentRowIndex].height = 25
                    currentRowIndex += 1
                # end of for eventItem
            # end of for slotItem

            currentRowIndex += 1
        # end of for dayItem

        columnWidths = {1: 12, 2: 15, 3: 14, 4: 48, 5: 30, 6: 20, 7: 22}
        for colNumber, widthValue in columnWidths.items():
            worksheetInstance.column_dimensions[get_column_letter(colNumber)].width = widthValue
        # end of for colNumber

        workbookInstance.save(pOutputFilePath)
    # end of export

# end of class MaxExcelExporter
# end of ExcelExporter.py
