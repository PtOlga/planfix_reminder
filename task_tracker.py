#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль отслеживания задач
Отвечает за управление состоянием уведомлений (закрытые, отложенные, просмотренные)
"""

import datetime
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

# Импортируем систему файлового логирования
from file_logger import debug, info, success, warning, error, critical

@dataclass
class TaskState:
    """Состояние задачи в системе уведомлений"""
    task_id: str
    closed_time: datetime.datetime
    snooze_until: Optional[datetime.datetime] = None
    auto_closed: bool = False
    category: str = 'current'

class TaskTracker:
    """Класс для отслеживания состояния задач и уведомлений"""
    
    def __init__(self):
        # Словарь отслеживаемых задач: task_id -> TaskState
        self._tracked_tasks: Dict[str, TaskState] = {}
        
        # Множество ID активных окон уведомлений
        self._active_notifications: Set[str] = set()
        
        # Настройки времени повторного показа (в минутах)
        self._reshow_intervals = {
            'overdue': 5,   # Просроченные - каждые 5 минут
            'urgent': 15,   # Срочные - каждые 15 минут
            'current': 30   # Обычные - каждые 30 минут
        }
        
        info("TaskTracker инициализирован", "TRACKER")
        debug(f"Интервалы повторного показа: {self._reshow_intervals}", "TRACKER")
    
    def should_show_notification(self, task_id: str, category: str, 
                                max_total_windows: int = 10, 
                                max_category_windows: int = 5) -> bool:
        """
        Определяет нужно ли показывать уведомление для задачи
        
        Args:
            task_id: ID задачи
            category: Категория задачи (overdue, urgent, current)
            max_total_windows: Максимум окон всего
            max_category_windows: Максимум окон одной категории
            
        Returns:
            bool: True если нужно показать уведомление
        """
        if not task_id:
            warning("Попытка проверки показа уведомления без ID задачи", "TRACKER")
            return True
        
        debug(f"Проверка показа уведомления для задачи #{task_id} ({category})", "TRACKER")
        
        # 1. Проверяем лимиты активных окон
        if not self._check_window_limits(category, max_total_windows, max_category_windows):
            debug(f"Задача #{task_id} не показана: превышены лимиты окон", "TRACKER")
            return False
        
        # 2. Проверяем уже открытые уведомления
        if task_id in self._active_notifications:
            debug(f"Задача #{task_id} не показана: уведомление уже активно", "TRACKER")
            return False
        
        # 3. Проверяем состояние задачи
        if task_id not in self._tracked_tasks:
            debug(f"Задача #{task_id} новая - показываем уведомление", "TRACKER")
            return True  # Новая задача - показываем
        
        task_state = self._tracked_tasks[task_id]
        now = datetime.datetime.now()
        
        # 4. Если задача отложена и время еще не пришло
        if task_state.snooze_until and now < task_state.snooze_until:
            time_left = task_state.snooze_until - now
            debug(f"Задача #{task_id} отложена еще на {time_left}", "TRACKER")
            return False
        
        # 5. Если время отложения прошло - удаляем из отслеживания и показываем
        if task_state.snooze_until and now >= task_state.snooze_until:
            info(f"Время отложения задачи #{task_id} истекло - показываем снова", "TRACKER")
            del self._tracked_tasks[task_id]
            return True
        
        # 6. Если задача помечена как "Готово" (без времени отложения)
        if not task_state.snooze_until:
            debug(f"Задача #{task_id} помечена как готовая - не показываем", "TRACKER")
            return False
        
        debug(f"Задача #{task_id} не прошла проверки - не показываем", "TRACKER")
        return False
    
    def _check_window_limits(self, category: str, max_total: int, max_category: int) -> bool:
        """Проверяет лимиты активных окон"""
        total_active = len(self._active_notifications)
        
        if total_active >= max_total:
            debug(f"Превышен общий лимит окон: {total_active}/{max_total}", "TRACKER")
            return False
        
        # Подсчитываем окна данной категории (предполагаем что ID содержит категорию)
        category_count = sum(1 for notification_id in self._active_notifications 
                           if f"_{category}_" in notification_id)
        
        if category_count >= max_category:
            debug(f"Превышен лимит окон категории {category}: {category_count}/{max_category}", "TRACKER")
            return False
        
        debug(f"Лимиты окон в норме: всего {total_active}/{max_total}, {category} {category_count}/{max_category}", "TRACKER")
        return True
    
    def register_notification_shown(self, task_id: str, category: str):
        """
        Регистрирует показ уведомления
        
        Args:
            task_id: ID задачи
            category: Категория задачи
        """
        try:
            notification_id = f"{task_id}_{category}_{datetime.datetime.now().timestamp()}"
            self._active_notifications.add(notification_id)
            
            # Сохраняем связь для быстрого поиска
            setattr(self, f"_notification_for_{task_id}", notification_id)
            
            info(f"Зарегистрирован показ уведомления для задачи #{task_id} ({category})", "TRACKER")
            debug(f"ID уведомления: {notification_id}", "TRACKER")
            debug(f"Всего активных уведомлений: {len(self._active_notifications)}", "TRACKER")
            
        except Exception as e:
            error(f"Ошибка регистрации показа уведомления для задачи #{task_id}: {e}", "TRACKER", exc_info=True)
    
    def register_notification_closed(self, task_id: str, close_reason: str = 'manual'):
        """
        Регистрирует закрытие уведомления
        
        Args:
            task_id: ID задачи
            close_reason: Причина закрытия (manual, snooze_15min, snooze_1hour, done)
        """
        try:
            info(f"Регистрация закрытия уведомления для задачи #{task_id}, причина: {close_reason}", "TRACKER")
            
            # Удаляем из активных уведомлений
            notification_id = getattr(self, f"_notification_for_{task_id}", None)
            if notification_id and notification_id in self._active_notifications:
                self._active_notifications.remove(notification_id)
                delattr(self, f"_notification_for_{task_id}")
                debug(f"Удалено активное уведомление: {notification_id}", "TRACKER")
            else:
                warning(f"Активное уведомление для задачи #{task_id} не найдено", "TRACKER")
            
            # Обрабатываем разные причины закрытия
            now = datetime.datetime.now()
            
            if close_reason == 'snooze_15min':
                snooze_until = now + datetime.timedelta(minutes=15)
                self._tracked_tasks[task_id] = TaskState(
                    task_id=task_id,
                    closed_time=now,
                    snooze_until=snooze_until,
                    auto_closed=False
                )
                info(f"Задача #{task_id} отложена на 15 минут до {snooze_until.strftime('%H:%M')}", "TRACKER")
            
            elif close_reason == 'snooze_1hour':
                snooze_until = now + datetime.timedelta(hours=1)
                self._tracked_tasks[task_id] = TaskState(
                    task_id=task_id,
                    closed_time=now,
                    snooze_until=snooze_until,
                    auto_closed=False
                )
                info(f"Задача #{task_id} отложена на 1 час до {snooze_until.strftime('%H:%M')}", "TRACKER")
            
            elif close_reason == 'done':
                # Помечаем как просмотренную (больше не показывать)
                self._tracked_tasks[task_id] = TaskState(
                    task_id=task_id,
                    closed_time=now,
                    snooze_until=None,  # Без времени = не показывать больше
                    auto_closed=False
                )
                info(f"Задача #{task_id} помечена как готовая (больше не показывать)", "TRACKER")
            
            elif close_reason == 'manual':
                # Закрыто вручную - показать снова через интервал по категории
                category = self._get_task_category(task_id)
                reshow_minutes = self._reshow_intervals.get(category, 30)
                snooze_until = now + datetime.timedelta(minutes=reshow_minutes)
                
                self._tracked_tasks[task_id] = TaskState(
                    task_id=task_id,
                    closed_time=now,
                    snooze_until=snooze_until,
                    auto_closed=True,
                    category=category
                )
                info(f"Задача #{task_id} закрыта вручную, повтор через {reshow_minutes} мин в {snooze_until.strftime('%H:%M')}", "TRACKER")
            
            else:
                warning(f"Неизвестная причина закрытия: {close_reason} для задачи #{task_id}", "TRACKER")
            
            debug(f"Всего отслеживаемых задач: {len(self._tracked_tasks)}", "TRACKER")
            debug(f"Активных уведомлений: {len(self._active_notifications)}", "TRACKER")
            
        except Exception as e:
            error(f"Ошибка регистрации закрытия уведомления для задачи #{task_id}: {e}", "TRACKER", exc_info=True)
    
    def _get_task_category(self, task_id: str) -> str:
        """Получает категорию задачи из отслеживаемых или возвращает значение по умолчанию"""
        if task_id in self._tracked_tasks:
            category = self._tracked_tasks[task_id].category
            debug(f"Категория задачи #{task_id} из истории: {category}", "TRACKER")
            return category
        
        # В реальной реализации категория должна передаваться при закрытии
        # Или сохраняться при показе уведомления
        debug(f"Категория задачи #{task_id} неизвестна, используется 'current'", "TRACKER")
        return 'current'
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Очищает старые записи о задачах
        
        Args:
            max_age_hours: Максимальный возраст записи в часах
        """
        try:
            info(f"Начало очистки задач старше {max_age_hours} часов", "TRACKER")
            
            now = datetime.datetime.now()
            cutoff_time = now - datetime.timedelta(hours=max_age_hours)
            
            # Находим задачи для удаления
            tasks_to_remove = []
            for task_id, task_state in self._tracked_tasks.items():
                if task_state.closed_time < cutoff_time:
                    tasks_to_remove.append(task_id)
                    debug(f"Задача #{task_id} помечена для удаления (возраст: {now - task_state.closed_time})", "TRACKER")
            
            # Удаляем старые записи
            for task_id in tasks_to_remove:
                del self._tracked_tasks[task_id]
            
            if tasks_to_remove:
                success(f"Очищено {len(tasks_to_remove)} старых записей о задачах", "TRACKER")
                debug(f"Удаленные задачи: {tasks_to_remove}", "TRACKER")
            else:
                debug("Старых задач для очистки не найдено", "TRACKER")
            
            debug(f"Осталось отслеживаемых задач: {len(self._tracked_tasks)}", "TRACKER")
            
        except Exception as e:
            error(f"Ошибка очистки старых задач: {e}", "TRACKER", exc_info=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику отслеживания
        
        Returns:
            Dict: Статистика (количество отслеживаемых задач, активных уведомлений и т.д.)
        """
        try:
            now = datetime.datetime.now()
            
            # Подсчитываем разные типы задач
            snoozed_tasks = 0
            done_tasks = 0
            auto_closed_tasks = 0
            expired_snooze_tasks = 0
            
            for task_state in self._tracked_tasks.values():
                if task_state.snooze_until:
                    if now < task_state.snooze_until:
                        snoozed_tasks += 1
                    else:
                        expired_snooze_tasks += 1
                else:
                    done_tasks += 1
                
                if task_state.auto_closed:
                    auto_closed_tasks += 1
            
            stats = {
                'total_tracked_tasks': len(self._tracked_tasks),
                'active_notifications': len(self._active_notifications),
                'snoozed_tasks': snoozed_tasks,
                'done_tasks': done_tasks,
                'auto_closed_tasks': auto_closed_tasks,
                'expired_snooze_tasks': expired_snooze_tasks
            }
            
            debug(f"Статистика TaskTracker: {stats}", "TRACKER")
            return stats
            
        except Exception as e:
            error(f"Ошибка получения статистики: {e}", "TRACKER", exc_info=True)
            return {
                'total_tracked_tasks': 0,
                'active_notifications': 0,
                'snoozed_tasks': 0,
                'done_tasks': 0,
                'auto_closed_tasks': 0,
                'expired_snooze_tasks': 0,
                'error': str(e)
            }
    
    def get_tracked_tasks(self) -> Dict[str, TaskState]:
        """Возвращает копию отслеживаемых задач"""
        try:
            tasks_copy = self._tracked_tasks.copy()
            debug(f"Возвращена копия {len(tasks_copy)} отслеживаемых задач", "TRACKER")
            return tasks_copy
        except Exception as e:
            error(f"Ошибка получения копии отслеживаемых задач: {e}", "TRACKER", exc_info=True)
            return {}
    
    def is_task_snoozed(self, task_id: str) -> bool:
        """Проверяет отложена ли задача"""
        try:
            if task_id not in self._tracked_tasks:
                debug(f"Задача #{task_id} не отслеживается", "TRACKER")
                return False
            
            task_state = self._tracked_tasks[task_id]
            if not task_state.snooze_until:
                debug(f"Задача #{task_id} не имеет времени отложения", "TRACKER")
                return False
            
            is_snoozed = datetime.datetime.now() < task_state.snooze_until
            debug(f"Задача #{task_id} {'отложена' if is_snoozed else 'не отложена'}", "TRACKER")
            return is_snoozed
            
        except Exception as e:
            error(f"Ошибка проверки отложения задачи #{task_id}: {e}", "TRACKER", exc_info=True)
            return False
    
    def get_snooze_time_left(self, task_id: str) -> Optional[datetime.timedelta]:
        """
        Возвращает оставшееся время отложения для задачи
        
        Args:
            task_id: ID задачи
            
        Returns:
            Optional[timedelta]: Оставшееся время или None
        """
        try:
            if not self.is_task_snoozed(task_id):
                debug(f"Задача #{task_id} не отложена", "TRACKER")
                return None
            
            task_state = self._tracked_tasks[task_id]
            time_left = task_state.snooze_until - datetime.datetime.now()
            debug(f"У задачи #{task_id} осталось времени отложения: {time_left}", "TRACKER")
            return time_left
            
        except Exception as e:
            error(f"Ошибка получения времени отложения для задачи #{task_id}: {e}", "TRACKER", exc_info=True)
            return None
    
    def force_show_task(self, task_id: str):
        """
        Принудительно разрешает показ задачи (удаляет из отслеживания)
        
        Args:
            task_id: ID задачи
        """
        try:
            info(f"Принудительное разрешение показа задачи #{task_id}", "TRACKER")
            
            # Удаляем из отслеживаемых задач
            if task_id in self._tracked_tasks:
                del self._tracked_tasks[task_id]
                debug(f"Задача #{task_id} удалена из отслеживания", "TRACKER")
            
            # Также удаляем из активных уведомлений если есть
            notification_id = getattr(self, f"_notification_for_{task_id}", None)
            if notification_id and notification_id in self._active_notifications:
                self._active_notifications.remove(notification_id)
                delattr(self, f"_notification_for_{task_id}")
                debug(f"Активное уведомление для задачи #{task_id} удалено", "TRACKER")
            
            success(f"Задача #{task_id} принудительно разрешена для показа", "TRACKER")
            
        except Exception as e:
            error(f"Ошибка принудительного разрешения показа задачи #{task_id}: {e}", "TRACKER", exc_info=True)
    
    def get_active_notifications_count(self) -> int:
        """Возвращает количество активных уведомлений"""
        count = len(self._active_notifications)
        debug(f"Количество активных уведомлений: {count}", "TRACKER")
        return count
    
    def clear_all_tracking(self):
        """Очищает все отслеживание (для экстренных случаев)"""
        try:
            warning("Выполнение полной очистки отслеживания задач", "TRACKER")
            
            tracked_count = len(self._tracked_tasks)
            active_count = len(self._active_notifications)
            
            self._tracked_tasks.clear()
            self._active_notifications.clear()
            
            # Удаляем все связанные атрибуты
            attrs_to_remove = [attr for attr in dir(self) if attr.startswith('_notification_for_')]
            for attr in attrs_to_remove:
                try:
                    delattr(self, attr)
                except:
                    pass
            
            warning(f"Очистка завершена: удалено {tracked_count} отслеживаемых задач и {active_count} активных уведомлений", "TRACKER")
            
        except Exception as e:
            error(f"Ошибка полной очистки отслеживания: {e}", "TRACKER", exc_info=True)

# ===== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ДЛЯ ИСПОЛЬЗОВАНИЯ В ПРИЛОЖЕНИИ =====

# Создаем глобальный трекер для использования в других модулях
task_tracker = TaskTracker()

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_task_tracker():
    """Тестирует TaskTracker с файловым логированием"""
    # Настраиваем логирование для тестов
    from file_logger import setup_logging, get_logs_directory, startup, success
    setup_logging(debug_mode=True, console_debug=True)
    
    startup("Тестирование TaskTracker с файловым логированием")
    
    tracker = TaskTracker()
    
    # Тест 1: Показ новой задачи
    info("=== ТЕСТ 1: Показ новой задачи ===", "TEST")
    should_show = tracker.should_show_notification("test_task_1", "urgent")
    success(f"Новая задача должна показываться: {should_show}", "TEST")
    
    # Тест 2: Регистрация показа
    info("=== ТЕСТ 2: Регистрация показа уведомления ===", "TEST")
    tracker.register_notification_shown("test_task_1", "urgent")
    success("Показ уведомления зарегистрирован", "TEST")
    
    # Тест 3: Проверка повторного показа
    info("=== ТЕСТ 3: Проверка повторного показа ===", "TEST")
    should_show_again = tracker.should_show_notification("test_task_1", "urgent")
    success(f"Задача не должна показываться повторно: {not should_show_again}", "TEST")
    
    # Тест 4: Закрытие с отложением
    info("=== ТЕСТ 4: Тестирование отложения на 15 минут ===", "TEST")
    tracker.register_notification_closed("test_task_1", "snooze_15min")
    success("Отложение на 15 минут зарегистрировано", "TEST")
    
    # Тест 5: Проверка состояния отложения
    info("=== ТЕСТ 5: Проверка состояния отложения ===", "TEST")
    is_snoozed = tracker.is_task_snoozed("test_task_1")
    time_left = tracker.get_snooze_time_left("test_task_1")
    success(f"Задача отложена: {is_snoozed}", "TEST")
    if time_left:
        info(f"Осталось времени отложения: {time_left}", "TEST")
    
    # Тест 6: Статистика
    info("=== ТЕСТ 6: Статистика трекера ===", "TEST")
    stats = tracker.get_statistics()
    success(f"Получена статистика: {stats}", "TEST")
    
    # Тест 7: Принудительный показ
    info("=== ТЕСТ 7: Принудительный показ задачи ===", "TEST")
    tracker.force_show_task("test_task_1")
    should_show_forced = tracker.should_show_notification("test_task_1", "urgent")
    success(f"После принудительного разрешения показывается: {should_show_forced}", "TEST")
    
    # Тест 8: Тест с несколькими задачами
    info("=== ТЕСТ 8: Тестирование лимитов окон ===", "TEST")
    for i in range(3):
        task_id = f"test_task_{i+2}"
        tracker.register_notification_shown(task_id, "current")
        debug(f"Зарегистрирована задача {task_id}", "TEST")
    
    active_count = tracker.get_active_notifications_count()
    success(f"Активных уведомлений: {active_count}", "TEST")
    
    # Тест 9: Очистка старых задач
    info("=== ТЕСТ 9: Тестирование очистки ===", "TEST")
    tracker.cleanup_old_tasks(max_age_hours=0)  # Очистить все
    success("Очистка старых задач выполнена", "TEST")
    
    # Финальная статистика
    final_stats = tracker.get_statistics()
    info(f"Финальная статистика: {final_stats}", "TEST")
    
    startup(f"Тестирование завершено! Логи сохранены в: {get_logs_directory()}")
    success("Все тесты TaskTracker пройдены успешно", "TEST")

if __name__ == "__main__":
    test_task_tracker()