#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planfix Reminder - Модульная версия
Главный файл приложения
"""

import sys
import time
import threading
import datetime
import webbrowser
from typing import Optional

# Импортируем наши модули
from config_manager import ConfigManager
from planfix_api import PlanfixAPI, TaskProcessor
from task_tracker import task_tracker
from ui_components import ToastManager, SystemTray

class PlanfixReminderApp:
    """Главный класс приложения"""
    
    def __init__(self):
        # Компоненты приложения
        self.config_manager = ConfigManager()
        self.planfix_api: Optional[PlanfixAPI] = None
        self.toast_manager: Optional[ToastManager] = None
        self.system_tray: Optional[SystemTray] = None
        
        # Состояние приложения
        self.is_running = False
        self.is_paused = False
        self.pause_until: Optional[datetime.datetime] = None
        
        # Настройки (загружаются из конфига)
        self.app_settings = {}
        
        # Статистика
        self.current_stats = {'total': 0, 'overdue': 0, 'urgent': 0}
        self.last_check_time: Optional[datetime.datetime] = None
    
    def initialize(self) -> bool:
        """
        Инициализирует все компоненты приложения
        
        Returns:
            bool: True если инициализация успешна
        """
        print("🚀 Запуск Planfix Reminder (модульная версия)")
        print("=" * 50)
        
        # 1. Загружаем конфигурацию
        print("📋 Загрузка конфигурации...")
        if not self._load_configuration():
            return False
        
        # 2. Инициализируем API
        print("\n🌐 Инициализация Planfix API...")
        if not self._initialize_api():
            return False
        
        # 3. Создаем UI компоненты
        print("\n🎨 Создание интерфейса...")
        if not self._initialize_ui():
            return False
        
        print("\n✅ Инициализация завершена успешно!")
        return True
    
    def _load_configuration(self) -> bool:
        """Загружает конфигурацию"""
        if not self.config_manager.load_config(show_diagnostics=True):
            print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить конфигурацию!")
            
            # Предлагаем создать пример конфига
            try:
                choice = input("\nСоздать пример config.ini? (y/n): ").lower().strip()
                if choice in ['y', 'yes', 'да', 'д', '']:
                    self.config_manager.create_sample_config()
                    print("\n✅ Пример config.ini создан!")
                    print("📝 Отредактируйте его и перезапустите программу")
            except (KeyboardInterrupt, EOFError):
                pass
            
            return False
        
        # Получаем настройки
        self.app_settings = self.config_manager.get_app_settings()
        print("✅ Конфигурация загружена успешно")
        
        return True
    
    def _initialize_api(self) -> bool:
        """Инициализирует API клиент"""
        planfix_config = self.config_manager.get_planfix_config()
        role_settings = self.config_manager.get_role_settings()
        
        self.planfix_api = PlanfixAPI(planfix_config, role_settings)
        
        # Тестируем соединение
        print("🔄 Проверка подключения к API...")
        if not self.planfix_api.test_connection():
            print("❌ Не удалось подключиться к Planfix API")
            print("\n💡 Возможные причины:")
            print("• Нет интернет соединения")
            print("• Неверный API токен")
            print("• Неверный URL аккаунта")
            print("• Сервер Planfix недоступен")
            return False
        
        print("✅ Подключение к API успешно!")
        
        # Показываем настройки
        filter_id = planfix_config.get('filter_id')
        user_id = planfix_config.get('user_id')
        print(f"   Filter ID: {filter_id or 'НЕ ИСПОЛЬЗУЕТСЯ'}")
        print(f"   User ID: {user_id}")
        print(f"   Интервал проверки: {self.app_settings['check_interval']} сек")
        
        return True
    
    def _initialize_ui(self) -> bool:
        """Инициализирует компоненты интерфейса"""
        try:
            # Создаем менеджер Toast уведомлений
            self.toast_manager = ToastManager()
            
            # Устанавливаем callback функции
            self.toast_manager.on_open_task = self._handle_open_task
            self.toast_manager.on_close_notification = self._handle_close_notification
            
            print("✅ Менеджер уведомлений создан")
            
            # Создаем системный трей
            self.system_tray = SystemTray()
            
            # Устанавливаем callback функции для трея
            self.system_tray.on_check_now = self._handle_check_tasks_now
            self.system_tray.on_pause = self._handle_pause_monitoring
            self.system_tray.on_resume = self._handle_resume_monitoring
            self.system_tray.on_quit = self._handle_quit_application
            
            # Запускаем трей
            self.system_tray.start()
            print("✅ Системный трей создан")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания интерфейса: {e}")
            return False
    
    def run(self):
        """Запускает основной цикл приложения"""
        if not self.is_running:
            print("\n⏰ Запуск мониторинга задач...")
            print("🎉 Приложение готово к работе!")
            print("=" * 50)
            
            self.is_running = True
            
            # Запускаем мониторинг в отдельном потоке
            monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
            monitor_thread.start()
            
            # Запускаем GUI в главном потоке
            try:
                self.toast_manager.run()
            except KeyboardInterrupt:
                print("\n⏹️ Остановка по Ctrl+C")
            except Exception as e:
                print(f"\n❌ Критическая ошибка GUI: {e}")
            finally:
                self._shutdown()
    
    def _monitor_tasks(self):
        """Основной цикл мониторинга задач"""
        cleanup_counter = 0
        
        while self.is_running:
            try:
                # Проверяем не на паузе ли мы
                if self._check_pause_status():
                    time.sleep(60)  # Ждем минуту и проверяем снова
                    continue
                
                # Очищаем закрытые окна и старые записи
                if cleanup_counter >= 10:
                    task_tracker.cleanup_old_tasks()
                    cleanup_counter = 0
                
                # Получаем задачи
                tasks = self.planfix_api.get_filtered_tasks()
                if not tasks:
                    print("ℹ️ Задач не найдено или ошибка получения")
                    time.sleep(self.app_settings['check_interval'])
                    continue
                
                # Категоризируем задачи
                categorized_tasks = TaskProcessor.categorize_tasks(tasks)
                
                # Обновляем статистику
                self._update_statistics(tasks, categorized_tasks)
                
                # Показываем уведомления
                self._show_notifications(categorized_tasks)
                
                # Обновляем время последней проверки
                self.last_check_time = datetime.datetime.now()
                
                cleanup_counter += 1
                time.sleep(self.app_settings['check_interval'])
                
            except Exception as e:
                print(f"❌ Ошибка в мониторинге: {e}")
                time.sleep(30)  # Ждем 30 секунд при ошибке
    
    def _check_pause_status(self) -> bool:
        """Проверяет состояние паузы"""
        if not self.is_paused:
            return False
        
        # Если время паузы истекло
        if self.pause_until and datetime.datetime.now() >= self.pause_until:
            self._handle_resume_monitoring()
            return False
        
        return True
    
    def _update_statistics(self, tasks: list, categorized_tasks: dict):
        """Обновляет статистику"""
        self.current_stats = {
            'total': len(tasks),
            'overdue': len(categorized_tasks.get('overdue', [])),
            'urgent': len(categorized_tasks.get('urgent', []))
        }
        
        # Обновляем статистику в трее
        if self.system_tray:
            self.system_tray.update_stats(
                self.current_stats['total'],
                self.current_stats['overdue'],
                self.current_stats['urgent']
            )
        
        print(f"📊 Найдено задач: {self.current_stats['total']} "
              f"(просрочено: {self.current_stats['overdue']}, "
              f"срочно: {self.current_stats['urgent']})")
    
    def _show_notifications(self, categorized_tasks: dict):
        """Показывает уведомления для задач"""
        new_notifications = 0
        
        for category, tasks_list in categorized_tasks.items():
            # Проверяем включены ли уведомления для этой категории
            if not self.app_settings['notifications'].get(category, True):
                continue
            
            for task in tasks_list:
                task_id = str(task.get('id'))
                
                # Проверяем нужно ли показывать уведомление
                should_show = task_tracker.should_show_notification(
                    task_id,
                    category,
                    self.app_settings['max_total_windows'],
                    self.app_settings['max_windows_per_category']
                )
                
                if should_show:
                    # Форматируем сообщение
                    title, message = TaskProcessor.format_task_message(task, category)
                    
                    # Показываем уведомление
                    self.toast_manager.show_notification(title, message, category, task_id)
                    
                    # Регистрируем показ
                    task_tracker.register_notification_shown(task_id, category)
                    
                    new_notifications += 1
                    print(f"📬 Показано уведомление: {category} - {task.get('name', 'Без названия')}")
                    
                    # Небольшая пауза между уведомлениями
                    time.sleep(1)
        
        if new_notifications == 0:
            print("📭 Новых уведомлений нет")
    
    # ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
    
    def _handle_open_task(self, task_id: str):
        """Обработчик открытия задачи"""
        try:
            planfix_config = self.config_manager.get_planfix_config()
            account_url = planfix_config['account_url'].replace('/rest', '')
            task_url = f"{account_url}/task/{task_id}/"
            webbrowser.open(task_url)
            print(f"🌐 Открыта задача #{task_id}")
        except Exception as e:
            print(f"❌ Ошибка открытия задачи: {e}")
            # Резервный URL
            webbrowser.open(f"https://planfix.com/task/{task_id}/")
    
    def _handle_close_notification(self, task_id: str, reason: str):
        """Обработчик закрытия уведомления"""
        task_tracker.register_notification_closed(task_id, reason)
        print(f"❌ Закрыто уведомление #{task_id}, причина: {reason}")
    
    def _handle_check_tasks_now(self):
        """Обработчик принудительной проверки задач"""
        print("🔄 Принудительная проверка задач...")
        
        try:
            tasks = self.planfix_api.get_filtered_tasks()
            categorized_tasks = TaskProcessor.categorize_tasks(tasks)
            
            # Обновляем статистику
            self._update_statistics(tasks, categorized_tasks)
            
            # Показываем уведомления
            new_notifications = 0
            for category, tasks_list in categorized_tasks.items():
                if not self.app_settings['notifications'].get(category, True):
                    continue
                
                for task in tasks_list:
                    task_id = str(task.get('id'))
                    
                    # Принудительно разрешаем показ
                    task_tracker.force_show_task(task_id)
                    
                    title, message = TaskProcessor.format_task_message(task, category)
                    self.toast_manager.show_notification(title, message, category, task_id)
                    task_tracker.register_notification_shown(task_id, category)
                    
                    new_notifications += 1
                    time.sleep(0.5)
            
            print(f"✅ Принудительная проверка завершена: {new_notifications} уведомлений")
            
        except Exception as e:
            print(f"❌ Ошибка принудительной проверки: {e}")
    
    def _handle_pause_monitoring(self, minutes: int):
        """Обработчик паузы мониторинга"""
        self.is_paused = True
        self.pause_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        if self.system_tray:
            self.system_tray.set_paused(True, self.pause_until)
        
        print(f"⏸️ Мониторинг приостановлен на {minutes} минут")
    
    def _handle_resume_monitoring(self):
        """Обработчик возобновления мониторинга"""
        self.is_paused = False
        self.pause_until = None
        
        if self.system_tray:
            self.system_tray.set_paused(False)
        
        print("▶️ Мониторинг возобновлен")
    
    def _handle_quit_application(self):
        """Обработчик выхода из приложения"""
        print("👋 Завершение работы приложения...")
        self._shutdown()
    
    def _shutdown(self):
        """Завершает работу приложения"""
        self.is_running = False
        
        if self.system_tray:
            self.system_tray.stop()
        
        if self.toast_manager:
            self.toast_manager.stop()
        
        print("🔄 Приложение завершено")
        sys.exit(0)

def main():
    """Точка входа в приложение"""
    try:
        # Создаем и инициализируем приложение
        app = PlanfixReminderApp()
        
        if app.initialize():
            # Запускаем приложение
            app.run()
        else:
            print("\n❌ Не удалось инициализировать приложение")
            input("Нажмите Enter для выхода...")
            
    except KeyboardInterrupt:
        print("\n👋 Выход по Ctrl+C")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

if __name__ == "__main__":
    main()