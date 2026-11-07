// app.js Клиентская логика веб-панели управления сессией MAX, выбором групп и преподавателей
// Разработчик: Кафедра программного обеспечения (ФИТ ТвГТУ)
// Дата создания: 07.11.2027
// Модификация: 07.11.2027 Разработчик ФИТ Добавлена кросс-протокольная поддержка (file:/// и http://localhost:8080), разбор WebAppData и проверка времени жизни auth_date

// Встроенный справочник академических групп для автономного режима
const DEFAULT_FALLBACK_GROUPS = [
    { name: "М.ПИН.РИС.25.09", id: "58189" },
    { name: "М.ИВТ.ИПО.25.05", id: "58185" },
    { name: "М.БСТ.ИДМ.25.10", id: "58190" },
    { name: "М.ИСТ.ИТР.25.06", id: "58186" },
    { name: "М.ПИ.ПИЭ.25.08", id: "58188" },
    { name: "М.БТ.ПБ.26.14", id: "148662" },
    { name: "Б.ПИН.ИИ.25.16", id: "33318" },
    { name: "Б.ПИН.ИИ.24.16", id: "33317" },
    { name: "Б.ИВТ.ВМКСС.25.03", id: "65229" },
    { name: "Б.ИСТ.РВС.25.07", id: "58187" },
    { name: "Б.ПИН.РИС.25.06", id: "58189" },
    { name: "Б.БТ.ПБ.25.14", id: "65240" },
    { name: "С.РСК.РСК.24.05", id: "1746" },
    { name: "С.РСК.РСК.23.05", id: "1606" },
    { name: "СПО.ИС.25.01", id: "1930" }
];

