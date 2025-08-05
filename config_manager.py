#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления конфигурацией Planfix Reminder
Отвечает за загрузку, валидацию и предоставление настроек
"""

from pathlib import Path
import configparser
from typing import Dict, Any, Optional
import os

class ConfigManager:
    """Управление конфигурацией приложения"""
    
    def __init__(self):
        self.config_data = {
            'check_interval': 300,
            'max_windows_per_category': 5,
            'max_total_windows': 10,
            'notifications': {
                'current': True,
                'urgent': True,
                'overdue': True
            },
            'roles': {
                'include_assignee': True,
                'include_assigner': True,
                'include_auditor': True
            },
            'planfix': {
                'api_token': '',
                'account_url': '',
                'filter_id': None,
                'user_id': '1'
            }
        }
        self._config_loaded = False
        
    def load_config(self, show_diagnostics: bool = True) -> bool:
        """
        Загружает конфигурацию из файла config.ini
        
        Args:
            show_diagnostics: Показывать диагностику процесса загрузки
            
        Returns:
            bool: True если конфиг загружен успешно
        """
        if show_diagnostics:
            print("=== ДИАГНОСТИКА ПОИСКА КОНФИГА ===")
        
        config_file_path = self._find_config_file(show_diagnostics)
        if not config_file_path:
            return False
        
        success = self._parse_config_file(config_file_path, show_diagnostics)
        if success:
            self._config_loaded = True
            
        return success
    
    def _find_config_file(self, show_diagnostics: bool) -> Optional[Path]:
        """Ищет файл config.ini в разных местах"""
        script_dir = Path(__file__).parent.absolute()
        current_dir = Path.cwd()
        
        if show_diagnostics:
            print(f"Текущая рабочая директория: {current_dir}")
            print(f"Директория скрипта: {script_dir}")
            print()
        
        # Возможные пути к конфигу (в порядке приоритета)
        config_paths = [
            current_dir / 'config.ini',
            script_dir / 'config.ini',
            Path('config.ini'),
        ]
        
        # Ищем конфиг в разных местах
        for i, path in enumerate(config_paths, 1):
            if show_diagnostics:
                print(f"🔍 Путь {i}: {path}")
                print(f"   Абсолютный: {path.absolute()}")
                print(f"   Существует: {path.exists()}")
            
            if path.exists():
                try:
                    size = path.stat().st_size
                    if show_diagnostics:
                        print(f"   ✅ Размер: {size} байт")
                    return path
                except Exception as e:
                    if show_diagnostics:
                        print(f"   ❌ Ошибка доступа: {e}")
            else:
                if show_diagnostics:
                    print(f"   ❌ Файл не найден")
            
            if show_diagnostics:
                print()
        
        # Файл не найден - показываем диагностику
        if show_diagnostics:
            print("🚨 ФАЙЛ CONFIG.INI НЕ НАЙДЕН!")
            self._show_directory_contents(current_dir, script_dir)
        
        return None
    
    def _parse_config_file(self, config_path: Path, show_diagnostics: bool) -> bool:
        """Парсит файл конфигурации с разными кодировками"""
        if show_diagnostics:
            print(f"✅ НАЙДЕН CONFIG.INI: {config_path}")
        
        config = configparser.ConfigParser()
        encodings_to_try = ['utf-8', 'cp1251', 'windows-1251', 'latin-1']
        
        for encoding in encodings_to_try:
            try:
                if show_diagnostics:
                    print(f"Пробую кодировку: {encoding}")
                
                config.read(str(config_path), encoding=encoding)
                
                # Проверяем базовую структуру
                if not self._validate_config_structure(config, show_diagnostics):
                    continue
                
                # Проверяем обязательные поля
                if not self._validate_required_fields(config, show_diagnostics):
                    continue
                
                # Загружаем настройки
                self._load_settings_from_config(config)
                
                if show_diagnostics:
                    print(f"  ✅ Конфиг успешно загружен с кодировкой {encoding}")
                    self._show_loaded_settings()
                
                return True
                
            except Exception as e:
                if show_diagnostics:
                    print(f"  ❌ Ошибка с кодировкой {encoding}: {e}")
                continue
        
        if show_diagnostics:
            print("❌ НЕ УДАЛОСЬ ЗАГРУЗИТЬ КОНФИГ!")
        return False
    
    def _validate_config_structure(self, config: configparser.ConfigParser, show_diagnostics: bool) -> bool:
        """Проверяет структуру конфига"""
        sections = config.sections()
        
        if show_diagnostics:
            print(f"  Найдены секции: {sections}")
        
        if 'Planfix' not in sections:
            if show_diagnostics:
                print(f"  ❌ Секция [Planfix] не найдена")
            return False
        
        return True
    
    def _validate_required_fields(self, config: configparser.ConfigParser, show_diagnostics: bool) -> bool:
        """Проверяет обязательные поля"""
        api_token = config.get('Planfix', 'api_token', fallback='')
        account_url = config.get('Planfix', 'account_url', fallback='')
        
        if show_diagnostics:
            print(f"  API Token: {'***' + api_token[-4:] if len(api_token) > 4 else 'НЕ ЗАДАН'}")
            print(f"  Account URL: {account_url}")
        
        # Проверяем API токен
        if not api_token or api_token in ['ВАШ_API_ТОКЕН', 'YOUR_API_TOKEN', 'YOUR_API_TOKEN_HERE']:
            if show_diagnostics:
                print(f"  ❌ API токен не настроен")
            return False
        
        # Проверяем URL
        if not account_url.endswith('/rest'):
            if show_diagnostics:
                print(f"  ❌ URL должен заканчиваться на /rest")
            return False
        
        return True
    
    def _load_settings_from_config(self, config: configparser.ConfigParser):
        """Загружает все настройки из ConfigParser"""
        # Настройки Planfix
        self.config_data['planfix']['api_token'] = config['Planfix']['api_token']
        self.config_data['planfix']['account_url'] = config['Planfix']['account_url']
        self.config_data['planfix']['filter_id'] = config.get('Planfix', 'filter_id', fallback=None)
        self.config_data['planfix']['user_id'] = config.get('Planfix', 'user_id', fallback='1')
        
        # Очищаем filter_id если он пустой
        if self.config_data['planfix']['filter_id'] == '':
            self.config_data['planfix']['filter_id'] = None
        
        # Настройки приложения
        if config.has_section('Settings'):
            self.config_data['check_interval'] = int(config.get('Settings', 'check_interval', fallback=300))
            self.config_data['max_windows_per_category'] = int(config.get('Settings', 'max_windows_per_category', fallback=5))
            self.config_data['max_total_windows'] = int(config.get('Settings', 'max_total_windows', fallback=10))
            
            self.config_data['notifications']['current'] = config.getboolean('Settings', 'notify_current', fallback=True)
            self.config_data['notifications']['urgent'] = config.getboolean('Settings', 'notify_urgent', fallback=True)
            self.config_data['notifications']['overdue'] = config.getboolean('Settings', 'notify_overdue', fallback=True)
        
        # Настройки ролей
        if config.has_section('Roles'):
            self.config_data['roles']['include_assignee'] = config.getboolean('Roles', 'include_assignee', fallback=True)
            self.config_data['roles']['include_assigner'] = config.getboolean('Roles', 'include_assigner', fallback=True)
            self.config_data['roles']['include_auditor'] = config.getboolean('Roles', 'include_auditor', fallback=True)
    
    def _show_loaded_settings(self):
        """Показывает загруженные настройки"""
        print("✅ Все настройки успешно загружены")
        print(f"   Filter ID: {self.config_data['planfix']['filter_id'] or 'НЕ ИСПОЛЬЗУЕТСЯ'}")
        print(f"   User ID: {self.config_data['planfix']['user_id']}")
        print(f"   Интервал проверки: {self.config_data['check_interval']} сек")
        print("=" * 35)
    
    def _show_directory_contents(self, current_dir: Path, script_dir: Path):
        """Показывает содержимое директорий для диагностики"""
        print(f"\n📂 Содержимое текущей директории ({current_dir}):")
        try:
            for item in sorted(current_dir.iterdir()):
                if item.is_file():
                    print(f"   📄 {item.name}")
                else:
                    print(f"   📁 {item.name}/")
        except Exception as e:
            print(f"   ❌ Ошибка чтения: {e}")
        
        if current_dir != script_dir:
            print(f"\n📂 Содержимое директории скрипта ({script_dir}):")
            try:
                for item in sorted(script_dir.iterdir()):
                    if item.is_file():
                        print(f"   📄 {item.name}")
                    else:
                        print(f"   📁 {item.name}/")
            except Exception as e:
                print(f"   ❌ Ошибка чтения: {e}")
    
    # ===== ПУБЛИЧНЫЕ МЕТОДЫ =====
    
    def is_loaded(self) -> bool:
        """Проверяет загружена ли конфигурация"""
        return self._config_loaded
    
    def get_config(self) -> Dict[str, Any]:
        """Возвращает полную конфигурацию"""
        if not self._config_loaded:
            raise RuntimeError("Конфигурация не загружена. Вызовите load_config() сначала.")
        return self.config_data.copy()
    
    def get_planfix_config(self) -> Dict[str, Any]:
        """Возвращает настройки Planfix API"""
        if not self._config_loaded:
            raise RuntimeError("Конфигурация не загружена")
        return self.config_data['planfix'].copy()
    
    def get_app_settings(self) -> Dict[str, Any]:
        """Возвращает настройки приложения"""
        if not self._config_loaded:
            raise RuntimeError("Конфигурация не загружена")
        return {
            'check_interval': self.config_data['check_interval'],
            'max_windows_per_category': self.config_data['max_windows_per_category'],
            'max_total_windows': self.config_data['max_total_windows'],
            'notifications': self.config_data['notifications'].copy(),
            'roles': self.config_data['roles'].copy()
        }
    
    def get_notification_settings(self) -> Dict[str, bool]:
        """Возвращает настройки уведомлений"""
        if not self._config_loaded:
            raise RuntimeError("Конфигурация не загружена")
        return self.config_data['notifications'].copy()
    
    def get_role_settings(self) -> Dict[str, bool]:
        """Возвращает настройки ролей"""
        if not self._config_loaded:
            raise RuntimeError("Конфигурация не загружена")
        return self.config_data['roles'].copy()
    
    def create_sample_config(self, filepath: str = 'config.ini') -> bool:
        """
        Создает пример файла конфигурации
        
        Args:
            filepath: Путь к создаваемому файлу
            
        Returns:
            bool: True если файл создан успешно
        """
        sample_config = """[Planfix]
