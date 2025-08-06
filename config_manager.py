#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления конфигурацией
Загружает и валидирует настройки из config.ini
"""

import os
import configparser
from typing import Dict, Any, Optional

# Импортируем систему файлового логирования
try:
    from file_logger import (
        setup_logging, debug, info, success, warning, error, critical,
        config_event, log_config_summary
    )
except ImportError:
    # Если модуль логирования не найден, используем простые print
    def setup_logging(debug_mode=False, console_debug=False): pass
    def debug(message, category="DEBUG"): pass
    def info(message, category="INFO"): 
        if category in ["INFO", "SUCCESS"]: print(f"ℹ️ {message}")
    def success(message, category="SUCCESS"): print(f"✅ {message}")
    def warning(message, category="WARNING"): print(f"⚠️ {message}")
    def error(message, category="ERROR", exc_info=False): print(f"❌ {message}")
    def critical(message, category="CRITICAL", exc_info=False): print(f"💥 {message}")
    def config_event(message): pass
    def log_config_summary(config_dict): pass

class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.is_loaded = False
        
        # Настройки по умолчанию
        self.defaults = {
            'Planfix': {
                'user_id': '1',
                'filter_id': ''
            },
            'Settings': {
                'check_interval': '300',
                'notify_current': 'true',
                'notify_urgent': 'true', 
                'notify_overdue': 'true',
                'max_windows_per_category': '5',
                'max_total_windows': '10',
                'debug_mode': 'false'
            },
            'Roles': {
                'include_assignee': 'true',
                'include_assigner': 'true',
                'include_auditor': 'true'
            }
        }
    
    def load_config(self, show_diagnostics: bool = False) -> bool:
        """
        Загружает конфигурацию из файла
        
        Args:
            show_diagnostics: Показывать подробную диагностику в консоли
            
        Returns:
            bool: True если конфигурация загружена успешно
        """
        if show_diagnostics:
            print("📋 Загрузка конфигурации...")
        
        # Проверяем существование файла
        if not os.path.exists(self.config_file):
            error(f"Файл конфигурации не найден: {self.config_file}")
            return False
        
        try:
            self.config.read(self.config_file, encoding='utf-8')
            
            # Сначала загружаем debug_mode чтобы настроить логирование
            debug_mode = self._get_bool_setting('Settings', 'debug_mode', False)
            
            # Настраиваем систему логирования
            setup_logging(debug_mode=debug_mode, console_debug=show_diagnostics)
            
            config_event(f"Режим отладки: {'включен' if debug_mode else 'выключен'}")
            config_event(f"Консольная диагностика: {'включена' if show_diagnostics else 'выключена'}")
            
            # Применяем значения по умолчанию
            self._apply_defaults()
            
            # Валидируем конфигурацию
            if not self._validate_config():
                return False
            
            self.is_loaded = True
            
            # Логируем сводку конфигурации в файл
            if debug_mode:
                config_summary = {
                    'Planfix': dict(self.config['Planfix']),
                    'Settings': dict(self.config['Settings']),
                    'Roles': dict(self.config['Roles'])
                }
                log_config_summary(config_summary)
            
            if show_diagnostics:
                self._show_config_summary_console()
            
            success("Конфигурация успешно загружена")
            return True
            
        except Exception as e:
            critical(f"Ошибка загрузки конфигурации: {e}", exc_info=True)
            return False
    
    def _apply_defaults(self):
        """Применяет значения по умолчанию для отсутствующих параметров"""
        for section_name, section_defaults in self.defaults.items():
            if not self.config.has_section(section_name):
                self.config.add_section(section_name)
                config_event(f"Создана секция [{section_name}]")
            
            for key, default_value in section_defaults.items():
                if not self.config.has_option(section_name, key):
                    self.config.set(section_name, key, default_value)
                    config_event(f"Установлено значение по умолчанию: {section_name}.{key} = {default_value}")
    
    def _validate_config(self) -> bool:
        """Валидирует обязательные параметры конфигурации"""
        config_event("Начало валидации конфигурации")
        
        # Проверяем обязательные параметры
        required_settings = [
            ('Planfix', 'api_token', "API токен обязателен"),
            ('Planfix', 'account_url', "URL аккаунта обязателен")
        ]
        
        for section, key, error_msg in required_settings:
            value = self.config.get(section, key, fallback='').strip()
            if not value:
                error(f"Валидация не пройдена: {error_msg}")
                return False
            config_event(f"Проверен обязательный параметр: {section}.{key}")
        
        # Валидируем URL
        account_url = self.config.get('Planfix', 'account_url', fallback='')
        if not account_url.endswith('/rest'):
            error("Валидация URL: URL аккаунта должен заканчиваться на '/rest'")
            return False
        config_event(f"URL валиден: {account_url}")
        
        # Валидируем числовые параметры
        numeric_settings = [
            ('Planfix', 'user_id'),
            ('Settings', 'check_interval'),
            ('Settings', 'max_windows_per_category'),
            ('Settings', 'max_total_windows')
        ]
        
        for section, key in numeric_settings:
            try:
                value = int(self.config.get(section, key, fallback='0'))
                if value <= 0:
                    error(f"Валидация числовых параметров: {section}.{key} должен быть положительным числом")
                    return False
                config_event(f"Числовой параметр валиден: {section}.{key} = {value}")
            except ValueError:
                error(f"Валидация числовых параметров: {section}.{key} должен быть числом")
                return False
        
        config_event("Валидация конфигурации завершена успешно")
        return True
    
    def _show_config_summary_console(self):
        """Показывает сводку загруженной конфигурации в консоли"""
        print("\n📋 Сводка конфигурации:")
        print("=" * 50)
        
        # Planfix настройки (скрываем токен)
        api_token = self.config.get('Planfix', 'api_token', fallback='')
        masked_token = f"{api_token[:8]}...{api_token[-4:]}" if len(api_token) > 12 else "***"
        
        print(f"🌐 Planfix:")
        print(f"   API Token: {masked_token}")
        print(f"   Account URL: {self.config.get('Planfix', 'account_url', fallback='')}")
        print(f"   User ID: {self.config.get('Planfix', 'user_id', fallback='')}")
        print(f"   Filter ID: {self.config.get('Planfix', 'filter_id', fallback='НЕ ЗАДАН')}")
        
        print(f"\n⚙️ Настройки:")
        print(f"   Интервал проверки: {self.config.get('Settings', 'check_interval', fallback='')} сек")
        print(f"   Макс. окон на категорию: {self.config.get('Settings', 'max_windows_per_category', fallback='')}")
        print(f"   Макс. окон всего: {self.config.get('Settings', 'max_total_windows', fallback='')}")
        print(f"   Режим отладки: {self.config.get('Settings', 'debug_mode', fallback='')}")
        
        print(f"\n🔔 Уведомления:")
        print(f"   Текущие: {self.config.get('Settings', 'notify_current', fallback='')}")
        print(f"   Срочные: {self.config.get('Settings', 'notify_urgent', fallback='')}")
        print(f"   Просроченные: {self.config.get('Settings', 'notify_overdue', fallback='')}")
        
        print("=" * 50)
    
    def get_planfix_config(self) -> Dict[str, Any]:
        """Возвращает настройки Planfix"""
        if not self.is_loaded:
            error("Попытка получить настройки Planfix до загрузки конфигурации")
            raise RuntimeError("Конфигурация не загружена")
        
        config = {
            'api_token': self.config.get('Planfix', 'api_token'),
            'account_url': self.config.get('Planfix', 'account_url'),
            'user_id': self.config.getint('Planfix', 'user_id'),
            'filter_id': self.config.get('Planfix', 'filter_id') or None
        }
        
        config_event("Получены настройки Planfix")
        return config
    
    def get_app_settings(self) -> Dict[str, Any]:
        """Возвращает настройки приложения"""
        if not self.is_loaded:
            error("Попытка получить настройки приложения до загрузки конфигурации")
            raise RuntimeError("Конфигурация не загружена")
        
        settings = {
            'check_interval': self.config.getint('Settings', 'check_interval'),
            'max_windows_per_category': self.config.getint('Settings', 'max_windows_per_category'),
            'max_total_windows': self.config.getint('Settings', 'max_total_windows'),
            'debug_mode': self.config.getboolean('Settings', 'debug_mode'),
            'notifications': {
                'current': self.config.getboolean('Settings', 'notify_current'),
                'urgent': self.config.getboolean('Settings', 'notify_urgent'),
                'overdue': self.config.getboolean('Settings', 'notify_overdue')
            }
        }
        
        config_event("Получены настройки приложения")
        return settings
    
    def get_role_settings(self) -> Dict[str, bool]:
        """Возвращает настройки ролей"""
        if not self.is_loaded:
            error("Попытка получить настройки ролей до загрузки конфигурации")
            raise RuntimeError("Конфигурация не загружена")
        
        roles = {
            'include_assignee': self.config.getboolean('Roles', 'include_assignee'),
            'include_assigner': self.config.getboolean('Roles', 'include_assigner'),
            'include_auditor': self.config.getboolean('Roles', 'include_auditor')
        }
        
        config_event("Получены настройки ролей")
        return roles
    
    def _get_bool_setting(self, section: str, key: str, default: bool = False) -> bool:
        """Безопасно получает boolean настройку"""
        try:
            value = self.config.getboolean(section, key)
            debug(f"Получена boolean настройка: {section}.{key} = {value}")
            return value
        except Exception as e:
            warning(f"Ошибка получения boolean настройки {section}.{key}, используется значение по умолчанию: {default}")
            debug(f"Детали ошибки: {e}")
            return default
    
    def create_sample_config(self) -> bool:
        """Создает пример файла конфигурации"""
        config_event("Создание примера конфигурации")
        
        sample_content = """[Planfix]