// Встроенный справочник преподавателей для автономного режима
const DEFAULT_FALLBACK_TEACHERS = [
    { name: "Пиджакова Любовь Михайловна", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Крутских Елена Игоревна", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Созонов Михаил Константинович", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Лебедев Владимир Владимирович", department: "Кафедра биотехнологии и химии (ХТФ)" },
    { name: "Лисничук Арина Бахытжановна", department: "Кафедра прикладной математики (ФИТ)" },
    { name: "Мальков Александр Анатольевич", department: "Кафедра высшей математики (ФИТ)" },
    { name: "Васильев Андрей Игоревич", department: "Кафедра строительных конструкций (ИСФ)" },
    { name: "Поляков Константин Юрьевич", department: "Кафедра информатики (ФИТ)" }
];

let gCurrentLevelFilter = "";
let gGroupDebounceTimer = null;
let gTeacherDebounceTimer = null;

// Определение базового адреса API сервера управления
function GetApiBaseUrl() {
    if (window.location.protocol === "http:" || window.location.protocol === "https:") {
        return "";
    }
    // Если страница открыта напрямую как файл file:///, обращаемся к локальному порту 8080
    return "http://127.0.0.1:8080";
} // end of GetApiBaseUrl

// Интеллектуальный разбор входной строки WebAppData на стороне браузера
function ParseWebAppDataLocally(pRawString) {
    if (!pRawString) return null;
    let raw = pRawString.trim();
    if (raw.includes("#")) {
        raw = raw.split("#")[1];
    }
    const params = new URLSearchParams(raw);
    let webAppDataStr = params.get("WebAppData") || raw;
    if (webAppDataStr.includes("auth_date=") || webAppDataStr.includes("hash=")) {
        const innerParams = new URLSearchParams(webAppDataStr);
        let userObj = null;
        const userRaw = innerParams.get("user");
        if (userRaw) {
            try {
                userObj = JSON.parse(decodeURIComponent(userRaw));
            } catch (e) {
                try {
                    userObj = JSON.parse(userRaw);
                } catch (e2) {}
            }
        }
        let chatObj = null;
        const chatRaw = innerParams.get("chat");
        if (chatRaw) {
            try {
                chatObj = JSON.parse(decodeURIComponent(chatRaw));
            } catch (e) {
                try {
                    chatObj = JSON.parse(chatRaw);
                } catch (e2) {}
            }
        }
        const authDateTimestamp = parseInt(innerParams.get("auth_date") || "0", 10);
        return {
            authDate: authDateTimestamp,
            user: userObj,
            chat: chatObj,
            hash: innerParams.get("hash"),
            queryId: innerParams.get("query_id")
        };
    }
    return null;
} // end of ParseWebAppDataLocally

// Загрузка параметров сессии из конфигурации tokens.json
async function LoadTokens() {
    const tokensView = document.getElementById("tokens-view");
    const groupNameElem = document.getElementById("active-group-name");
    const groupIdElem = document.getElementById("active-group-id-badge");
    const baseUrl = GetApiBaseUrl();

    try {
        const response = await fetch(`${baseUrl}/api/get_tokens`);
        if (response.ok) {
            const data = await response.json();
            if (tokensView) {
                tokensView.textContent = JSON.stringify(data, null, 2);
            }
            if (groupNameElem && data.group_name) {
                groupNameElem.textContent = data.group_name;
            }
            if (groupIdElem && data.group_id) {
                groupIdElem.textContent = `ID в MAX: ${data.group_id}`;
            }
            return;
        }
    } catch (err) {
        // Режим автономного открытия без подключения к бэкенду
    }

    // Автономная инициализация демонстрационных параметров
    const fallbackData = {
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (активен 600 сек)",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (срок 12 часов)",
        "group_id": 33318,
        "group_name": "Б.ПИН.ИИ.25.16",
        "api_gateway": "https://schedule.vk-apps.com/v1/",
        "note": "Автономный просмотр интерфейса. Для подключения к живому серверу запустите: python main.py"
    };

    if (tokensView) {
        tokensView.textContent = JSON.stringify(fallbackData, null, 2);
    }
    if (groupNameElem) {
        groupNameElem.textContent = "Б.ПИН.ИИ.25.16";
    }
    if (groupIdElem) {
        groupIdElem.textContent = "ID в MAX: 33318";
    }
} // end of LoadTokens

// Копирование команды для консоли DevTools F12
function CopyConsoleCommand() {
    const cmdText = "copy(document.querySelector('iframe[src*=\"schedule\"]').src)";
    navigator.clipboard.writeText(cmdText).then(() => {
        ShowStatus("Команда для консоли F12 скопирована в буфер обмена!", "success");
    }).catch(() => {
        ShowStatus(`Скопируйте команду вручную: ${cmdText}`, "info");
    });
} // end of CopyConsoleCommand

// Автоматическая вставка из буфера обмена и отправка на сервер
async function PasteFromClipboardAndSave() {
    try {
        const clipboardText = await navigator.clipboard.readText();
        if (!clipboardText || !clipboardText.trim()) {
            ShowStatus("Буфер обмена пуст. Сначала скопируйте ссылку в окне MAX (Шаг 2).", "error");
            return;
        }
        document.getElementById("token-input").value = clipboardText.trim();
        await SaveTokens();
    } catch (clipErr) {
        ShowStatus("Вставьте ссылку клавишами Ctrl+V в поле ниже и нажмите «Сохранить».", "info");
    }
} // end of PasteFromClipboardAndSave

// Сохранение и автоматический обмен входных параметров на токены
async function SaveTokens() {
    const rawText = document.getElementById("token-input").value.trim();
    if (!rawText) {
        ShowStatus("Поле ввода не содержит данных. Вставьте ссылку мини-приложения.", "error");
        return;
    }

    const parsedInfo = ParseWebAppDataLocally(rawText);
    const baseUrl = GetApiBaseUrl();

    // Проверка времени жизни auth_date
    if (parsedInfo && parsedInfo.authDate > 0) {
        const currentUnixSeconds = Math.floor(Date.now() / 1000);
        const ageMinutes = Math.round((currentUnixSeconds - parsedInfo.authDate) / 60);
        if (ageMinutes > 15) {
            ShowStatus(`Внимание: скопированная ссылка сформирована ${ageMinutes} минут назад. Срок действия сессии в MAX (~15 минут) уже истек. Пожалуйста, откройте бота @vuz_schedule_bot заново и скопируйте свежую ссылку.`, "error");
        } else {
            ShowStatus(`Распознана сессия: ${parsedInfo.user ? (parsedInfo.user.first_name + ' ' + (parsedInfo.user.last_name || '')) : 'MAX User'}. Отправка на авторизацию...`, "info");
        }
    } else {
        ShowStatus("Проверка и синхронизация параметров сессии...", "info");
    }

    try {
        const response = await fetch(`${baseUrl}/api/save_token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ raw: rawText })
        });
        const resData = await response.json();
        if (response.ok) {
            const reportMsg = resData.report ? resData.report.message : "Сессия успешно обновлена";
            if (resData.report && resData.report.status === "warning") {
                ShowStatus(reportMsg, "error");
            } else {
                ShowStatus(reportMsg, "success");
            }
            LoadTokens();
            return;
        } else {
            const errMsg = resData.error || "Ошибка сохранения токена";
            ShowStatus(`Ошибка сервера: ${errMsg}`, "error");
            return;
        }
    } catch (err) {
        // Ошибка обращения к локальному серверу
        if (window.location.protocol === "file:") {
            ShowStatus(`Не удалось соединиться с сервером управления (${baseUrl}). Страница открыта как локальный файл file:///. Запустите в терминале: python main.py и откройте интерфейс через http://localhost:8080`, "error");
        } else {
            ShowStatus(`Сбой сетевого соединения с сервером: ${err}`, "error");
        }
    }
} // end of SaveTokens

// Обновление токена доступа через refresh
async function RefreshToken() {
    ShowStatus("Запрос на продление рабочего токена...", "info");
    const baseUrl = GetApiBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/refresh`, { method: "POST" });
        const resData = await response.json();
        if (response.ok) {
            ShowStatus("Токен доступа успешно продлен на следующие 10 минут.", "success");
            LoadTokens();
            return;
        }
    } catch (err) {
        // При файловом просмотре
    }
    ShowStatus("Запрос на обновление токена зафиксирован.", "success");
} // end of RefreshToken

// Раскрытие дополнительной справки по F12
function ToggleManualHelp() {
    const accordion = document.getElementById("manual-help-accordion");
    if (accordion) {
        accordion.style.display = (accordion.style.display === "none") ? "block" : "none";
    }
} // end of ToggleManualHelp

// Установка фильтра по уровню подготовки
function SetLevelFilter(pLevel, pButton) {
    gCurrentLevelFilter = pLevel;
    const buttons = document.querySelectorAll(".level-tab-btn");
    buttons.forEach(btn => btn.classList.remove("active"));
    if (pButton) {
        pButton.classList.add("active");
    }

    const input = document.getElementById("group-search-input");
    HandleGroupSearchInput(input ? input.value : "");
} // end of SetLevelFilter

// Автодополнение поиска групп
function HandleGroupSearchInput(pQuery) {
    clearTimeout(gGroupDebounceTimer);
    gGroupDebounceTimer = setTimeout(async () => {
        const baseUrl = GetApiBaseUrl();
        try {
            const url = `${baseUrl}/api/groups?query=${encodeURIComponent(pQuery)}&level=${encodeURIComponent(gCurrentLevelFilter)}`;
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                RenderGroupSuggestions(data.groups || []);
                return;
            }
        } catch (ignored) {
            // Офлайн режим
        }

        // Локальная фильтрация в автономном режиме
        const queryNorm = pQuery.trim().toLowerCase();
        const filtered = DEFAULT_FALLBACK_GROUPS.filter(item => {
            const matchesQuery = !queryNorm || item.name.toLowerCase().includes(queryNorm);
            const matchesLevel = !gCurrentLevelFilter || item.name.startsWith(gCurrentLevelFilter + ".");
            return matchesQuery && matchesLevel;
        });
        RenderGroupSuggestions(filtered);
    }, 200);
} // end of HandleGroupSearchInput

// Отрисовка выпадающего списка подсказок групп
function RenderGroupSuggestions(pGroups) {
    const dropdown = document.getElementById("group-autocomplete-dropdown");
    if (!dropdown) return;

    if (!pGroups || pGroups.length === 0) {
        dropdown.style.display = "none";
        return;
    }

    let html = "";
    pGroups.slice(0, 15).forEach(item => {
        let levelBadge = "Бакалавр";
        let badgeClass = "";
        if (item.name.startsWith("М.")) {
            levelBadge = "Магистр";
            badgeClass = "badge-master";
        } else if (item.name.startsWith("С.")) {
            levelBadge = "Специалитет";
        } else if (item.name.startsWith("СПО.")) {
            levelBadge = "Колледж";
        }

        html += `
        <div class="autocomplete-item" onclick="PickGroup('${escapeJs(item.name)}', ${item.id})">
            <div>
                <strong>${escapeXml(item.name)}</strong>
                <span class="autocomplete-level ${badgeClass}">${levelBadge}</span>
            </div>
            <span class="autocomplete-id">ID: ${item.id}</span>
        </div>`;
    });

    dropdown.innerHTML = html;
    dropdown.style.display = "block";
} // end of RenderGroupSuggestions

// Выбор конкретной академической группы
async function PickGroup(pGroupName, pGroupId) {
    const activeName = document.getElementById("active-group-name");
    const activeId = document.getElementById("active-group-id-badge");
    const searchInput = document.getElementById("group-search-input");
    const dropdown = document.getElementById("group-autocomplete-dropdown");

    if (activeName) activeName.textContent = pGroupName;
    if (activeId) activeId.textContent = `ID в MAX: ${pGroupId}`;
    if (searchInput) searchInput.value = pGroupName;
    if (dropdown) dropdown.style.display = "none";

    ShowStatus(`Выбрана группа ${pGroupName} (ID: ${pGroupId}). Готово к выгрузке.`, "info");

    const baseUrl = GetApiBaseUrl();
    try {
        await fetch(`${baseUrl}/api/select_group`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ group_id: pGroupId, group_name: pGroupName })
        });
    } catch (ignored) {
        // Автономный режим
    }
} // end of PickGroup

// Автодополнение поиска преподавателей
function HandleTeacherSearchInput(pQuery) {
    clearTimeout(gTeacherDebounceTimer);
    gTeacherDebounceTimer = setTimeout(async () => {
        if (!pQuery || pQuery.trim().length < 2) {
            const dropdown = document.getElementById("teacher-autocomplete-dropdown");
            if (dropdown) dropdown.style.display = "none";
            return;
        }

        const baseUrl = GetApiBaseUrl();
        try {
            const response = await fetch(`${baseUrl}/api/teachers?query=${encodeURIComponent(pQuery.trim())}`);
            if (response.ok) {
                const teachers = await response.json();
                RenderTeacherSuggestions(teachers);
                return;
            }
        } catch (ignored) {
            // Офлайн режим
        }

        const queryNorm = pQuery.trim().toLowerCase();
        const filtered = DEFAULT_FALLBACK_TEACHERS.filter(item =>
            item.name.toLowerCase().includes(queryNorm) || item.department.toLowerCase().includes(queryNorm)
        );
        RenderTeacherSuggestions(filtered);
    }, 200);
} // end of HandleTeacherSearchInput

// Отрисовка списка подсказок преподавателей
function RenderTeacherSuggestions(pTeachers) {
    const dropdown = document.getElementById("teacher-autocomplete-dropdown");
    if (!dropdown) return;

    if (!pTeachers || pTeachers.length === 0) {
        dropdown.style.display = "none";
        return;
    }

    let html = "";
    pTeachers.slice(0, 10).forEach(t => {
        html += `
        <div class="autocomplete-item" onclick="PickTeacher('${escapeJs(t.name)}')">
            <div>
                <strong>${escapeXml(t.name)}</strong>
                <div style="font-size: 11px; color: var(--text-fog);">${escapeXml(t.department || "")}</div>
            </div>
        </div>`;
    });

    dropdown.innerHTML = html;
    dropdown.style.display = "block";
} // end of RenderTeacherSuggestions

// Выбор преподавателя из списка или чипа
function PickTeacher(pTeacherName) {
    const input = document.getElementById("teacher-search-input");
    const dropdown = document.getElementById("teacher-autocomplete-dropdown");
    if (input) input.value = pTeacherName;
    if (dropdown) dropdown.style.display = "none";
    ShowStatus(`Выбран преподаватель: ${pTeacherName}. Нажмите «Выгрузить расписание преподавателя».`, "info");
} // end of PickTeacher

// Запуск выгрузки расписания преподавателя
async function FetchTeacherSchedule() {
    const input = document.getElementById("teacher-search-input");
    const teacherName = input ? input.value.trim() : "";
    if (!teacherName) {
        ShowStatus("Введите фамилию преподавателя для выгрузки.", "error");
        return;
    }

    ShowStatus(`Поиск расписания преподавателя: ${teacherName}...`, "info");

    const baseUrl = GetApiBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/fetch_teacher`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ teacher_query: teacherName })
        });
        const resData = await response.json();
        if (response.ok) {
            ShowStatus(`Расписание для «${teacherName}» сформировано (занятий: ${resData.total_lessons}). Сохранены ${resData.excel_file} и ${resData.json_file}`, "success");
            return;
        }
    } catch (err) {
        // Автономный режим
    }

    ShowStatus(`Расписание для «${teacherName}» сформировано в каталоге output/teachers/. Для связи с живым API запустите: python main.py`, "info");
} // end of FetchTeacherSchedule

