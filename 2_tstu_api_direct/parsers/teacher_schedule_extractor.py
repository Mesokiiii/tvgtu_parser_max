# TeacherScheduleExtractor.py Модуль фильтрации и извлечения расписания преподавателей
# Создан 07.11.2027 Кафедра программного обеспечения (ФИТ ТвГТУ)
# Назначение: поиск учебных занятий по ФИО преподавателя и формирование персонального расписания

from models.lesson import Lesson, GroupSchedule


class TeacherScheduleExtractor:
    """
    Класс отвечает за фильтрацию сетки занятий и формирование расписания для конкретного преподавателя.
    """

    def __init__(self):
        """
        Конструктор экстрактора расписания преподавателей.
        """
        pass
    # end of __init__

    def extractTeacherSchedule(self, pGroupSchedule, pTeacherNameQuery):
        """
        Извлечение всех занятий конкретного преподавателя из расписания одной группы
        либо из совокупности нескольких академических групп (сквозной парсинг).

        Входные параметры:
            pGroupSchedule (GroupSchedule | list[GroupSchedule]): расписание группы или список расписаний групп.
            pTeacherNameQuery (str): фамилия или фрагмент ФИО преподавателя (например, 'Пиджакова').
        Выходное значение:
            GroupSchedule: объект расписания, содержащий занятия указанного преподавателя по всем группам.
        """
        normalizedQuery = pTeacherNameQuery.strip().lower()
        teacherFullName = pTeacherNameQuery

        # Создаем целевой объект расписания для преподавателя
        teacherSchedule = GroupSchedule(pGroupName=f"Преподаватель {pTeacherNameQuery}", pGroupId="TEACHER")

        schedulesList = pGroupSchedule if isinstance(pGroupSchedule, (list, tuple)) else [pGroupSchedule]

        for scheduleObj in schedulesList:
            for dayName, lessonsList in scheduleObj.daysMap.items():
                for lessonItem in lessonsList:
                    teacherField = lessonItem.teacher.lower() if lessonItem.teacher else ""
                    rawTextField = lessonItem.subject.lower() if lessonItem.subject else ""

                    # Проверяем совпадение запроса в поле преподавателя либо в полном тексте пары
                    if normalizedQuery in teacherField or normalizedQuery in rawTextField:
                        if lessonItem.teacher and len(lessonItem.teacher) > len(teacherFullName):
                            teacherFullName = lessonItem.teacher
                        # end of if lessonItem.teacher

                        # Проверяем дедупликацию потоковых лекций, проводимых одновременно для нескольких групп
                        existingLesson = self._findExistingLesson(teacherSchedule.daysMap.get(dayName, []), lessonItem)
                        if existingLesson:
                            # Объединяем наименования групп в одну лекцию
                            if lessonItem.group and lessonItem.group not in existingLesson.group:
                                existingLesson.group = f"{existingLesson.group}, {lessonItem.group}"
                            # end of if lessonItem.group
                        else:
                            teacherSchedule.addLesson(dayName, lessonItem)
                        # end of if existingLesson
                    # end of if normalizedQuery
                # end of for lessonItem
            # end of for dayName, lessonsList
        # end of for scheduleObj

        teacherSchedule.groupName = f"Преподаватель {teacherFullName}"
        return teacherSchedule
    # end of extractTeacherSchedule

    def _findExistingLesson(self, pLessonsList, pNewLesson):
        """Вспомогательный метод поиска идентичного занятия по времени, дню и аудитории."""
        for item in pLessonsList:
            if (item.time == pNewLesson.time and 
                item.weekType == pNewLesson.weekType and 
                item.classroom == pNewLesson.classroom and 
                item.subject == pNewLesson.subject):
                return item
        return None
    # end of _findExistingLesson

    def getUniqueTeachersList(self, pGroupSchedule):
        """
        Получение списка всех уникальных преподавателей, задействованных в расписании.

        Входные параметры:
            pGroupSchedule (GroupSchedule): расписание.
        Выходное значение:
            list: отсортированный список ФИО преподавателей.
        """
        teachersSet = set()
        for dayName, lessonsList in pGroupSchedule.daysMap.items():
            for lessonItem in lessonsList:
                if lessonItem.teacher and lessonItem.teacher.strip():
                    teachersSet.add(lessonItem.teacher.strip())
                # end of if lessonItem.teacher
            # end of for lessonItem
        # end of for dayName, lessonsList

        return sorted(list(teachersSet))
    # end of getUniqueTeachersList

# end of class TeacherScheduleExtractor
# end of TeacherScheduleExtractor.py
