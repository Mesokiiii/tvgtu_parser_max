# HttpServer.py Модуль встроенного локального веб-сервера управления сессией MAX
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Модификация 07.11.2027 Разработчик ФИТ Добавлены поддержка CORS, обработка OPTIONS и сохранение выгрузок в папки output/
# Назначение: предоставление веб-интерфейса и REST API для ввода токенов, выбора групп и запуска выгрузок

import os
import json
import urllib.parse
import http.server
import socketserver


class WebControlServer:
    """
    Класс инкапсулирует запуск локального веб-сервера управления авторизацией.
    """

    def __init__(self, pPort, pSessionManager, pAuthClient, pScheduleClient, pExcelExporter, pJsonExporter, pWebDir):
        """
        Конструктор сервера управления.
        """
        self.port = pPort
        self.sessionManager = pSessionManager
        self.authClient = pAuthClient
        self.scheduleClient = pScheduleClient
        self.excelExporter = pExcelExporter
        self.jsonExporter = pJsonExporter
        self.webDir = pWebDir
    # end of __init__

    def createHandler(self):
        """
        Фабричный метод создания обработчика HTTP-запросов с внедрением контекста.
        """
        serverContext = self

        class BoundRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=serverContext.webDir, **kwargs)
            # end of __init__

            def _sendCorsHeaders(self):
                """Отправка CORS заголовков для поддержки обращений с file:/// и кросс-доменов."""
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            # end of _sendCorsHeaders

            def do_OPTIONS(self):
                """Обработка предварительных preflight CORS запросов браузера."""
                self.send_response(200)
                self._sendCorsHeaders()
                self.end_headers()
            # end of do_OPTIONS

            def do_GET(self):
                parsedUrl = urllib.parse.urlparse(self.path)
                urlPath = parsedUrl.path
                queryParams = urllib.parse.parse_qs(parsedUrl.query)

                # 1. Отдача главной страницы авторизации
                if urlPath == "/" or urlPath == "/login":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    pageFile = os.path.join(serverContext.webDir, "login_page.html")
                    with open(pageFile, "rb") as fd:
                        self.wfile.write(fd.read())
                    # end of with open
                    return
                # end of if urlPath == "/"

                # 2. Отдача вынесенного файла каскадных таблиц стилей (CSS)
                elif urlPath == "/style.css":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    cssFile = os.path.join(serverContext.webDir, "style.css")
                    if os.path.exists(cssFile):
                        with open(cssFile, "rb") as fd:
                            self.wfile.write(fd.read())
                        # end of with open
                    # end of if os.path.exists
                    return
                # end of elif urlPath == "/style.css"

                # 3. Отдача вынесенного файла клиентского JavaScript (JS)
                elif urlPath == "/app.js":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    jsFile = os.path.join(serverContext.webDir, "app.js")
                    if os.path.exists(jsFile):
                        with open(jsFile, "rb") as fd:
                            self.wfile.write(fd.read())
                        # end of with open
                    # end of if os.path.exists
                    return
                # end of elif urlPath == "/app.js"

                # 4. REST API: получение текущих параметров сессии
                elif urlPath == "/api/get_tokens":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    tokensData = serverContext.sessionManager.tokensCache
                    self.wfile.write(json.dumps(tokensData, ensure_ascii=False, indent=2).encode("utf-8"))
                    return
                # end of elif urlPath == "/api/get_tokens"

                # 5. REST API: получение и фильтрация каталога групп (включая магистратуру)
                elif urlPath == "/api/groups":
                    searchQuery = queryParams.get("query", [""])[0]
                    levelFilter = queryParams.get("level", [""])[0]
                    groupsList = serverContext.sessionManager.searchGroups(pQuery=searchQuery, pLevel=levelFilter)

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "total": len(groupsList),
                        "groups": groupsList
                    }, ensure_ascii=False, indent=2).encode("utf-8"))
                    return
                # end of elif urlPath == "/api/groups"

                # 6. REST API: каталог преподавателей
                elif urlPath == "/api/teachers":
                    searchQuery = queryParams.get("query", [""])[0].lower()
                    teachersDataPath = os.path.join(os.path.dirname(serverContext.webDir), "data", "teachers_directory.json")
                    teachersList = []
                    if os.path.exists(teachersDataPath):
                        with open(teachersDataPath, "r", encoding="utf-8") as tFd:
                            teachersList = json.load(tFd)
                        if searchQuery:
                            teachersList = [t for t in teachersList if searchQuery in t.get("name", "").lower() or searchQuery in t.get("department", "").lower()]
                        # end of if searchQuery
                    # end of if os.path.exists

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._sendCorsHeaders()
                    self.end_headers()
                    self.wfile.write(json.dumps(teachersList, ensure_ascii=False, indent=2).encode("utf-8"))
                    return
                # end of elif urlPath == "/api/teachers"

                super().do_GET()
            # end of do_GET

            def do_POST(self):
                contentLength = int(self.headers.get("Content-Length", 0))
                requestPayload = self.rfile.read(contentLength).decode("utf-8") if contentLength > 0 else ""

                if self.path == "/api/save_token":
                    try:
                        inputData = json.loads(requestPayload)
                        rawString = inputData.get("raw", "")
                        report = serverContext.sessionManager.parseAndStoreRawInput(rawString, serverContext.authClient)

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": True,
                            "report": report,
                            "tokens": serverContext.sessionManager.tokensCache
                        }, ensure_ascii=False).encode("utf-8"))
                    except Exception as saveError:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(saveError)}, ensure_ascii=False).encode("utf-8"))
                    # end of try
                    return

                elif self.path == "/api/select_group":
                    try:
                        inputData = json.loads(requestPayload)
                        groupId = inputData.get("group_id")
                        groupName = inputData.get("group_name")
                        if not groupId or not groupName:
                            raise ValueError("Параметры group_id и group_name обязательны")
                        # end of if not groupId

                        serverContext.sessionManager.setTargetGroup(groupId, groupName)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": True,
                            "group_id": groupId,
                            "group_name": groupName
                        }, ensure_ascii=False).encode("utf-8"))
                    except Exception as selectError:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(selectError)}, ensure_ascii=False).encode("utf-8"))
                    # end of try
                    return

                elif self.path == "/api/refresh":
                    try:
                        refreshToken = serverContext.sessionManager.getRefreshToken()
                        freshAuthToken = serverContext.authClient.refreshAccessToken(refreshToken)
                        serverContext.sessionManager.save({"auth_token": freshAuthToken})

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "auth_token": freshAuthToken}, ensure_ascii=False).encode("utf-8"))
                    except Exception as refError:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(refError)}, ensure_ascii=False).encode("utf-8"))
                    # end of try
                    return

                elif self.path == "/api/fetch_schedule":
                    try:
                        fallbackPath = os.path.join(os.path.dirname(serverContext.webDir), "data", "cached_schedule_pin.json")
                        targetGrpId = serverContext.sessionManager.getTargetGroupId()
                        targetGrpName = serverContext.sessionManager.getTargetGroupName()

                        scheduleData = serverContext.scheduleClient.fetchSchedule(pGroupId=targetGrpId, pFallbackFilePath=fallbackPath)

                        baseDir = os.path.dirname(serverContext.webDir)
                        cleanName = targetGrpName.replace("/", "_").replace("\\", "_")
                        outputGroupsDir = os.path.join(baseDir, "output", "groups")
                        os.makedirs(outputGroupsDir, exist_ok=True)
                        jsonOut = os.path.join(outputGroupsDir, f"schedule_{cleanName}.json")
                        excelOut = os.path.join(outputGroupsDir, f"schedule_{cleanName}.xlsx")

                        serverContext.jsonExporter.export(scheduleData, jsonOut)
                        serverContext.excelExporter.export(scheduleData, targetGrpName, excelOut)

                        totalLessons = sum(
                            sum(len(s.get("events", [])) for s in d.get("slots", []))
                            for d in scheduleData
                        )

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": True,
                            "group_name": targetGrpName,
                            "total_lessons": totalLessons,
                            "excel_file": f"output/groups/schedule_{cleanName}.xlsx",
                            "json_file": f"output/groups/schedule_{cleanName}.json"
                        }, ensure_ascii=False).encode("utf-8"))
                    except Exception as fetchError:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(fetchError)}, ensure_ascii=False).encode("utf-8"))
                    # end of try
                    return

                elif self.path == "/api/fetch_teacher":
                    try:
                        inputData = json.loads(requestPayload)
                        teacherQuery = inputData.get("teacher_query", "").strip()
                        if not teacherQuery:
                            raise ValueError("Укажите фамилию или ФИО преподавателя")
                        # end of if not teacherQuery

                        fallbackPath = os.path.join(os.path.dirname(serverContext.webDir), "data", "cached_schedule_pin.json")
                        teacherDays = serverContext.scheduleClient.fetchTeacherSchedule(teacherQuery, pFallbackFilePath=fallbackPath)

                        baseDir = os.path.dirname(serverContext.webDir)
                        title = f"Преподаватель_{teacherQuery.replace(' ', '_')}"
                        outputTeachersDir = os.path.join(baseDir, "output", "teachers")
                        os.makedirs(outputTeachersDir, exist_ok=True)
                        jsonOut = os.path.join(outputTeachersDir, f"{title}.json")
                        excelOut = os.path.join(outputTeachersDir, f"{title}.xlsx")

                        serverContext.jsonExporter.export(teacherDays, jsonOut)
                        serverContext.excelExporter.export(teacherDays, f"Преподаватель: {teacherQuery}", excelOut)

                        totalLessons = sum(
                            sum(len(s.get("events", [])) for s in d.get("slots", []))
                            for d in teacherDays
                        )

                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": True,
                            "teacher_name": teacherQuery,
                            "total_lessons": totalLessons,
                            "excel_file": f"output/teachers/{title}.xlsx",
                            "json_file": f"output/teachers/{title}.json"
                        }, ensure_ascii=False).encode("utf-8"))
                    except Exception as teacherError:
                        self.send_response(500)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._sendCorsHeaders()
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(teacherError)}, ensure_ascii=False).encode("utf-8"))
                    # end of try
                    return
                # end of if self.path
            # end of do_POST
        # end of class BoundRequestHandler

        return BoundRequestHandler
    # end of createHandler

    def start(self):
        """Запуск цикла прослушивания входящих сетевых подключений."""
        handlerClass = self.createHandler()
        with socketserver.TCPServer(("", self.port), handlerClass) as httpDaemon:
            try:
                print(f"Сервер управления запущен на порту {self.port} (http://localhost:{self.port})")
                httpDaemon.serve_forever()
            except KeyboardInterrupt:
                print("Сервер остановлен пользователем.")
            # end of try
        # end of with socketserver
    # end of start

# end of class WebControlServer
# end of HttpServer.py
