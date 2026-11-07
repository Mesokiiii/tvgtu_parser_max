# Lesson.py Доменные модели данных учебных занятий и расписания ТвГТУ
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: описание структур данных одного занятия, учебного дня и расписания группы

class Lesson:
    """
    Класс описывает одно конкретное занятие в сетке расписания.
    Инкапсулирует время, четность недели, тип занятия, аудиторию и преподавателя.
    """

    def __init__(self, pTime, pWeekType, pLessonType, pSubject, pClassroom, pTeacher, pSubgroup=None, pGroupName="Б.ПИН.ИИ.25.16"):
        """
        Конструктор объекта занятия.

        Входные параметры:
            pTime (str): время проведения занятия (например, '08:30').
            pWeekType (str): маркер четности недели ('RED' - нечетная, 'BLUE' - четная, 'BOTH' - еженедельно).
            pLessonType (str): форма проведения (Лекция, Практика, Лабораторная).
            pSubject (str): наименование учебной дисциплины.
            pClassroom (str): номер аудитории и корпус (например, 'Вц-205').
            pTeacher (str): фамилия, имя и отчество преподавателя.
            pSubgroup (str, optional): номер академической подгруппы при делении группы.
            pGroupName (str, optional): академическая группа, у которой проводится занятие.
        """
        self.time = pTime
        self.weekType = pWeekType
        self.lessonType = pLessonType
        self.subject = pSubject
        self.classroom = pClassroom
        self.teacher = pTeacher
        self.subgroup = pSubgroup
        self.group = pGroupName
    # end of __init__

    def toDictionary(self):
        """
        Преобразование объекта занятия в стандартный словарь для сериализации.

        Выходное значение:
            dict: сериализованное представление занятия.
        """
        return {
            "time": self.time,
            "week_type": self.weekType,
            "lesson_type": self.lessonType,
            "subject": self.subject,
            "classroom": self.classroom,
            "teacher": self.teacher,
            "subgroup": self.subgroup,
            "group": self.group
        }
    # end of toDictionary

# end of class Lesson


class GroupSchedule:
    """
    Класс агрегирует расписание занятий для всей учебной группы по дням недели.
    """

    def __init__(self, pGroupName, pGroupId):
        """
        Конструктор объекта расписания группы.

        Входные параметры:
            pGroupName (str): наименование учебной группы.
            pGroupId (str): системный идентификатор группы в базе университета.
        """
        self.groupName = pGroupName
        self.groupId = pGroupId
        # Дни недели хранятся в виде словаря: день недели -> список объектов Lesson
        self.daysMap = {}
    # end of __init__

    def addLesson(self, pDayName, pLesson):
        """
        Добавление занятия в конкретный день недели.

        Входные параметры:
            pDayName (str): наименование дня недели (например, 'Вторник').
            pLesson (Lesson): экземпляр занятия.
        """
        if pDayName not in self.daysMap:
            self.daysMap[pDayName] = []
        # end of if pDayName not in self.daysMap
        self.daysMap[pDayName].append(pLesson)
    # end of addLesson

    def toDictionary(self):
        """
        Преобразование расписания группы в словарь.

        Выходное значение:
            dict: структура данных для выгрузки в JSON.
        """
        serializedDays = {}
        for dayName, lessonsList in self.daysMap.items():
            serializedDays[dayName] = [lesson.toDictionary() for lesson in lessonsList]
        # end of for dayName, lessonsList

        return {
            "group": self.groupName,
            "group_id": self.groupId,
            "schedule": serializedDays
        }
    # end of toDictionary

# end of class GroupSchedule
# end of Lesson.py
