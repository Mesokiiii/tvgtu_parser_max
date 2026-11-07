# Модуль прямого взаимодействия с веб-шлюзом ТвГТУ (Вариант 2)

Модуль предназначен для получения и обработки данных учебного расписания непосредственно через веб-интерфейс Тверского государственного технического университета (ТвГТУ).

Адрес источника данных:
`https://new.tstu.tver.ru/api/tver_polytech_bot/schedule_groups/`

---

## 1. Особенности архитектуры решения

1. **Открытый доступ без авторизации.** Доступ к расписанию предоставляется в открытом режиме без передачи ключей доступа, токенов и файлов cookie.
2. **Поддержка полного перечня групп университета (438+ групп).** Включает все ступени обучения:
   - Магистратура (префикс `М.`, 74 группы);
   - Бакалавриат (префикс `Б.`, 253 группы);
   - Специалитет (префикс `С.`, 33 группы);
   - Колледж СПО (префикс `СПО.`, 5 групп);
   - Аспирантура (префиксы `А.` / `АС.`, 73 группы).
3. **Экспорт в CalDAV-сервер Radicale и iCalendar (.ics).** Генерация стандартных календарей RFC 5545 с поддержкой повторяющихся событий (RRULE), точного расчета чередования нечетных (красных) и четных (синих) недель, а также прямая сетевая синхронизация по протоколу CalDAV (HTTP PUT / MKCALENDAR).
4. **Контейнеризация в Docker и Docker Compose.** Готовая инфраструктура для запуска в изолированном контейнере с возможностью автозапуска встроенного CalDAV-сервера Radicale.
5. **Полная параметризация через переменные окружения.** Возможность гибкой настройки через файл `.env` без правки исходного кода.
6. **Разделение занятий по четности недель.** В разметке шлюза четность закодирована CSS-классами:
   - класс `table-danger` соответствует нечетной (красной) неделе;
   - класс `table-primary` соответствует четной (синей) неделе;
   - базовый стиль указывает на проведение занятия еженедельно.
7. **Устойчивость к сетевым задержкам.** При нестабильной работе внешнего сервера шлюза ТвГТУ предусмотрены быстрые таймауты и локальные резервные снимки учебных планов по каждой ступени образования.

---

## 2. Модульная структура

```text
2_tstu_api_direct/
├── network/                    # Сетевой транспорт к серверу ТвГТУ
│   └── web_client.py           # TstuWebClient: HTTP-запросы с настраиваемыми таймаутами
├── parsers/                    # Синтаксический анализ разметки
│   ├── groups_parser.py        # GroupsCatalogParser: извлечение списка групп и сопоставление ID
│   ├── html_schedule_parser.py # HtmlScheduleParser: разбор таблицы пар, аудиторий и преподавателей
│   └── teacher_schedule_extractor.py # TeacherScheduleExtractor: поиск по преподавателям
├── models/                     # Доменные структуры данных
│   └── lesson.py               # Lesson (занятие) и GroupSchedule (расписание группы)
├── exporters/                  # Модули формирования отчетов
│   ├── radicale_exporter.py    # RadicaleScheduleExporter: экспорт в Radicale (CalDAV) и iCalendar (.ics)
│   ├── excel_exporter.py       # ExcelScheduleExporter: стилизованная таблица Excel (.xlsx)
│   └── json_exporter.py        # JsonScheduleExporter: экспорт в машиночитаемый JSON
├── data/                       # Локальные справочники
│   ├── groups_list.json        # 438+ академических групп ТвГТУ с номерами шлюза
│   └── teachers_directory.json # Реестр научно-педагогического состава всех факультетов
├── output/                     # Каталог сформированных отчетов
│   ├── groups/                 # Расписания академических групп (.json, .xlsx, .ics)
│   └── teachers/               # Расписания преподавателей (.json, .xlsx, .ics)
├── schedule_service.py         # Фасад TstuScheduleService (сквозной поиск и кэширование)
├── web_viewer.html             # Интерактивный просмотрщик расписания групп и преподавателей
├── viewer_app.js               # Клиентская логика фильтрации, поиска и выгрузки (Excel, .ics)
├── viewer_style.css            # Оформление по дизайн-системе Altitude
├── main.py                     # Консольная точка входа (CLI + чтение ENV)
├── Dockerfile                  # Описание сборки Docker-образа
├── docker-compose.yml          # Стек приложения: парсер расписания + CalDAV-сервер Radicale
├── requirements.txt            # Зависимости Python
├── .env.example                # Шаблон переменных окружения
├── .env                        # Файл рабочих параметров окружения
└── README.md
```

