#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки exe файла Planfix Reminder
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

def check_requirements():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        ('PyInstaller', 'pyinstaller'),
        ('requests', 'requests'),
        ('pystray', 'pystray'),
        ('PIL', 'Pillow'),
        ('plyer', 'plyer')
    ]

    missing_packages = []

    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"  ❌ {package_name}")
    
    if missing_packages:
        print(f"\n⚠️ Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("Установите их командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def clean_build_dirs():
    """Очищает папки сборки"""
    print("\n🧹 Очистка папок сборки...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  🗑️ Удалена папка: {dir_name}")
            except Exception as e:
                print(f"  ⚠️ Не удалось удалить {dir_name}: {e}")
    
    # Удаляем .pyc файлы
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

def build_exe():
    """Собирает exe файл"""
    print("\n🔨 Сборка exe файла...")
    
    # Проверяем наличие spec файла
    spec_file = 'planfix_reminder.spec'
    if not os.path.exists(spec_file):
        print(f"❌ Файл {spec_file} не найден!")
        return False
    
    try:
        # Запускаем PyInstaller
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', spec_file]
        print(f"Выполняется команда: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Сборка завершена успешно!")
            return True
        else:
            print("❌ Ошибка сборки:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка выполнения PyInstaller: {e}")
        return False

def check_result():
    """Проверяет результат сборки"""
    print("\n📦 Проверка результата...")
    
    exe_path = Path('dist/PlanfixReminder.exe')
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Exe файл создан: {exe_path}")
        print(f"📏 Размер: {size_mb:.1f} МБ")
        
        # Проверяем дополнительные файлы
        dist_path = Path('dist')
        files_in_dist = list(dist_path.glob('*'))
        
        print(f"📁 Файлы в папке dist:")
        for file in files_in_dist:
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                print(f"  📄 {file.name} ({size_kb:.1f} КБ)")
            else:
                print(f"  📁 {file.name}/")
        
        return True
    else:
        print("❌ Exe файл не найден!")
        return False

def create_distribution():
    """Создает папку для распространения"""
    print("\n📦 Создание дистрибутива...")
    
    dist_folder = Path('PlanfixReminder_Distribution')
    
    # Создаем папку дистрибутива
    if dist_folder.exists():
        shutil.rmtree(dist_folder)
    
    dist_folder.mkdir()
    
    # Копируем exe файл
    exe_source = Path('dist/PlanfixReminder.exe')
    if exe_source.exists():
        shutil.copy2(exe_source, dist_folder / 'PlanfixReminder.exe')
        print(f"  ✅ Скопирован: PlanfixReminder.exe")
    
    # Копируем конфигурационные файлы
    config_files = [
        'config.ini.example',
        'README.md',
        'planfix_reminder_help.html'
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            shutil.copy2(config_file, dist_folder / config_file)
            print(f"  ✅ Скопирован: {config_file}")
    
    # Создаем инструкцию по установке
    install_instructions = """# Planfix Reminder - Инструкция по установке

## Быстрый старт

1. Скопируйте файл `config.ini.example` в `config.ini`
2. Отредактируйте `config.ini` - укажите ваши данные Planfix API
3. Запустите `PlanfixReminder.exe`

## Настройка

Откройте файл `config.ini` и заполните:

```ini
[planfix]
api_key = ваш_api_ключ
account = ваш_аккаунт.planfix.ru
user_id = ваш_id_пользователя
```

## Справка

Подробная справка доступна в файле `planfix_reminder_help.html`

## Поддержка

При возникновении проблем:
1. Запустите диагностику из меню трея (🔧 Диагностика)
2. Отправьте результаты в IT-поддержку
"""
    
    with open(dist_folder / 'INSTALL.md', 'w', encoding='utf-8') as f:
        f.write(install_instructions)
    
    print(f"  ✅ Создана инструкция: INSTALL.md")
    print(f"\n🎉 Дистрибутив готов в папке: {dist_folder}")
    
    return True

def main():
    """Основная функция сборки"""
    print("🚀 Сборка Planfix Reminder в exe файл")
    print("=" * 50)
    
    start_time = time.time()
    
    # Проверяем зависимости
    if not check_requirements():
        return False
    
    # Очищаем папки сборки
    clean_build_dirs()
    
    # Собираем exe
    if not build_exe():
        return False
    
    # Проверяем результат
    if not check_result():
        return False
    
    # Создаем дистрибутив
    create_distribution()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n⏱️ Время сборки: {duration:.1f} секунд")
    print("🎉 Сборка завершена успешно!")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ Сборка завершена с ошибками")
        sys.exit(1)
    else:
        print("\n✅ Готово! Exe файл находится в папке PlanfixReminder_Distribution")
        sys.exit(0)
