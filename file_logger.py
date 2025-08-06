#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Система логирования в файлы для диагностики
Записывает логи в файлы для решения проблем пользователей
"""

import os
import sys
import logging
import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
import traceback

class FileLogger:
    """Класс для логирования в файлы с ротацией"""
    
    def __init__(self):
        self.debug_enabled = False
        self.console_debug = False
        self.logs_dir: Optional[Path] = None
        self.main_logger: Optional[logging.Logger] = None
        self.error_logger: Optional[logging.Logger] = None
        self.api_logger: Optional[logging.Logger] = None
        self.setup_complete = False
    
    def setup_logging(self, debug_mode: bool = False, console_debug: bool = False):
        """
        Настраивает систему логирования
        
        Args:
            debug_mode: Записывать подробные логи в файлы
            console_debug: Показывать отладочные сообщения в консоли
        """
        self.debug_enabled = debug_mode
        self.console_debug = console_debug
        
        try:
            # Создаем папку для логов
            self.logs_dir = self._create_logs_directory()
            
            # Настраиваем логгеры
            self._setup_main_logger()
            self._setup_error_logger()
            self._setup_api_logger()
            
            self.setup_complete = True
            
            if debug_mode:
                self.info("🐛 Режим отладки включен - подробные логи записываются в файлы")
            else:
                self.info("📝 Базовое логирование включено - только важные события")
            
            if console_debug:
                print(f"📁 Логи сохраняются в: {self.logs_dir}")
        except Exception as e:
            print(f"⚠️ Не удалось настроить файловое логирование: {e}")
            self.setup_complete = False
    
    def _create_logs_directory(self) -> Path:
        """Создает директорию для логов рядом с исполняемым файлом"""
        try:
            # Определяем путь к исполняемому файлу или скрипту
            if getattr(sys, 'frozen', False):
                # Если запущен как exe файл
                app_dir = Path(sys.executable).parent
            else:
                # Если запущен как Python скрипт
                app_dir = Path(__file__).parent

            # Создаем папку logs рядом с приложением
            logs_dir = app_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            return logs_dir

        except Exception as e:
            # Fallback: если не удалось создать рядом с приложением,
            # используем временную папку
            import tempfile
            logs_dir = Path(tempfile.gettempdir()) / "PlanfixReminder_logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            print(f"⚠️ Используется временная папка для логов: {logs_dir}")
            return logs_dir
    
    def _setup_main_logger(self):
        """Настраивает основной логгер"""
        self.main_logger = logging.getLogger('PlanfixReminder.Main')
        self.main_logger.setLevel(logging.DEBUG if self.debug_enabled else logging.INFO)
        
        # Очищаем существующие обработчики
        self.main_logger.handlers.clear()
        
        # Файл для основных логов с ротацией
        main_log_file = self.logs_dir / "planfix_reminder.log"
        main_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Формат для основных логов
        main_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        main_handler.setFormatter(main_formatter)
        self.main_logger.addHandler(main_handler)
        
        # Консольный вывод только в режиме отладки консоли
        if self.console_debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(main_formatter)
            self.main_logger.addHandler(console_handler)
    
    def _setup_error_logger(self):
        """Настраивает логгер для ошибок"""
        self.error_logger = logging.getLogger('PlanfixReminder.Errors')
        self.error_logger.setLevel(logging.WARNING)
        
        # Очищаем существующие обработчики
        self.error_logger.handlers.clear()
        
        # Отдельный файл для ошибок
        error_log_file = self.logs_dir / "errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=2*1024*1024,  # 2 MB
            backupCount=3,
            encoding='utf-8'
        )
        
        # Подробный формат для ошибок
        error_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
    
    def _setup_api_logger(self):
        """Настраивает логгер для API операций"""
        self.api_logger = logging.getLogger('PlanfixReminder.API')
        self.api_logger.setLevel(logging.DEBUG if self.debug_enabled else logging.INFO)
        
        # Очищаем существующие обработчики
        self.api_logger.handlers.clear()
        
        # Отдельный файл для API логов
        api_log_file = self.logs_dir / "api_operations.log"
        api_handler = RotatingFileHandler(
            api_log_file,
            maxBytes=3*1024*1024,  # 3 MB
            backupCount=3,
            encoding='utf-8'
        )
        
        # Формат для API логов
        api_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        api_handler.setFormatter(api_formatter)
        self.api_logger.addHandler(api_handler)
    
    def _log_to_console_if_needed(self, level: str, message: str):
        """Выводит в консоль если это важное сообщение"""
        if self.console_debug:
            return  # Консольный вывод уже настроен через handler
        
        # Показываем в консоли только критичные сообщения
        if level in ['ERROR', 'CRITICAL', 'STARTUP', 'USER_ACTION', 'WARNING']:
            print(message)
    
    # ===== ОСНОВНЫЕ МЕТОДЫ ЛОГИРОВАНИЯ =====
    
    def debug(self, message: str, category: str = "DEBUG"):
        """Отладочные сообщения - только в файлы при debug_mode=True"""
        if not self.setup_complete:
            return
        
        if self.debug_enabled:
            self.main_logger.debug(f"{category} | {message}")
    
    def info(self, message: str, category: str = "INFO"):
        """Информационные сообщения"""
        if not self.setup_complete:
            return
        
        self.main_logger.info(f"{category} | {message}")
    
    def success(self, message: str, category: str = "SUCCESS"):
        """Сообщения об успехе"""
        if not self.setup_complete:
            return
        
        self.main_logger.info(f"{category} | {message}")
    
    def warning(self, message: str, category: str = "WARNING"):
        """Предупреждения - всегда записываются и показываются"""
        full_message = f"⚠️ {message}"
        
        if not self.setup_complete:
            print(full_message)
            return
        
        self.main_logger.warning(f"{category} | {message}")
        self.error_logger.warning(f"{category} | {message}")
        self._log_to_console_if_needed("WARNING", full_message)
    
    def error(self, message: str, category: str = "ERROR", exc_info: bool = False):
        """Ошибки - всегда записываются и показываются"""
        full_message = f"❌ {message}"
        
        if not self.setup_complete:
            print(full_message)
            return
        
        log_message = f"{category} | {message}"
        
        self.main_logger.error(log_message, exc_info=exc_info)
        self.error_logger.error(log_message, exc_info=exc_info)
        self._log_to_console_if_needed("ERROR", full_message)
    
    def critical(self, message: str, category: str = "CRITICAL", exc_info: bool = False):
        """Критические ошибки - всегда записываются и показываются"""
        full_message = f"💥 {message}"
        
        if not self.setup_complete:
            print(full_message)
            return
        
        log_message = f"{category} | {message}"
        
        self.main_logger.critical(log_message, exc_info=exc_info)
        self.error_logger.critical(log_message, exc_info=exc_info)
        self._log_to_console_if_needed("CRITICAL", full_message)
    
    def startup(self, message: str):
        """Сообщения запуска - всегда показываются"""
        full_message = f"🚀 {message}"
        
        if not self.setup_complete:
            print(full_message)
            return
        
        self.main_logger.info(f"STARTUP | {message}")
        self._log_to_console_if_needed("STARTUP", full_message)
    
    def user_action(self, message: str):
        """Действия пользователя - всегда записываются"""
        full_message = f"👤 {message}"
        
        if not self.setup_complete:
            print(full_message)
            return
        
        self.main_logger.info(f"USER_ACTION | {message}")
        self._log_to_console_if_needed("USER_ACTION", full_message)
    
    def config_event(self, message: str):
        """События конфигурации"""
        self.debug(message, "CONFIG")
    
    def api_request(self, method: str, url: str, status_code: int = None):
        """Логирование API запросов"""
        if not self.setup_complete:
            return
        
        if status_code:
            message = f"REQUEST | {method} {url} -> {status_code}"
        else:
            message = f"REQUEST | {method} {url}"
        
        if self.debug_enabled and self.api_logger:
            self.api_logger.debug(message)
    
    def api_response(self, message: str, data_size: int = None):
        """Логирование API ответов"""
        if not self.setup_complete:
            return
        
        if data_size:
            full_message = f"RESPONSE | {message} ({data_size} bytes)"
        else:
            full_message = f"RESPONSE | {message}"
        
        if self.debug_enabled and self.api_logger:
            self.api_logger.debug(full_message)
    
    def api_error(self, message: str, exc: Exception = None):
        """Логирование ошибок API"""
        if not self.setup_complete:
            print(f"❌ API Error: {message}")
            return
        
        if self.api_logger:
            self.api_logger.error(f"API_ERROR | {message}")
            if exc:
                self.api_logger.error(f"API_ERROR | Exception: {exc}")
                self.error_logger.error(f"API_ERROR | {message}: {exc}", exc_info=True)
    
    def get_logs_directory(self) -> Path:
        """Возвращает путь к директории логов"""
        return self.logs_dir if self.logs_dir else Path(".")

# Глобальный экземпляр логгера
file_logger = FileLogger()

# Удобные функции для импорта
def setup_logging(debug_mode: bool = False, console_debug: bool = False):
    """Настраивает систему логирования"""
    file_logger.setup_logging(debug_mode, console_debug)

def debug(message: str, category: str = "DEBUG"):
    """Отладочные сообщения"""
    file_logger.debug(message, category)

def info(message: str, category: str = "INFO"):
    """Информационные сообщения"""
    file_logger.info(message, category)

def success(message: str, category: str = "SUCCESS"):
    """Сообщения об успехе"""
    file_logger.success(message, category)

def warning(message: str, category: str = "WARNING"):
    """Предупреждения"""
    file_logger.warning(message, category)

def error(message: str, category: str = "ERROR", exc_info: bool = False):
    """Ошибки"""
    file_logger.error(message, category, exc_info)

def critical(message: str, category: str = "CRITICAL", exc_info: bool = False):
    """Критические ошибки"""
    file_logger.critical(message, category, exc_info)

def startup(message: str):
    """Сообщения запуска"""
    file_logger.startup(message)

def user_action(message: str):
    """Действия пользователя"""
    file_logger.user_action(message)

def config_event(message: str):
    """События конфигурации"""
    file_logger.config_event(message)

def api_request(method: str, url: str, status_code: int = None):
    file_logger.api_request(method, url, status_code)

def api_response(message: str, data_size: int = None):
    file_logger.api_response(message, data_size)

def api_error(message: str, exc: Exception = None):
    file_logger.api_error(message, exc)

def log_config_summary(config_dict: dict):
    """Записывает сводку конфигурации (без секретных данных)"""
    if not file_logger.debug_enabled:
        return
    
    debug("=== CONFIG SUMMARY ===", "CONFIG")
    for section, settings in config_dict.items():
        debug(f"[{section}]", "CONFIG")
        for key, value in settings.items():
            # Маскируем секретные данные
            if 'token' in key.lower() or 'password' in key.lower():
                if isinstance(value, str) and len(value) > 8:
                    masked_value = f"{value[:4]}...{value[-4:]}"
                else:
                    masked_value = "***"
                debug(f"  {key} = {masked_value}", "CONFIG")
            else:
                debug(f"  {key} = {value}", "CONFIG")
    debug("=====================", "CONFIG")

def get_logs_directory() -> Path:
    return file_logger.get_logs_directory()

if __name__ == "__main__":
    print("🧪 Тестирование системы файлового логирования")
    
    setup_logging(debug_mode=True, console_debug=True)
    
    startup("Тестовое приложение запущено")
    info("Информационное сообщение")
    debug("Отладочное сообщение")
    success("Операция успешна")
    warning("Предупреждение")
    error("Тестовая ошибка")
    critical("Критическая тестовая ошибка")
    user_action("Пользователь нажал кнопку")
    
    print(f"\n📁 Логи сохранены в: {get_logs_directory()}")
    print("✅ Тестирование файлового логирования завершено!")