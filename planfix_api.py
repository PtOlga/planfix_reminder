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
            'Authorization': f'Bearer {self.api_token}'
        })
        
        # Статусы закрытых задач
        self.closed_statuses = ['Выполненная', 'Отменена', 'Закрыта', 'Завершенная']
    
    def test_connection(self) -> bool:
        """
        Тестирует соединение с API Planfix
        
        Returns:
            bool: True если соединение успешно
        """
        try:
            if self.filter_id:
                payload = {
                    "offset": 0,
                    "pageSize": 1,
                    "filterId": int(self.filter_id),
                    "fields": "id,name"
                }
            else:
                payload = {
                    "offset": 0,
                    "pageSize": 1,
                    "fields": "id,name"
                }
            
            response = self.session.post(
                f"{self.account_url}/task/list",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') == 'fail':
                    return False
                return True
            else:
                return False
                
        except Exception:
            return False
    
    def get_filtered_tasks(self) -> List[Dict[Any, Any]]:
        """
        Получает задачи по фильтру ИЛИ по ролям пользователя
        
        Returns:
            List[Dict]: Список активных задач
        """
        try:
            if self.filter_id:
                return self._get_tasks_by_filter()
            else:
                return self._get_tasks_by_roles()
        except Exception as e:
            print(f"❌ Ошибка получения задач: {e}")
            return []
    
    def _get_tasks_by_filter(self) -> List[Dict[Any, Any]]:
        """Получает задачи по готовому фильтру Planfix"""
        try:
            payload = {
                "offset": 0,
                "pageSize": 100,
                "filterId": int(self.filter_id),
                "fields": "id,name,description,endDateTime,startDateTime,status,priority,assignees,participants,auditors,assigner,overdue"
            }
            
            response = self.session.post(
                f"{self.account_url}/task/list",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') != 'fail':
                    all_tasks = data.get('tasks', [])
                    return self._filter_active_tasks(all_tasks)
            
            return []
            
        except Exception as e:
            print(f"❌ Ошибка получения задач по фильтру: {e}")
            return []
    
    def _get_tasks_by_roles(self) -> List[Dict[Any, Any]]:
        """Получает задачи по ролям пользователя"""
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
        
        # Получаем задачи для каждой роли
        for role_type, role_name in roles_to_check:
            role_tasks = self._get_tasks_by_role_type(self.user_id, role_type)
            
            for task in role_tasks:
                task_id = task.get('id')
                if task_id not in task_ids_seen:
                    task_ids_seen.add(task_id)
                    all_tasks.append(task)
        
        return self._filter_active_tasks(all_tasks)
    
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
            
            response = self.session.post(
                f"{self.account_url}/task/list",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result') != 'fail':
                    return data.get('tasks', [])
            
            return []
            
        except Exception as e:
            print(f"❌ Ошибка получения задач для роли {role_type}: {e}")
            return []
    
    def _filter_active_tasks(self, all_tasks: List[Dict]) -> List[Dict]:
        """
        Фильтрует только активные задачи (убирает закрытые)
        
        Args:
            all_tasks: Список всех задач
            
        Returns:
            List[Dict]: Список только активных задач
        """
        active_tasks = []
        
        for task in all_tasks:
            status = task.get('status', {})
            status_name = status.get('name', '') if isinstance(status, dict) else str(status)
            
            if status_name not in self.closed_statuses:
                active_tasks.append(task)
        
        return active_tasks

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
                # Пропускаем закрытые задачи
                status = task.get('status', {})
                status_name = status.get('name', '') if isinstance(status, dict) else str(status)
                
                if status_name in closed_statuses:
                    continue
                
                # Проверяем флаг просрочки от API
                if task.get('overdue', False):
                    categorized['overdue'].append(task)
                    continue
                
                # Определяем дату окончания
                end_date = TaskProcessor._extract_end_date(task)
                
                if end_date:
                    if end_date < today:
                        categorized['overdue'].append(task)
                    elif end_date <= tomorrow:
                        categorized['urgent'].append(task)
                    else:
                        categorized['current'].append(task)
                else:
                    # Задачи без даты окончания считаем текущими
                    categorized['current'].append(task)
                    
            except Exception:
                # В случае ошибки считаем задачу текущей
                categorized['current'].append(task)
        
        return categorized
    
    @staticmethod
    def _extract_end_date(task: Dict) -> Optional[datetime.date]:
        """
        Извлекает дату окончания задачи из разных полей
        
        Args:
            task: Данные задачи
            
        Returns:
            Optional[datetime.date]: Дата окончания или None
        """
        # Пробуем разные поля с датой окончания
        date_fields = ['endDateTime', 'endDate']
        
        for field in date_fields:
            date_info = task.get(field)
            if not date_info:
                continue
            
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
                    return parsed_date
        
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
            # ISO формат с временем
            if 'T' in date_str:
                return datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            
            # Формат с дефисами
            elif '-' in date_str:
                formats_to_try = ['%d-%m-%Y', '%Y-%m-%d', '%d-%m-%y']
                for date_format in formats_to_try:
                    try:
                        return datetime.datetime.strptime(date_str, date_format).date()
                    except ValueError:
                        continue
            
            # Формат с точками
            elif '.' in date_str:
                formats_to_try = ['%d.%m.%Y', '%d.%m.%y']
                for date_format in formats_to_try:
                    try:
                        return datetime.datetime.strptime(date_str, date_format).date()
                    except ValueError:
                        continue
            
        except Exception:
            pass
        
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
        task_name = task.get('name', 'Задача без названия')
        
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
        
        return title, message
    
    @staticmethod
    def _get_formatted_end_date(task: Dict) -> str:
        """Получает отформатированную дату окончания"""
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
    
    @staticmethod
    def _get_assignee_names(task: Dict) -> str:
        """Получает имена исполнителей задачи"""
        assignees = task.get('assignees', {})
        assignee_names = []
        
        if assignees:
            users = assignees.get('users', [])
            for user in users:
                name = user.get('name', f"ID:{user.get('id')}")
                assignee_names.append(name)
        
        return ', '.join(assignee_names) if assignee_names else 'Не назначен'

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_planfix_api():
    """Тестирует PlanfixAPI"""
    print("🧪 Тестирование PlanfixAPI")
    print("=" * 40)
    
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
    api = PlanfixAPI(planfix_config, role_settings)
    
    # Тест 1: Проверка соединения
    print("1. Тестирование соединения с API...")
    if api.test_connection():
        print("✅ Соединение с API успешно")
    else:
        print("❌ Ошибка соединения с API")
        return
    
    # Тест 2: Получение задач
    print("\n2. Получение задач...")
    tasks = api.get_filtered_tasks()
    print(f"✅ Получено задач: {len(tasks)}")
    
    if tasks:
        # Тест 3: Категоризация задач
        print("\n3. Категоризация задач...")
        categorized = TaskProcessor.categorize_tasks(tasks)
        
        print(f"📊 Просроченные: {len(categorized['overdue'])}")
        print(f"📊 Срочные: {len(categorized['urgent'])}")
        print(f"📊 Текущие: {len(categorized['current'])}")
        
        # Тест 4: Форматирование сообщений
        print("\n4. Примеры форматирования:")
        for category, task_list in categorized.items():
            if task_list:
                task = task_list[0]  # Берем первую задачу
                title, message = TaskProcessor.format_task_message(task, category)
                print(f"   {category}: {title}")
                print(f"   Сообщение: {message.replace(chr(10), ' | ')}")
                break

if __name__ == "__main__":
    test_planfix_api()