#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль отслеживания задач
Отвечает за управление состоянием уведомлений (закрытые, отложенные, просмотренные)
"""

import datetime
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass

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
            return True
        
        # 1. Проверяем лимиты активных окон
        if not self._check_window_limits(category, max_total_windows, max_category_windows):
            return False
        
        # 2. Проверяем уже открытые уведомления
        if task_id in self._active_notifications:
            return False
        
        # 3. Проверяем состояние задачи
        if task_id not in self._tracked_tasks:
            return True  # Новая задача - показываем
        
        task_state = self._tracked_tasks[task_id]
        now = datetime.datetime.now()
        
        # 4. Если задача отложена и время еще не пришло
        if task_state.snooze_until and now < task_state.snooze_until:
            return False
        
        # 5. Если время отложения прошло - удаляем из отслеживания и показываем
        if task_state.snooze_until and now >= task_state.snooze_until:
            del self._tracked_tasks[task_id]
            return True
        
        # 6. Если задача помечена как "Готово" (без времени отложения)
        if not task_state.snooze_until:
            return False
        
        return False
    
    def _check_window_limits(self, category: str, max_total: int, max_category: int) -> bool:
        """Проверяет лимиты активных окон"""
        total_active = len(self._active_notifications)
        
        if total_active >= max_total:
            return False
        
        # Подсчитываем окна данной категории (предполагаем что ID содержит категорию)
        category_count = sum(1 for notification_id in self._active_notifications 
                           if f"_{category}_" in notification_id)
        
        if category_count >= max_category:
            return False
        
        return True
    
    def register_notification_shown(self, task_id: str, category: str):
        """
        Регистрирует показ уведомления
        
        Args:
            task_id: ID задачи
            category: Категория задачи
        """
        notification_id = f"{task_id}_{category}_{datetime.datetime.now().timestamp()}"
        self._active_notifications.add(notification_id)
        
        # Сохраняем связь для быстрого поиска
        setattr(self, f"_notification_for_{task_id}", notification_id)
    
    def register_notification_closed(self, task_id: str, close_reason: str = 'manual'):
        """
        Регистрирует закрытие уведомления
        
        Args:
            task_id: ID задачи
            close_reason: Причина закрытия (manual, snooze_15min, snooze_1hour, done)
        """
        # Удаляем из активных уведомлений
        notification_id = getattr(self, f"_notification_for_{task_id}", None)
        if notification_id and notification_id in self._active_notifications:
            self._active_notifications.remove(notification_id)
            delattr(self, f"_notification_for_{task_id}")
        
        # Обрабатываем разные причины закрытия
        now = datetime.datetime.now()
        
        if close_reason == 'snooze_15min':
            self._tracked_tasks[task_id] = TaskState(
                task_id=task_id,
                closed_time=now,
                snooze_until=now + datetime.timedelta(minutes=15),
                auto_closed=False
            )
        
        elif close_reason == 'snooze_1hour':
            self._tracked_tasks[task_id] = TaskState(
                task_id=task_id,
                closed_time=now,
                snooze_until=now + datetime.timedelta(hours=1),
                auto_closed=False
            )
        
        elif close_reason == 'done':
            # Помечаем как просмотренную (больше не показывать)
            self._tracked_tasks[task_id] = TaskState(
                task_id=task_id,
                closed_time=now,
                snooze_until=None,  # Без времени = не показывать больше
                auto_closed=False
            )
        
        elif close_reason == 'manual':
            # Закрыто вручную - показать снова через интервал по категории
            category = self._get_task_category(task_id)
            reshow_minutes = self._reshow_intervals.get(category, 30)
            
            self._tracked_tasks[task_id] = TaskState(
                task_id=task_id,
                closed_time=now,
                snooze_until=now + datetime.timedelta(minutes=reshow_minutes),
                auto_closed=True,
                category=category
            )
    
    def _get_task_category(self, task_id: str) -> str:
        """Получает категорию задачи (заглушка, в реальности можно передавать параметром)"""
        # В реальной реализации категория должна передаваться при закрытии
        # Или сохраняться при показе уведомления
        return 'current'
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        Очищает старые записи о задачах
        
        Args:
            max_age_hours: Максимальный возраст записи в часах
        """
        now = datetime.datetime.now()
        cutoff_time = now - datetime.timedelta(hours=max_age_hours)
        
        # Находим задачи для удаления
        tasks_to_remove = []
        for task_id, task_state in self._tracked_tasks.items():
            if task_state.closed_time < cutoff_time:
                tasks_to_remove.append(task_id)
        
        # Удаляем старые записи
        for task_id in tasks_to_remove:
            del self._tracked_tasks[task_id]
        
        if tasks_to_remove:
            print(f"🧹 Очищено {len(tasks_to_remove)} старых записей о задачах")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику отслеживания
        
        Returns:
            Dict: Статистика (количество отслеживаемых задач, активных уведомлений и т.д.)
        """
        now = datetime.datetime.now()
        
        # Подсчитываем разные типы задач
        snoozed_tasks = 0
        done_tasks = 0
        auto_closed_tasks = 0
        
        for task_state in self._tracked_tasks.values():
            if task_state.snooze_until:
                if now < task_state.snooze_until:
                    snoozed_tasks += 1
            else:
                done_tasks += 1
            
            if task_state.auto_closed:
                auto_closed_tasks += 1
        
        return {
            'total_tracked_tasks': len(self._tracked_tasks),
            'active_notifications': len(self._active_notifications),
            'snoozed_tasks': snoozed_tasks,
            'done_tasks': done_tasks,
            'auto_closed_tasks': auto_closed_tasks
        }
    
    def get_tracked_tasks(self) -> Dict[str, TaskState]:
        """Возвращает копию отслеживаемых задач"""
        return self._tracked_tasks.copy()
    
    def is_task_snoozed(self, task_id: str) -> bool:
        """Проверяет отложена ли задача"""
        if task_id not in self._tracked_tasks:
            return False
        
        task_state = self._tracked_tasks[task_id]
        if not task_state.snooze_until:
            return False
        
        return datetime.datetime.now() < task_state.snooze_until
    
    def get_snooze_time_left(self, task_id: str) -> Optional[datetime.timedelta]:
        """
        Возвращает оставшееся время отложения для задачи
        
        Args:
            task_id: ID задачи
            
        Returns:
            Optional[timedelta]: Оставшееся время или None
        """
        if not self.is_task_snoozed(task_id):
            return None
        
        task_state = self._tracked_tasks[task_id]
        return task_state.snooze_until - datetime.datetime.now()
    
    def force_show_task(self, task_id: str):
        """
        Принудительно разрешает показ задачи (удаляет из отслеживания)
        
        Args:
            task_id: ID задачи
        """
        if task_id in self._tracked_tasks:
            del self._tracked_tasks[task_id]
        
        # Также удаляем из активных уведомлений если есть
        notification_id = getattr(self, f"_notification_for_{task_id}", None)
        if notification_id and notification_id in self._active_notifications:
            self._active_notifications.remove(notification_id)
            delattr(self, f"_notification_for_{task_id}")

# ===== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ДЛЯ ИСПОЛЬЗОВАНИЯ В ПРИЛОЖЕНИИ =====

# Создаем глобальный трекер для использования в других модулях
task_tracker = TaskTracker()

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_task_tracker():
    """Тестирует TaskTracker"""
    print("🧪 Тестирование TaskTracker")
    print("=" * 40)
    
    tracker = TaskTracker()
    
    # Тест 1: Показ новой задачи
    print("1. Тестирование показа новой задачи...")
    should_show = tracker.should_show_notification("task_1", "urgent")
    print(f"✅ Новая задача должна показываться: {should_show}")
    
    # Тест 2: Регистрация показа
    print("\n2. Регистрация показа уведомления...")
    tracker.register_notification_shown("task_1", "urgent")
    
    # Тест 3: Проверка повторного показа
    should_show_again = tracker.should_show_notification("task_1", "urgent")
    print(f"✅ Задача не должна показываться повторно: {not should_show_again}")
    
    # Тест 4: Закрытие с отложением
    print("\n3. Тестирование отложения на 15 минут...")
    tracker.register_notification_closed("task_1", "snooze_15min")
    
    # Тест 5: Проверка состояния отложения
    is_snoozed = tracker.is_task_snoozed("task_1")
    time_left = tracker.get_snooze_time_left("task_1")
    print(f"✅ Задача отложена: {is_snoozed}")
    if time_left:
        print(f"✅ Осталось времени: {time_left}")
    
    # Тест 6: Статистика
    print("\n4. Статистика трекера...")
    stats = tracker.get_statistics()
    print(f"✅ Статистика: {stats}")
    
    # Тест 7: Принудительный показ
    print("\n5. Принудительный показ задачи...")
    tracker.force_show_task("task_1")
    should_show_forced = tracker.should_show_notification("task_1", "urgent")
    print(f"✅ После принудительного разрешения показывается: {should_show_forced}")

if __name__ == "__main__":
    test_task_tracker()