---

## 3. Выбор учебной группы (магистратура, бакалавриат, специалитет, колледж)

### 3.1. Просмотр доступных групп в консоли
Для вывода групп с фильтром по наименованию или ступени образования используется ключ `--list-groups`:
```bash
# Вывести группы магистратуры
python main.py --list-groups магистратура

# Вывести группы по префиксу
python main.py --list-groups М.
python main.py --list-groups СПО.
python main.py --list-groups С.РСК

# Вывести все 438 групп
python main.py --list-groups
```

### 3.2. Интерактивный выбор группы в терминале
```bash
python main.py --select-group
```
Программа выведет нумерованный список и запросит порядковый номер желаемой группы.

### 3.3. Прямое указание группы для выгрузки
```bash
# Магистратура
python main.py --group М.ПИН.РИС.25.09
python main.py М.ИВТ.ИПО.25.05

# Бакалавриат
python main.py --group Б.ПИН.ИИ.25.16

# Специалитет
python main.py --group С.РСК.РСК.24.05

# Колледж СПО
python main.py --group СПО.ИС.25.01
```
По итогам выполнения формируются файлы:
- `output/groups/schedule_<наименование_группы>.json`
- `output/groups/schedule_<наименование_группы>.xlsx`
- `output/groups/schedule_<наименование_группы>.ics` (календарь iCalendar)

---

## 4. Сквозной поиск и расширенные возможности для преподавателя

В модуль встроен мощный аналитический и поисковый механизм для преподавателей университета:
```bash
# Быстрый шорткат для расписания преподавателя Созонова М.К. (ФИТ)
python main.py --sozonov

# Поиск любого преподавателя по фамилии
python main.py --teacher Созонов
python main.py --teacher Пиджакова
python main.py --teacher Лебедев
```

### 4.1. Супер-фишки CLI для преподавателя

| Флаг | Описание | Пример вызова |
| :--- | :--- | :--- |
| `--today` | Показать расписание только на **сегодня** | `python main.py --sozonov --today` |
| `--tomorrow` | Показать пары на **завтра** | `python main.py --sozonov --tomorrow` |
| `--day <День>` | Выбор конкретного дня недели | `python main.py --sozonov --day Вторник` |
| `--current-week` | Автоматически определить текущую неделю семестра и показать пары для неё | `python main.py --sozonov --current-week` |
| `--week <red\|blue>` | Фильтр по четности (красная/нечетная или синяя/четная) | `python main.py --sozonov --week red` |
| `--building <Корпус>` | Фильтр по учебному корпусу (`Вц`, `Ц`, `ХТ`, `Уч`) | `python main.py --sozonov --building Вц` |
| `--next`, `--upcoming` | Показать **ближайшую пару** и сколько минут осталось | `python main.py --sozonov --next` |
| `--workload`, `--stats` | **Педагогическая нагрузка**: акад. часы, % лекций/лаб/практик, распределение по группам, окна | `python main.py --sozonov --workload` |
| `--conflicts` | Аудит коллизий: накладки пар и резкая смена корпусов | `python main.py --sozonov --conflicts` |
| `--free-days` | Методические и научные дни (свободные от пар) | `python main.py --sozonov --free-days` |
| `--card`, `--summary` | Визитная карточка преподавателя в терминале | `python main.py --sozonov --card` |
| `--attendance-sheet` | Сгенерировать **журнал учета посещаемости и ведомость БРС** в Excel (.xlsx) | `python main.py --sozonov --attendance-sheet` |
| `--alarm <минуты>` | Напоминание перед каждой парой в Radicale / смартфоне (VALARM) | `python main.py --sozonov --alarm 15 --sync-radicale` |
| `--format <table>` | Псевдографическая ASCII-таблица (по умолчанию) | `python main.py --sozonov --format table` |
| `--format <compact>`| Компактный строковый список | `python main.py --sozonov --format compact` |
| `--format <markdown>`| Markdown-таблица для заметок (Obsidian / Notion) | `python main.py --sozonov --format markdown` |

