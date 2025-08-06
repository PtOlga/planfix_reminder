#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для отладки и логирования
Позволяют включать/выключать подробные логи через конфигурацию
"""

import sys
import datetime
from typing import Any

class DebugLogger:
    """Класс для условного логирования"""
    
    def __init__(self):
        self.debug_enabled = False
        self.app_name = "Planfix Reminder"
    
    def set_debug_mode(self, enabled: bool):
        """Устанавливает режим отладки"""
        self.debug_enabled = enabled
        if enabled:
            self.info("🐛 Режим отладки включен")
        
    def _get_timestamp(self) -> str:
        """Возвращает текущее время в формате для логов"""
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def _format_message(self, level: str, *args) -> str:
        """Форматирует сообщение для вывода"""
        timestamp = self._get_timestamp()
        message = " ".join(str(arg) for arg in args)
        return f"[{timestamp}] {level} {message}"
    
    def debug(self, *args, **kwargs):
        """Отладочные сообщения - показываются только в debug режиме"""
        if self.debug_enabled:
            print(self._format_message("🔍", *args), **kwargs)
    
    def info(self, *args, **kwargs):
        """Информационные сообщения - показываются только в debug режиме"""
        if self.debug_enabled:
            print(self._format_message("ℹ️", *args), **kwargs)
    
    def success(self, *args, **kwargs):
        """Сообщения об успехе - показываются только в debug режиме"""
        if self.debug_enabled:
            print(self._format_message("✅", *args), **kwargs)
    
    def warning(self, *args, **kwargs):
        """Предупреждения - показываются всегда"""
        print(self._format_message("⚠️", *args), **kwargs)
    
    def error(self, *args, **kwargs):
        """Ошибки - показываются всегда"""
        print(self._format_message("❌", *args), **kwargs, file=sys.stderr)
    
    def critical(self, *args, **kwargs):
        """Критические ошибки - показываются всегда"""
        print(self._format_message("💥", *args), **kwargs, file=sys.stderr)
    
    def startup(self, *args, **kwargs):
        """Сообщения запуска - показываются всегда"""
        print(self._format_message("🚀", *args), **kwargs)
    
    def user_action(self, *args, **kwargs):
        """Действия пользователя - показываются всегда"""
        print(self._format_message("👤", *args), **kwargs)
    
    def separator(self, char: str = "=", length: int = 50):
        """Разделитель - только в debug режиме"""
        if self.debug_enabled:
            print(char * length)
    
    def header(self, text: str, char: str = "="):
        """Заголовок секции - только в debug режиме"""
        if self.debug_enabled:
            self.separator(char)
            print(f" {text} ".center(50, char))
            self.separator(char)

# Глобальный экземпляр логгера
logger = DebugLogger()

# Удобные функции для импорта
def set_debug_mode(enabled: bool):
    """Устанавливает режим отладки"""
    logger.set_debug_mode(enabled)

def debug(*args, **kwargs):
    """Отладочные сообщения"""
    logger.debug(*args, **kwargs)

def info(*args, **kwargs):
    """Информационные сообщения"""
    logger.info(*args, **kwargs)

def success(*args, **kwargs):
    """Сообщения об успехе"""
    logger.success(*args, **kwargs)

def warning(*args, **kwargs):
    """Предупреждения"""
    logger.warning(*args, **kwargs)

def error(*args, **kwargs):
    """Ошибки"""
    logger.error(*args, **kwargs)

def critical(*args, **kwargs):
    """Критические ошибки"""
    logger.critical(*args, **kwargs)

def startup(*args, **kwargs):
    """Сообщения запуска"""
    logger.startup(*args, **kwargs)

def user_action(*args, **kwargs):
    """Действия пользователя"""
    logger.user_action(*args, **kwargs)

def separator(char: str = "=", length: int = 50):
    """Разделитель"""
    logger.separator(char, length)

def header(text: str, char: str = "="):
    """Заголовок секции"""
    logger.header(text, char)

# Функции для специфичных категорий логов
def api_log(*args, **kwargs):
    """Логи API операций"""
    logger.debug("🌐 API:", *args, **kwargs)

def config_log(*args, **kwargs):
    """Логи конфигурации"""
    logger.debug("⚙️ CONFIG:", *args, **kwargs)

def ui_log(*args, **kwargs):
    """Логи интерфейса"""
    logger.debug("🎨 UI:", *args, **kwargs)

def task_log(*args, **kwargs):
    """Логи обработки задач"""
    logger.debug("📋 TASKS:", *args, **kwargs)

def notification_log(*args, **kwargs):
    """Логи уведомлений"""
    logger.debug("🔔 NOTIFY:", *args, **kwargs)

# Тестирование модуля
if __name__ == "__main__":
    print("🧪 Тестирование системы логирования")
    
    print("\n--- Режим без отладки ---")
    set_debug_mode(False)
    
    debug("Это отладочное сообщение (не должно показываться)")
    info("Это информационное сообщение (не должно показываться)")
    success("Это сообщение об успехе (не должно показываться)")
    warning("Это предупреждение (должно показываться)")
    error("Это ошибка (должна показываться)")
    
    print("\n--- Режим с отладкой ---")
    set_debug_mode(True)
    
    header("Тестирование всех типов сообщений")
    debug("Это отладочное сообщение")
    info("Это информационное сообщение")  
    success("Это сообщение об успехе")
    warning("Это предупреждение")
    error("Это ошибка")
    critical("Это критическая ошибка")
    startup("Это сообщение запуска")
    user_action("Это действие пользователя")
    
    separator()
    
    # Тестирование специфичных логов
    api_log("Подключение к API")
    config_log("Загрузка конфигурации")
    ui_log("Создание интерфейса")
    task_log("Обработка задач")
    notification_log("Показ уведомления")
    
    print("\n✅ Тестирование завершено")