# Ваш API токен из настроек Planfix
api_token = ВАШ_API_ТОКЕН_ЗДЕСЬ

# URL вашего аккаунта (обязательно с /rest на конце!)
account_url = https://ваш-аккаунт.planfix.com/rest

# ID готового фильтра (если есть)
filter_id = 

# ID пользователя (если нет фильтра)
user_id = 1

[Settings]
# Интервал проверки в секундах (300 = 5 минут)
check_interval = 300

# Включить уведомления для разных типов задач
notify_current = true
notify_urgent = true
notify_overdue = true

# Лимиты окон уведомлений
max_windows_per_category = 5
max_total_windows = 10

[Roles]
# Показывать задачи где я исполнитель
include_assignee = true

# Показывать задачи где я постановщик
include_assigner = true

# Показывать задачи где я контролер/участник
include_auditor = true
"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(sample_config)
            print(f"✅ Создан пример config.ini: {filepath}")
            print("📝 Отредактируйте файл и укажите ваши данные")
            return True
        except Exception as e:
            print(f"❌ Ошибка создания config.ini: {e}")
            return False

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_config_manager():
    """Тестирует ConfigManager"""
    print("🧪 Тестирование ConfigManager")
    print("=" * 40)
    
    config_manager = ConfigManager()
    
    # Тест 1: Загрузка конфига
    print("1. Тестирование загрузки конфига...")
    success = config_manager.load_config(show_diagnostics=True)
    
    if success:
        print("✅ Конфиг загружен успешно")
        
        # Тест 2: Получение настроек
        print("\n2. Тестирование получения настроек...")
        try:
            planfix_config = config_manager.get_planfix_config()
            app_settings = config_manager.get_app_settings()
            
            print(f"✅ Planfix настройки: {planfix_config}")
            print(f"✅ Настройки приложения: {app_settings}")
            
        except Exception as e:
            print(f"❌ Ошибка получения настроек: {e}")
    else:
        print("❌ Конфиг не загружен")
        
        # Тест 3: Создание примера
        print("\n3. Создание примера config.ini...")
        config_manager.create_sample_config('config_sample.ini')

if __name__ == "__main__":
    test_config_manager()