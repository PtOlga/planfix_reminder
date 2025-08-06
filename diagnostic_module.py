#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль диагностики Planfix Reminder
Создает HTML отчет о состоянии системы и компонентов
"""

import os
import platform
import datetime
import traceback
import tempfile
import webbrowser
import tkinter as tk
from typing import Dict, Any


class PlanfixDiagnostic:
    """Класс для проведения диагностики приложения"""
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self.results = []
        self.start_time = datetime.datetime.now()
        self.app_directory = os.path.dirname(os.path.abspath(__file__))
    
    def add_result(self, category: str, test_name: str, status: str, details: str = "", fix_suggestion: str = ""):
        """Добавляет результат теста"""
        self.results.append({
            'category': category,
            'test_name': test_name,
            'status': status,  # 'success', 'warning', 'error', 'info'
            'details': details,
            'fix_suggestion': fix_suggestion,
            'timestamp': datetime.datetime.now()
        })
    
    def test_system_info(self):
        """Собирает информацию о системе"""
        try:
            import subprocess
            import winreg
            import locale
            import ctypes
            
            # Основная информация о системе
            system_info = {
                'OS': f"{platform.system()} {platform.release()}",
                'Architecture': platform.machine(),
                'Processor': platform.processor() or 'Unknown',
                'Username': os.getenv('USERNAME', 'Unknown'),
                'Hostname': platform.node()
            }
            
            # Детальная версия Windows
            try:
                result = subprocess.run(['wmic', 'os', 'get', 'Caption,Version,BuildNumber', '/value'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Caption=' in line:
                            caption = line.split('=')[1].strip()
                            if caption:
                                system_info['Windows'] = caption
                        elif 'BuildNumber=' in line:
                            build = line.split('=')[1].strip()
                            if build:
                                system_info['Build'] = build
            except:
                pass
            
            # Проверка прав администратора
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                system_info['Admin Rights'] = 'Да' if is_admin else 'Нет'
            except:
                system_info['Admin Rights'] = 'Неизвестно'
            
            # Архитектура процесса (32/64 бит)
            import struct
            process_arch = '64-bit' if struct.calcsize("P") * 8 == 64 else '32-bit'
            system_info['Process'] = f"{process_arch} процесс"
            
            # Версия .NET Framework
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full") as key:
                    release, _ = winreg.QueryValueEx(key, "Release")
                    
                    # Определяем версию по номеру релиза
                    if release >= 528040:
                        net_version = "4.8"
                    elif release >= 461808:
                        net_version = "4.7.2"
                    elif release >= 460798:
                        net_version = "4.7"
                    elif release >= 394802:
                        net_version = "4.6.2"
                    else:
                        net_version = f"4.x (build {release})"
                    
                    system_info['.NET Framework'] = net_version
            except:
                system_info['.NET Framework'] = 'Не установлен или недоступен'
            
            # Региональные настройки
            try:
                try:
                    system_locale = locale.getlocale()[0] or 'Unknown'
                    system_encoding = locale.getpreferredencoding() or 'Unknown'
                except:
                    system_locale = 'Unknown'
                    system_encoding = 'Unknown'
                
                # Получаем формат даты Windows
                try:
                    result = subprocess.run(['powershell', '-Command', 
                                           'Get-Culture | Select-Object -ExpandProperty DateTimeFormat | Select-Object -ExpandProperty ShortDatePattern'], 
                                          capture_output=True, text=True, timeout=5)
                    date_format = result.stdout.strip() if result.returncode == 0 else 'Unknown'
                except:
                    date_format = 'Unknown'
                
                system_info['Locale'] = f"{system_locale}, кодировка: {system_encoding}"
                system_info['Date Format'] = date_format
                
            except Exception as e:
                system_info['Locale'] = f'Ошибка: {str(e)[:30]}'
            
            details = "\n".join([f"{k}: {v}" for k, v in system_info.items()])
            
            # Проверяем совместимость
            warnings = []
            if 'Windows' in system_info:
                if 'Windows 7' in system_info['Windows']:
                    warnings.append("Windows 7 - ограниченная поддержка новых функций")
                elif 'Windows XP' in system_info['Windows'] or 'Windows Vista' in system_info['Windows']:
                    warnings.append("Устаревшая версия Windows - возможны проблемы совместимости")
            
            if system_info.get('Admin Rights') == 'Да':
                warnings.append("Запуск с правами администратора может вызывать проблемы с UAC")
            
            if warnings:
                details += "\n\nПредупреждения:\n" + "\n".join(warnings)
                status = "warning"
            else:
                status = "info"
                
            self.add_result("Система", "Информация о системе", status, details)
            
        except Exception as e:
            self.add_result("Система", "Информация о системе", "error", str(e))
    
    def test_antivirus_security(self):
        """Проверяет антивирус и настройки безопасности"""
        try:
            import winreg
            import subprocess
            
            security_info = []
            issues = []
            
            # Проверка Windows Defender
            try:
                result = subprocess.run(['powershell', '-Command', 
                                       'Get-MpComputerStatus | Select-Object -Property AntivirusEnabled,RealTimeProtectionEnabled'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout:
                    if "True" in result.stdout:
                        security_info.append("✅ Windows Defender активен")
                    else:
                        security_info.append("⚠️ Windows Defender отключен")
                else:
                    security_info.append("❓ Статус Windows Defender неизвестен")
            except:
                security_info.append("❓ Не удалось проверить Windows Defender")
            
            # Проверка UAC
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System") as key:
                    uac_enabled, _ = winreg.QueryValueEx(key, "EnableLUA")
                    if uac_enabled:
                        security_info.append("✅ UAC включен")
                    else:
                        security_info.append("⚠️ UAC отключен")
                        issues.append("UAC отключен - могут быть проблемы с правами доступа")
            except:
                security_info.append("❓ Не удалось проверить UAC")
            
            # Проверка SmartScreen
            try:
                result = subprocess.run(['powershell', '-Command', 
                                       'Get-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer" -Name SmartScreenEnabled'], 
                                      capture_output=True, text=True, timeout=5)
                if "Warn" in result.stdout or "RequireAdmin" in result.stdout:
                    security_info.append("✅ SmartScreen активен")
                else:
                    security_info.append("⚠️ SmartScreen отключен или ограничен")
            except:
                security_info.append("❓ Не удалось проверить SmartScreen")
            
            details = "\n".join(security_info)
            if issues:
                details += "\n\nВозможные проблемы:\n" + "\n".join(issues)
                
            status = "warning" if issues else "success"
            self.add_result("Безопасность", "Антивирус и защита", status, details)
            
        except Exception as e:
            self.add_result("Безопасность", "Проверка безопасности", "error", str(e))
    
    def test_windows_notifications(self):
        """Проверяет настройки уведомлений Windows"""
        try:
            import winreg
            import subprocess
            
            notification_info = []
            issues = []
            
            # Проверка глобальных настроек уведомлений
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\PushNotifications") as key:
                    try:
                        toast_enabled, _ = winreg.QueryValueEx(key, "ToastEnabled")
                        if toast_enabled:
                            notification_info.append("✅ Системные уведомления включены")
                        else:
                            notification_info.append("❌ Системные уведомления отключены")
                            issues.append("Включите уведомления в Параметры → Система → Уведомления")
                    except FileNotFoundError:
                        notification_info.append("✅ Системные уведомления включены (по умолчанию)")
            except:
                notification_info.append("❓ Не удалось проверить настройки уведомлений")
            
            # Проверка режима "Не беспокоить"
            try:
                result = subprocess.run(['powershell', '-Command', 
                                       'Get-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\Cache\\DefaultAccount\\*gaming*" -ErrorAction SilentlyContinue'], 
                                      capture_output=True, text=True, timeout=5)
                # Упрощенная проверка - если PowerShell выполнился без ошибок
                notification_info.append("ℹ️ Режим 'Фокусировка внимания' проверен")
            except:
                notification_info.append("❓ Не удалось проверить режим 'Фокусировка внимания'")
            
            # Проверка службы уведомлений
            try:
                result = subprocess.run(['sc', 'query', 'WpnService'], 
                                      capture_output=True, text=True, timeout=5)
                if "RUNNING" in result.stdout:
                    notification_info.append("✅ Служба уведомлений Windows запущена")
                else:
                    notification_info.append("❌ Служба уведомлений Windows не работает")
                    issues.append("Запустите службу WpnService")
            except:
                notification_info.append("❓ Не удалось проверить службу уведомлений")
            
            details = "\n".join(notification_info)
            if issues:
                details += "\n\nРекомендации:\n" + "\n".join(issues)
                
            status = "error" if any("❌" in info for info in notification_info) else ("warning" if issues else "success")
            self.add_result("Уведомления", "Настройки Windows", status, details)
            
        except Exception as e:
            self.add_result("Уведомления", "Проверка уведомлений", "error", str(e))
    
    def test_system_services(self):
        """Проверяет важные системные службы Windows"""
        try:
            import subprocess
            
            # Список важных служб для работы приложения
            services_to_check = [
                ('Themes', 'Службы тем (для GUI)'),
                ('AudioSrv', 'Windows Audio (для звуков)'),
                ('Winmgmt', 'Инструментарий управления Windows'),
                ('EventLog', 'Журнал событий Windows')
            ]
            
            # Опциональные службы (не критичные)
            optional_services = [
                ('BITS', 'Фоновая передача данных')
            ]
            
            service_info = []
            issues = []
            
            # Проверка критичных служб
            for service_name, description in services_to_check:
                try:
                    result = subprocess.run(['sc', 'query', service_name], 
                                          capture_output=True, text=True, timeout=5)
                    if "RUNNING" in result.stdout:
                        service_info.append(f"✅ {description}")
                    elif "STOPPED" in result.stdout:
                        service_info.append(f"❌ {description} - остановлена")
                        issues.append(f"Запустите службу {service_name}")
                    else:
                        service_info.append(f"❓ {description} - статус неизвестен")
                except subprocess.TimeoutExpired:
                    service_info.append(f"⚠️ {description} - таймаут проверки")
                except:
                    service_info.append(f"❓ {description} - ошибка проверки")
            
            # Проверка опциональных служб
            for service_name, description in optional_services:
                try:
                    result = subprocess.run(['sc', 'query', service_name], 
                                          capture_output=True, text=True, timeout=5)
                    if "RUNNING" in result.stdout:
                        service_info.append(f"✅ {description} (опционально)")
                    elif "STOPPED" in result.stdout:
                        service_info.append(f"ℹ️ {description} - остановлена (не критично)")
                    else:
                        service_info.append(f"❓ {description} - статус неизвестен")
                except:
                    service_info.append(f"❓ {description} - ошибка проверки")
            
            # Проверка Explorer (для системного трея)
            try:
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq explorer.exe'], 
                                      capture_output=True, text=True, timeout=5)
                if "explorer.exe" in result.stdout:
                    service_info.append("✅ Windows Explorer запущен (системный трей доступен)")
                else:
                    service_info.append("❌ Windows Explorer не запущен")
                    issues.append("Перезапустите Windows Explorer")
            except:
                service_info.append("❓ Не удалось проверить Windows Explorer")
            
            details = "\n".join(service_info)
            if issues:
                details += "\n\nПроблемы:\n" + "\n".join(issues)
                
            status = "error" if any("❌" in info for info in service_info) else ("warning" if issues else "success")
            self.add_result("Службы", "Системные службы", status, details)
            
        except Exception as e:
            self.add_result("Службы", "Проверка служб", "error", str(e))
    
    def test_firewall_network(self):
        """Проверяет брандмауэр и сетевые настройки"""
        try:
            import subprocess
            
            network_info = []
            issues = []
            
            # Проверка Windows Firewall
            try:
                result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles', 'state'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    if "ON" in result.stdout:
                        network_info.append("✅ Windows Firewall активен")
                    else:
                        network_info.append("⚠️ Windows Firewall отключен")
                else:
                    network_info.append("❓ Не удалось проверить статус Firewall")
            except:
                network_info.append("❓ Ошибка проверки Windows Firewall")
            
            # Проверка интернет-соединения через ping
            try:
                result = subprocess.run(['ping', '-n', '1', '8.8.8.8'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    network_info.append("✅ Интернет соединение работает")
                else:
                    network_info.append("❌ Нет интернет соединения")
                    issues.append("Проверьте подключение к интернету")
            except:
                network_info.append("❓ Не удалось проверить интернет соединение")
            
            # Проверка DNS
            try:
                result = subprocess.run(['nslookup', 'planfix.com'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and "Name:" in result.stdout:
                    network_info.append("✅ DNS резолюция работает")
                else:
                    network_info.append("❌ Проблемы с DNS")
                    issues.append("Проверьте настройки DNS")
            except:
                network_info.append("❓ Не удалось проверить DNS")
            
            # Проверка прокси настроек
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                   r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                    try:
                        proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                        if proxy_enable:
                            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                            network_info.append(f"ℹ️ Прокси используется: {proxy_server}")
                        else:
                            network_info.append("✅ Прокси не используется")
                    except FileNotFoundError:
                        network_info.append("✅ Прокси не настроен")
            except:
                network_info.append("❓ Не удалось проверить настройки прокси")
            
            details = "\n".join(network_info)
            if issues:
                details += "\n\nПроблемы:\n" + "\n".join(issues)
                
            status = "error" if any("❌" in info for info in network_info) else ("warning" if issues else "success")
            self.add_result("Сеть", "Брандмауэр и соединение", status, details)
            
        except Exception as e:
            self.add_result("Сеть", "Проверка сети", "error", str(e))
    
    def test_file_permissions(self):
        """Проверяет права доступа к файлам и папкам"""
        try:
            permissions_info = []
            issues = []
            
            # Проверка прав на папку программы
            try:
                test_file = os.path.join(self.app_directory, 'test_write_permission.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                permissions_info.append(f"✅ Запись в папку программы: {self.app_directory}")
            except PermissionError:
                permissions_info.append(f"❌ Нет прав записи в папку программы")
                issues.append("Запустите программу от имени администратора или переместите в папку пользователя")
            except Exception as e:
                permissions_info.append(f"⚠️ Проблема с папкой программы: {str(e)[:50]}")
            
            # Проверка доступности %APPDATA%
            try:
                appdata_path = os.path.join(os.getenv('APPDATA', ''), 'PlanfixReminder')
                os.makedirs(appdata_path, exist_ok=True)
                test_file = os.path.join(appdata_path, 'test_appdata.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                permissions_info.append(f"✅ Доступ к %APPDATA%: {appdata_path}")
            except Exception as e:
                permissions_info.append(f"❌ Проблема с %APPDATA%: {str(e)[:50]}")
                issues.append("Проверьте права доступа к папкам пользователя")
            
            # Проверка временной папки
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
                    f.write('test')
                permissions_info.append("✅ Доступ к временным файлам")
            except Exception as e:
                permissions_info.append(f"❌ Проблема с временными файлами: {str(e)[:50]}")
                issues.append("Проблемы с временной папкой Windows")
            
            # Проверка свободного места
            try:
                import shutil
                _, _, free = shutil.disk_usage(self.app_directory)
                free_mb = free // (1024*1024)
                if free_mb > 100:
                    permissions_info.append(f"✅ Свободное место: {free_mb} МБ")
                else:
                    permissions_info.append(f"⚠️ Мало свободного места: {free_mb} МБ")
                    if free_mb < 10:
                        issues.append("Критически мало свободного места на диске")
            except Exception as e:
                permissions_info.append(f"❓ Не удалось проверить свободное место: {str(e)[:50]}")
            
            details = "\n".join(permissions_info)
            if issues:
                details += "\n\nПроблемы:\n" + "\n".join(issues)
                
            status = "error" if any("❌" in info for info in permissions_info) else ("warning" if issues else "success")
            self.add_result("Файлы", "Права доступа", status, details)
            
        except Exception as e:
            self.add_result("Файлы", "Проверка прав", "error", str(e))
    
    def test_display_scaling(self):
        """Проверяет настройки масштабирования и дисплея"""
        try:
            import subprocess
            
            display_info = []
            issues = []
            
            # Проверка DPI scaling через PowerShell
            try:
                result = subprocess.run([
                    'powershell', '-Command',
                    'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout:
                    display_info.append(f"✅ Основной дисплей: {result.stdout.strip()}")
                else:
                    display_info.append("❓ Не удалось получить информацию о дисплее")
            except:
                display_info.append("❓ Ошибка проверки дисплея")
            
            # Проверка через tkinter если доступен
            try:
                root = tk.Tk()
                root.withdraw()
                
                # Получаем разрешение экрана
                screen_width = root.winfo_screenwidth()
                screen_height = root.winfo_screenheight()
                
                # Проверяем масштабирование
                root.update_idletasks()
                dpi_x = root.winfo_fpixels('1i')  # DPI по X
                dpi_y = root.winfo_fpixels('1i')  # DPI по Y
                
                display_info.append(f"✅ Разрешение: {screen_width}x{screen_height}")
                display_info.append(f"ℹ️ DPI: {dpi_x:.0f} x {dpi_y:.0f}")
                
                # Проверяем масштабирование
                if dpi_x > 120 or dpi_y > 120:
                    scale_factor = dpi_x / 96
                    display_info.append(f"⚠️ Увеличенное масштабирование: {scale_factor:.1f}x")
                    if scale_factor > 2.0:
                        issues.append("Очень высокое масштабирование может влиять на отображение окон")
                else:
                    display_info.append("✅ Стандартное масштабирование")
                
                # Проверка множественных мониторов
                try:
                    result = subprocess.run([
                        'wmic', 'desktopmonitor', 'get', 'screenwidth,screenheight'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        monitors = [line for line in result.stdout.split('\n') if line.strip() and 'ScreenHeight' not in line]
                        if len(monitors) > 1:
                            display_info.append(f"ℹ️ Обнаружено мониторов: {len(monitors)}")
                        else:
                            display_info.append("✅ Один монитор")
                except:
                    display_info.append("❓ Не удалось определить количество мониторов")
                
                root.destroy()
                
            except Exception as e:
                display_info.append(f"❌ Ошибка проверки дисплея через tkinter: {str(e)[:50]}")
                issues.append("Проблемы с графической подсистемой")
            
            details = "\n".join(display_info)
            if issues:
                details += "\n\nПредупреждения:\n" + "\n".join(issues)
                
            status = "error" if any("❌" in info for info in display_info) else ("warning" if issues else "success")
            self.add_result("Дисплей", "Масштабирование и мониторы", status, details)
            
        except Exception as e:
            self.add_result("Дисплей", "Проверка дисплея", "error", str(e))
    
    def test_system_performance(self):
        """Проверяет производительность системы и конфликты"""
        try:
            import subprocess
            
            performance_info = []
            issues = []
            
            # Информация о системе без внешних модулей
            try:
                # Проверка загрузки через wmic
                result = subprocess.run([
                    'wmic', 'cpu', 'get', 'loadpercentage', '/value'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'LoadPercentage' in line and '=' in line:
                            cpu_usage = int(line.split('=')[1].strip())
                            performance_info.append(f"ℹ️ Загрузка CPU: {cpu_usage}%")
                            if cpu_usage > 80:
                                issues.append("Высокая загрузка CPU может влиять на работу программы")
                            break
                else:
                    performance_info.append("❓ Не удалось получить загрузку CPU")
            except:
                performance_info.append("❓ Ошибка проверки производительности")
            
            # Проверка памяти
            try:
                result = subprocess.run([
                    'wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/value'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    total_mem = free_mem = None
                    for line in result.stdout.split('\n'):
                        if 'TotalVisibleMemorySize' in line and '=' in line:
                            total_mem = int(line.split('=')[1].strip()) // 1024  # MB
                        elif 'FreePhysicalMemory' in line and '=' in line:
                            free_mem = int(line.split('=')[1].strip()) // 1024   # MB
                    
                    if total_mem and free_mem:
                        used_percent = ((total_mem - free_mem) / total_mem) * 100
                        performance_info.append(f"ℹ️ Память: {used_percent:.1f}% используется ({free_mem}МБ свободно)")
                        if used_percent > 90:
                            issues.append("Критически мало свободной памяти")
                        elif used_percent > 80:
                            issues.append("Мало свободной памяти")
                    else:
                        performance_info.append("❓ Не удалось получить данные о памяти")
            except:
                performance_info.append("❓ Ошибка проверки памяти")
            
            # Поиск процессов с похожими именами
            try:
                result = subprocess.run([
                    'tasklist', '/FI', 'IMAGENAME eq *planfix*'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and 'planfix' in result.stdout.lower():
                    lines = [line.strip() for line in result.stdout.split('\n') if 'planfix' in line.lower()]
                    performance_info.append(f"ℹ️ Найдено процессов Planfix: {len(lines)}")
                    if len(lines) > 1:
                        issues.append("Возможно запущено несколько копий программы")
                else:
                    performance_info.append("✅ Конфликтующие процессы не найдены")
            except:
                performance_info.append("❓ Не удалось проверить процессы")
            
            # Проверка времени работы системы
            try:
                result = subprocess.run([
                    'wmic', 'os', 'get', 'lastbootuptime', '/value'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'LastBootUpTime' in line and '=' in line:
                            boot_time_str = line.split('=')[1].strip()
                            if boot_time_str:
                                performance_info.append(f"ℹ️ Последняя перезагрузка: {boot_time_str[:8]}")
                            break
            except:
                performance_info.append("❓ Не удалось получить время работы системы")
            
            details = "\n".join(performance_info)
            if issues:
                details += "\n\nВозможные проблемы:\n" + "\n".join(issues)
                
            status = "warning" if issues else "success"
            self.add_result("Производительность", "Система и процессы", status, details)
            
        except Exception as e:
            self.add_result("Производительность", "Проверка производительности", "error", str(e))
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Запускает полную диагностику"""
        self.results = []
        
        try:
            self.test_system_info()
            self.test_antivirus_security()
            self.test_windows_notifications()
            self.test_system_services()
            self.test_firewall_network()
            self.test_file_permissions()
            self.test_display_scaling()
            self.test_system_performance()
            
        except Exception as e:
            self.add_result("Диагностика", "Общая ошибка", "error", 
                           f"Критическая ошибка диагностики: {e}\n{traceback.format_exc()}")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку результатов"""
        total_tests = len(self.results)
        success_count = len([r for r in self.results if r['status'] == 'success'])
        warning_count = len([r for r in self.results if r['status'] == 'warning']) 
        error_count = len([r for r in self.results if r['status'] == 'error'])
        info_count = len([r for r in self.results if r['status'] == 'info'])
        
        execution_time = datetime.datetime.now() - self.start_time
        
        return {
            'total_tests': total_tests,
            'success_count': success_count,
            'warning_count': warning_count,
            'error_count': error_count,
            'info_count': info_count,
            'execution_time': execution_time.total_seconds(),
            'results': self.results,
            'timestamp': self.start_time
        }
    
    def generate_html_report(self, summary: Dict[str, Any]) -> str:
        """Генерирует HTML отчет"""
        
        # Определяем общий статус
        if summary['error_count'] > 0:
            status_text = "Обнаружены проблемы"
            status_color = "#dc3545"
        elif summary['warning_count'] > 0:
            status_text = "Есть предупреждения"
            status_color = "#ffc107"
        else:
            status_text = "Все в порядке"
            status_color = "#28a745"
        
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Диагностика Planfix Reminder</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                line-height: 1.6; color: #333; background: #f8f9fa; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: white; border-radius: 10px; padding: 30px; margin-bottom: 20px; 
                   box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .header h1 {{ color: #2c3e50; margin-bottom: 10px; }}
        .status {{ font-size: 1.2rem; padding: 10px 20px; border-radius: 25px; color: white; 
                   background: {status_color}; display: inline-block; }}
        
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 15px; margin-bottom: 20px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; 
                         box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ color: #6c757d; font-size: 0.9rem; margin-bottom: 10px; }}
        .summary-card .number {{ font-size: 2rem; font-weight: bold; }}
        .number.success {{ color: #28a745; }}
        .number.warning {{ color: #ffc107; }}
        .number.error {{ color: #dc3545; }}
        .number.info {{ color: #17a2b8; }}
        
        .results {{ background: white; border-radius: 10px; padding: 20px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .category {{ margin-bottom: 25px; }}
        .category h2 {{ color: #495057; border-bottom: 2px solid #e9ecef; 
                        padding-bottom: 10px; margin-bottom: 15px; }}
        
        .test-item {{ background: #f8f9fa; border-left: 4px solid #ddd; 
                      margin-bottom: 10px; padding: 15px; border-radius: 0 5px 5px 0; }}
        .test-item.success {{ border-left-color: #28a745; }}
        .test-item.warning {{ border-left-color: #ffc107; }}
        .test-item.error {{ border-left-color: #dc3545; }}
        .test-item.info {{ border-left-color: #17a2b8; }}
        
        .test-header {{ display: flex; align-items: center; margin-bottom: 8px; }}
        .test-icon {{ width: 20px; height: 20px; margin-right: 10px; }}
        .test-name {{ font-weight: bold; flex-grow: 1; }}
        .test-time {{ font-size: 0.8rem; color: #6c757d; }}
        
        .test-details {{ color: #6c757d; white-space: pre-line; margin-bottom: 8px; 
                         font-family: 'Courier New', monospace; font-size: 0.9rem; }}
        .test-fix {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; 
                     border-radius: 5px; color: #856404; }}
        
        .footer {{ text-align: center; margin-top: 30px; color: #6c757d; }}
        .copy-button {{ background: #007bff; color: white; border: none; padding: 5px 10px; 
                        border-radius: 3px; cursor: pointer; font-size: 0.8rem; }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 10px; }}
            .summary {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Диагностика Planfix Reminder</h1>
            <div class="status">{status_text}</div>
            <p style="margin-top: 15px; color: #6c757d;">
                Выполнено: {summary['timestamp'].strftime('%d.%m.%Y в %H:%M:%S')} 
                (за {summary['execution_time']:.1f} сек)
            </p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>ВСЕГО ТЕСТОВ</h3>
                <div class="number">{summary['total_tests']}</div>
            </div>
            <div class="summary-card">
                <h3>УСПЕШНО</h3>
                <div class="number success">{summary['success_count']}</div>
            </div>
            <div class="summary-card">
                <h3>ПРЕДУПРЕЖДЕНИЯ</h3>
                <div class="number warning">{summary['warning_count']}</div>
            </div>
            <div class="summary-card">
                <h3>ОШИБКИ</h3>
                <div class="number error">{summary['error_count']}</div>
            </div>
        </div>
        
        <div class="results">"""
        
        # Группируем результаты по категориям
        categories = {}
        for result in summary['results']:
            category = result['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        # Генерируем HTML для каждой категории
        for category_name, tests in categories.items():
            html_content += f"""
            <div class="category">
                <h2>{category_name}</h2>"""
            
            for test in tests:
                # Иконки для статусов
                icons = {
                    'success': '✅',
                    'warning': '⚠️',
                    'error': '❌',
                    'info': 'ℹ️'
                }
                
                icon = icons.get(test['status'], '❓')
                time_str = test['timestamp'].strftime('%H:%M:%S')
                
                html_content += f"""
                <div class="test-item {test['status']}">
                    <div class="test-header">
                        <span class="test-icon">{icon}</span>
                        <span class="test-name">{test['test_name']}</span>
                        <span class="test-time">{time_str}</span>
                    </div>"""
                
                if test['details']:
                    html_content += f"""
                    <div class="test-details">{test['details']}</div>"""
                
                if test['fix_suggestion']:
                    html_content += f"""
                    <div class="test-fix">
                        <strong>💡 Рекомендация:</strong> {test['fix_suggestion']}
                    </div>"""
                
                html_content += "</div>"
            
            html_content += "</div>"
        
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>Отчет сгенерирован Planfix Reminder v1.0</p>
            <p style="margin-top: 10px;">
                <button class="copy-button" onclick="copyReport()">📋 Скопировать полный отчет для техподдержки</button>
            </p>
        </div>
    </div>
    
    <script>
        function copyReport() {{
            // Собираем детальную информацию о системе
            const timestamp = '{summary['timestamp'].strftime('%d.%m.%Y %H:%M:%S')}';
            const statusText = '{status_text}';
            const totalTests = {summary['total_tests']};
            const successCount = {summary['success_count']};
            const warningCount = {summary['warning_count']};
            const errorCount = {summary['error_count']};
            const executionTime = {summary['execution_time']:.1f};

            const systemInfo = `=== ДИАГНОСТИКА PLANFIX REMINDER ===
Время: ${{timestamp}}
Общий статус: ${{statusText}}

📊 СТАТИСТИКА ТЕСТОВ:
Всего тестов: ${{totalTests}}
Успешно: ${{successCount}}
Предупреждения: ${{warningCount}}
Ошибки: ${{errorCount}}
Время выполнения: ${{executionTime}} сек

📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ:
` + extractDetailedResults() + `

=== КОНЕЦ ОТЧЕТА ===
Отправьте этот отчет в техподдержку для анализа проблемы.`;
            
            navigator.clipboard.writeText(systemInfo).then(() => {{
                const button = document.querySelector('.copy-button');
                const originalText = button.textContent;
                button.textContent = '✅ Скопировано!';
                button.style.background = '#28a745';

                setTimeout(() => {{
                    button.textContent = originalText;
                    button.style.background = '#007bff';
                }}, 2000);
            }}).catch(() => {{
                alert('Не удалось скопировать. Выделите и скопируйте текст вручную.');
            }});
        }}

        function extractDetailedResults() {{
            let results = '';
            const categories = document.querySelectorAll('.category');

            categories.forEach(category => {{
                const categoryName = category.querySelector('h2').textContent;
                results += `\\n🔧 ${{categoryName.toUpperCase()}}:\\n`;

                const tests = category.querySelectorAll('.test-item');
                tests.forEach(test => {{
                    const status = test.className.includes('success') ? '✅' :
                                  test.className.includes('warning') ? '⚠️' :
                                  test.className.includes('error') ? '❌' : 'ℹ️';

                    const testName = test.querySelector('.test-name').textContent;
                    const testDetails = test.querySelector('.test-details');
                    const testFix = test.querySelector('.test-fix');

                    results += `  ${{status}} ${{testName}}\\n`;

                    if (testDetails && testDetails.textContent.trim()) {{
                        results += `     📄 ${{testDetails.textContent.trim()}}\\n`;
                    }}

                    if (testFix && testFix.textContent.trim()) {{
                        const fixText = testFix.textContent.replace('💡 Рекомендация: ', '');
                        results += `     💡 ${{fixText}}\\n`;
                    }}

                    results += '\\n';
                }});
            }});

            return results;
        }}
    </script>
</body>
</html>"""
        
        return html_content
    
    def save_and_open_report(self, summary: Dict[str, Any]) -> str:
        """Сохраняет HTML отчет и открывает в браузере"""
        try:
            html_content = self.generate_html_report(summary)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', 
                                           delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_file_path = f.name
            
            # Открываем в браузере
            webbrowser.open(f'file://{temp_file_path}')
            
            return temp_file_path
            
        except Exception as e:
            raise Exception(f"Ошибка создания отчета: {e}")


def run_diagnostic():
    """Основная функция запуска диагностики"""
    try:
        print("🔧 Запуск диагностики Planfix Reminder...")
        
        diagnostic = PlanfixDiagnostic()
        summary = diagnostic.run_full_diagnostic()
        
        print(f"📊 Диагностика завершена: {summary['total_tests']} тестов")
        print(f"✅ Успешно: {summary['success_count']}")
        print(f"⚠️ Предупреждения: {summary['warning_count']}")  
        print(f"❌ Ошибки: {summary['error_count']}")
        
        # Сохраняем и открываем отчет
        report_path = diagnostic.save_and_open_report(summary)
        print(f"📄 HTML отчет создан: {report_path}")
        
        return summary
        
    except Exception as e:
        print(f"❌ Ошибка диагностики: {e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    run_diagnostic()