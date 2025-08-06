@echo off
chcp 65001 >nul
echo 🚀 Сборка Planfix Reminder
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+ и добавьте в PATH
    pause
    exit /b 1
)

REM Проверяем наличие pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip не найден! Переустановите Python с включенным pip
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

REM Устанавливаем PyInstaller если его нет
echo 📦 Проверка PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 📥 Установка PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ Ошибка установки PyInstaller
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller готов
echo.

REM Запускаем сборку
echo 🔨 Запуск сборки...
python tools\build_exe.py

if errorlevel 1 (
    echo.
    echo ❌ Сборка завершена с ошибками
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Сборка завершена успешно!
    echo 📁 Результат в папке: PlanfixReminder_Distribution
    echo.
    pause
)
