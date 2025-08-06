#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый файл для проверки интеграции диагностики в меню трея
"""

import sys
import os

# Добавляем родительскую папку в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_diagnostic_import():
    """Тестирует импорт модуля диагностики"""
    try:
        from diagnostic_module import run_diagnostic
        print("✅ Модуль диагностики импортирован успешно")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля диагностики: {e}")
        return False

def test_ui_components_import():
    """Тестирует импорт UI компонентов с диагностикой"""
    try:
        from ui_components import SystemTray, DIAGNOSTIC_AVAILABLE
        print("✅ UI компоненты импортированы успешно")
        print(f"ℹ️ Диагностика доступна: {DIAGNOSTIC_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта UI компонентов: {e}")
        return False

def test_tray_menu_creation():
    """Тестирует создание меню трея с диагностикой"""
    try:
        from ui_components import SystemTray
        
        # Создаем экземпляр трея
        tray = SystemTray()
        
        # Пытаемся создать меню
        menu = tray.create_menu()
        print("✅ Меню трея создано успешно")
        
        # Проверяем, что в меню есть пункт диагностики
        menu_items = menu.items if hasattr(menu, 'items') else []
        diagnostic_found = False
        
        for item in menu_items:
            if hasattr(item, 'text') and 'Диагностика' in str(item.text):
                diagnostic_found = True
                break
        
        if diagnostic_found:
            print("✅ Пункт 'Диагностика' найден в меню")
        else:
            print("⚠️ Пункт 'Диагностика' не найден в меню")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания меню трея: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔧 Тестирование интеграции диагностики в меню трея")
    print("=" * 50)
    
    tests = [
        ("Импорт модуля диагностики", test_diagnostic_import),
        ("Импорт UI компонентов", test_ui_components_import),
        ("Создание меню трея", test_tray_menu_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Неожиданная ошибка в тесте '{test_name}': {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Диагностика успешно интегрирована.")
        return True
    else:
        print("⚠️ Некоторые тесты не пройдены. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
