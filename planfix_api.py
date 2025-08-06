#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль работы с API Planfix
Отвечает за получение задач, их фильтрацию и категоризацию
"""

import requests
import datetime
from typing import List, Dict, Any, Optional, Tuple
import json

# Импортируем систему файлового логирования
from file_logger import (
    debug, info, success, warning, error, critical,
    api_request, api_response, api_error
)

class PlanfixAPI:
    """Класс для работы с API Planfix"""
    
    def __init__(self, planfix_config: Dict[str, Any], role_settings: Dict[str, bool]):
        """
        Инициализация API клиента
        
        Args:
            planfix_config: Настройки Planfix (api_token, account_url, filter_id, user_id)
            role_settings: Настройки ролей (include_assignee, include_assigner, include_auditor)
        """
        self.account_url = planfix_config['account_url'].rstrip('/')
        self.api_token = planfix_config['api_token']
        self.filter_id = planfix_config['filter_id']
        self.user_id = planfix_config['user_id']
        self.role_settings = role_settings
        
        # Настраиваем сессию
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token[:8]}...'  # Маскируем токен в логах
        })
        
        # Статусы закрытых задач
        self.closed_statuses = ['Выполненная', 'Отменена', 'Закрыта', 'Завершенная']
        
        info(f"PlanfixAPI инициализирован для {self.account_url}", "API")
        debug(f"User ID: {self.user_id}, Filter ID: {self.filter_id or 'не используется'}", "API")
        debug(f"Роли: {self.role_settings}", "API")
        debug(f"Закрытые статусы: {self.closed_statuses}", "API")
        
        # Устанавливаем реальный токен в заголовки (без логирования)
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_token}'
        })
    
    def test_connection(self) -> bool:
        """
        Тестирует соединение с API Planfix
        
        Returns:
            bool: True если соединение успешно
        """
        try:
            info("Тестирование соединения с Planfix API", "API")
            
            if self.filter_id:
                payload = {
                    "offset": 0,
                    "pageSize": 1,
                    "filterId": int(self.filter_id),
                    "fields": "id,name"
                }
                debug(f"Тестовый запрос с фильтром ID: {self.filter_id}", "API")
            else:
                payload = {
                    "offset": 0,
                    "pageSize": 1,
                    "fields": "id,name"
                }
                debug("Тестовый запрос без фильтра", "API")
            
            url = f"{self.account_url}/task/list"
            api_request("POST", url)
            
            response = self.session.post(url, json=payload, timeout=10)
            
            api_request("POST", url, response.status_code)
            debug(f"Размер ответа: {len(response.content)} байт", "API")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result') == 'fail':
                    error_msg = data.get('error', 'Неизвестная ошибка API')
                    api_error(f"API вернуло ошибку: {error_msg}")
                    return False
                
                tasks_count = len(data.get('tasks', []))
                api_response(f"Тестовое соединение успешно, найдено задач: {tasks_count}")
                success("Соединение с Planfix API установлено", "API")
                return True
            else:
                api_error(f"HTTP ошибка: {response.status_code}")
                error(f"Ошибка HTTP при тестировании соединения: {response.status_code}", "API")
                try:
                    error_text = response.text[:200]
                    debug(f"Ответ сервера: {error_text}", "API")
                except:
                    pass
                return False
                
        except requests.exceptions.ConnectTimeout:
            api_error("Таймаут подключения к API")
            error("Таймаут подключения к Planfix API", "API")
            return False
        except requests.exceptions.ConnectionError:
            api_error("Ошибка подключения к API")
            error("Ошибка подключения к Planfix API", "API")
            return False
        except Exception as e:
            api_error(f"Неожиданная ошибка при тестировании: {e}", e)
            error(f"Неожиданная ошибка при тестировании API: {e}", "API", exc_info=True)
            return False
    
    def get_filtered_tasks(self) -> List[Dict[Any, Any]]:
        """
        Получает задачи по фильтру ИЛИ по ролям пользователя
        
        Returns:
            List[Dict]: Список активных задач
        """
        try:
            info("Начало получения задач из Planfix", "API")
            
            if self.filter_id:
                info(f"Получение задач по фильтру ID: {self.filter_id}", "API")
                tasks = self._get_tasks_by_filter()
            else:
                info("Получение задач по ролям пользователя", "API")
                tasks = self._get_tasks_by_roles()
            
            success(f"Получено задач из API: {len(tasks)}", "API")
            debug(f"ID полученных задач: {[t.get('id') for t in tasks[:10]]}", "API")  # Только первые 10
            
            return tasks
            
        except Exception as e:
            api_error(f"Критическая ошибка получения задач: {e}", e)
            error(f"Критическая ошибка получения задач: {e}", "API", exc_info=True)
            return []
    
    def _get_tasks_by_filter(self) -> List[Dict[Any, Any]]:
        """Получает задачи по готовому фильтру Planfix"""
        try:
            debug(f"Запрос задач по фильтру {self.filter_id}", "API")
            
            payload = {
                "offset": 0,
                "pageSize": 100,
                "filterId": int(self.filter_id),
                "fields": "id,name,description,endDateTime,startDateTime,status,priority,assignees,participants,auditors,assigner,overdue"
            }
            
            url = f"{self.account_url}/task/list"
            api_request("POST", url)
            
            response = self.session.post(url, json=payload, timeout=30)
            
            api_request("POST", url, response.status_code)
            api_response(f"Ответ получен", len(response.content))
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result') == 'fail':
                    error_msg = data.get('error', 'Неизвестная ошибка')
                    api_error(f"Ошибка фильтра: {error_msg}")
                    error(f"API вернуло ошибку для фильтра {self.filter_id}: {error_msg}", "API")
                    return []
                
                all_tasks = data.get('tasks', [])
                debug(f"Получено задач от фильтра: {len(all_tasks)}", "API")
                
                active_tasks = self._filter_active_tasks(all_tasks)
                info(f"Активных задач после фильтрации: {len(active_tasks)}", "API")
                
                return active_tasks
            else:
                api_error(f"HTTP ошибка при запросе фильтра: {response.status_code}")
                error(f"HTTP ошибка {response.status_code} при получении задач по фильтру", "API")
                return []
            
        except Exception as e:
            api_error(f"Ошибка получения задач по фильтру: {e}", e)
            error(f"Ошибка получения задач по фильтру {self.filter_id}: {e}", "API", exc_info=True)
            return []
    
    def _get_tasks_by_roles(self) -> List[Dict[Any, Any]]:
        """Получает задачи по ролям пользователя"""
        try:
            debug("Получение задач по ролям пользователя", "API")
            
            all_tasks = []
            task_ids_seen = set()
            
            # Роли в API Planfix: 2 = исполнитель, 3 = постановщик, 4 = контролер/участник
            roles_to_check = []
            
            if self.role_settings.get('include_assignee', True):
                roles_to_check.append((2, "ИСПОЛНИТЕЛЬ"))
            if self.role_settings.get('include_assigner', True):
                roles_to_check.append((3, "ПОСТАНОВЩИК"))
            if self.role_settings.get('include_auditor', True):
                roles_to_check.append((4, "КОНТРОЛЕР/УЧАСТНИК"))
            
            debug(f"Проверяемые роли: {[role[1] for role in roles_to_check]}", "API")
            
            # Получаем задачи для каждой роли
            for role_type, role_name in roles_to_check:
                info(f"Получение задач для роли: {role_name}", "API")
                role_tasks = self._get_tasks_by_role_type(self.user_id, role_type)
                
                debug(f"Получено задач для роли {role_name}: {len(role_tasks)}", "API")
                
                # Добавляем уникальные задачи
                new_tasks = 0
                for task in role_tasks:
                    task_id = task.get('id')
                    if task_id not in task_ids_seen:
                        task_ids_seen.add(task_id)
                        all_tasks.append(task)
                        new_tasks += 1
                
                debug(f"Новых уникальных задач от роли {role_name}: {new_tasks}", "API")
            
            info(f"Всего уникальных задач по всем ролям: {len(all_tasks)}", "API")
            
            active_tasks = self._filter_active_tasks(all_tasks)
            info(f"Активных задач после фильтрации: {len(active_tasks)}", "API")
            
            return active_tasks
            
        except Exception as e:
            api_error(f"Ошибка получения задач по ролям: {e}", e)
            error(f"Ошибка получения задач по ролям: {e}", "API", exc_info=True)
            return []
    
    def _get_tasks_by_role_type(self, user_id: str, role_type: int) -> List[Dict]:
        """
        Получает задачи по конкретному типу роли
        
        Args:
            user_id: ID пользователя
            role_type: Тип роли (2=исполнитель, 3=постановщик, 4=контролер)
            
        Returns:
            List[Dict]: Список задач для данной роли
        """
        try:
            debug(f"Запрос задач для пользователя {user_id} в роли {role_type}", "API")
            
            payload = {
                "offset": 0,
                "pageSize": 100,
                "filters": [
                    {
                        "type": role_type,
                        "operator": "equal",
                        "value": f"user:{user_id}"
                    }
                ],
                "fields": "id,name,description,endDateTime,startDateTime,status,priority,assignees,participants,auditors,assigner,overdue"
            }
            
            url = f"{self.account_url}/task/list"
            api_request("POST", url)
            
            response = self.session.post(url, json=payload, timeout=30)
            
            api_request("POST", url, response.status_code)
            api_response(f"Ответ для роли {role_type} получен", len(response.content))
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('result') == 'fail':
                    error_msg = data.get('error', 'Неизвестная ошибка')
                    api_error(f"Ошибка запроса роли {role_type}: {error_msg}")
                    warning(f"API вернуло ошибку для роли {role_type}: {error_msg}", "API")
                    return []
                
                tasks = data.get('tasks', [])
                debug(f"Получено задач для роли {role_type}: {len(tasks)}", "API")
                return tasks
            else:
                api_error(f"HTTP ошибка для роли {role_type}: {response.status_code}")
                warning(f"HTTP ошибка {response.status_code} для роли {role_type}", "API")
                return []
            
        except Exception as e:
            api_error(f"Ошибка получения задач для роли {role_type}: {e}", e)
            error(f"Ошибка получения задач для роли {role_type}: {e}", "API", exc_info=True)
            return []
    
    def _filter_active_tasks(self, all_tasks: List[Dict]) -> List[Dict]:
        """
        Фильтрует только активные задачи (убирает закрытые)
        
        Args:
            all_tasks: Список всех задач
            
        Returns:
            List[Dict]: Список только активных задач
        """
        try:
            debug(f"Фильтрация активных задач из {len(all_tasks)}", "API")
            
            active_tasks = []
            closed_count = 0
            
            for task in all_tasks:
                status = task.get('status', {})
                status_name = status.get('name', '') if isinstance(status, dict) else str(status)
                
                if status_name in self.closed_statuses:
                    closed_count += 1
                    debug(f"Задача #{task.get('id')} пропущена: статус '{status_name}'", "API")
                else:
                    active_tasks.append(task)
            
            info(f"Отфильтровано активных задач: {len(active_tasks)}, закрытых: {closed_count}", "API")
            
            return active_tasks
            
        except Exception as e:
            error(f"Ошибка фильтрации активных задач: {e}", "API", exc_info=True)
            return all_tasks  # Возвращаем все задачи в случае ошибки

class TaskProcessor:
    """Класс для обработки и категоризации задач"""
    
    @staticmethod
    def categorize_tasks(tasks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Категоризует задачи на текущие, просроченные и срочные
        
        Args:
            tasks: Список задач для категоризации
            
        Returns:
            Dict[str, List[Dict]]: Словарь с категориями задач
        """
        try:
            info(f"Начало категоризации {len(tasks)} задач", "PROCESSOR")
            
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            
            categorized = {
                'overdue': [],
                'urgent': [],
                'current': []
            }
            
            closed_statuses = ['Выполненная', 'Отменена', 'Закрыта', 'Завершенная']
            
            for task in tasks:
                try:
                    task_id = task.get('id')
                    
                    # Пропускаем закрытые задачи
                    status = task.get('status', {})
                    status_name = status.get('name', '') if isinstance(status, dict) else str(status)
                    
                    if status_name in closed_statuses:
                        debug(f"Задача #{task_id} пропущена при категоризации: статус '{status_name}'", "PROCESSOR")
                        continue
                    
                    # Проверяем флаг просрочки от API
                    if task.get('overdue', False):
                        categorized['overdue'].append(task)
                        debug(f"Задача #{task_id} помечена как просроченная API", "PROCESSOR")
                        continue
                    
                    # Определяем дату окончания
                    end_date = TaskProcessor._extract_end_date(task)
                    
                    if end_date:
                        if end_date < today:
                            categorized['overdue'].append(task)
                            debug(f"Задача #{task_id} просрочена: {end_date} < {today}", "PROCESSOR")
                        elif end_date <= tomorrow:
                            categorized['urgent'].append(task)
                            debug(f"Задача #{task_id} срочная: {end_date} <= {tomorrow}", "PROCESSOR")
                        else:
                            categorized['current'].append(task)
                            debug(f"Задача #{task_id} текущая: {end_date} > {tomorrow}", "PROCESSOR")
                    else:
                        # Задачи без даты окончания считаем текущими
                        categorized['current'].append(task)
                        debug(f"Задача #{task_id} без даты - помещена в текущие", "PROCESSOR")
                        
                except Exception as task_error:
                    # В случае ошибки считаем задачу текущей
                    categorized['current'].append(task)
                    warning(f"Ошибка категоризации задачи #{task.get('id')}: {task_error}", "PROCESSOR")
            
            result_summary = {
                'overdue': len(categorized['overdue']),
                'urgent': len(categorized['urgent']),
                'current': len(categorized['current'])
            }
            
            success(f"Категоризация завершена: {result_summary}", "PROCESSOR")
            
            return categorized
            
        except Exception as e:
            error(f"Критическая ошибка категоризации задач: {e}", "PROCESSOR", exc_info=True)
            # Возвращаем все задачи как текущие в случае критической ошибки
            return {
                'overdue': [],
                'urgent': [],
                'current': tasks
            }
    
    @staticmethod
    def _extract_end_date(task: Dict) -> Optional[datetime.date]:
        """
        Извлекает дату окончания задачи из разных полей
        
        Args:
            task: Данные задачи
            
        Returns:
            Optional[datetime.date]: Дата окончания или None
        """
        try:
            task_id = task.get('id')
            
            # Пробуем разные поля с датой окончания
            date_fields = ['endDateTime', 'endDate']
            
            for field in date_fields:
                date_info = task.get(field)
                if not date_info:
                    continue
                
                debug(f"Задача #{task_id}: найдено поле {field} = {date_info}", "PROCESSOR")
                
                # Если поле - словарь (объект с вложенными полями)
                if isinstance(date_info, dict):
                    date_str = (date_info.get('datetime') or 
                              date_info.get('date') or 
                              date_info.get('dateTimeUtcSeconds'))
                else:
                    date_str = str(date_info)
                
                if date_str:
                    parsed_date = TaskProcessor._parse_date_string(date_str)
                    if parsed_date:
                        debug(f"Задача #{task_id}: дата окончания {parsed_date}", "PROCESSOR")
                        return parsed_date
                    else:
                        debug(f"Задача #{task_id}: не удалось распарсить дату '{date_str}'", "PROCESSOR")
            
            debug(f"Задача #{task_id}: дата окончания не найдена", "PROCESSOR")
            return None
            
        except Exception as e:
            warning(f"Ошибка извлечения даты для задачи #{task.get('id')}: {e}", "PROCESSOR")
            return None
    
    @staticmethod
    def _parse_date_string(date_str: str) -> Optional[datetime.date]:
        """
        Парсит строку с датой в различных форматах
        
        Args:
            date_str: Строка с датой
            
        Returns:
            Optional[datetime.date]: Распарсенная дата или None
        """
        try:
            debug(f"Парсинг даты: '{date_str}'", "PROCESSOR")
            
            # ISO формат с временем
            if 'T' in date_str:
                parsed = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                debug(f"Дата распарсена как ISO: {parsed}", "PROCESSOR")
                return parsed
            
            # Формат с дефисами
            elif '-' in date_str:
                formats_to_try = ['%d-%m-%Y', '%Y-%m-%d', '%d-%m-%y']
                for date_format in formats_to_try:
                    try:
                        parsed = datetime.datetime.strptime(date_str, date_format).date()
                        debug(f"Дата распарсена как {date_format}: {parsed}", "PROCESSOR")
                        return parsed
                    except ValueError:
                        continue
            
            # Формат с точками
            elif '.' in date_str:
                formats_to_try = ['%d.%m.%Y', '%d.%m.%y']
                for date_format in formats_to_try:
                    try:
                        parsed = datetime.datetime.strptime(date_str, date_format).date()
                        debug(f"Дата распарсена как {date_format}: {parsed}", "PROCESSOR")
                        return parsed
                    except ValueError:
                        continue
            
            warning(f"Не удалось распарсить дату: '{date_str}'", "PROCESSOR")
            
        except Exception as e:
            warning(f"Ошибка парсинга даты '{date_str}': {e}", "PROCESSOR")
        
        return None
    
    @staticmethod
    def format_task_message(task: Dict, category: str) -> Tuple[str, str]:
        """
        Форматирует заголовок и текст уведомления для задачи
        
        Args:
            task: Данные задачи
            category: Категория задачи (overdue, urgent, current)
            
        Returns:
            Tuple[str, str]: (заголовок, сообщение)
        """
        try:
            task_id = task.get('id')
            task_name = task.get('name', 'Задача без названия')
            
            debug(f"Форматирование сообщения для задачи #{task_id} ({category})", "PROCESSOR")
            
            # Получаем дату окончания
            end_date_str = TaskProcessor._get_formatted_end_date(task)
            
            # Получаем исполнителей
            assignee_text = TaskProcessor._get_assignee_names(task)
            
            # Формируем заголовок
            title_prefix = {
                'overdue': '🔴 ПРОСРОЧЕНО',
                'urgent': '🟡 СРОЧНО', 
                'current': '📋 ЗАДАЧА'
            }.get(category, '📋 ЗАДАЧА')
            
            # Ограничиваем длину заголовка
            safe_limit = 45
            separator = ": "
            prefix_and_separator_length = len(title_prefix) + len(separator)
            max_task_name_length = safe_limit - prefix_and_separator_length
            
            if max_task_name_length <= 3:
                task_name_short = "..."
            elif len(task_name) > max_task_name_length:
                task_name_short = task_name[:max_task_name_length-3] + "..."
            else:
                task_name_short = task_name
            
            title = f"{title_prefix}{separator}{task_name_short}"
            
            # Формируем сообщение
            message_parts = [f"📅 {end_date_str}", f"👤 {assignee_text}"]
            message = '\n'.join(message_parts)
            
            debug(f"Сформирован заголовок: '{title}'", "PROCESSOR")
            debug(f"Сформировано сообщение: '{message.replace(chr(10), ' | ')}'", "PROCESSOR")
            
            return title, message
            
        except Exception as e:
            error(f"Ошибка форматирования сообщения для задачи #{task.get('id')}: {e}", "PROCESSOR", exc_info=True)
            return f"📋 ЗАДАЧА: {task.get('name', 'Ошибка форматирования')}", "Ошибка отображения данных"
    
    @staticmethod
    def _get_formatted_end_date(task: Dict) -> str:
        """Получает отформатированную дату окончания"""
        try:
            end_date_info = task.get('endDateTime')
            if not end_date_info:
                return 'Не указана'
            
            if isinstance(end_date_info, dict):
                end_date_str = (end_date_info.get('date') or 
                              end_date_info.get('datetime') or 
                              'Указана')
            else:
                end_date_str = str(end_date_info)
            
            # Пытаемся отформатировать дату
            if end_date_str and end_date_str not in ['Не указана', 'Указана']:
                try:
                    if 'T' in end_date_str:
                        date_obj = datetime.datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        return date_obj.strftime('%d.%m.%Y')
                    elif '-' in end_date_str and len(end_date_str) >= 8:
                        for date_format in ['%d-%m-%Y', '%Y-%m-%d', '%d-%m-%y']:
                            try:
                                date_obj = datetime.datetime.strptime(end_date_str, date_format)
                                return date_obj.strftime('%d.%m.%Y')
                            except ValueError:
                                continue
                except Exception:
                    pass
            
            return end_date_str
            
        except Exception as e:
            warning(f"Ошибка форматирования даты для задачи #{task.get('id')}: {e}", "PROCESSOR")
            return 'Ошибка даты'
    
    @staticmethod
    def _get_assignee_names(task: Dict) -> str:
        """Получает имена исполнителей задачи"""
        try:
            assignees = task.get('assignees', {})
            assignee_names = []
            
            if assignees:
                users = assignees.get('users', [])
                for user in users:
                    name = user.get('name', f"ID:{user.get('id')}")
                    assignee_names.append(name)
            
            result = ', '.join(assignee_names) if assignee_names else 'Не назначен'
            debug(f"Исполнители задачи #{task.get('id')}: {result}", "PROCESSOR")
            return result
            
        except Exception as e:
            warning(f"Ошибка получения исполнителей для задачи #{task.get('id')}: {e}", "PROCESSOR")
            return 'Ошибка получения'

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_planfix_api():
    """Тестирует PlanfixAPI с файловым логированием"""
    # Настраиваем логирование для тестов
    from file_logger import setup_logging, get_logs_directory, startup
    setup_logging(debug_mode=True, console_debug=True)
    
    startup("Тестирование PlanfixAPI с файловым логированием")
    
    # Тестовые настройки (замените на реальные)
    planfix_config = {
        'api_token': '8abc3f545edfac301b30d6e1d0600323',
        'account_url': 'https://l-s.planfix.com/rest',
        'filter_id': None,  # Используем роли
        'user_id': '4'
    }
    
    role_settings = {
        'include_assignee': True,
        'include_assigner': True,
        'include_auditor': True
    }
    
    # Создаем API клиент
    info("=== ТЕСТ 1: Создание API клиента ===", "TEST")
    api = PlanfixAPI(planfix_config, role_settings)
    success("API клиент создан", "TEST")
    
    # Тест 1: Проверка соединения
    info("=== ТЕСТ 2: Проверка соединения с API ===", "TEST")
    if api.test_connection():
        success("Соединение с API установлено", "TEST")
    else:
        error("Ошибка соединения с API", "TEST")
        warning("Завершение тестов из-за отсутствия соединения", "TEST")
        return
    
    # Тест 2: Получение задач
    info("=== ТЕСТ 3: Получение задач ===", "TEST")
    tasks = api.get_filtered_tasks()
    success(f"Получено задач: {len(tasks)}", "TEST")
    
    if tasks:
        # Тест 3: Категоризация задач
        info("=== ТЕСТ 4: Категоризация задач ===", "TEST")
        categorized = TaskProcessor.categorize_tasks(tasks)
        
        overdue_count = len(categorized['overdue'])
        urgent_count = len(categorized['urgent'])
        current_count = len(categorized['current'])
        
        success(f"Просроченные: {overdue_count}", "TEST")
        success(f"Срочные: {urgent_count}", "TEST")
        success(f"Текущие: {current_count}", "TEST")
        
        # Тест 4: Форматирование сообщений
        info("=== ТЕСТ 5: Форматирование сообщений ===", "TEST")
        for category, task_list in categorized.items():
            if task_list:
                task = task_list[0]  # Берем первую задачу
                title, message = TaskProcessor.format_task_message(task, category)
                info(f"Пример {category}:", "TEST")
                info(f"  Заголовок: {title}", "TEST")
                info(f"  Сообщение: {message.replace(chr(10), ' | ')}", "TEST")
                break
    else:
        warning("Задачи не найдены - часть тестов пропущена", "TEST")
    
    startup(f"Тестирование завершено! Логи сохранены в: {get_logs_directory()}")
    success("Все тесты PlanfixAPI пройдены", "TEST")

if __name__ == "__main__":
    test_planfix_api()