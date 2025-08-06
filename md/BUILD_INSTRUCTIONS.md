# Инструкция по сборке exe файла Planfix Reminder

## Быстрый старт

### Автоматическая сборка (рекомендуется)

1. **Запустите batch файл:**
   ```cmd
   build.bat
   ```
   
2. **Или запустите Python скрипт:**
   ```cmd
   python build_exe.py
   ```

### Результат

После успешной сборки в папке `PlanfixReminder_Distribution` будут:
- `PlanfixReminder.exe` - основной исполняемый файл
- `config.ini.example` - пример конфигурации
- `README.md` - документация
- `planfix_reminder_help.html` - справка
- `INSTALL.md` - инструкция по установке

## Ручная сборка

### 1. Установка зависимостей

```cmd
pip install pyinstaller requests pystray Pillow plyer
```

### 2. Сборка через PyInstaller

```cmd
pyinstaller --clean planfix_reminder.spec
```

### 3. Альтернативная команда (без spec файла)

```cmd
pyinstaller --onefile --windowed --name PlanfixReminder ^
    --add-data "config.ini.example;." ^
    --add-data "planfix_reminder_help.html;." ^
    --add-data "README.md;." ^
    --hidden-import tkinter ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import requests ^
    --hidden-import plyer ^
    --hidden-import winsound ^
    --hidden-import winreg ^
    main.py
```

## Требования к системе

### Для сборки:
- Python 3.8 или выше
- pip (менеджер пакетов Python)
- Windows 10/11 (для Windows exe)

### Зависимости Python:
- pyinstaller
- requests >= 2.31.0
- pystray >= 0.19.0
- Pillow >= 10.0.0
- plyer >= 2.1.0

## Структура проекта

```
planfix_reminder/
├── main.py                    # Точка входа
├── config_manager.py          # Управление конфигурацией
├── planfix_api.py            # API Planfix
├── task_tracker.py           # Отслеживание задач
├── ui_components.py          # UI компоненты
├── file_logger.py            # Логирование
├── diagnostic_module.py      # Диагностика
├── debug_utils.py            # Утилиты отладки
├── config.ini.example        # Пример конфигурации
├── requirements.txt          # Зависимости
├── planfix_reminder.spec     # Конфигурация PyInstaller
├── build_exe.py             # Скрипт сборки
├── build.bat                # Batch файл сборки
└── BUILD_INSTRUCTIONS.md    # Эта инструкция
```

## Параметры сборки

### В файле `planfix_reminder.spec`:

- **`console=False`** - GUI приложение без консоли
- **`onefile=True`** - один exe файл (в EXE секции)
- **`upx=True`** - сжатие для уменьшения размера
- **`hiddenimports`** - явно указанные модули
- **`excludes`** - исключенные модули для уменьшения размера

### Дополнительные файлы:
- `config.ini.example` - пример конфигурации
- `planfix_reminder_help.html` - справка пользователя
- `README.md` - документация

## Решение проблем

### Ошибка "Module not found"
Добавьте модуль в `hiddenimports` в файле `planfix_reminder.spec`

### Большой размер exe файла
1. Добавьте ненужные модули в `excludes`
2. Включите UPX сжатие (`upx=True`)
3. Используйте виртуальное окружение с минимальными зависимостями

### Ошибки при запуске exe
1. Проверьте логи в папке приложения
2. Запустите exe из командной строки для просмотра ошибок
3. Убедитесь, что все файлы данных включены в сборку

### Проблемы с tkinter
Tkinter обычно входит в стандартную поставку Python, но иногда может отсутствовать:
```cmd
# Для Ubuntu/Debian
sudo apt-get install python3-tk

# Для Windows - переустановите Python с галочкой "tcl/tk and IDLE"
```

### Проблемы с pystray
Убедитесь, что установлена Pillow:
```cmd
pip install Pillow
```

## Оптимизация

### Уменьшение размера:
1. Используйте виртуальное окружение
2. Установите только необходимые пакеты
3. Добавьте больше модулей в `excludes`
4. Включите UPX сжатие

### Ускорение запуска:
1. Используйте `--onedir` вместо `--onefile` (быстрее запуск, но больше файлов)
2. Исключите ненужные модули
3. Оптимизируйте импорты в коде

## Тестирование

После сборки обязательно протестируйте:

1. **Запуск приложения**
2. **Работу системного трея**
3. **Показ уведомлений**
4. **Подключение к Planfix API**
5. **Диагностику системы**
6. **Справку и настройки**

## Распространение

Для распространения используйте папку `PlanfixReminder_Distribution`:
1. Заархивируйте всю папку
2. Приложите инструкцию по установке
3. Укажите системные требования

## Автоматизация

Для автоматической сборки в CI/CD:
```yaml
# Пример для GitHub Actions
- name: Build exe
  run: python build_exe.py
  
- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: PlanfixReminder
    path: PlanfixReminder_Distribution/
```
