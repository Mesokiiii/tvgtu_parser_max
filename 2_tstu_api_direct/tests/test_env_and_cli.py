# test_env_and_cli.py
# Тесты работы с переменными окружения, CLI и сквозного цикла экспорта

import os
import sys
import json
import openpyxl
import pytest

currentDir = os.path.dirname(os.path.abspath(__file__))
parentDir = os.path.dirname(currentDir)
if parentDir not in sys.path:
    sys.path.insert(0, parentDir)

import main
from schedule_service import TstuScheduleService


class TestEnvAndCli:

    def test_get_bool_env(self, monkeypatch):
        monkeypatch.setenv("TEST_FLAG_TRUE_1", "true")
        monkeypatch.setenv("TEST_FLAG_TRUE_2", "1")
        monkeypatch.setenv("TEST_FLAG_TRUE_3", "yes")
        monkeypatch.setenv("TEST_FLAG_FALSE_1", "false")
        monkeypatch.setenv("TEST_FLAG_FALSE_2", "0")
        monkeypatch.setenv("TEST_FLAG_FALSE_3", "no")

        assert main._getBoolEnv("TEST_FLAG_TRUE_1") is True
        assert main._getBoolEnv("TEST_FLAG_TRUE_2") is True
        assert main._getBoolEnv("TEST_FLAG_TRUE_3") is True
        assert main._getBoolEnv("TEST_FLAG_FALSE_1") is False
        assert main._getBoolEnv("TEST_FLAG_FALSE_2") is False
        assert main._getBoolEnv("TEST_FLAG_FALSE_3") is False
        assert main._getBoolEnv("NON_EXISTENT_VAR", True) is True
        assert main._getBoolEnv("NON_EXISTENT_VAR", False) is False

    def test_get_arg_value(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["main.py", "--group", "М.ПИН.РИС.25.09", "--port", "9090"])
        assert main._getArgValue("--group") == "М.ПИН.РИС.25.09"
        assert main._getArgValue("--port") == "9090"
        assert main._getArgValue("--unknown", "default_val") == "default_val"

    def test_schedule_service_facade_integration(self, tmp_path):
        service = TstuScheduleService()
        groupsCache = os.path.join(parentDir, "data", "groups_list.json")
        assert os.path.exists(groupsCache), "Groups cache should exist"

        catalog = service.loadGroupsCatalog(groupsCache)
        assert len(catalog) >= 400
        assert "М.ПИН.РИС.25.09" in catalog
        assert "Б.ПИН.ИИ.25.16" in catalog

        # Получение расписания для группы магистратуры
        schedule = service.fetchSchedule("М.ПИН.РИС.25.09", groupsCache)
        assert schedule.groupName == "М.ПИН.РИС.25.09"
        totalLessons = sum(len(l) for l in schedule.daysMap.values())
        assert totalLessons > 0

        # Экспорт во все 3 формата: JSON, Excel, iCalendar
        jsonFile = str(tmp_path / "test_out.json")
        excelFile = str(tmp_path / "test_out.xlsx")
        icsFile = str(tmp_path / "test_out.ics")

        service.saveToJson(schedule, jsonFile)
        service.saveToExcel(schedule, excelFile)
        service.saveToIcs(schedule, icsFile, "2026-09-01", "2027-01-31")

        # Проверка валидности JSON
        assert os.path.exists(jsonFile)
        with open(jsonFile, "r", encoding="utf-8") as jf:
            parsedJson = json.load(jf)
        assert parsedJson["group"] == "М.ПИН.РИС.25.09"
        assert "schedule" in parsedJson

        # Проверка валидности Excel через openpyxl
        assert os.path.exists(excelFile)
        wb = openpyxl.load_workbook(excelFile)
        assert len(wb.sheetnames) >= 1
        ws = wb.active
        assert ws.max_row > 1

        # Проверка валидности iCalendar
        assert os.path.exists(icsFile)
        with open(icsFile, "r", encoding="utf-8") as icf:
            icsContent = icf.read()
        assert "BEGIN:VCALENDAR" in icsContent
        assert "BEGIN:VEVENT" in icsContent
        assert "М.ПИН.РИС.25.09" in icsContent

    def test_run_schedule_cycle_group(self, tmp_path):
        service = TstuScheduleService()
        config = {
            "export_json": True,
            "export_excel": True,
            "export_ics": True,
            "export_radicale": False,
            "radicale_url": "http://localhost:5232",
            "radicale_user": "tstu",
            "radicale_pass": "",
            "radicale_cal": "schedule",
            "semester_start": "2026-09-01",
            "semester_end": "2027-01-31"
        }
        groupsCache = os.path.join(parentDir, "data", "groups_list.json")
        main.RunScheduleCycle(service, "Б.ПИН.ИИ.25.16", None, config, str(tmp_path), groupsCache)

        expectedJson = tmp_path / "output" / "groups" / "schedule_Б.ПИН.ИИ.25.16.json"
        expectedXlsx = tmp_path / "output" / "groups" / "schedule_Б.ПИН.ИИ.25.16.xlsx"
        expectedIcs = tmp_path / "output" / "groups" / "schedule_Б.ПИН.ИИ.25.16.ics"

        assert expectedJson.exists()
        assert expectedXlsx.exists()
        assert expectedIcs.exists()

    def test_run_schedule_cycle_teacher(self, tmp_path):
        service = TstuScheduleService()
        config = {
            "export_json": True,
            "export_excel": True,
            "export_ics": True,
            "export_radicale": False,
            "radicale_url": "http://localhost:5232",
            "radicale_user": "tstu",
            "radicale_pass": "",
            "radicale_cal": "schedule",
            "semester_start": "2026-09-01",
            "semester_end": "2027-01-31"
        }
        groupsCache = os.path.join(parentDir, "data", "groups_list.json")
        main.RunScheduleCycle(service, "Б.ПИН.ИИ.25.16", "Пиджакова", config, str(tmp_path), groupsCache)

        teacherFiles = list((tmp_path / "output" / "teachers").glob("*Пиджакова*"))
        assert len(teacherFiles) >= 3, "Should create .json, .xlsx, .ics for teacher"
        extensions = {f.suffix for f in teacherFiles}
        assert ".json" in extensions
        assert ".xlsx" in extensions
        assert ".ics" in extensions
