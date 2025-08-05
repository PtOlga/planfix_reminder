#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль пользовательского интерфейса
Отвечает за Toast уведомления и системный трей
"""

import tkinter as tk
from tkinter import ttk
import threading
import queue
import webbrowser
import datetime
from typing import Optional, Dict, Any, Callable
import pystray
from PIL import Image, ImageDraw
try:
    import winsound
except ImportError:
    winsound = None

class ToastNotification:
    """Кастомное Toast-уведомление"""
    
    def __init__(self, title: str, message: str, category: str, task_id: Optional[str] = None):
        self.title = title
        self.message = message
        self.category = category
        self.task_id = task_id
        self.root = None
        self.is_closed = False
        self.drag_data = {"x": 0, "y": 0}
        
        # Callback функции (устанавливаются извне)
        self.on_open_task: Optional[Callable[[str], None]] = None
        self.on_snooze: Optional[Callable[[str, str], None]] = None
        self.on_close: Optional[Callable[[str, str], None]] = None
        
        # Настройки внешнего вида по категориям
        self.styles = {
            'overdue': {
                'bg_color': '#FF4444',
                'text_color': 'white',
                'border_color': '#CC0000',
                'sound': True,
                'sound_type': 'critical'
            },
            'urgent': {
                'bg_color': '#FF8800',
                'text_color': 'white',
                'border_color': '#CC4400',
                'sound': True,
                'sound_type': 'warning'
            },
            'current': {
                'bg_color': '#0066CC',
                'text_color': 'white',
                'border_color': '#003388',
                'sound': False,
                'sound_type': None
            }
        }
    
    def create_window(self, master_root: tk.Tk, position: tuple = None):
        """Создает окно уведомления"""
        self.root = tk.Toplevel(master_root)
        self.root.withdraw()
        
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        
        style = self.styles.get(self.category, self.styles['current'])
        
        window_width = 320
        window_height = 140
        
        # Используем переданную позицию или вычисляем автоматически
        if position:
            x, y = position
        else:
            x, y = self._calculate_position(window_width, window_height)
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Создаем интерфейс
        self._create_ui(style)
        
        # Воспроизводим звук
        if style['sound']:
            threading.Thread(target=self._play_sound, args=(style['sound_type'],), daemon=True).start()
        
        self.root.deiconify()
        self._animate_in()
    
    def _create_ui(self, style: Dict[str, Any]):
        """Создает пользовательский интерфейс уведомления"""
        # Основной контейнер
        container = tk.Frame(
            self.root,
            bg=style['border_color'],
            relief='raised',
            bd=2
        )
        container.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Заголовочная панель
        title_bar = tk.Frame(container, bg=style['bg_color'], height=25)
        title_bar.pack(fill='x', padx=1, pady=(1, 0))
        title_bar.pack_propagate(False)
        
        # Иконка категории
        category_icon = {
            'overdue': '🔴',
            'urgent': '🟡',
            'current': '📋'
        }.get(self.category, '📋')
        
        icon_label = tk.Label(
            title_bar,
            text=category_icon,
            font=('Arial', 10),
            fg=style['text_color'],
            bg=style['bg_color']
        )
        icon_label.pack(side='left', padx=(5, 0), pady=2)
        
        # ID задачи
        if self.task_id:
            task_id_label = tk.Label(
                title_bar,
                text=f"#{self.task_id}",
                font=('Arial', 8),
                fg=style['text_color'],
                bg=style['bg_color']
            )
            task_id_label.pack(side='left', padx=(5, 0), pady=2)
        
        # Кнопки управления
        self._create_control_buttons(title_bar, style)
        
        # Привязываем перетаскивание к заголовку
        self._bind_dragging(title_bar, icon_label)
        
        # Область контента
        content_frame = tk.Frame(container, bg=style['bg_color'], padx=8, pady=5)
        content_frame.pack(fill='both', expand=True, padx=1, pady=(0, 1))
        
        # Заголовок задачи
        task_title = self.title.split(': ', 1)[-1] if ': ' in self.title else self.title
        title_label = tk.Label(
            content_frame,
            text=task_title,
            font=('Arial', 9, 'bold'),
            fg=style['text_color'],
            bg=style['bg_color'],
            wraplength=280,
            justify='left',
            anchor='w'
        )
        title_label.pack(fill='x', pady=(0, 3))
        
        # Сообщение
        message_lines = self.message.split('\n')[:2]
        message_text = '\n'.join(message_lines)
        
        info_label = tk.Label(
            content_frame,
            text=message_text,
            font=('Arial', 7),
            fg=style['text_color'],
            bg=style['bg_color'],
            wraplength=280,
            justify='left',
            anchor='w'
        )
        info_label.pack(fill='x', pady=(0, 5))
        
        # Кнопки действий
        self._create_action_buttons(content_frame, style)
    
    def _create_control_buttons(self, parent: tk.Frame, style: Dict[str, Any]):
        """Создает кнопки управления окном"""
        # Кнопка закрытия
        close_btn = tk.Button(
            parent,
            text="✕",
            font=('Arial', 8, 'bold'),
            command=lambda: self._handle_close('manual'),
            bg=style['text_color'],
            fg=style['bg_color'],
            relief='flat',
            width=2,
            height=1
        )
        close_btn.pack(side='right', padx=(0, 5), pady=2)
        
        # Кнопка закрепления
        pin_btn = tk.Button(
            parent,
            text="📌",
            font=('Arial', 6),
            command=self._toggle_pin,
            bg=style['text_color'],
            fg=style['bg_color'],
            relief='flat',
            width=2,
            height=1
        )
        pin_btn.pack(side='right', padx=(0, 2), pady=2)
    
    def _create_action_buttons(self, parent: tk.Frame, style: Dict[str, Any]):
        """Создает кнопки действий"""
        button_frame = tk.Frame(parent, bg=style['bg_color'])
        button_frame.pack(fill='x')
        
        # Кнопка "Открыть"
        if self.task_id:
            open_btn = tk.Button(
                button_frame,
                text="Открыть",
                font=('Arial', 7),
                command=self._handle_open_task,
                bg='white',
                fg='black',
                relief='flat',
                padx=6,
                pady=1
            )
            open_btn.pack(side='left', padx=(0, 3))
        
        # Кнопки отложения для срочных задач
        if self.category in ['overdue', 'urgent']:
            snooze_btn = tk.Button(
                button_frame,
                text="15мин",
                font=('Arial', 7),
                command=lambda: self._handle_close('snooze_15min'),
                bg='lightgray',
                fg='black',
                relief='flat',
                padx=6,
                pady=1
            )
            snooze_btn.pack(side='left', padx=(0, 3))
        
        # Кнопка "1 час"
        hour_btn = tk.Button(
            button_frame,
            text="1ч",
            font=('Arial', 7),
            command=lambda: self._handle_close('snooze_1hour'),
            bg='lightyellow',
            fg='black',
            relief='flat',
            padx=6,
            pady=1
        )
        hour_btn.pack(side='left', padx=(0, 3))
        
        # Кнопка "Готово"
        done_btn = tk.Button(
            button_frame,
            text="Готово",
            font=('Arial', 7),
            command=lambda: self._handle_close('done'),
            bg='lightgreen',
            fg='black',
            relief='flat',
            padx=6,
            pady=1
        )
        done_btn.pack(side='right')
    
    def _bind_dragging(self, *widgets):
        """Привязывает перетаскивание к виджетам"""
        for widget in widgets:
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
    
    def _calculate_position(self, width: int, height: int) -> tuple:
        """Вычисляет позицию окна"""
        # Получаем реальные размеры экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = screen_width - width - 20
        y = 20
        
        return x, y
    
    def _start_drag(self, event):
        """Начало перетаскивания"""
        self.drag_data["x"] = event.x_root - self.root.winfo_x()
        self.drag_data["y"] = event.y_root - self.root.winfo_y()
    
    def _on_drag(self, event):
        """Процесс перетаскивания"""
        x = event.x_root - self.drag_data["x"]
        y = event.y_root - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")
    
    def _toggle_pin(self):
        """Переключает закрепление окна"""
        current_topmost = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not current_topmost)
    
    def _animate_in(self):
        """Анимация появления окна"""
        alpha = 0.0
        def fade_in():
            nonlocal alpha
            if self.root and not self.is_closed:
                alpha += 0.15
                if alpha <= 0.95:
                    try:
                        self.root.attributes('-alpha', alpha)
                        self.root.after(40, fade_in)
                    except tk.TclError:
                        pass
        fade_in()
    
    def _play_sound(self, sound_type: str):
        """Воспроизводит звуковой сигнал"""
        if not winsound:
            return
        
        try:
            if sound_type == 'critical':
                for _ in range(3):
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    threading.Event().wait(0.3)
            elif sound_type == 'warning':
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
    
    def _handle_open_task(self):
        """Обработка открытия задачи"""
        if self.on_open_task and self.task_id:
            self.on_open_task(self.task_id)
    
    def _handle_close(self, reason: str):
        """Обработка закрытия уведомления"""
        if self.on_close and self.task_id:
            self.on_close(self.task_id, reason)
        
        self.is_closed = True
        if self.root:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

class ToastManager:
    """Менеджер Toast-уведомлений"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Planfix Reminder")
        
        # Очередь уведомлений
        self.notification_queue = queue.Queue()
        
        # Активные уведомления
        self.active_notifications = []
        
        # Callback функции
        self.on_open_task: Optional[Callable[[str], None]] = None
        self.on_close_notification: Optional[Callable[[str, str], None]] = None
        
        # Запускаем обработку очереди
        self._check_queue()
    
    def _check_queue(self):
        """Проверяет очередь уведомлений"""
        try:
            while True:
                toast_data = self.notification_queue.get_nowait()
                self._create_toast(toast_data)
        except queue.Empty:
            pass
        
        # Очищаем закрытые уведомления и пересчитываем позиции
        self.cleanup_notifications()
        
        self.root.after(100, self._check_queue)
    
    def _create_toast(self, toast_data: Dict[str, Any]):
        """Создает Toast уведомление"""
        toast = ToastNotification(
            title=toast_data['title'],
            message=toast_data['message'],
            category=toast_data['category'],
            task_id=toast_data.get('task_id')
        )
        
        # Устанавливаем callback функции
        toast.on_open_task = self.on_open_task
        toast.on_close = self.on_close_notification
        
        # Вычисляем позицию
        position = self._calculate_toast_position()
        
        # Создаем окно
        toast.create_window(self.root, position)
        self.active_notifications.append(toast)
    
    def _calculate_toast_position(self) -> tuple:
        """Вычисляет позицию нового уведомления с каскадным размещением"""
        # Получаем реальные размеры экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Размеры окна уведомления
        window_width = 320
        window_height = 140
        
        # Отступы от краев экрана
        margin_right = 20
        margin_top = 20
        margin_bottom = 60  # Отступ снизу для панели задач
        
        # Начальная позиция (правый верхний угол)
        start_x = screen_width - window_width - margin_right
        start_y = margin_top
        
        # Максимальное количество окон в столбце
        available_height = screen_height - margin_top - margin_bottom
        max_windows_in_column = max(1, available_height // (window_height + 10))
        
        # Количество активных уведомлений
        active_count = len(self.active_notifications)
        
        # Каскадное размещение
        if active_count < max_windows_in_column:
            # Простое вертикальное размещение для первых окон
            x = start_x
            y = start_y + (active_count * (window_height + 10))
        else:
            # Если окон много, используем каскадное смещение
            cascade_offset_x = 25  # Смещение по X для каскада
            cascade_offset_y = 15  # Дополнительное смещение по Y
            
            # Номер столбца и позиция в столбце
            column = active_count // max_windows_in_column
            position_in_column = active_count % max_windows_in_column
            
            # Вычисляем позицию с каскадным смещением
            x = start_x - (column * cascade_offset_x)
            y = start_y + (position_in_column * (window_height + 10)) + (column * cascade_offset_y)
            
            # Проверяем, не выходит ли окно за левую границу экрана
            if x < 50:  # Минимальный отступ от левого края
                # Начинаем новый ряд
                column = 0
                x = start_x
                y = start_y + (position_in_column * (window_height + 10))
        
        # Финальная проверка границ экрана  
        x = max(50, min(x, screen_width - window_width - 20))
        y = max(margin_top, min(y, screen_height - window_height - margin_bottom))
        
        return x, y
    
    def cleanup_notifications(self):
        """Очищает закрытые уведомления и пересчитывает позиции активных"""
        # Убираем закрытые уведомления
        old_count = len(self.active_notifications)
        self.active_notifications = [n for n in self.active_notifications if not n.is_closed]
        new_count = len(self.active_notifications)
        
        # Если количество изменилось, пересчитываем позиции активных окон
        if old_count != new_count and new_count > 0:
            self._reposition_active_notifications()
    
    def _reposition_active_notifications(self):
        """Пересчитывает позиции всех активных уведомлений"""
        # Получаем размеры экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        window_width = 320
        window_height = 140
        margin_right = 20
        margin_top = 20
        margin_bottom = 60
        
        start_x = screen_width - window_width - margin_right
        start_y = margin_top
        
        # Пересчитываем позицию для каждого активного уведомления
        for i, notification in enumerate(self.active_notifications):
            if notification.root and not notification.is_closed:
                try:
                    # Каскадное размещение с небольшим смещением
                    cascade_offset = min(i * 20, 100)  # Максимум 100px смещения
                    x = start_x - cascade_offset
                    y = start_y + (i * (window_height + 10))
                    
                    # Проверяем границы
                    x = max(50, min(x, screen_width - window_width - 20))
                    y = max(margin_top, min(y, screen_height - window_height - margin_bottom))
                    
                    # Плавно перемещаем окно
                    notification.root.geometry(f"+{x}+{y}")
                except tk.TclError:
                    # Окно уже закрыто
                    notification.is_closed = True
    
    def show_notification(self, title: str, message: str, category: str, task_id: Optional[str] = None):
        """Добавляет уведомление в очередь"""
        toast_data = {
            'title': title,
            'message': message,
            'category': category,
            'task_id': task_id
        }
        self.notification_queue.put(toast_data)
    
    def run(self):
        """Запускает цикл обработки событий"""
        self.root.mainloop()
    
    def stop(self):
        """Останавливает менеджер"""
        self.root.quit()

class SystemTray:
    """Системный трей приложения"""
    
    def __init__(self):
        self.tray_icon = None
        self.is_paused = False
        self.pause_until = None
        self.stats = {'total': 0, 'overdue': 0, 'urgent': 0}
        self.last_check_time = None
        
        # Callback функции
        self.on_check_now: Optional[Callable[[], None]] = None
        self.on_pause: Optional[Callable[[int], None]] = None
        self.on_resume: Optional[Callable[[], None]] = None
        self.on_quit: Optional[Callable[[], None]] = None
    
    def create_icon(self) -> Image.Image:
        """Создает иконку для трея"""
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Определяем цвет по состоянию
        if self.is_paused:
            color = (128, 128, 128)  # Серый - на паузе
        elif self.stats['overdue'] > 0:
            color = (255, 68, 68)    # Красный - есть просроченные
        elif self.stats['urgent'] > 0:
            color = (255, 136, 0)    # Оранжевый - есть срочные
        else:
            color = (0, 200, 0)      # Зеленый - все хорошо
        
        # Рисуем круг
        draw.ellipse([8, 8, 56, 56], fill=color, outline=(255, 255, 255), width=2)
        
        # Добавляем букву P
        draw.text((32, 32), "P", fill=(255, 255, 255), anchor="mm")
        
        return image
    
    def create_menu(self) -> pystray.Menu:
        """Создает меню трея"""
        # Строка состояния
        if self.is_paused:
            if self.pause_until:
                pause_str = f"На паузе до {self.pause_until.strftime('%H:%M')}"
            else:
                pause_str = "На паузе"
            status_item = pystray.MenuItem(f"⏸️ {pause_str}", None, enabled=False)
        else:
            total = self.stats['total']
            overdue = self.stats['overdue']
            status_item = pystray.MenuItem(f"🟢 Активен ({total} задач, {overdue} просроч.)", None, enabled=False)
        
        # Время последней проверки
        if self.last_check_time:
            time_str = self.last_check_time.strftime('%H:%M:%S')
            last_check_item = pystray.MenuItem(f"Последняя проверка: {time_str}", None, enabled=False)
        else:
            last_check_item = pystray.MenuItem("Еще не проверялось", None, enabled=False)
        
        # Создаем меню
        menu_items = [
            status_item,
            last_check_item,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📊 Проверить сейчас", lambda: self._handle_check_now()),
        ]
        
        # Пауза или возобновление
        if not self.is_paused:
            menu_items.extend([
                pystray.MenuItem("⏸️ Пауза на 1 час", lambda: self._handle_pause(60)),
                pystray.MenuItem("⏸️ Пауза до завтра 9:00", lambda: self._handle_pause_until_tomorrow()),
            ])
        else:
            menu_items.append(pystray.MenuItem("▶️ Возобновить", lambda: self._handle_resume()))
        
        menu_items.extend([
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🌐 Открыть Planfix", lambda: self._handle_open_planfix()),
            pystray.MenuItem("📖 Справка", lambda: self._handle_show_help()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Выход", lambda: self._handle_quit()),
        ])
        
        return pystray.Menu(*menu_items)
    
    def start(self):
        """Запускает системный трей"""
        self.tray_icon = pystray.Icon(
            name="Planfix Reminder",
            icon=self.create_icon(),
            title="Planfix Reminder",
            menu=self.create_menu()
        )
        
        # Обновляем меню каждые 30 секунд
        def update_menu():
            while True:
                threading.Event().wait(30)
                if self.tray_icon:
                    self.tray_icon.menu = self.create_menu()
        
        threading.Thread(target=update_menu, daemon=True).start()
        
        # Запускаем трей в отдельном потоке
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def update_stats(self, total: int, overdue: int, urgent: int):
        """Обновляет статистику"""
        self.stats = {'total': total, 'overdue': overdue, 'urgent': urgent}
        self.last_check_time = datetime.datetime.now()
        
        if self.tray_icon:
            self.tray_icon.icon = self.create_icon()
    
    def set_paused(self, paused: bool, until: Optional[datetime.datetime] = None):
        """Устанавливает состояние паузы"""
        self.is_paused = paused
        self.pause_until = until
        
        if self.tray_icon:
            self.tray_icon.icon = self.create_icon()
    
    def _handle_check_now(self):
        """Обработка проверки сейчас"""
        if self.on_check_now:
            self.on_check_now()
    
    def _handle_pause(self, minutes: int):
        """Обработка паузы"""
        if self.on_pause:
            self.on_pause(minutes)
    
    def _handle_pause_until_tomorrow(self):
        """Обработка паузы до завтра"""
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        tomorrow_9am = datetime.datetime.combine(tomorrow, datetime.time(9, 0))
        
        minutes = int((tomorrow_9am - datetime.datetime.now()).total_seconds() / 60)
        if self.on_pause:
            self.on_pause(minutes)
    
    def _handle_resume(self):
        """Обработка возобновления"""
        if self.on_resume:
            self.on_resume()
    
    def _handle_open_planfix(self):
        """Обработка открытия Planfix"""
        webbrowser.open("https://planfix.com")
    
    def _handle_show_help(self):
        """Обработка показа справки"""
        # Можно реализовать окно справки
        pass
    
    def _handle_quit(self):
        """Обработка выхода"""
        if self.on_quit:
            self.on_quit()
    
    def stop(self):
        """Останавливает трей"""
        if self.tray_icon:
            self.tray_icon.stop()

# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====

def test_toast_notification():
    """Тестирует Toast уведомления"""
    print("🧪 Тестирование Toast уведомлений")
    print("=" * 40)
    
    def on_open_task(task_id: str):
        print(f"📖 Открыть задачу: {task_id}")
    
    def on_close_notification(task_id: str, reason: str):
        print(f"❌ Закрыто уведомление {task_id}, причина: {reason}")
    
    # Создаем менеджер
    manager = ToastManager()
    manager.on_open_task = on_open_task
    manager.on_close_notification = on_close_notification
    
    # Показываем тестовые уведомления
    manager.show_notification(
        title="🔴 ПРОСРОЧЕНО: Тестовая задача",
        message="📅 01.12.2024\n👤 Тестовый пользователь",
        category="overdue",
        task_id="123"
    )
    
    manager.show_notification(
        title="🟡 СРОЧНО: Другая задача",
        message="📅 Сегодня\n👤 Другой пользователь",
        category="urgent",
        task_id="456"
    )
    
    # Добавляем еще несколько для тестирования каскада
    for i in range(3, 8):
        manager.show_notification(
            title=f"📋 Обычная задача {i}",
            message=f"📅 Задача номер {i}\n👤 Пользователь {i}",
            category="current",
            task_id=str(100 + i)
        )
    
    print("✅ Показано тестовых уведомлений: 7")
    print("🖱️ Взаимодействуйте с уведомлениями для тестирования каскада")
    print("💡 Закройте все окна для завершения теста")
    
    # Запускаем GUI
    manager.run()

if __name__ == "__main__":
    test_toast_notification()