Результаты автоматически сохраняются в `output/teachers/` в форматах JSON, Excel (`.xlsx`) и iCalendar (`.ics`).

---

## 5. Экспорт в CalDAV-сервер Radicale и iCalendar (.ics)

Модуль `exporters/radicale_exporter.py` обеспечивает полноценную интеграцию с календарями:

1. **Генерация файлов `.ics` (RFC 5545):**
   - Точные временные слоты пар с учетом часового пояса Москвы (`Europe/Moscow`, UTC+3).
   - Правила повторения `RRULE`:
     - еженедельные пары: `FREQ=WEEKLY;INTERVAL=1;UNTIL=...`;
     - пары нечетной (красной) недели: `FREQ=WEEKLY;INTERVAL=2;UNTIL=...` со стартом на 1-й неделе;
     - пары четной (синей) недели: `FREQ=WEEKLY;INTERVAL=2;UNTIL=...` со стартом на 2-й неделе.
   - Подробные метаданные каждого занятия: дисциплина, тип (лекция/практика/лабораторная), аудитория, подгруппа, преподаватель.
2. **Сетевая синхронизация с Radicale:**
   - Автоматическое создание календаря через HTTP `MKCALENDAR` / `MKCOL`.
   - Загрузка событий методом HTTP `PUT` по протоколу CalDAV на адрес `http://<radicale_host>:5232/<user>/<calendar>/<uid>.ics`.
   - Поддержка базовой аутентификации (Basic Auth).
   - При недоступности сервера Radicale модуль выдает диагностическое сообщение и гарантированно сохраняет локальный `.ics` файл без аварийного завершения.

Команды запуска:
```bash
# Синхронизация расписания группы с Radicale
python main.py --group М.ПИН.РИС.25.09 --sync-radicale --radicale-url http://localhost:5232

# Синхронизация персонального расписания преподавателя с Radicale
python main.py --teacher Пиджакова --sync-radicale --radicale-url http://localhost:5232

# Выгрузка только в .ics и Excel (без отправки на сервер)
python main.py --group Б.ПИН.ИИ.25.16 --no-radicale
```

---

## 6. Параметризация через переменные окружения (.env)

Все параметры программы можно передавать через переменные окружения. Создайте или отредактируйте файл `.env`:

| Переменная | Описание | Значение по умолчанию |
| :--- | :--- | :--- |
| `SCHEDULE_GROUP` | Академическая группа для обработки | `Б.ПИН.ИИ.25.16` |
| `SCHEDULE_TEACHER` | Фамилия преподавателя (если задано, группа игнорируется) | *пусто* |
| `RADICALE_URL` | Адрес сервера Radicale | `http://radicale:5232` (или `http://localhost:5232`) |
| `RADICALE_USER` | Имя пользователя CalDAV | `tstu` |
| `RADICALE_PASSWORD` | Пароль CalDAV | `tstu_password` |
| `RADICALE_CALENDAR` | Имя коллекции календаря | `schedule` |
| `EXPORT_RADICALE` | Включить сетевую синхронизацию с Radicale (`true`/`false`) | `true` |
| `EXPORT_ICS` | Создавать локальный файл календаря `.ics` (`true`/`false`) | `true` |
| `EXPORT_EXCEL` | Создавать таблицу Excel `.xlsx` (`true`/`false`) | `true` |
| `EXPORT_JSON` | Создавать файл `.json` (`true`/`false`) | `true` |
| `SEMESTER_START_DATE` | Дата начала семестра (ГГГГ-ММ-ДД) | `2026-09-01` |
| `SEMESTER_END_DATE` | Дата окончания семестра (ГГГГ-ММ-ДД) | `2027-01-31` |
| `SYNC_INTERVAL` | Интервал фоновой синхронизации в секундах (`0` = один раз) | `0` |
| `RUN_SERVER` | Запустить веб-сервер интерфейса (`true`/`false`) | `false` |
| `PORT` | Порт встроенного веб-сервера | `8081` |

