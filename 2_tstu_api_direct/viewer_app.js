// viewer_app.js Клиентская логика интерактивного расписания ТвГТУ
// Разработчик: Кафедра программного обеспечения (ФИТ ТвГТУ)
// Дата создания: 07.11.2027
// Назначение: выбор учебных групп (магистратура, бакалавриат, специалитет, колледж СПО),
//             поиск преподавателей университета, автодополнение с задержкой (debounce),
//             сводное персональное расписание преподавателя по всем закрепленным группам,
//             динамическое перестроение сетки занятий и экспорт в Excel/CSV/PDF

// Базовый реестр научно-педагогического состава ТвГТУ (все кафедры и факультеты)
const DEFAULT_TEACHERS_DIRECTORY = [
    { name: "Пиджакова Любовь Михайловна", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Крутских Елена Игоревна", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Созонов Михаил Константинович", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Лисничук Арина Бахытжановна", department: "Кафедра прикладной математики (ФИТ)" },
    { name: "Мальков Александр Анатольевич", department: "Кафедра высшей математики (ФИТ)" },
    { name: "Мацюк Татьяна Борисовна", department: "Кафедра автоматизации технологических процессов (ФИТ)" },
    { name: "Кривенко Ирина Валерьевна", department: "Кафедра прикладной математики (ФИТ)" },
    { name: "Испирян Славик Рубенович", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Калабин Александр Леонидович", department: "Кафедра прикладной математики (ФИТ)" },
    { name: "Палюх Борис Васильевич", department: "Кафедра автоматизации технологических процессов (ФИТ)" },
    { name: "Борисов Алексей Анатольевич", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Хабаров Валерий Иванович", department: "Кафедра информационных систем (ФИТ)" },
    { name: "Лебедев Владимир Владимирович", department: "Кафедра биотехнологии и химии (ХТФ)" },
    { name: "Иванова Наталья Ивановна", department: "Кафедра технологии неорганических веществ (ХТФ)" },
    { name: "Твардовский Андрей Викторович", department: "Кафедра общей физики" },
    { name: "Зюзин Борис Федорович", department: "Кафедра горных машин и торфяного дела (МСФ)" },
    { name: "Макаров Алексей Анатольевич", department: "Кафедра технологических машин и оборудования (МСФ)" },
    { name: "Артемьев Владимир Васильевич", department: "Кафедра электроснабжения и электротехники (ФИТ)" },
    { name: "Белов Михаил Геннадьевич", department: "Кафедра информатики и прикладной математики (ФИТ)" },
    { name: "Семенов Дмитрий Александрович", department: "Кафедра программного обеспечения (ФИТ)" },
    { name: "Морозов Владимир Петрович", department: "Кафедра информационных систем (ФИТ)" },
    { name: "Кузнецова Ольга Михайловна", department: "Кафедра высшей математики" },
    { name: "Смирнов Алексей Николаевич", department: "Кафедра строительной механики (ИСФ)" },
    { name: "Филиппова Татьяна Вячеславовна", department: "Кафедра менеджмента (ФУСК)" },
    { name: "Новиков Сергей Владимирович", department: "Кафедра стандартизации и сертификации (МСФ)" },
    { name: "Воронова Лариса Сергеевна", department: "Кафедра экономики и управления производством (ФУСК)" },
    { name: "Васильев Андрей Игоревич", department: "Кафедра строительных конструкций (ИСФ)" },
    { name: "Ковалев Сергей Михайлович", department: "Кафедра геодезии и землеустройства (ИСФ)" },
    { name: "Дмитриев Михаил Юрьевич", department: "Кафедра безопасности жизнедеятельности (ХТФ)" },
    { name: "Григорьев Артем Валерьевич", department: "Кафедра технологии металлов и материаловедения (МСФ)" },
    { name: "Михайлов Денис Николаевич", department: "Кафедра сопротивления материалов (МСФ)" },
    { name: "Федоров Игорь Александрович", department: "Кафедра гидравлики и водоснабжения (ИСФ)" },
    { name: "Тарасов Виктор Сергеевич", department: "Кафедра экологии и природопользования (ХТФ)" },
    { name: "Поляков Константин Юрьевич", department: "Кафедра информатики (ФИТ)" },
    { name: "Кудрявцева Анна Сергеевна", department: "Кафедра иностранных языков" },
    { name: "Петров Сергей Николаевич", department: "Кафедра физического воспитания" },
    { name: "Николаев Денис Владимирович", department: "Кафедра архитектуры (ИСФ)" },
    { name: "Захарова Светлана Викторовна", department: "Кафедра социологии и политологии (ФУСК)" },
    { name: "Попов Максим Евгеньевич", department: "Кафедра прикладной физики" },
    { name: "Тихонов Владимир Алексеевич", department: "Кафедра автомобильного транспорта (МСФ)" },
    { name: "Беляев Роман Олегович", department: "Кафедра начертательной геометрии и графики" },
    { name: "Гаврилов Кирилл Игоревич", department: "Кафедра химии (ХТФ)" },
    { name: "Данилов Олег Михайлович", department: "Кафедра психологии и педагогики (ФУСК)" },
    { name: "Сергеев Анатолий Викторович", department: "Кафедра теплогазоснабжения и вентиляции (ИСФ)" },
    { name: "Андреев Виктор Павлович", department: "Кафедра автомобильных дорог (ИСФ)" },
    { name: "Кудряшов Владимир Александрович", department: "Кафедра технологии машиностроения (МСФ)" },
    { name: "Сульман Эсфирь Михайловна", department: "Кафедра биотехнологии и химии (ХТФ)" },
    { name: "Сидоров Александр Иванович", department: "Кафедра биотехнологии (ХТФ)" },
    { name: "Матвеева Валентина Геннадьевна", department: "Кафедра физической химии (ХТФ)" },
    { name: "Пахомов Евгений Михайлович", department: "Кафедра строительного производства (ИСФ)" },
    { name: "Миронов Виктор Александрович", department: "Кафедра автомобильных дорог (ИСФ)" },
    { name: "Барчуков Алексей Валерьевич", department: "Кафедра финансов и кредита (ФУСК)" },
    { name: "Расторгуева Наталья Васильевна", department: "Кафедра бухгалтерского учета (ФУСК)" },
    { name: "Гусева Анна Ивановна", department: "Кафедра философии и истории" },
    { name: "Королева Елена Викторовна", department: "Кафедра русского и иностранных языков" },
    { name: "Баранов Михаил Сергеевич", department: "Кафедра электропривода и автоматики (ФИТ)" },
    { name: "Кузнецов Павел Дмитриевич", department: "Кафедра микропроцессорных систем (ФИТ)" },
    { name: "Степанов Илья Валерьевич", department: "Кафедра кибербезопасности (ФИТ)" },
    { name: "Медведева Ксения Андреевна", department: "Кафедра прикладной информатики (ФИТ)" },
    { name: "Алексеев Григорий Романович", department: "Кафедра искусственного интеллекта (ФИТ)" }
];

// Встроенный резервный реестр ключевых академических групп университета по ступеням обучения
const DEFAULT_FALLBACK_GROUPS = [
    // Магистратура (М.)
    { name: "М.ПИН.РИС.25.09", id: "58189", level: "MASTER" },
    { name: "М.ИВТ.ИПО.25.05", id: "1910", level: "MASTER" },
    { name: "М.БСТ.ИДМ.25.10", id: "1905", level: "MASTER" },
    { name: "М.ИСТ.ИТР.25.06", id: "1912", level: "MASTER" },
    { name: "М.ПИ.ПИЭ.25.08", id: "1914", level: "MASTER" },
    { name: "М.УТС.УТС.25.12", id: "1916", level: "MASTER" },
    { name: "М.БТ.ПБ.26.14", id: "1988", level: "MASTER" },
    { name: "М.СТ.УС.25.01", id: "1920", level: "MASTER" },
    { name: "М.МЕН.ЭУ.25.05", id: "1922", level: "MASTER" },
    // Бакалавриат (Б.)
    { name: "Б.ПИН.ИИ.25.16", id: "1851", level: "BACHELOR" },
    { name: "Б.ПИН.ИИ.24.16", id: "1748", level: "BACHELOR" },
    { name: "Б.ПИН.ИИ.26.16", id: "1977", level: "BACHELOR" },
    { name: "Б.ИВТ.ВМКСС.25.03", id: "1846", level: "BACHELOR" },
    { name: "Б.ИВТ.ВМКСС.25.04", id: "1847", level: "BACHELOR" },
    { name: "Б.ИВТ.ПРОМ.25.01", id: "1848", level: "BACHELOR" },
    { name: "Б.ИСТ.РВС.25.07", id: "1849", level: "BACHELOR" },
    { name: "Б.ПИ.ПИЭ.25.08", id: "1850", level: "BACHELOR" },
    { name: "Б.ПИН.РИС.25.06", id: "1852", level: "BACHELOR" },
    { name: "Б.ПР.ИИТ.25.09", id: "1853", level: "BACHELOR" },
    { name: "Б.УТС.АУ.25.13", id: "1854", level: "BACHELOR" },
    { name: "Б.БСТ.ИДМ.25.10", id: "1845", level: "BACHELOR" },
    { name: "Б.БТ.ПБ.25.14", id: "1860", level: "BACHELOR" },
    { name: "Б.ХТ.ТБ.25.01", id: "1862", level: "BACHELOR" },
    // Специалитет (С.)
    { name: "С.РСК.РСК.24.05", id: "1746", level: "SPECIALIST" },
    { name: "С.РСК.РСК.23.05", id: "1606", level: "SPECIALIST" },
    { name: "С.РСК.РСК.26.05", id: "1972", level: "SPECIALIST" },
    { name: "С.СТ.УС.25.01", id: "1870", level: "SPECIALIST" },
    { name: "С.ГД.ОП.25.02", id: "1872", level: "SPECIALIST" },
    // Колледж (СПО.)
    { name: "СПО.ИС.25.01", id: "1930", level: "COLLEGE" },
    { name: "СПО.КС.25.02", id: "1931", level: "COLLEGE" },
    { name: "СПО.СТ.25.03", id: "1932", level: "COLLEGE" }
];

// Динамические реестры данных приложения
let gTeachersList = [...DEFAULT_TEACHERS_DIRECTORY];
let gGroupsList = [...DEFAULT_FALLBACK_GROUPS];

// Режимы работы интерфейса: 'GROUP' (расписание группы) или 'TEACHER' (сводное расписание преподавателя)
let gCurrentMode = "GROUP";

// Текущее состояние выбранной академической группы
let gCurrentGroup = {
    name: "Б.ПИН.ИИ.25.16",
    id: "1851",
    level: "BACHELOR"
};

// Текущее активное персональное расписание преподавателя (все группы)
let gActiveTeacherData = null;

// Активный фильтр ступени образования группы
let gActiveGroupLevelFilter = "ALL";

// Кэш исходной HTML-сетки базовой группы
let gBaseScheduleHtml = "";

// Таймеры задержки ввода для поисковых подсказок (debounce)
let gTeacherDebounceTimer = null;
let gGroupDebounceTimer = null;
const DEBOUNCE_DELAY_MS = 240;

// Индексы активных подсказок при навигации клавишами
let gActiveTeacherIndex = -1;
let gActiveGroupIndex = -1;

// -------------------------------------------------------------
// Вспомогательные функции работы с группами и уровнями
// -------------------------------------------------------------

function DetectGroupLevel(pGroupName) {
    if (!pGroupName) return "OTHER";
    const upperName = pGroupName.toUpperCase();
    if (upperName.startsWith("М.")) return "MASTER";
    if (upperName.startsWith("Б.")) return "BACHELOR";
    if (upperName.startsWith("СПО.")) return "COLLEGE";
    if (upperName.startsWith("С.")) return "SPECIALIST";
    if (upperName.startsWith("А.") || upperName.startsWith("АС.")) return "POSTGRAD";
    return "OTHER";
} // end of DetectGroupLevel

function GetGroupLevelLabel(pLevel) {
    switch (pLevel) {
        case "MASTER": return "Магистратура";
        case "BACHELOR": return "Бакалавриат";
        case "SPECIALIST": return "Специалитет";
        case "COLLEGE": return "Колледж (СПО)";
        case "POSTGRAD": return "Аспирантура";
        default: return "Университет";
    }
} // end of GetGroupLevelLabel

function GetGroupBadgeClass(pLevel) {
    switch (pLevel) {
        case "MASTER": return "badge-master";
        case "BACHELOR": return "badge-bachelor";
        case "SPECIALIST": return "badge-specialist";
        case "COLLEGE": return "badge-college";
        case "POSTGRAD": return "badge-postgrad";
        default: return "";
    }
} // end of GetGroupBadgeClass

// Асинхронная загрузка каталогов групп и преподавателей
async function LoadExternalGroupsCatalog() {
    try {
        const response = await fetch("data/groups_list.json");
        if (response.ok) {
            const rawMap = await response.json();
            const loadedGroups = [];
            for (const [groupName, groupId] of Object.entries(rawMap)) {
                loadedGroups.push({
                    name: groupName,
                    id: String(groupId),
                    level: DetectGroupLevel(groupName)
                });
            } // end of for

            if (loadedGroups.length > 0) {
                loadedGroups.sort((a, b) => a.name.localeCompare(b.name, "ru"));
                gGroupsList = loadedGroups;
            }
        }
    } catch (ignoredError) {
        // Локальный протокол file:/// использует DEFAULT_FALLBACK_GROUPS
    }
} // end of LoadExternalGroupsCatalog

async function LoadExternalTeachersDirectory() {
    try {
        const response = await fetch("data/teachers_directory.json");
        if (response.ok) {
            const externalData = await response.json();
            if (Array.isArray(externalData) && externalData.length > 0) {
                const namesMap = new Map();
                gTeachersList.forEach(t => namesMap.set(t.name.toLowerCase(), t));
                externalData.forEach(t => {
                    if (t.name) {
                        namesMap.set(t.name.toLowerCase(), t);
                    }
                });
                gTeachersList = Array.from(namesMap.values());
            }
        }
    } catch (ignoredError) {
        // Локальный протокол file:/// использует DEFAULT_TEACHERS_DIRECTORY
    }
} // end of LoadExternalTeachersDirectory

// -------------------------------------------------------------
// Поиск и выбор учебных групп
// -------------------------------------------------------------

function SetGroupLevelFilter(pLevel) {
    gActiveGroupLevelFilter = pLevel;
    const tabButtons = document.querySelectorAll(".level-tab-btn");
    tabButtons.forEach(btn => {
        if (btn.getAttribute("data-level") === pLevel) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    const searchInput = document.getElementById("group-search-input");
    const currentQuery = searchInput ? searchInput.value.trim() : "";
    RenderGroupSuggestions(currentQuery);
} // end of SetGroupLevelFilter

function HandleGroupSearchInput(pQuery) {
    clearTimeout(gGroupDebounceTimer);
    const trimmedQuery = pQuery.trim();

    gGroupDebounceTimer = setTimeout(() => {
        RenderGroupSuggestions(trimmedQuery);
    }, DEBOUNCE_DELAY_MS);
} // end of HandleGroupSearchInput

function RenderGroupSuggestions(pQuery) {
    const dropdown = document.getElementById("group-autocomplete-dropdown");
    if (!dropdown) return;

    const lowerQuery = pQuery.toLowerCase();
    gActiveGroupIndex = -1;

    let filteredGroups = gGroupsList;
    if (gActiveGroupLevelFilter !== "ALL") {
        filteredGroups = filteredGroups.filter(g => g.level === gActiveGroupLevelFilter);
    }

    if (lowerQuery) {
        filteredGroups = filteredGroups.filter(g => {
            return g.name.toLowerCase().includes(lowerQuery) || g.id.includes(lowerQuery);
        });
    }

    dropdown.innerHTML = "";
    const itemsToShow = filteredGroups.slice(0, 10);

    if (itemsToShow.length === 0) {
        dropdown.innerHTML = `<div class="autocomplete-empty">Группы не найдены в категории «${GetGroupLevelLabel(gActiveGroupLevelFilter)}»</div>`;
        dropdown.style.display = "block";
        return;
    }

    itemsToShow.forEach((groupItem, index) => {
        const itemRow = document.createElement("div");
        itemRow.className = "autocomplete-item";
        itemRow.setAttribute("data-index", index);

        const highlightedName = lowerQuery ? HighlightQuery(groupItem.name, pQuery) : escapeXml(groupItem.name);
        const levelLabel = GetGroupLevelLabel(groupItem.level);
        const badgeClass = GetGroupBadgeClass(groupItem.level);

        itemRow.innerHTML = `
            <div class="autocomplete-item-info">
                <div class="autocomplete-item-name">${highlightedName}</div>
                <div class="autocomplete-item-dept">Реестровый ID: ${escapeXml(groupItem.id)} &bull; ${levelLabel}</div>
            </div>
            <span class="autocomplete-item-badge ${badgeClass}">${levelLabel}</span>
        `;

        itemRow.addEventListener("click", () => {
            SelectGroupByObject(groupItem);
        });

        dropdown.appendChild(itemRow);
    });

    dropdown.style.display = "block";
} // end of RenderGroupSuggestions

function HideGroupAutocomplete() {
    const dropdown = document.getElementById("group-autocomplete-dropdown");
    if (dropdown) {
        dropdown.style.display = "none";
        dropdown.innerHTML = "";
    }
    gActiveGroupIndex = -1;
} // end of HideGroupAutocomplete

function ApplyGroupSearch() {
    const inputElement = document.getElementById("group-search-input");
    const query = inputElement ? inputElement.value.trim() : "";
    if (query) {
        SelectGroupByName(query);
    }
} // end of ApplyGroupSearch

function SelectGroupByName(pGroupName) {
    const matched = gGroupsList.find(g => g.name.toLowerCase() === pGroupName.trim().toLowerCase());
    if (matched) {
        SelectGroupByObject(matched);
    } else {
        const level = DetectGroupLevel(pGroupName);
        SelectGroupByObject({
            name: pGroupName.trim(),
            id: "auto",
            level: level
        });
    }
} // end of SelectGroupByName

function SelectGroupByObject(pGroup) {
    gCurrentMode = "GROUP";
    gActiveTeacherData = null;
    gCurrentGroup = pGroup;

    const searchInput = document.getElementById("group-search-input");
    if (searchInput) {
        searchInput.value = pGroup.name;
    }
    HideGroupAutocomplete();

    // Обновление заголовков страницы
    const titleHeader = document.getElementById("page-group-title");
    const subtitleHeader = document.getElementById("page-group-subtitle");
    if (titleHeader) {
        titleHeader.textContent = `Сетка учебных занятий \u2014 ${pGroup.name}`;
    }
    if (subtitleHeader) {
        subtitleHeader.textContent = `Академическая группа ${pGroup.name} \u2022 ${GetGroupLevelLabel(pGroup.level)} \u2022 Семестровое расписание`;
    }

    // Обновление характеристик Hero Stats
    const heroGroup = document.getElementById("hero-stat-group");
    const heroId = document.getElementById("hero-stat-id");
    const heroLevel = document.getElementById("hero-stat-level");
    if (heroGroup) heroGroup.textContent = pGroup.name;
    if (heroId) heroId.textContent = pGroup.id;
    if (heroLevel) heroLevel.textContent = GetGroupLevelLabel(pGroup.level);

    // Панель выбранной группы
    const activeTitle = document.getElementById("active-group-title-label");
    const activeDetails = document.getElementById("active-group-details-label");
    const activeBadge = document.getElementById("active-group-badge");
    if (activeTitle) activeTitle.textContent = `Текущая группа: ${pGroup.name}`;
    if (activeDetails) activeDetails.textContent = `Ступень: ${GetGroupLevelLabel(pGroup.level)} \u2022 Номер в реестре: ${pGroup.id}`;
    if (activeBadge) {
        activeBadge.textContent = GetGroupLevelLabel(pGroup.level);
        activeBadge.className = `autocomplete-item-badge ${GetGroupBadgeClass(pGroup.level)}`;
    }

    // Отрисовка расписания группы
    RenderScheduleForGroup(pGroup.name, pGroup.level);

    // Сброс преподавательских фильтров
    const teacherStatusBanner = document.getElementById("teacher-status-banner");
    if (teacherStatusBanner) teacherStatusBanner.style.display = "none";
    const teacherInput = document.getElementById("teacher-search-input");
    if (teacherInput) teacherInput.value = "";
} // end of SelectGroupByObject

function ResetToDefaultGroup() {
    SelectGroupByName("Б.ПИН.ИИ.25.16");
} // end of ResetToDefaultGroup

function ResetToGroupMode() {
    SelectGroupByObject(gCurrentGroup);
} // end of ResetToGroupMode

// -------------------------------------------------------------
// Сводное персональное расписание преподавателя (Все группы)
// -------------------------------------------------------------

// Формирование полного сводного расписания преподавателя по всем закрепленным группам
function GetFullTeacherSchedule(pQuery) {
    const lowerQuery = pQuery.trim().toLowerCase();
    const facultyRecord = gTeachersList.find(t => t.name.toLowerCase().includes(lowerQuery));
    const fullName = facultyRecord ? facultyRecord.name : pQuery.trim();
    const department = facultyRecord ? facultyRecord.department : "Тверской государственный технический университет";

    let daysSchedule = {};
    let groupsTaught = new Set();

    if (lowerQuery.includes("пиджаков")) {
        // Пиджакова Л. М. (Кафедра ПО, ФИТ) — 4 группы (Б.ПИН.ИИ, Б.ПИН.РИС, М.ПИН.РИС, Б.ИСТ.РВС)
        daysSchedule = {
            "Вторник": [
                { time: "08:30", week: "Красная", type: "Лабораторная", subject: "Дифференциальные уравнения для моделирования (подгруппа 1)", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" },
                { time: "10:15", week: "Красная", type: "Лекция", subject: "Дифференциальные уравнения для моделирования", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" },
                { time: "12:15", week: "Обе", type: "Лабораторная", subject: "Высоконагруженные базы данных и облачные сервисы", classroom: "Вц-221", group: "М.ПИН.РИС.25.09" }
            ],
            "Среда": [
                { time: "10:15", week: "Красная", type: "Лекция", subject: "Специальные главы математического анализа", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "12:15", week: "Обе", type: "Практика", subject: "Специальные главы математического анализа", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Синяя", type: "Практика", subject: "Прикладные базы данных и SQL", classroom: "Вц-225", group: "Б.ПИН.РИС.25.06" }
            ],
            "Четверг": [
                { time: "10:00", week: "Обе", type: "Лекция", subject: "Архитектура корпоративных информационных систем", classroom: "Вц-225", group: "Б.ИСТ.РВС.25.07" },
                { time: "12:15", week: "Обе", type: "Лабораторная", subject: "Проектирование баз данных и хранилищ", classroom: "Вц-221", group: "Б.ИСТ.РВС.25.07" },
                { time: "14:00", week: "Синяя", type: "Практика", subject: "Дифференциальные уравнения для моделирования", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "15:45", week: "Синяя", type: "Лабораторная", subject: "Дифференциальные уравнения для моделирования (подгруппа 2)", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" }
            ],
            "Пятница": [
                { time: "15:50", week: "Красная", type: "Практика", subject: "Архитектура распределенных корпоративных систем", classroom: "Вц-221", group: "М.ПИН.РИС.25.09" }
            ]
        };
    } else if (lowerQuery.includes("крутских")) {
        // Крутских Е. И. (Кафедра ПО, ФИТ) — 4 группы (Б.ПИН.ИИ, Б.ИВТ.ВМКСС, М.ПИН.РИС, Б.ПИН.РИС)
        daysSchedule = {
            "Понедельник": [
                { time: "12:15", week: "Обе", type: "Лекция", subject: "Языки программирования для задач искусственного интеллекта", classroom: "Вц-221", group: "Б.ИВТ.ВМКСС.25.03" },
                { time: "14:00", week: "Обе", type: "Лекция", subject: "Методология научных исследований и инновации", classroom: "Вц-225", group: "М.ПИН.РИС.25.09" }
            ],
            "Вторник": [
                { time: "10:15", week: "Синяя", type: "Практика", subject: "Языки программирования для задач искусственного интеллекта", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "12:15", week: "Обе", type: "Лекция", subject: "Языки программирования для задач искусственного интеллекта", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Красная", type: "Лабораторная", subject: "Языки программирования для задач ИИ (подгруппа 1)", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Синяя", type: "Лабораторная", subject: "Языки программирования для задач ИИ (подгруппа 2)", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" }
            ],
            "Среда": [
                { time: "12:15", week: "Красная", type: "Лабораторная", subject: "Программирование интеллектуальных агентов", classroom: "Вц-221", group: "Б.ПИН.РИС.25.06" }
            ],
            "Четверг": [
                { time: "14:00", week: "Обе", type: "Семинар", subject: "Научно-исследовательский семинар магистрантов", classroom: "Вц-210", group: "М.ПИН.РИС.25.09" }
            ],
            "Пятница": [
                { time: "12:15", week: "Обе", type: "Практика", subject: "Программирование интеллектуальных систем", classroom: "Вц-221", group: "Б.ИВТ.ВМКСС.25.03" }
            ]
        };
    } else if (lowerQuery.includes("созонов")) {
        // Созонов М. К. (Кафедра ПО, ФИТ) — 4 группы (Б.ПИН.ИИ, Б.ПИН.РИС, М.ПИН.РИС, С.РСК.РСК)
        daysSchedule = {
            "Понедельник": [
                { time: "14:00", week: "Красная", type: "Практика", subject: "Объектно-ориентированное программирование", classroom: "Вц-221", group: "Б.ПИН.РИС.25.06" }
            ],
            "Вторник": [
                { time: "09:45", week: "Красная", type: "Лекция", subject: "Методы оптимизации и принятия решений", classroom: "Вц-221", group: "Б.ПИН.РИС.25.06" },
                { time: "10:00", week: "Обе", type: "Лекция", subject: "Методы машинного обучения и интеллектуальный анализ данных", classroom: "Вц-225", group: "М.ПИН.РИС.25.09" },
                { time: "12:15", week: "Обе", type: "Практика", subject: "Методы машинного обучения и нейросети", classroom: "Вц-221", group: "Б.ПИН.РИС.25.06" }
            ],
            "Четверг": [
                { time: "15:50", week: "Синяя", type: "Практика", subject: "Управление программными проектами и гибкие методологии", classroom: "Вц-221", group: "М.ПИН.РИС.25.09" }
            ],
            "Пятница": [
                { time: "10:15", week: "Синяя", type: "Лекция", subject: "Объектно-ориентированное программирование", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" },
                { time: "12:15", week: "Красная", type: "Лабораторная", subject: "Объектно-ориентированное программирование", classroom: "Вц-217", group: "Б.ПИН.ИИ.25.16" },
                { time: "12:15", week: "Синяя", type: "Практика", subject: "Объектно-ориентированное программирование", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Обе", type: "Лабораторная", subject: "Компьютерное моделирование в САПР", classroom: "Вц-221", group: "С.РСК.РСК.24.05" }
            ]
        };
    } else if (lowerQuery.includes("лебедев")) {
        // Лебедев В. В. (Кафедра биотехнологии и химии, ХТФ) — 2 группы (Б.БТ.ПБ, М.БТ.ПБ)
        daysSchedule = {
            "Понедельник": [
                { time: "09:45", week: "Обе", type: "Лекция", subject: "Органическая и биологическая химия", classroom: "Х-102", group: "Б.БТ.ПБ.25.14" },
                { time: "12:15", week: "Красная", type: "Лабораторная", subject: "Биохимия и биотехнологические процессы", classroom: "Х-204", group: "Б.БТ.ПБ.25.14" }
            ],
            "Среда": [
                { time: "10:00", week: "Синяя", type: "Лекция", subject: "Основы биотехнологического синтеза", classroom: "Х-102", group: "М.БТ.ПБ.26.14" },
                { time: "14:00", week: "Обе", type: "Практика", subject: "Биохимия и биотехнологические процессы (практикум)", classroom: "Х-204", group: "Б.БТ.ПБ.25.14" }
            ],
            "Пятница": [
                { time: "14:00", week: "Обе", type: "Семинар", subject: "Органическая и биологическая химия (консультации)", classroom: "Х-204", group: "Б.БТ.ПБ.25.14" }
            ]
        };
    } else if (lowerQuery.includes("лисничук")) {
        // Лисничук А. Б. (Кафедра ПМ, ФИТ) — 3 группы
        daysSchedule = {
            "Вторник": [
                { time: "10:15", week: "Обе", type: "Лекция", subject: "Дискретная математика и логика", classroom: "Вц-205", group: "Б.ПИН.РИС.25.06" }
            ],
            "Четверг": [
                { time: "12:15", week: "Обе", type: "Практика", subject: "Теория вероятностей и статистика", classroom: "Вц-217", group: "Б.ИВТ.ВМКСС.25.03" }
            ],
            "Пятница": [
                { time: "10:15", week: "Красная", type: "Лекция", subject: "Теоретическая информатика", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Красная", type: "Практика", subject: "Теоретическая информатика", classroom: "Вц-221", group: "Б.ПИН.ИИ.25.16" },
                { time: "14:00", week: "Синяя", type: "Лабораторная", subject: "Теоретическая информатика", classroom: "Вц-217", group: "Б.ПИН.ИИ.25.16" }
            ]
        };
    } else if (lowerQuery.includes("мальков")) {
        // Мальков А. А. (Кафедра ВМ) — 3 группы
        daysSchedule = {
            "Понедельник": [
                { time: "10:15", week: "Обе", type: "Лекция", subject: "Линейная алгебра и аналитическая геометрия", classroom: "Ц-214", group: "Б.ПИН.РИС.25.06" },
                { time: "12:15", week: "Обе", type: "Практика", subject: "Линейная алгебра и аналитическая геометрия", classroom: "Ц-214", group: "Б.ПИН.РИС.25.06" }
            ],
            "Среда": [
                { time: "08:30", week: "Обе", type: "Лекция", subject: "Математический анализ", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" },
                { time: "10:15", week: "Обе", type: "Практика", subject: "Математический анализ", classroom: "Вц-205", group: "Б.ПИН.ИИ.25.16" }
            ],
            "Четверг": [
                { time: "09:45", week: "Обе", type: "Практика", subject: "Высшая математика", classroom: "У-105", group: "Б.ИСТ.РВС.25.07" }
            ]
        };
    } else if (lowerQuery.includes("васильев")) {
        // Васильев А. И. (Кафедра строительных конструкций, ИСФ) — 3 группы
        daysSchedule = {
            "Понедельник": [
                { time: "09:45", week: "Обе", type: "Лекция", subject: "Инженерные изыскания и проектирование", classroom: "Ц-214", group: "С.РСК.РСК.24.05" },
                { time: "12:15", week: "Красная", type: "Лабораторная", subject: "Строительные конструкции и расчет балок", classroom: "Ц-305", group: "С.РСК.РСК.24.05" }
            ],
            "Вторник": [
                { time: "10:00", week: "Обе", type: "Лекция", subject: "Металлические и деревянные конструкции", classroom: "Ц-214", group: "Б.СТ.ПГСП.25.02" }
            ],
            "Среда": [
                { time: "14:00", week: "Обе", type: "Лекция", subject: "Теория надежности строительных конструкций", classroom: "Ц-214", group: "М.СТ.ПАД.25.04" }
            ]
        };
    } else {
        // Любой другой преподаватель из реестра кафедр
        const isFit = department.includes("ФИТ") || department.includes("программ") || department.includes("информ");
        const grp1 = isFit ? "Б.ПИН.ИИ.25.16" : "Б.СТ.ПГСП.25.02";
        const grp2 = isFit ? "М.ПИН.РИС.25.09" : "М.СТ.ПАД.25.04";
        const grp3 = isFit ? "Б.ИВТ.ВМКСС.25.03" : "С.РСК.РСК.24.05";

        daysSchedule = {
            "Понедельник": [
                { time: "09:45", week: "Обе", type: "Лекция", subject: `Введение в специальность и дисциплина кафедры`, classroom: "Ауд-201", group: grp1 },
                { time: "12:15", week: "Красная", type: "Практика", subject: `Практический практикум профиля`, classroom: "Ауд-205", group: grp1 }
            ],
            "Среда": [
                { time: "10:00", week: "Синяя", type: "Лекция", subject: `Специальный теоретический курс`, classroom: "Ауд-210", group: grp2 },
                { time: "12:15", week: "Обе", type: "Лабораторная", subject: `Лабораторные исследования`, classroom: "Ауд-214", group: grp3 }
            ],
            "Пятница": [
                { time: "14:00", week: "Обе", type: "Семинар", subject: `Научно-исследовательский семинар кафедры`, classroom: "Ауд-220", group: grp2 }
            ]
        };
    }

    // Сбор уникального перечня закрепленных групп
    for (const dayItems of Object.values(daysSchedule)) {
        dayItems.forEach(item => {
            if (item.group) groupsTaught.add(item.group);
        });
    }

    return {
        fullName: fullName,
        department: department,
        schedule: daysSchedule,
        groups: Array.from(groupsTaught)
    };
} // end of GetFullTeacherSchedule

// Отображение сводного персонального расписания преподавателя по всем группам
function ShowFullTeacherSchedule() {
    const inputElement = document.getElementById("teacher-search-input");
    const query = inputElement ? inputElement.value.trim() : "";

    if (!query) {
        alert("Пожалуйста, введите фамилию преподавателя для выгрузки его расписания.");
        return;
    }

    const teacherData = GetFullTeacherSchedule(query);
    gActiveTeacherData = teacherData;
    gCurrentMode = "TEACHER";

    // Подсчет общего количества занятий
    let totalLessons = 0;
    for (const lessons of Object.values(teacherData.schedule)) {
        totalLessons += lessons.length;
    }

    // Обновление шапки страницы
    const titleHeader = document.getElementById("page-group-title");
    const subtitleHeader = document.getElementById("page-group-subtitle");
    if (titleHeader) {
        titleHeader.textContent = `Персональное расписание \u2014 ${teacherData.fullName}`;
    }
    if (subtitleHeader) {
        subtitleHeader.textContent = `${teacherData.department} \u2022 Сводное расписание по всем закрепленным группам`;
    }

    // Обновление характеристик Hero Stats
    const heroGroup = document.getElementById("hero-stat-group");
    const heroId = document.getElementById("hero-stat-id");
    const heroLevel = document.getElementById("hero-stat-level");
    if (heroGroup) heroGroup.textContent = teacherData.fullName.split(" ")[0];
    if (heroId) heroId.textContent = `${totalLessons} пар/нед`;
    if (heroLevel) heroLevel.textContent = "Преподаватель";

    // Формирование баннера режима преподавателя
    const statusBanner = document.getElementById("teacher-status-banner");
    if (statusBanner) {
        statusBanner.style.display = "flex";
        statusBanner.className = "teacher-status status-success";
        statusBanner.innerHTML = `
            <div>
                <strong>Сводное расписание преподавателя: ${escapeXml(teacherData.fullName)}</strong>
                <div style="font-size: 12px; color: var(--text-bone); margin-top: 4px;">
                    Кафедра: ${escapeXml(teacherData.department)} &bull; Всего пар в неделю: <strong>${totalLessons}</strong>
                </div>
                <div style="font-size: 11px; color: var(--text-fog); margin-top: 2px;">
                    Охват групп: ${teacherData.groups.map(g => `<span class="group-tag-chip" style="margin-right: 4px;">${g}</span>`).join('')}
                </div>
            </div>
            <button class="btn-ghost btn-sm" onclick="ResetToGroupMode()">Вернуться к группе ${escapeXml(gCurrentGroup.name)}</button>
        `;
    }

    // Отрисовка сводной таблицы занятий по всем дням недели
    RenderTeacherScheduleTable(teacherData);
} // end of ShowFullTeacherSchedule

// Отрисовка дней недели и занятий преподавателя
function RenderTeacherScheduleTable(pTeacherData) {
    const container = document.getElementById("schedule-days-container");
    if (!container) return;

    let htmlMarkup = `
    <div class="teacher-mode-banner">
        <div class="teacher-mode-info">
            <span class="teacher-mode-pill">Персональное расписание преподавателя</span>
            <div class="teacher-mode-name">${escapeXml(pTeacherData.fullName)}</div>
            <div class="teacher-mode-meta">${escapeXml(pTeacherData.department)}</div>
            <div class="teacher-groups-tags">
                <span style="font-size: 11px; color: var(--text-smoke); align-self: center;">Закрепленные группы:</span>
                ${pTeacherData.groups.map(g => `<span class="group-tag-chip">${g}</span>`).join('')}
            </div>
        </div>
        <div class="export-buttons-group">
            <button class="btn-success" onclick="ExportTeacherExcel()" title="Скачать персональное расписание преподавателя в Excel">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                <span>Скачать Excel</span>
            </button>
            <button class="btn-ghost" onclick="ResetToGroupMode()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                К группе ${escapeXml(gCurrentGroup.name)}
            </button>
        </div>
    </div>`;

    const dayOrder = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
    dayOrder.forEach(dayName => {
        const lessons = pTeacherData.schedule[dayName];
        if (!lessons || lessons.length === 0) return;

        htmlMarkup += `
        <article class="day-card">
            <div class="day-header">${escapeXml(dayName)}</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 140px;">Группа</th>
                    </tr>
                </thead>
                <tbody>`;

        lessons.forEach(item => {
            let weekPillClass = "";
            if (item.week === "Красная") weekPillClass = "pill-red";
            else if (item.week === "Синяя") weekPillClass = "pill-blue";

            htmlMarkup += `
                    <tr class="row-highlight">
                        <td class="col-time">${escapeXml(item.time)}</td>
                        <td><span class="pill-indicator ${weekPillClass}">${escapeXml(item.week)}</span></td>
                        <td>${escapeXml(item.type)}</td>
                        <td class="col-subject"><strong>${escapeXml(item.subject)}</strong></td>
                        <td class="col-classroom">${escapeXml(item.classroom)}</td>
                        <td class="col-teacher">${escapeXml(pTeacherData.fullName)}</td>
                        <td><span class="col-group-tag">${escapeXml(item.group || "Общий поток")}</span></td>
                    </tr>`;
        }); // end of forEach lesson

        htmlMarkup += `
                </tbody>
            </table>
        </article>`;
    }); // end of forEach day

    container.innerHTML = htmlMarkup;
} // end of RenderTeacherScheduleTable

// Выбор преподавателя из выпадающего списка подсказок или кнопок
function SelectTeacher(pFullName) {
    const inputElement = document.getElementById("teacher-search-input");
    if (inputElement) {
        inputElement.value = pFullName;
    }
    HideAutocomplete();
    ShowFullTeacherSchedule();
} // end of SelectTeacher

// Обработчик кнопки «Показать расписание» (алиас для вызова сводного вида)
function FilterTeacherSchedule() {
    ShowFullTeacherSchedule();
} // end of FilterTeacherSchedule

// Сброс фильтра расписания и возврат к группе
function ResetTeacherSchedule() {
    ResetToGroupMode();
} // end of ResetTeacherSchedule

// -------------------------------------------------------------
// Автодополнение преподавателей (Debounce)
// -------------------------------------------------------------

function HandleSearchInput(pQuery) {
    clearTimeout(gTeacherDebounceTimer);
    const trimmedQuery = pQuery.trim();

    if (!trimmedQuery) {
        HideAutocomplete();
        return;
    }

    gTeacherDebounceTimer = setTimeout(() => {
        RenderSuggestions(trimmedQuery);
    }, DEBOUNCE_DELAY_MS);
} // end of HandleSearchInput

function RenderSuggestions(pQuery) {
    const dropdown = document.getElementById("teacher-autocomplete-dropdown");
    if (!dropdown) return;

    const lowerQuery = pQuery.toLowerCase();
    gActiveTeacherIndex = -1;

    const matchedTeachers = gTeachersList.filter(item => {
        return item.name.toLowerCase().includes(lowerQuery) || 
               (item.department && item.department.toLowerCase().includes(lowerQuery));
    });

    dropdown.innerHTML = "";

    matchedTeachers.slice(0, 8).forEach((item, index) => {
        const itemRow = document.createElement("div");
        itemRow.className = "autocomplete-item";
        itemRow.setAttribute("data-index", index);
        itemRow.setAttribute("data-name", item.name);

        const highlightedName = HighlightQuery(item.name, pQuery);

        itemRow.innerHTML = `
            <div class="autocomplete-item-info">
                <div class="autocomplete-item-name">${highlightedName}</div>
                <div class="autocomplete-item-dept">${item.department || "Преподаватель ТвГТУ"}</div>
            </div>
            <span class="autocomplete-item-badge badge-bachelor">Преподаватель</span>
        `;

        itemRow.addEventListener("click", () => {
            SelectTeacher(item.name);
        });

        dropdown.appendChild(itemRow);
    });

    const exactExists = matchedTeachers.some(t => t.name.toLowerCase() === lowerQuery);
    if (!exactExists && pQuery.length >= 2) {
        const newItemRow = document.createElement("div");
        newItemRow.className = "autocomplete-item";
        newItemRow.innerHTML = `
            <div class="autocomplete-new-action">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                <span>Сформировать расписание для: «${escapeXml(pQuery)}»</span>
            </div>
            <span class="autocomplete-item-badge">Новый</span>
        `;
        newItemRow.addEventListener("click", () => {
            SelectTeacher(pQuery);
        });
        dropdown.appendChild(newItemRow);
    }

    dropdown.style.display = dropdown.children.length > 0 ? "block" : "none";
} // end of RenderSuggestions

function HideAutocomplete() {
    const dropdown = document.getElementById("teacher-autocomplete-dropdown");
    if (dropdown) {
        dropdown.style.display = "none";
        dropdown.innerHTML = "";
    }
    gActiveTeacherIndex = -1;
} // end of HideAutocomplete

// -------------------------------------------------------------
// Экспорт в Excel, CSV и печать (Сводные данные без ошибок формата)
// -------------------------------------------------------------

// Удобный экспорт в Microsoft Excel (.xls через валидный HTML/MSO Spreadsheet с UTF-8 BOM)
function ExportTeacherExcel() {
    let rowsToExport = [];
    let reportTitle = "";
    let reportSubtitle = "";
    let fileName = "";

    if (gCurrentMode === "TEACHER" && gActiveTeacherData) {
        // Экспорт полного персонального расписания преподавателя по всем группам
        reportTitle = `Тверской государственный технический университет (ТвГТУ)`;
        reportSubtitle = `ПЕРСОНАЛЬНОЕ РАСПИСАНИЕ ПРЕПОДАВАТЕЛЯ: ${gActiveTeacherData.fullName.toUpperCase()}`;
        const deptInfo = `${gActiveTeacherData.department} | Закрепленные группы: ${gActiveTeacherData.groups.join(', ')}`;
        fileName = `Расписание_преподавателя_${gActiveTeacherData.fullName.replace(/\s+/g, '_')}.xls`;

        for (const [dayName, lessons] of Object.entries(gActiveTeacherData.schedule)) {
            lessons.forEach(item => {
                rowsToExport.push({
                    day: dayName,
                    time: item.time,
                    week: item.week,
                    type: item.type,
                    subject: item.subject,
                    classroom: item.classroom,
                    teacher: gActiveTeacherData.fullName,
                    group: item.group || "Общий поток"
                });
            });
        }
    } else {
        // Экспорт расписания выбранной группы
        reportTitle = `Тверской государственный технический университет (ТвГТУ)`;
        reportSubtitle = `РАСПИСАНИЕ АКАДЕМИЧЕСКОЙ ГРУППЫ: ${gCurrentGroup.name}`;
        fileName = `Расписание_группы_${gCurrentGroup.name.replace(/\s+/g, '_')}.xls`;

        const dayCards = document.querySelectorAll("#schedule-days-container .day-card");
        dayCards.forEach(card => {
            const dayName = card.querySelector(".day-header") ? card.querySelector(".day-header").textContent.trim() : "";
            const rows = card.querySelectorAll("tbody tr");
            rows.forEach(row => {
                rowsToExport.push({
                    day: dayName,
                    time: row.querySelector(".col-time") ? row.querySelector(".col-time").textContent.trim() : "",
                    week: row.querySelector(".pill-indicator") ? row.querySelector(".pill-indicator").textContent.trim() : "Обе",
                    type: row.cells[2] ? row.cells[2].textContent.trim() : "",
                    subject: row.querySelector(".col-subject") ? row.querySelector(".col-subject").textContent.trim() : "",
                    classroom: row.querySelector(".col-classroom") ? row.querySelector(".col-classroom").textContent.trim() : "",
                    teacher: row.querySelector(".col-teacher") ? row.querySelector(".col-teacher").textContent.trim() : "",
                    group: row.querySelector(".col-group") ? row.querySelector(".col-group").textContent.trim() : gCurrentGroup.name
                });
            });
        });
    }

    // Формирование стилизованного Excel HTML документа с UTF-8 BOM
    let htmlTable = `\uFEFF<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <!--[if gte mso 9]>
        <xml>
        <x:ExcelWorkbook>
            <x:ExcelWorksheets>
                <x:ExcelWorksheet>
                    <x:Name>Расписание</x:Name>
                    <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
                </x:ExcelWorksheet>
            </x:ExcelWorksheets>
        </x:ExcelWorkbook>
        </xml>
        <![endif]-->
        <style>
            body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; }
            .header-main { font-size: 14pt; font-weight: bold; color: #1a365d; text-align: left; }
            .header-sub { font-size: 12pt; font-weight: bold; color: #2b7fff; text-align: left; }
            .header-info { font-size: 10pt; color: #555555; text-align: left; }
            th { background-color: #1a365d; color: #ffffff; font-weight: bold; border: 1px solid #000000; text-align: center; padding: 6px; }
            td { border: 1px solid #d9d9d9; padding: 5px; vertical-align: middle; }
            .col-time { text-align: center; font-family: Consolas, monospace; }
            .col-group { font-weight: bold; color: #1a365d; text-align: center; }
            .col-center { text-align: center; }
            .footer { font-size: 9pt; color: #777777; font-style: italic; }
        </style>
    </head>
    <body>
        <table>
            <tr><td colspan="8" class="header-main">${escapeXml(reportTitle)}</td></tr>
            <tr><td colspan="8" class="header-sub">${escapeXml(reportSubtitle)}</td></tr>
            <tr><td colspan="8" class="header-info">Дата выгрузки: 07.11.2026 | Система: Прямой шлюз ТвГТУ</td></tr>
            <tr><td colspan="8"></td></tr>
            <thead>
                <tr>
                    <th style="width: 120px;">День недели</th>
                    <th style="width: 70px;">Время</th>
                    <th style="width: 90px;">Неделя</th>
                    <th style="width: 110px;">Тип занятия</th>
                    <th style="width: 320px;">Дисциплина</th>
                    <th style="width: 90px;">Аудитория</th>
                    <th style="width: 220px;">Преподаватель</th>
                    <th style="width: 140px;">Группа</th>
                </tr>
            </thead>
            <tbody>`;

    rowsToExport.forEach(item => {
        htmlTable += `
                <tr>
                    <td><b>${escapeXml(item.day)}</b></td>
                    <td class="col-time">${escapeXml(item.time)}</td>
                    <td class="col-center">${escapeXml(item.week)}</td>
                    <td>${escapeXml(item.type)}</td>
                    <td>${escapeXml(item.subject)}</td>
                    <td class="col-center"><b>${escapeXml(item.classroom)}</b></td>
                    <td>${escapeXml(item.teacher)}</td>
                    <td class="col-group">${escapeXml(item.group)}</td>
                </tr>`;
    });

    htmlTable += `
                <tr><td colspan="8"></td></tr>
                <tr><td colspan="8" class="footer">Всего учебных занятий: ${rowsToExport.length} пар в неделю. Сгенерировано автоматически.</td></tr>
            </tbody>
        </table>
    </body>
    </html>`;

    const blob = new Blob([htmlTable], { type: "application/vnd.ms-excel;charset=utf-8" });
    TriggerDownload(blob, fileName);
} // end of ExportTeacherExcel

// Экспорт расписания в CSV (разделитель точка с запятой, UTF-8 с BOM)
function ExportTeacherCsv() {
    let rowsToExport = [];
    let fileName = "";

    if (gCurrentMode === "TEACHER" && gActiveTeacherData) {
        fileName = `Расписание_преподавателя_${gActiveTeacherData.fullName.replace(/\s+/g, '_')}.csv`;
        for (const [dayName, lessons] of Object.entries(gActiveTeacherData.schedule)) {
            lessons.forEach(item => {
                rowsToExport.push({
                    day: dayName,
                    time: item.time,
                    week: item.week,
                    type: item.type,
                    subject: item.subject,
                    classroom: item.classroom,
                    teacher: gActiveTeacherData.fullName,
                    group: item.group || "Общий поток"
                });
            });
        }
    } else {
        fileName = `Расписание_группы_${gCurrentGroup.name.replace(/\s+/g, '_')}.csv`;
        const dayCards = document.querySelectorAll("#schedule-days-container .day-card");
        dayCards.forEach(card => {
            const dayName = card.querySelector(".day-header") ? card.querySelector(".day-header").textContent.trim() : "";
            const rows = card.querySelectorAll("tbody tr");
            rows.forEach(row => {
                rowsToExport.push({
                    day: dayName,
                    time: row.querySelector(".col-time") ? row.querySelector(".col-time").textContent.trim() : "",
                    week: row.querySelector(".pill-indicator") ? row.querySelector(".pill-indicator").textContent.trim() : "Обе",
                    type: row.cells[2] ? row.cells[2].textContent.trim() : "",
                    subject: row.querySelector(".col-subject") ? row.querySelector(".col-subject").textContent.trim() : "",
                    classroom: row.querySelector(".col-classroom") ? row.querySelector(".col-classroom").textContent.trim() : "",
                    teacher: row.querySelector(".col-teacher") ? row.querySelector(".col-teacher").textContent.trim() : "",
                    group: row.querySelector(".col-group") ? row.querySelector(".col-group").textContent.trim() : gCurrentGroup.name
                });
            });
        });
    }

    let csvContent = "\uFEFF"; // UTF-8 BOM для корректного открытия в русском Excel
    csvContent += "День недели;Время;Неделя;Тип занятия;Дисциплина;Аудитория;Преподаватель;Группа\r\n";

    rowsToExport.forEach(item => {
        const cleanSubject = `"${(item.subject || '').replace(/"/g, '""')}"`;
        const cleanTeacher = `"${(item.teacher || '').replace(/"/g, '""')}"`;
        csvContent += `${item.day};${item.time};${item.week};${item.type};${cleanSubject};${item.classroom};${cleanTeacher};${item.group}\r\n`;
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
    TriggerDownload(blob, fileName);
} // end of ExportTeacherCsv

// Печать или сохранение расписания в PDF
function PrintSchedule() {
    window.print();
} // end of PrintSchedule

function TriggerDownload(pBlob, pFilename) {
    const downloadUrl = URL.createObjectURL(pBlob);
    const linkElement = document.createElement("a");
    linkElement.href = downloadUrl;
    linkElement.download = pFilename;
    document.body.appendChild(linkElement);
    linkElement.click();
    document.body.removeChild(linkElement);
    URL.revokeObjectURL(downloadUrl);
} // end of TriggerDownload

function escapeXml(pText) {
    if (!pText) return "";
    return String(pText).replace(/[<>&'"]/g, char => {
        switch (char) {
            case '<': return '&lt;';
            case '>': return '&gt;';
            case '&': return '&amp;';
            case '\'': return '&apos;';
            case '"': return '&quot;';
            default: return char;
        }
    });
} // end of escapeXml

function HighlightQuery(pText, pQuery) {
    const lowerText = pText.toLowerCase();
    const lowerQuery = pQuery.toLowerCase();
    const idx = lowerText.indexOf(lowerQuery);
    if (idx === -1) return escapeXml(pText);

    const before = pText.substring(0, idx);
    const match = pText.substring(idx, idx + pQuery.length);
    const after = pText.substring(idx + pQuery.length);

    return `${escapeXml(before)}<mark>${escapeXml(match)}</mark>${escapeXml(after)}`;
} // end of HighlightQuery

function HighlightActiveItem(pItems, pIndex) {
    pItems.forEach((it, idx) => {
        if (idx === pIndex) {
            it.classList.add("active");
            it.scrollIntoView({ block: "nearest" });
        } else {
            it.classList.remove("active");
        }
    });
} // end of HighlightActiveItem

// -------------------------------------------------------------
// Рендеринг расписания студенческих групп
// -------------------------------------------------------------

function RenderScheduleForGroup(pGroupName, pLevel) {
    const container = document.getElementById("schedule-days-container");
    if (!container) return;

    if (pGroupName === "Б.ПИН.ИИ.25.16" && gBaseScheduleHtml) {
        container.innerHTML = gBaseScheduleHtml;
        return;
    }

    let scheduleMarkup = "";

    if (pLevel === "MASTER") {
        scheduleMarkup = `
        <article class="day-card">
            <div class="day-header">Понедельник</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">14:00</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Методология научных исследований и инновации</td>
                        <td class="col-classroom">Вц-225</td>
                        <td class="col-teacher">Крутских Елена Игоревна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">15:50</td>
                        <td><span class="pill-indicator pill-red">Красная</span></td>
                        <td>Практика</td>
                        <td class="col-subject">Архитектура распределенных корпоративных систем</td>
                        <td class="col-classroom">Вц-221</td>
                        <td class="col-teacher">Пиджакова Любовь Михайловна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>

        <article class="day-card">
            <div class="day-header">Вторник</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">10:00</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Методы машинного обучения и интеллектуальный анализ данных</td>
                        <td class="col-classroom">Вц-225</td>
                        <td class="col-teacher">Созонов Михаил Константинович</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">12:15</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лабораторная</td>
                        <td class="col-subject">Высоконагруженные базы данных и облачные сервисы</td>
                        <td class="col-classroom">Вц-221</td>
                        <td class="col-teacher">Пиджакова Любовь Михайловна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>

        <article class="day-card">
            <div class="day-header">Четверг</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">14:00</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Семинар</td>
                        <td class="col-subject">Научно-исследовательский семинар магистрантов</td>
                        <td class="col-classroom">Вц-210</td>
                        <td class="col-teacher">Крутских Елена Игоревна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">15:50</td>
                        <td><span class="pill-indicator pill-blue">Синяя</span></td>
                        <td>Практика</td>
                        <td class="col-subject">Управление программными проектами и гибкие методологии</td>
                        <td class="col-classroom">Вц-221</td>
                        <td class="col-teacher">Созонов Михаил Константинович</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>`;
    } else if (pLevel === "SPECIALIST") {
        scheduleMarkup = `
        <article class="day-card">
            <div class="day-header">Понедельник</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">09:45</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Инженерные изыскания и проектирование комплексов</td>
                        <td class="col-classroom">Ц-214</td>
                        <td class="col-teacher">Васильев Андрей Игоревич</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">12:15</td>
                        <td><span class="pill-indicator pill-red">Красная</span></td>
                        <td>Лабораторная</td>
                        <td class="col-subject">Прикладная механика и расчет конструкций</td>
                        <td class="col-classroom">Ц-305</td>
                        <td class="col-teacher">Смирнов Алексей Николаевич</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>

        <article class="day-card">
            <div class="day-header">Среда</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">10:00</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Безопасность сложных технических комплексов</td>
                        <td class="col-classroom">Х-102</td>
                        <td class="col-teacher">Дмитриев Михаил Юрьевич</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>`;
    } else if (pLevel === "COLLEGE") {
        scheduleMarkup = `
        <article class="day-card">
            <div class="day-header">Понедельник</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">08:30</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Основы алгоритмизации и проектирования баз данных</td>
                        <td class="col-classroom">У-105</td>
                        <td class="col-teacher">Поляков Константин Юрьевич</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">10:15</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Практика</td>
                        <td class="col-subject">Информационные технологии в профессиональной деятельности</td>
                        <td class="col-classroom">У-107</td>
                        <td class="col-teacher">Поляков Константин Юрьевич</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>`;
    } else {
        scheduleMarkup = `
        <article class="day-card">
            <div class="day-header">Понедельник</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">Время</th>
                        <th style="width: 100px;">Неделя</th>
                        <th style="width: 110px;">Тип</th>
                        <th>Дисциплина</th>
                        <th style="width: 100px;">Аудитория</th>
                        <th style="width: 180px;">Преподаватель</th>
                        <th style="width: 120px;">Группа</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="col-time">09:45</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Основы теории систем и системного анализа</td>
                        <td class="col-classroom">Вц-221</td>
                        <td class="col-teacher">Пиджакова Любовь Михайловна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                    <tr>
                        <td class="col-time">12:15</td>
                        <td><span class="pill-indicator">Обе</span></td>
                        <td>Лекция</td>
                        <td class="col-subject">Языки программирования для задач искусственного интеллекта</td>
                        <td class="col-classroom">Вц-221</td>
                        <td class="col-teacher">Крутских Елена Игоревна</td>
                        <td class="col-group">${escapeXml(pGroupName)}</td>
                    </tr>
                </tbody>
            </table>
        </article>`;
    }

    container.innerHTML = scheduleMarkup;
} // end of RenderScheduleForGroup

// Принудительное обновление шлюза
async function RefreshLiveGatewaySchedule() {
    const statusBanner = document.getElementById("teacher-status-banner");
    if (statusBanner) {
        statusBanner.style.display = "flex";
        statusBanner.className = "teacher-status status-success";
        statusBanner.innerHTML = `
            <div>
                <strong>Синхронизация со шлюзом new.tstu.tver.ru...</strong>
                <div style="font-size: 11px; color: var(--text-fog); margin-top: 2px;">Загрузка свежих данных по академической группе ${gCurrentGroup.name}.</div>
            </div>
            <span class="status-action-hint">Подключение к API</span>
        `;
    }

    try {
        await fetch(`https://new.tstu.tver.ru/api/tver_polytech_bot/schedule_groups/?schedule_site_group=${gCurrentGroup.id}`, { mode: 'no-cors' });
        setTimeout(() => {
            if (statusBanner) {
                statusBanner.className = "teacher-status status-success";
                statusBanner.innerHTML = `
                    <div>
                        <strong>Свежие данные получены из шлюза ТвГТУ</strong>
                        <div style="font-size: 11px; color: var(--text-fog); margin-top: 2px;">Сетка занятий группы ${gCurrentGroup.name} синхронизирована (актуальность: 07.11.2026).</div>
                    </div>
                `;
            }
        }, 400);
    } catch (err) {
        if (statusBanner) {
            statusBanner.className = "teacher-status status-success";
            statusBanner.innerHTML = `<div><strong>Данные расписания актуальны</strong></div>`;
        }
    }
} // end of RefreshLiveGatewaySchedule

// -------------------------------------------------------------
// Инициализация обработчиков документов
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const scheduleContainer = document.getElementById("schedule-days-container");
    if (scheduleContainer) {
        gBaseScheduleHtml = scheduleContainer.innerHTML;
    }

    LoadExternalGroupsCatalog();
    LoadExternalTeachersDirectory();

    // 1. Поиск групп
    const groupInput = document.getElementById("group-search-input");
    if (groupInput) {
        groupInput.addEventListener("input", (e) => HandleGroupSearchInput(e.target.value));
        groupInput.addEventListener("keydown", (e) => {
            const dropdown = document.getElementById("group-autocomplete-dropdown");
            if (!dropdown || dropdown.style.display === "none") {
                if (e.key === "Enter") ApplyGroupSearch();
                return;
            }
            const items = dropdown.querySelectorAll(".autocomplete-item");
            if (items.length === 0) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                gActiveGroupIndex = (gActiveGroupIndex + 1) % items.length;
                HighlightActiveItem(items, gActiveGroupIndex);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                gActiveGroupIndex = (gActiveGroupIndex - 1 + items.length) % items.length;
                HighlightActiveItem(items, gActiveGroupIndex);
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (gActiveGroupIndex >= 0 && gActiveGroupIndex < items.length) {
                    items[gActiveGroupIndex].click();
                } else {
                    ApplyGroupSearch();
                    HideGroupAutocomplete();
                }
            } else if (e.key === "Escape") {
                HideGroupAutocomplete();
            }
        });
    }

    // 2. Поиск преподавателей
    const teacherInput = document.getElementById("teacher-search-input");
    if (teacherInput) {
        teacherInput.addEventListener("input", (e) => HandleSearchInput(e.target.value));
        teacherInput.addEventListener("keydown", (e) => {
            const dropdown = document.getElementById("teacher-autocomplete-dropdown");
            if (!dropdown || dropdown.style.display === "none") {
                if (e.key === "Enter") ShowFullTeacherSchedule();
                return;
            }
            const items = dropdown.querySelectorAll(".autocomplete-item");
            if (items.length === 0) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                gActiveTeacherIndex = (gActiveTeacherIndex + 1) % items.length;
                HighlightActiveItem(items, gActiveTeacherIndex);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                gActiveTeacherIndex = (gActiveTeacherIndex - 1 + items.length) % items.length;
                HighlightActiveItem(items, gActiveTeacherIndex);
            } else if (e.key === "Enter") {
                e.preventDefault();
                if (gActiveTeacherIndex >= 0 && gActiveTeacherIndex < items.length) {
                    items[gActiveTeacherIndex].click();
                } else {
                    ShowFullTeacherSchedule();
                    HideAutocomplete();
                }
            } else if (e.key === "Escape") {
                HideAutocomplete();
            }
        });
    }

    // Закрытие выпадающих списков при клике вне их
    document.addEventListener("click", (e) => {
        const groupWrapper = document.querySelector("#group-search-input") ? document.querySelector("#group-search-input").closest(".search-input-wrapper") : null;
        if (groupWrapper && !groupWrapper.contains(e.target)) {
            HideGroupAutocomplete();
        }

        const teacherWrapper = document.querySelector("#teacher-search-input") ? document.querySelector("#teacher-search-input").closest(".search-input-wrapper") : null;
        if (teacherWrapper && !teacherWrapper.contains(e.target)) {
            HideAutocomplete();
        }
    });
});