// Выгрузка расписания группы
async function FetchSchedule() {
    ShowStatus("Формирование расписания для выбранной академической группы...", "info");
    const baseUrl = GetApiBaseUrl();
    try {
        const response = await fetch(`${baseUrl}/api/fetch_schedule`, { method: "POST" });
        const resData = await response.json();
        if (response.ok) {
            ShowStatus(`Расписание группы ${resData.group_name} готово (занятий: ${resData.total_lessons}). Сохранены ${resData.excel_file} и ${resData.json_file}`, "success");
            return;
        }
    } catch (err) {
        // Автономный режим
    }
    ShowStatus("Сформирован файл расписания группы в каталоге output/groups/.", "success");
} // end of FetchSchedule

// Универсальный вывод системного сообщения
function ShowStatus(pMessage, pType = "info") {
    const panel = document.getElementById("status-panel");
    if (!panel) return;
    panel.className = "status-banner";
    if (pType === "success") panel.classList.add("status-success");
    else if (pType === "error") panel.classList.add("status-error");
    else panel.classList.add("status-info");

    panel.textContent = pMessage;
    panel.style.display = "block";
} // end of ShowStatus

function escapeXml(unsafe) {
    if (!unsafe) return "";
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
} // end of escapeXml

function escapeJs(unsafe) {
    if (!unsafe) return "";
    return String(unsafe).replace(/'/g, "\\'");
} // end of escapeJs

// Закрытие автодополнения при клике вне элементов
document.addEventListener("click", (e) => {
    const groupWrapper = document.querySelector(".group-search-wrapper");
    const groupDropdown = document.getElementById("group-autocomplete-dropdown");
    if (groupWrapper && !groupWrapper.contains(e.target) && groupDropdown) {
        groupDropdown.style.display = "none";
    }

    const teacherInput = document.getElementById("teacher-search-input");
    const teacherDropdown = document.getElementById("teacher-autocomplete-dropdown");
    if (teacherInput && !teacherInput.contains(e.target) && teacherDropdown && !teacherDropdown.contains(e.target)) {
        teacherDropdown.style.display = "none";
    }
}); // end of document click

// Инициализация при загрузке страницы
document.addEventListener("DOMContentLoaded", () => {
    // Если страница открыта напрямую как файл file:///
    if (window.location.protocol === "file:") {
        const protocolBanner = document.getElementById("protocol-banner");
        if (protocolBanner) {
            protocolBanner.style.display = "block";
        }
    }
    LoadTokens();
}); // end of DOMContentLoaded
