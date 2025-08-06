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

# Импортируем систему файлового логирования
from file_logger import (
    setup_logging, debug, info, success, warning, error, critical, 
    startup, user_action, config_event, api_request, api_response, 
    api_error, get_logs_directory
)

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
        startup("Запуск Planfix Reminder (модульная версия)")
        
        # 1. Загружаем конфигурацию
        info("Начало инициализации приложения", "INIT")
        if not self._load_configuration():
            return False
        
        # 2. Инициализируем API
        info("Инициализация Planfix API", "INIT")
        if not self._initialize_api():
            return False
        
        # 3. Создаем UI компоненты
        info("Создание интерфейса", "INIT")
        if not self._initialize_ui():
            return False
        
        # 4. Логируем информацию о системе
        self._log_system_info()
        
        success("Инициализация завершена успешно", "INIT")
        return True
    
    def _load_configuration(self) -> bool:
        """Загружает конфигурацию"""
        config_event("Начало загрузки конфигурации")
        
        if not self.config_manager.load_config(show_diagnostics=True):
            critical("КРИТИЧЕСКАЯ ОШИБКА: Не удалось загрузить конфигурацию!", "CONFIG")
            
            # Предлагаем создать пример конфига
            try:
                choice = input("\nСоздать пример config.ini? (y/n): ").lower().strip()
                if choice in ['y', 'yes', 'да', 'д', '']:
                    if self.config_manager.create_sample_config():
                        success("Пример config.ini создан!", "CONFIG")
                        warning("Отредактируйте его и перезапустите программу")
                        info(f"Логи приложения сохраняются в: {get_logs_directory()}")
                    else:
                        error("Не удалось создать пример конфигурации", "CONFIG")
            except (KeyboardInterrupt, EOFError):
                config_event("Пользователь отменил создание примера конфигурации")
            
            return False
        
        # Получаем настройки
        try:
            self.app_settings = self.config_manager.get_app_settings()
            config_event(f"Настройки приложения загружены: интервал={self.app_settings['check_interval']}с")
            success("Конфигурация загружена успешно", "CONFIG")
            return True
        except Exception as e:
            error(f"Ошибка получения настроек приложения: {e}", "CONFIG", exc_info=True)
            return False
    
    def _initialize_api(self) -> bool:
        """Инициализирует API клиент"""
        try:
            planfix_config = self.config_manager.get_planfix_config()
            role_settings = self.config_manager.get_role_settings()
            
            info(f"Создание API клиента для {planfix_config['account_url']}", "API")
            self.planfix_api = PlanfixAPI(planfix_config, role_settings)
            
            # Тестируем соединение
            info("Проверка подключения к API", "API")
            if not self.planfix_api.test_connection():
                error("Не удалось подключиться к Planfix API", "API")
                warning("Возможные причины:")
                warning("• Нет интернет соединения")
                warning("• Неверный API токен")
                warning("• Неверный URL аккаунта")
                warning("• Сервер Planfix недоступен")
                return False
            
            success("Подключение к API успешно!", "API")
            
            # Логируем настройки API в debug режиме
            filter_id = planfix_config.get('filter_id')
            user_id = planfix_config.get('user_id')
            debug(f"API настройки - Filter ID: {filter_id or 'НЕ ИСПОЛЬЗУЕТСЯ'}, User ID: {user_id}", "API")
            debug(f"Интервал проверки: {self.app_settings['check_interval']} сек", "API")
            
            return True
            
        except Exception as e:
            error(f"Ошибка инициализации API: {e}", "API", exc_info=True)
            return False
    
    def _initialize_ui(self) -> bool:
        """Инициализирует компоненты интерфейса"""
        try:
            # Создаем менеджер Toast уведомлений
            info("Создание менеджера уведомлений", "UI")
            self.toast_manager = ToastManager()
            
            # Устанавливаем callback функции
            self.toast_manager.on_open_task = self._handle_open_task
            self.toast_manager.on_close_notification = self._handle_close_notification
            
            success("Менеджер уведомлений создан", "UI")
            
            # Создаем системный трей
            info("Создание системного трея", "UI")
            self.system_tray = SystemTray()
            
            # Устанавливаем callback функции для трея
            self.system_tray.on_check_now = self._handle_check_tasks_now
            self.system_tray.on_pause = self._handle_pause_monitoring
            self.system_tray.on_resume = self._handle_resume_monitoring
            self.system_tray.on_quit = self._handle_quit_application
            
            # Запускаем трей
            self.system_tray.start()
            success("Системный трей создан", "UI")
            
            return True
            
        except Exception as e:
            error(f"Ошибка создания интерфейса: {e}", "UI", exc_info=True)
            return False
    
    def _log_system_info(self):
        """Логирует информацию о системе"""
        try:
            import platform
            
            info("=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===", "SYSTEM")
            info(f"ОС: {platform.system()} {platform.release()}", "SYSTEM")
            info(f"Python: {sys.version.split()[0]}", "SYSTEM")
            info(f"Архитектура: {platform.architecture()[0]}", "SYSTEM")
            info(f"Машина: {platform.machine()}", "SYSTEM")
            info(f"Процессор: {platform.processor()}", "SYSTEM")
            info(f"Логи сохраняются в: {get_logs_directory()}", "SYSTEM")
            info("================================", "SYSTEM")
            
        except Exception as e:
            warning(f"Не удалось получить системную информацию: {e}", "SYSTEM")
    
    def run(self):
        """Запускает основной цикл приложения"""
        if not self.is_running:
            info("Запуск мониторинга задач", "APP")
            startup("Приложение готово к работе!")
            
            self.is_running = True
            
            # Запускаем мониторинг в отдельном потоке
            monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
            monitor_thread.start()
            info("Поток мониторинга задач запущен", "APP")
            
            # Запускаем GUI в главном потоке
            try:
                info("Запуск GUI цикла", "APP")
                self.toast_manager.run()
            except KeyboardInterrupt:
                warning("Остановка по Ctrl+C", "APP")
            except Exception as e:
                critical(f"Критическая ошибка GUI: {e}", "APP", exc_info=True)
            finally:
                self._shutdown()
    
    def _monitor_tasks(self):
        """Основной цикл мониторинга задач"""
        cleanup_counter = 0
        info("Цикл мониторинга задач запущен", "MONITOR")
        
        while self.is_running:
            try:
                # Проверяем не на паузе ли мы
                if self._check_pause_status():
                    debug("Мониторинг на паузе, ожидание 60 секунд", "MONITOR")
                    time.sleep(60)
                    continue
                
                # Очищаем закрытые окна и старые записи
                if cleanup_counter >= 10:
                    debug("Выполнение очистки старых задач", "MONITOR")
                    task_tracker.cleanup_old_tasks()
                    cleanup_counter = 0
                
                # Получаем задачи
                debug("Получение задач из API", "MONITOR")
                tasks = self.planfix_api.get_filtered_tasks()
                
                if not tasks:
                    debug("Задач не найдено или ошибка получения", "MONITOR")
                    time.sleep(self.app_settings['check_interval'])
                    continue
                
                # Категоризируем задачи
                debug(f"Категоризация {len(tasks)} задач", "MONITOR")
                categorized_tasks = TaskProcessor.categorize_tasks(tasks)
                
                # Обновляем статистику
                self._update_statistics(tasks, categorized_tasks)
                
                # Показываем уведомления
                self._show_notifications(categorized_tasks)
                
                # Обновляем время последней проверки
                self.last_check_time = datetime.datetime.now()
                debug(f"Проверка завершена в {self.last_check_time.strftime('%H:%M:%S')}", "MONITOR")
                
                cleanup_counter += 1
                time.sleep(self.app_settings['check_interval'])
                
            except Exception as e:
                error(f"Ошибка в мониторинге: {e}", "MONITOR", exc_info=True)
                warning("Ожидание 30 секунд перед повторной попыткой", "MONITOR")
                time.sleep(30)
    
    def _check_pause_status(self) -> bool:
        """Проверяет состояние паузы"""
        if not self.is_paused:
            return False
        
        # Если время паузы истекло
        if self.pause_until and datetime.datetime.now() >= self.pause_until:
            info("Время паузы истекло, возобновление мониторинга", "MONITOR")
            self._handle_resume_monitoring()
            return False
        
        return True
    
    def _update_statistics(self, tasks: list, categorized_tasks: dict):
        """Обновляет статистику"""
        old_stats = self.current_stats.copy()
        
        self.current_stats = {
            'total': len(tasks),
            'overdue': len(categorized_tasks.get('overdue', [])),
            'urgent': len(categorized_tasks.get('urgent', []))
        }
        
        # Логируем изменения в статистике
        if old_stats != self.current_stats:
            info(f"Статистика обновлена: всего={self.current_stats['total']}, "
                f"просрочено={self.current_stats['overdue']}, "
                f"срочно={self.current_stats['urgent']}", "STATS")
        else:
            debug(f"Статистика без изменений: {self.current_stats}", "STATS")
        
        # Обновляем статистику в трее
        if self.system_tray:
            self.system_tray.update_stats(
                self.current_stats['total'],
                self.current_stats['overdue'],
                self.current_stats['urgent']
            )
    
    def _show_notifications(self, categorized_tasks: dict):
        """Показывает уведомления для задач"""
        new_notifications = 0
        
        for category, tasks_list in categorized_tasks.items():
            # Проверяем включены ли уведомления для этой категории
            if not self.app_settings['notifications'].get(category, True):
                debug(f"Уведомления для категории {category} отключены", "NOTIFY")
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
                    info(f"Показано уведомление: {category} - задача #{task_id}: {task.get('name', 'Без названия')}", "NOTIFY")
                    
                    # Небольшая пауза между уведомлениями
                    time.sleep(1)
                else:
                    debug(f"Уведомление для задачи #{task_id} пропущено (лимиты или уже показано)", "NOTIFY")
        
        if new_notifications == 0:
            debug("Новых уведомлений нет", "NOTIFY")
        else:
            info(f"Показано новых уведомлений: {new_notifications}", "NOTIFY")
    
    # ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
    
    def _handle_open_task(self, task_id: str):
        """Обработчик открытия задачи"""
        try:
            planfix_config = self.config_manager.get_planfix_config()
            account_url = planfix_config['account_url'].replace('/rest', '')
            task_url = f"{account_url}/task/{task_id}/"
            
            debug(f"Открытие задачи в браузере: {task_url}", "USER")
            webbrowser.open(task_url)
            user_action(f"Открыта задача #{task_id}")
            
        except Exception as e:
            error(f"Ошибка открытия задачи #{task_id}: {e}", "USER", exc_info=True)
            
            # Резервный URL
            try:
                backup_url = f"https://planfix.com/task/{task_id}/"
                warning(f"Попытка открытия через резервный URL: {backup_url}", "USER")
                webbrowser.open(backup_url)
                user_action(f"Открыта задача #{task_id} (резервный URL)")
            except Exception as backup_e:
                error(f"Резервный URL также не сработал: {backup_e}", "USER")
    
    def _handle_close_notification(self, task_id: str, reason: str):
        """Обработчик закрытия уведомления"""
        try:
            task_tracker.register_notification_closed(task_id, reason)
            info(f"Закрыто уведомление #{task_id}, причина: {reason}", "USER")
        except Exception as e:
            error(f"Ошибка при закрытии уведомления #{task_id}: {e}", "USER")
    
    def _handle_check_tasks_now(self):
        """Обработчик принудительной проверки задач"""
        user_action("Принудительная проверка задач запущена")
        
        try:
            info("Начало принудительной проверки задач", "FORCE_CHECK")
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
                    debug(f"Принудительный показ задачи #{task_id}", "FORCE_CHECK")
                    
                    title, message = TaskProcessor.format_task_message(task, category)
                    self.toast_manager.show_notification(title, message, category, task_id)
                    task_tracker.register_notification_shown(task_id, category)
                    
                    new_notifications += 1
                    time.sleep(0.5)
            
            success(f"Принудительная проверка завершена: {new_notifications} уведомлений", "FORCE_CHECK")
            user_action(f"Принудительная проверка завершена: показано {new_notifications} уведомлений")
            
        except Exception as e:
            error(f"Ошибка принудительной проверки: {e}", "FORCE_CHECK", exc_info=True)
    
    def _handle_pause_monitoring(self, minutes: int):
        """Обработчик паузы мониторинга"""
        self.is_paused = True
        self.pause_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        
        if self.system_tray:
            self.system_tray.set_paused(True, self.pause_until)
        
        info(f"Мониторинг приостановлен на {minutes} минут до {self.pause_until.strftime('%H:%M')}", "PAUSE")
        user_action(f"Мониторинг приостановлен на {minutes} минут")
    
    def _handle_resume_monitoring(self):
        """Обработчик возобновления мониторинга"""
        self.is_paused = False
        self.pause_until = None
        
        if self.system_tray:
            self.system_tray.set_paused(False)
        
        info("Мониторинг возобновлен", "PAUSE")
        user_action("Мониторинг возобновлен")
    
    def _handle_quit_application(self):
        """Обработчик выхода из приложения"""
        user_action("Завершение работы приложения")
        info("Начало процедуры завершения приложения", "SHUTDOWN")
        self._shutdown()
    
    def _shutdown(self):
        """Завершает работу приложения"""
        info("Выполнение завершения приложения", "SHUTDOWN")
        self.is_running = False
        
        try:
            if self.system_tray:
                info("Остановка системного трея", "SHUTDOWN")
                self.system_tray.stop()
            
            if self.toast_manager:
                info("Остановка менеджера уведомлений", "SHUTDOWN")
                self.toast_manager.stop()
            
            info("Приложение корректно завершено", "SHUTDOWN")
            
        except Exception as e:
            error(f"Ошибка при завершении приложения: {e}", "SHUTDOWN", exc_info=True)
        finally:
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
            critical("Не удалось инициализировать приложение", "MAIN")
            print(f"\n📁 Логи для диагностики сохранены в: {get_logs_directory()}")
            input("Нажмите Enter для выхода...")
            
    except KeyboardInterrupt:
        warning("Выход по Ctrl+C", "MAIN")
        sys.exit(0)
    except Exception as e:
        critical(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", "MAIN", exc_info=True)
        print(f"\n📁 Логи с деталями ошибки сохранены в: {get_logs_directory()}")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

if __name__ == "__main__":
    main()