Пример запуска с переменными окружения:
```bash
# В терминале Linux / macOS:
SCHEDULE_GROUP="М.ПИН.РИС.25.09" RADICALE_URL="http://localhost:5232" python main.py

# В PowerShell:
$env:SCHEDULE_GROUP="М.ПИН.РИС.25.09"; python main.py
```

---

## 7. Запуск через Docker и Docker Compose

### 7.1. Запуск полного стека через Docker Compose (Рекомендуется)

В проект включен файл `docker-compose.yml`, объединяющий сервис расписания и CalDAV-сервер Radicale.

```bash
# Сборка и запуск Radicale + парсера расписания
docker compose up -d

# Просмотр логов синхронизации
docker compose logs -f tstu-schedule

# Остановка контейнеров
docker compose down
```

После выполнения:
- Сервер Radicale доступен по адресу: `http://localhost:5232`
- Календарь расписания загружен в коллекцию: `http://localhost:5232/tstu/schedule/`
- Все сформированные файлы (`.ics`, `.xlsx`, `.json`) сохранены в локальную папку `./output/`

### 7.2. Запуск отдельного Docker-контейнера

```bash
# 1. Сборка Docker-образа
docker build -t tstu-schedule-direct .

# 2. Разовый запуск с выгрузкой в локальную папку output
docker run --rm \
  -e SCHEDULE_GROUP="М.ПИН.РИС.25.09" \
  -v "${PWD}/output:/app/output" \
  tstu-schedule-direct

# 3. Запуск для преподавателя с подключением к Radicale на хосте
docker run --rm \
  -e SCHEDULE_TEACHER="Пиджакова" \
  -e RADICALE_URL="http://host.docker.internal:5232" \
  -e EXPORT_RADICALE="true" \
  -v "${PWD}/output:/app/output" \
  tstu-schedule-direct

# 4. Запуск в режиме веб-просмотрщика на порту 8081
docker run -d --name tstu-web \
  -p 8081:8081 \
  -e RUN_SERVER="true" \
  -v "${PWD}/output:/app/output" \
  tstu-schedule-direct
```

---

## 8. Подключение календаря Radicale к устройствам

После выгрузки расписания в Radicale календарь можно подключить к любому смартфону или почтовому клиенту:

- **Адрес CalDAV:** `http://<ip-сервера>:5232/tstu/schedule/`
- **Логин:** `tstu`
- **Пароль:** `tstu_password`
- **Поддерживаемые клиенты:**
  - **iOS / macOS:** Настройки → Календарь → Учетные записи → Добавить CalDAV.
  - **Android:** Приложение DAVx⁵ (синхронизирует с Google Календарем).
  - **Thunderbird:** Создать календарь → В сети → CalDAV.
  - **Outlook:** Импорт файла `output/groups/schedule_<группа>.ics`.

---

## 9. Интерактивный просмотрщик `web_viewer.html`

Интерфейс `web_viewer.html` открывается в браузере и включает:
1. Фильтрацию по ступеням образования (Магистратура, Бакалавриат, Специалитет, Колледж).
2. Автопоиск групп с автодополнением и бейджами.
3. Преподавательский режим (60+ преподавателей).
4. Кнопки мгновенной выгрузки расписания в **Excel (.xls)**, **CSV** и **iCalendar (.ics) / Radicale**.