# API токен Planfix (обязательно)
api_token = YOUR_API_TOKEN_HERE

# URL вашего аккаунта Planfix с /rest на конце (обязательно) 
account_url = https://your-account.planfix.com/rest

# ID готового фильтра задач (опционально)
filter_id = 

# ID пользователя (по умолчанию 1)
user_id = 1

[Settings]
# Интервал проверки задач в секундах (по умолчанию 300 = 5 минут)
check_interval = 300

# Включить уведомления для разных типов задач
notify_current = true
notify_urgent = true
notify_overdue = true

# Максимальное количество окон уведомлений
max_windows_per_category = 5
max_total_windows = 10

# Режим отладки - если true, записывает подробные логи в файлы
# Полезно для диагностики проблем
debug_mode = false

[Roles]
# Включать задачи где пользователь является исполнителем
include_assignee = true

# Включать задачи где пользователь является постановщиком
include_assigner = true

# Включать задачи где пользователь является контролером
include_auditor = true
"""
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            success(f"Создан пример конфигурации: {self.config_file}")
            config_event(f"Записан файл примера конфигурации: {os.path.abspath(self.config_file)}")
            return True
        except Exception as e:
            error(f"Не удалось создать пример конфигурации: {e}")
            return False

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_config_manager():
    """Тестирует загрузку конфигурации"""
    print("🧪 Тестирование ConfigManager с файловым логированием")
    print("=" * 60)
    
    manager = ConfigManager()
    
    # Тест 1: Загрузка несуществующего файла
    print("\nТест 1: Загрузка несуществующего файла")
    if not manager.load_config(show_diagnostics=True):
        print("✓ Корректно обработан отсутствующий файл")
    
    # Тест 2: Создание примера конфигурации
    print("\nТест 2: Создание примера конфигурации")
    if manager.create_sample_config():
        print("✓ Пример конфигурации создан")
        
        # Тест 3: Загрузка созданного примера
        print("\nТест 3: Загрузка созданного примера (должна быть ошибка валидации)")
        if manager.load_config(show_diagnostics=True):
            print("✗ Пример конфигурации содержит заглушки, должна быть ошибка валидации")
        else:
            print("✓ Корректно отклонена конфигурация с заглушками")
    
    from file_logger import get_logs_directory
    print(f"\n📁 Логи сохранены в: {get_logs_directory()}")
    print("✅ Тестирование завершено - проверьте файлы логов!")

if __name__ == "__main__":
    test_config_manager()