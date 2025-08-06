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
import tempfile

try:
    import winsound
except ImportError:
    winsound = None

# Импортируем систему файлового логирования
from file_logger import debug, info, success, warning, error, critical

# Импортируем модуль диагностики
try:
    from diagnostic_module import run_diagnostic
    DIAGNOSTIC_AVAILABLE = True
except ImportError:
    DIAGNOSTIC_AVAILABLE = False
    warning("Модуль диагностики недоступен", "UI")


class ToastNotification:
    """Кастомное Toast-уведомление"""

    def __init__(
        self, title: str, message: str, category: str, task_id: Optional[str] = None
    ):
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
            "overdue": {
                "bg_color": "#FF4444",
                "text_color": "white",
                "border_color": "#CC0000",
                "sound": True,
                "sound_type": "critical",
            },
            "urgent": {
                "bg_color": "#FF8800",
                "text_color": "white",
                "border_color": "#CC4400",
                "sound": True,
                "sound_type": "warning",
            },
            "current": {
                "bg_color": "#0066CC",
                "text_color": "white",
                "border_color": "#003388",
                "sound": False,
                "sound_type": None,
            },
        }

        debug(
            f"Создано Toast уведомление: задача #{task_id}, категория {category}", "UI"
        )

    def create_window(self, master_root: tk.Tk, position: tuple = None):
        """Создает окно уведомления"""
        try:
            debug(
                f"Создание окна для задачи #{self.task_id} на позиции {position}", "UI"
            )

            self.root = tk.Toplevel(master_root)
            self.root.withdraw()

            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.95)

            style = self.styles.get(self.category, self.styles["current"])

            window_width = 320
            window_height = 140

            # Используем переданную позицию или вычисляем автоматически
            if position:
                x, y = position
                debug(f"Использована переданная позиция: {x}, {y}", "UI")
            else:
                x, y = self._calculate_position(window_width, window_height)
                debug(f"Вычислена автоматическая позиция: {x}, {y}", "UI")

            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

            # Создаем интерфейс
            self._create_ui(style)

            # Воспроизводим звук
            if style["sound"]:
                debug(f"Воспроизведение звука типа: {style['sound_type']}", "UI")
                threading.Thread(
                    target=self._play_sound, args=(style["sound_type"],), daemon=True
                ).start()
            else:
                debug("Звук отключен для данной категории", "UI")

            self.root.deiconify()
            self._animate_in()

            success(
                f"Окно уведомления для задачи #{self.task_id} создано успешно", "UI"
            )

        except Exception as e:
            error(
                f"Ошибка создания окна уведомления для задачи #{self.task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def _create_ui(self, style: Dict[str, Any]):
        """Создает пользовательский интерфейс уведомления"""
        try:
            debug(f"Создание UI для задачи #{self.task_id}", "UI")

            # Основной контейнер
            container = tk.Frame(
                self.root, bg=style["border_color"], relief="raised", bd=2
            )
            container.pack(fill="both", expand=True, padx=2, pady=2)

            # Заголовочная панель
            title_bar = tk.Frame(container, bg=style["bg_color"], height=25)
            title_bar.pack(fill="x", padx=1, pady=(1, 0))
            title_bar.pack_propagate(False)

            # Иконка категории
            category_icon = {"overdue": "🔴", "urgent": "🟡", "current": "📋"}.get(
                self.category, "📋"
            )

            icon_label = tk.Label(
                title_bar,
                text=category_icon,
                font=("Arial", 10),
                fg=style["text_color"],
                bg=style["bg_color"],
            )
            icon_label.pack(side="left", padx=(5, 0), pady=2)

            # ID задачи
            if self.task_id:
                task_id_label = tk.Label(
                    title_bar,
                    text=f"#{self.task_id}",
                    font=("Arial", 8),
                    fg=style["text_color"],
                    bg=style["bg_color"],
                )
                task_id_label.pack(side="left", padx=(5, 0), pady=2)

            # Кнопки управления
            self._create_control_buttons(title_bar, style)

            # Привязываем перетаскивание к заголовку
            self._bind_dragging(title_bar, icon_label)

            # Область контента
            content_frame = tk.Frame(container, bg=style["bg_color"], padx=8, pady=5)
            content_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))

            # Заголовок задачи
            task_title = (
                self.title.split(": ", 1)[-1] if ": " in self.title else self.title
            )
            title_label = tk.Label(
                content_frame,
                text=task_title,
                font=("Arial", 9, "bold"),
                fg=style["text_color"],
                bg=style["bg_color"],
                wraplength=280,
                justify="left",
                anchor="w",
            )
            title_label.pack(fill="x", pady=(0, 3))

            # Сообщение
            message_lines = self.message.split("\n")[:2]
            message_text = "\n".join(message_lines)

            info_label = tk.Label(
                content_frame,
                text=message_text,
                font=("Arial", 7),
                fg=style["text_color"],
                bg=style["bg_color"],
                wraplength=280,
                justify="left",
                anchor="w",
            )
            info_label.pack(fill="x", pady=(0, 5))

            # Кнопки действий
            self._create_action_buttons(content_frame, style)

            debug(f"UI для задачи #{self.task_id} создан успешно", "UI")

        except Exception as e:
            error(
                f"Ошибка создания UI для задачи #{self.task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def _create_control_buttons(self, parent: tk.Frame, style: Dict[str, Any]):
        """Создает кнопки управления окном"""
        try:
            # Кнопка закрытия
            close_btn = tk.Button(
                parent,
                text="✕",
                font=("Arial", 8, "bold"),
                command=lambda: self._handle_close("manual"),
                bg=style["text_color"],
                fg=style["bg_color"],
                relief="flat",
                width=2,
                height=1,
            )
            close_btn.pack(side="right", padx=(0, 5), pady=2)

            # Кнопка закрепления
            pin_btn = tk.Button(
                parent,
                text="📌",
                font=("Arial", 6),
                command=self._toggle_pin,
                bg=style["text_color"],
                fg=style["bg_color"],
                relief="flat",
                width=2,
                height=1,
            )
            pin_btn.pack(side="right", padx=(0, 2), pady=2)

            debug(f"Кнопки управления для задачи #{self.task_id} созданы", "UI")

        except Exception as e:
            error(
                f"Ошибка создания кнопок управления для задачи #{self.task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def _create_action_buttons(self, parent: tk.Frame, style: Dict[str, Any]):
        """Создает кнопки действий"""
        try:
            button_frame = tk.Frame(parent, bg=style["bg_color"])
            button_frame.pack(fill="x")

            buttons_created = []

            # Кнопка "Открыть"
            if self.task_id:
                open_btn = tk.Button(
                    button_frame,
                    text="Открыть",
                    font=("Arial", 7),
                    command=self._handle_open_task,
                    bg="white",
                    fg="black",
                    relief="flat",
                    padx=6,
                    pady=1,
                )
                open_btn.pack(side="left", padx=(0, 3))
                buttons_created.append("Открыть")

            # Кнопки отложения для срочных задач
            if self.category in ["overdue", "urgent"]:
                snooze_btn = tk.Button(
                    button_frame,
                    text="15мин",
                    font=("Arial", 7),
                    command=lambda: self._handle_close("snooze_15min"),
                    bg="lightgray",
                    fg="black",
                    relief="flat",
                    padx=6,
                    pady=1,
                )
                snooze_btn.pack(side="left", padx=(0, 3))
                buttons_created.append("15мин")

            # Кнопка "1 час"
            hour_btn = tk.Button(
                button_frame,
                text="1ч",
                font=("Arial", 7),
                command=lambda: self._handle_close("snooze_1hour"),
                bg="lightyellow",
                fg="black",
                relief="flat",
                padx=6,
                pady=1,
            )
            hour_btn.pack(side="left", padx=(0, 3))
            buttons_created.append("1ч")

            # Кнопка "Готово"
            done_btn = tk.Button(
                button_frame,
                text="Готово",
                font=("Arial", 7),
                command=lambda: self._handle_close("done"),
                bg="lightgreen",
                fg="black",
                relief="flat",
                padx=6,
                pady=1,
            )
            done_btn.pack(side="right")
            buttons_created.append("Готово")

            debug(
                f"Кнопки действий для задачи #{self.task_id}: {buttons_created}", "UI"
            )

        except Exception as e:
            error(
                f"Ошибка создания кнопок действий для задачи #{self.task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def _bind_dragging(self, *widgets):
        """Привязывает перетаскивание к виджетам"""
        try:
            for widget in widgets:
                widget.bind("<Button-1>", self._start_drag)
                widget.bind("<B1-Motion>", self._on_drag)
            debug(
                f"Перетаскивание привязано к {len(widgets)} виджетам для задачи #{self.task_id}",
                "UI",
            )
        except Exception as e:
            warning(
                f"Ошибка привязки перетаскивания для задачи #{self.task_id}: {e}", "UI"
            )

    def _calculate_position(self, width: int, height: int) -> tuple:
        """Вычисляет позицию окна"""
        try:
            # Получаем реальные размеры экрана
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            x = screen_width - width - 20
            y = 20

            debug(
                f"Размеры экрана: {screen_width}x{screen_height}, позиция окна: {x},{y}",
                "UI",
            )
            return x, y

        except Exception as e:
            error(f"Ошибка вычисления позиции для задачи #{self.task_id}: {e}", "UI")
            return 100, 100  # Безопасная позиция по умолчанию

    def _start_drag(self, event):
        """Начало перетаскивания"""
        try:
            self.drag_data["x"] = event.x_root - self.root.winfo_x()
            self.drag_data["y"] = event.y_root - self.root.winfo_y()
            debug(
                f"Начало перетаскивания задачи #{self.task_id}: {self.drag_data}", "UI"
            )
        except Exception as e:
            warning(
                f"Ошибка начала перетаскивания для задачи #{self.task_id}: {e}", "UI"
            )

    def _on_drag(self, event):
        """Процесс перетаскивания"""
        try:
            x = event.x_root - self.drag_data["x"]
            y = event.y_root - self.drag_data["y"]
            self.root.geometry(f"+{x}+{y}")
        except Exception as e:
            warning(f"Ошибка перетаскивания для задачи #{self.task_id}: {e}", "UI")

    def _toggle_pin(self):
        """Переключает закрепление окна"""
        try:
            current_topmost = self.root.attributes("-topmost")
            new_topmost = not current_topmost
            self.root.attributes("-topmost", new_topmost)
            debug(
                f"Переключение закрепления задачи #{self.task_id}: {'закреплено' if new_topmost else 'откреплено'}",
                "UI",
            )
        except Exception as e:
            warning(
                f"Ошибка переключения закрепления для задачи #{self.task_id}: {e}", "UI"
            )

    def _animate_in(self):
        """Анимация появления окна"""
        try:
            alpha = 0.0

            def fade_in():
                nonlocal alpha
                if self.root and not self.is_closed:
                    alpha += 0.15
                    if alpha <= 0.95:
                        try:
                            self.root.attributes("-alpha", alpha)
                            self.root.after(40, fade_in)
                        except tk.TclError:
                            pass
                    else:
                        debug(
                            f"Анимация появления завершена для задачи #{self.task_id}",
                            "UI",
                        )

            fade_in()
        except Exception as e:
            warning(f"Ошибка анимации для задачи #{self.task_id}: {e}", "UI")

    def _play_sound(self, sound_type: str):
        """Воспроизводит звуковой сигнал"""
        try:
            if not winsound:
                debug("Модуль winsound недоступен - звук не воспроизведен", "UI")
                return

            debug(
                f"Воспроизведение звука '{sound_type}' для задачи #{self.task_id}", "UI"
            )

            if sound_type == "critical":
                for i in range(3):
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    debug(f"Критический звук #{i+1} для задачи #{self.task_id}", "UI")
                    threading.Event().wait(0.3)
            elif sound_type == "warning":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                debug(f"Предупреждающий звук для задачи #{self.task_id}", "UI")

            success(
                f"Звук '{sound_type}' воспроизведен для задачи #{self.task_id}", "UI"
            )

        except Exception as e:
            warning(
                f"Ошибка воспроизведения звука для задачи #{self.task_id}: {e}", "UI"
            )

    def _handle_open_task(self):
        """Обработка открытия задачи"""
        try:
            debug(f"Обработка открытия задачи #{self.task_id}", "UI")
            if self.on_open_task and self.task_id:
                self.on_open_task(self.task_id)
                success(f"Задача #{self.task_id} передана для открытия", "UI")
            else:
                warning(
                    f"Невозможно открыть задачу #{self.task_id}: отсутствует callback или ID",
                    "UI",
                )
        except Exception as e:
            error(
                f"Ошибка обработки открытия задачи #{self.task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def _handle_close(self, reason: str):
        """Обработка закрытия уведомления"""
        try:
            debug(f"Обработка закрытия задачи #{self.task_id}, причина: {reason}", "UI")

            if self.on_close and self.task_id:
                self.on_close(self.task_id, reason)
                info(f"Задача #{self.task_id} закрыта с причиной: {reason}", "UI")

            self.is_closed = True
            if self.root:
                try:
                    self.root.destroy()
                    success(f"Окно задачи #{self.task_id} уничтожено", "UI")
                except tk.TclError as e:
                    debug(f"Окно задачи #{self.task_id} уже было закрыто: {e}", "UI")

        except Exception as e:
            error(f"Ошибка закрытия задачи #{self.task_id}: {e}", "UI", exc_info=True)


class ToastManager:
    """Менеджер Toast-уведомлений"""

    def __init__(self):
        try:
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

            info("ToastManager инициализирован", "UI")

        except Exception as e:
            critical(
                f"Критическая ошибка инициализации ToastManager: {e}",
                "UI",
                exc_info=True,
            )
            raise

    def _check_queue(self):
        """Проверяет очередь уведомлений"""
        try:
            processed_count = 0
            while True:
                try:
                    toast_data = self.notification_queue.get_nowait()
                    self._create_toast(toast_data)
                    processed_count += 1
                except queue.Empty:
                    break

            if processed_count > 0:
                debug(f"Обработано уведомлений из очереди: {processed_count}", "UI")

            # Очищаем закрытые уведомления и пересчитываем позиции
            self.cleanup_notifications()

            self.root.after(100, self._check_queue)

        except Exception as e:
            error(f"Ошибка проверки очереди уведомлений: {e}", "UI", exc_info=True)
            # Продолжаем работу даже при ошибке
            self.root.after(1000, self._check_queue)  # Увеличенная пауза при ошибке

    def _create_toast(self, toast_data: Dict[str, Any]):
        """Создает Toast уведомление"""
        try:
            task_id = toast_data.get("task_id")
            category = toast_data.get("category")

            debug(f"Создание Toast для задачи #{task_id} ({category})", "UI")

            toast = ToastNotification(
                title=toast_data["title"],
                message=toast_data["message"],
                category=category,
                task_id=task_id,
            )

            # Устанавливаем callback функции
            toast.on_open_task = self.on_open_task
            toast.on_close = self.on_close_notification

            # Вычисляем позицию
            position = self._calculate_toast_position()
            debug(f"Вычисленная позиция для задачи #{task_id}: {position}", "UI")

            # Создаем окно
            toast.create_window(self.root, position)
            self.active_notifications.append(toast)

            success(
                f"Toast создан для задачи #{task_id}, всего активных: {len(self.active_notifications)}",
                "UI",
            )

        except Exception as e:
            error(f"Ошибка создания Toast: {e}", "UI", exc_info=True)

    def _calculate_toast_position(self) -> tuple:
        """Вычисляет позицию нового уведомления с каскадным размещением"""
        try:
            # Получаем реальные размеры экрана
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            debug(f"Размеры экрана: {screen_width}x{screen_height}", "UI")

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

            debug(
                f"Активных уведомлений: {active_count}, макс. в столбце: {max_windows_in_column}",
                "UI",
            )

            # Каскадное размещение
            if active_count < max_windows_in_column:
                # Простое вертикальное размещение для первых окон
                x = start_x
                y = start_y + (active_count * (window_height + 10))
                debug(f"Простое вертикальное размещение: {x}, {y}", "UI")
            else:
                # Если окон много, используем каскадное смещение
                cascade_offset_x = 25  # Смещение по X для каскада
                cascade_offset_y = 15  # Дополнительное смещение по Y

                # Номер столбца и позиция в столбце
                column = active_count // max_windows_in_column
                position_in_column = active_count % max_windows_in_column

                # Вычисляем позицию с каскадным смещением
                x = start_x - (column * cascade_offset_x)
                y = (
                    start_y
                    + (position_in_column * (window_height + 10))
                    + (column * cascade_offset_y)
                )

                debug(
                    f"Каскадное размещение: столбец {column}, позиция {position_in_column}, координаты {x},{y}",
                    "UI",
                )

                # Проверяем, не выходит ли окно за левую границу экрана
                if x < 50:  # Минимальный отступ от левого края
                    # Начинаем новый ряд
                    column = 0
                    x = start_x
                    y = start_y + (position_in_column * (window_height + 10))
                    debug(f"Коррекция границ: новые координаты {x},{y}", "UI")

            # Финальная проверка границ экрана
            x = max(50, min(x, screen_width - window_width - 20))
            y = max(margin_top, min(y, screen_height - window_height - margin_bottom))

            debug(f"Финальная позиция после проверки границ: {x},{y}", "UI")

            return x, y

        except Exception as e:
            error(f"Ошибка вычисления позиции Toast: {e}", "UI", exc_info=True)
            return 100, 100  # Безопасная позиция по умолчанию

    def cleanup_notifications(self):
        """Очищает закрытые уведомления и пересчитывает позиции активных"""
        try:
            # Убираем закрытые уведомления
            old_count = len(self.active_notifications)
            self.active_notifications = [
                n for n in self.active_notifications if not n.is_closed
            ]
            new_count = len(self.active_notifications)

            if old_count != new_count:
                debug(f"Очистка уведомлений: было {old_count}, стало {new_count}", "UI")

                # Если количество изменилось, пересчитываем позиции активных окон
                if new_count > 0:
                    self._reposition_active_notifications()

        except Exception as e:
            error(f"Ошибка очистки уведомлений: {e}", "UI", exc_info=True)

    def _reposition_active_notifications(self):
        """Пересчитывает позиции всех активных уведомлений"""
        try:
            debug(
                f"Перепозиционирование {len(self.active_notifications)} активных уведомлений",
                "UI",
            )

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

            repositioned_count = 0

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
                        y = max(
                            margin_top,
                            min(y, screen_height - window_height - margin_bottom),
                        )

                        # Плавно перемещаем окно
                        notification.root.geometry(f"+{x}+{y}")
                        repositioned_count += 1

                        debug(
                            f"Уведомление #{notification.task_id} перемещено в позицию {x},{y}",
                            "UI",
                        )

                    except tk.TclError:
                        # Окно уже закрыто
                        notification.is_closed = True
                        debug(
                            f"Уведомление #{notification.task_id} помечено как закрытое",
                            "UI",
                        )
                    except Exception as e:
                        warning(
                            f"Ошибка перемещения уведомления #{notification.task_id}: {e}",
                            "UI",
                        )

            if repositioned_count > 0:
                success(f"Перепозиционировано уведомлений: {repositioned_count}", "UI")

        except Exception as e:
            error(f"Ошибка перепозиционирования уведомлений: {e}", "UI", exc_info=True)

    def show_notification(
        self, title: str, message: str, category: str, task_id: Optional[str] = None
    ):
        """Добавляет уведомление в очередь"""
        try:
            toast_data = {
                "title": title,
                "message": message,
                "category": category,
                "task_id": task_id,
            }
            self.notification_queue.put(toast_data)

            debug(
                f"Уведомление добавлено в очередь: задача #{task_id} ({category})", "UI"
            )
            info(f"Запланировано показать уведомление для задачи #{task_id}", "UI")

        except Exception as e:
            error(
                f"Ошибка добавления уведомления в очередь для задачи #{task_id}: {e}",
                "UI",
                exc_info=True,
            )

    def run(self):
        """Запускает цикл обработки событий"""
        try:
            info("Запуск GUI цикла ToastManager", "UI")
            self.root.mainloop()
        except Exception as e:
            critical(f"Критическая ошибка GUI цикла: {e}", "UI", exc_info=True)
            raise

    def stop(self):
        """Останавливает менеджер"""
        try:
            info("Остановка ToastManager", "UI")

            # Закрываем все активные уведомления
            for notification in self.active_notifications:
                if notification.root and not notification.is_closed:
                    try:
                        notification.root.destroy()
                    except:
                        pass

            self.root.quit()
            success("ToastManager остановлен", "UI")

        except Exception as e:
            error(f"Ошибка остановки ToastManager: {e}", "UI", exc_info=True)


class SystemTray:
    """Системный трей приложения"""

    def __init__(self):
        self.tray_icon = None
        self.is_paused = False
        self.pause_until = None
        self.stats = {"total": 0, "overdue": 0, "urgent": 0}
        self.last_check_time = None

        # Callback функции
        self.on_check_now: Optional[Callable[[], None]] = None
        self.on_pause: Optional[Callable[[int], None]] = None
        self.on_resume: Optional[Callable[[], None]] = None
        self.on_quit: Optional[Callable[[], None]] = None

        info("SystemTray инициализирован", "UI")

    def create_icon(self) -> Image.Image:
        """Создает иконку для трея"""
        try:
            debug("Создание иконки для системного трея", "UI")

            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # Определяем цвет по состоянию
            if self.is_paused:
                color = (128, 128, 128)  # Серый - на паузе
                status = "на паузе"
            elif self.stats["overdue"] > 0:
                color = (255, 68, 68)  # Красный - есть просроченные
                status = f"{self.stats['overdue']} просроченных"
            elif self.stats["urgent"] > 0:
                color = (255, 136, 0)  # Оранжевый - есть срочные
                status = f"{self.stats['urgent']} срочных"
            else:
                color = (0, 200, 0)  # Зеленый - все хорошо
                status = "все в порядке"

            # Рисуем круг
            draw.ellipse([8, 8, 56, 56], fill=color, outline=(255, 255, 255), width=2)

            # Добавляем букву P
            draw.text((32, 32), "P", fill=(255, 255, 255), anchor="mm")

            debug(f"Иконка создана: {status}", "UI")
            return image

        except Exception as e:
            error(f"Ошибка создания иконки трея: {e}", "UI", exc_info=True)
            # Возвращаем простую иконку при ошибке
            return Image.new("RGBA", (64, 64), (0, 100, 200, 255))

    def create_menu(self) -> pystray.Menu:
        """Создает меню трея"""
        try:
            debug("Создание меню системного трея", "UI")

            # Строка состояния
            if self.is_paused:
                if self.pause_until:
                    pause_str = f"На паузе до {self.pause_until.strftime('%H:%M')}"
                else:
                    pause_str = "На паузе"
                status_item = pystray.MenuItem(f"⏸️ {pause_str}", None, enabled=False)
            else:
                total = self.stats["total"]
                overdue = self.stats["overdue"]
                status_item = pystray.MenuItem(
                    f"🟢 Активен ({total} задач, {overdue} просроч.)",
                    None,
                    enabled=False,
                )

            # Время последней проверки
            if self.last_check_time:
                time_str = self.last_check_time.strftime("%H:%M:%S")
                last_check_item = pystray.MenuItem(
                    f"Последняя проверка: {time_str}", None, enabled=False
                )
            else:
                last_check_item = pystray.MenuItem(
                    "Еще не проверялось", None, enabled=False
                )

            # Создаем меню
            menu_items = [
                status_item,
                last_check_item,
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "📊 Проверить сейчас", lambda: self._handle_check_now()
                ),
            ]

            # Пауза или возобновление
            if not self.is_paused:
                menu_items.extend(
                    [
                        pystray.MenuItem(
                            "⏸️ Пауза на 1 час", lambda: self._handle_pause(60)
                        ),
                        pystray.MenuItem(
                            "⏸️ Пауза до завтра 9:00",
                            lambda: self._handle_pause_until_tomorrow(),
                        ),
                    ]
                )
            else:
                menu_items.append(
                    pystray.MenuItem("▶️ Возобновить", lambda: self._handle_resume())
                )

            menu_items.extend(
                [
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(
                        "🌐 Открыть Planfix", lambda: self._handle_open_planfix()
                    ),
                    pystray.MenuItem("📖 Справка", lambda: self._handle_show_help()),
                ]
            )

            # Добавляем диагностику, если модуль доступен
            if DIAGNOSTIC_AVAILABLE:
                menu_items.append(
                    pystray.MenuItem("🔧 Диагностика", lambda: self._handle_diagnostic())
                )

            menu_items.extend(
                [
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("❌ Выход", lambda: self._handle_quit()),
                ]
            )

            debug(f"Меню создано с {len(menu_items)} пунктами", "UI")
            return pystray.Menu(*menu_items)

        except Exception as e:
            error(f"Ошибка создания меню трея: {e}", "UI", exc_info=True)
            # Возвращаем минимальное меню при ошибке
            return pystray.Menu(pystray.MenuItem("Ошибка", None, enabled=False))

    def start(self):
        """Запускает системный трей"""
        try:
            info("Запуск системного трея", "UI")

            self.tray_icon = pystray.Icon(
                name="Planfix Reminder",
                icon=self.create_icon(),
                title="Planfix Reminder",
                menu=self.create_menu(),
            )

            # Обновляем меню каждые 30 секунд
            def update_menu():
                try:
                    while True:
                        threading.Event().wait(30)
                        if self.tray_icon:
                            self.tray_icon.menu = self.create_menu()
                            debug("Меню системного трея обновлено", "UI")
                except Exception as e:
                    error(f"Ошибка обновления меню трея: {e}", "UI")

            threading.Thread(target=update_menu, daemon=True).start()

            # Запускаем трей в отдельном потоке
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

            success("Системный трей запущен", "UI")

        except Exception as e:
            error(f"Ошибка запуска системного трея: {e}", "UI", exc_info=True)

    def update_stats(self, total: int, overdue: int, urgent: int):
        """Обновляет статистику"""
        try:
            old_stats = self.stats.copy()
            self.stats = {"total": total, "overdue": overdue, "urgent": urgent}
            self.last_check_time = datetime.datetime.now()

            # Логируем изменения
            if old_stats != self.stats:
                info(f"Статистика трея обновлена: {self.stats}", "UI")
            else:
                debug(f"Статистика трея без изменений: {self.stats}", "UI")

            if self.tray_icon:
                self.tray_icon.icon = self.create_icon()

        except Exception as e:
            error(f"Ошибка обновления статистики трея: {e}", "UI", exc_info=True)

    def set_paused(self, paused: bool, until: Optional[datetime.datetime] = None):
        """Устанавливает состояние паузы"""
        try:
            self.is_paused = paused
            self.pause_until = until

            status = f"{'включена' if paused else 'отключена'}"
            if until:
                status += f" до {until.strftime('%H:%M')}"

            info(f"Пауза {status}", "UI")

            if self.tray_icon:
                self.tray_icon.icon = self.create_icon()

        except Exception as e:
            error(f"Ошибка установки состояния паузы: {e}", "UI", exc_info=True)

    def _handle_check_now(self):
        """Обработка проверки сейчас"""
        try:
            debug("Обработка команды 'Проверить сейчас'", "UI")
            if self.on_check_now:
                self.on_check_now()
            else:
                warning("Callback для проверки сейчас не установлен", "UI")
        except Exception as e:
            error(f"Ошибка обработки 'Проверить сейчас': {e}", "UI", exc_info=True)

    def _handle_pause(self, minutes: int):
        """Обработка паузы"""
        try:
            debug(f"Обработка команды 'Пауза на {minutes} минут'", "UI")
            if self.on_pause:
                self.on_pause(minutes)
            else:
                warning("Callback для паузы не установлен", "UI")
        except Exception as e:
            error(f"Ошибка обработки паузы: {e}", "UI", exc_info=True)

    def _handle_pause_until_tomorrow(self):
        """Обработка паузы до завтра"""
        try:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            tomorrow_9am = datetime.datetime.combine(tomorrow, datetime.time(9, 0))

            minutes = int((tomorrow_9am - datetime.datetime.now()).total_seconds() / 60)
            debug(f"Пауза до завтра: {minutes} минут", "UI")

            if self.on_pause:
                self.on_pause(minutes)
            else:
                warning("Callback для паузы не установлен", "UI")
        except Exception as e:
            error(f"Ошибка обработки паузы до завтра: {e}", "UI", exc_info=True)

    def _handle_resume(self):
        """Обработка возобновления"""
        try:
            debug("Обработка команды 'Возобновить'", "UI")
            if self.on_resume:
                self.on_resume()
            else:
                warning("Callback для возобновления не установлен", "UI")
        except Exception as e:
            error(f"Ошибка обработки возобновления: {e}", "UI", exc_info=True)

    def _handle_open_planfix(self):
        """Обработка открытия Planfix"""
        try:
            debug("Открытие Planfix в браузере", "UI")
            webbrowser.open("https://planfix.com")
            success("Planfix открыт в браузере", "UI")
        except Exception as e:
            error(f"Ошибка открытия Planfix: {e}", "UI", exc_info=True)

    def _handle_show_help(self):
        """Обработка показа справки"""
        try:
            debug("Открытие справки пользователя", "UI")

            # HTML содержимое справки
            help_html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Справка - Planfix Reminder</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 700px; margin: 0 auto; padding: 15px; }
        .header { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 15px; padding: 25px; text-align: center; margin-bottom: 20px; box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1); }
        .header h1 { font-size: 2rem; background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 8px; }
        .subtitle { color: #666; font-size: 1rem; }
        .main-content { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 15px; padding: 30px; box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1); }
        .section { margin-bottom: 25px; }
        .section h2 { color: #667eea; font-size: 1.3rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .notification-types { display: flex; gap: 15px; margin: 15px 0; flex-wrap: wrap; }
        .notification-card { flex: 1; min-width: 180px; padding: 18px; border-radius: 12px; color: white; text-align: center; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15); }
        .notification-card.overdue { background: linear-gradient(135deg, #ff4444, #cc0000); }
        .notification-card.urgent { background: linear-gradient(135deg, #ff8800, #cc4400); }
        .notification-card.current { background: linear-gradient(135deg, #0066cc, #003388); }
        .notification-card h3 { color: white; margin-bottom: 8px; font-size: 1.1rem; }
        .notification-card p { margin: 4px 0; font-size: 0.85rem; opacity: 0.9; }
        .controls-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 15px 0; }
        .control-item { background: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 3px solid #667eea; text-align: center; }
        .control-item .button { background: #667eea; color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; display: block; margin: 0 auto 6px; width: fit-content; }
        .control-item p { color: #555; font-size: 0.8rem; line-height: 1.3; }
        .tray-menu { background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 15px 0; }
        .tray-menu ul { list-style: none; padding: 0; }
        .tray-menu li { margin: 8px 0; padding: 6px 0; border-bottom: 1px solid #eee; }
        .tray-colors { display: flex; gap: 10px; margin: 15px 0; flex-wrap: wrap; }
        .tray-color { flex: 1; min-width: 120px; background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border-top: 3px solid; font-size: 0.85rem; }
        .tray-color.red { border-top-color: #ff4444; }
        .tray-color.orange { border-top-color: #ff8800; }
        .tray-color.green { border-top-color: #00cc66; }
        .tray-color.gray { border-top-color: #888888; }
        .troubleshooting-item { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 12px 0; }
        .troubleshooting-item h4 { color: #856404; margin-bottom: 8px; font-size: 1rem; }
        .tip-box { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #00d2d3; }
        .faq-item { margin-bottom: 15px; }
        .faq-item h4 { color: #667eea; font-size: 1rem; margin-bottom: 6px; }
        ul, ol { padding-left: 18px; }
        li { margin: 4px 0; }
        p { margin: 8px 0; font-size: 0.95rem; }
        .icon { font-size: 1.2rem; }
        @media (max-width: 600px) {
            .notification-types { flex-direction: column; }
            .controls-grid { grid-template-columns: repeat(2, 1fr); }
            .tray-colors { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📋 Planfix Reminder</h1>
            <p class="subtitle">Быстрая справка по использованию</p>
        </header>

        <main class="main-content">
            <section class="section">
                <h2><span class="icon">🎯</span>О программе</h2>
                <p>Программа автоматически показывает уведомления о ваших задачах из Planfix. Работает в фоне и напоминает о важных делах.</p>
            </section>

            <section class="section">
                <h2><span class="icon">🔔</span>Типы уведомлений</h2>
                <div class="notification-types">
                    <div class="notification-card overdue">
                        <h3>🔴 ПРОСРОЧЕННЫЕ</h3>
                        <p>Срок прошел</p>
                        <p>Громкий сигнал</p>
                        <p>Каждые 5 мин</p>
                    </div>
                    <div class="notification-card urgent">
                        <h3>🟡 СРОЧНЫЕ</h3>
                        <p>До срока < 1 дня</p>
                        <p>Предупреждение</p>
                        <p>Каждые 15 мин</p>
                    </div>
                    <div class="notification-card current">
                        <h3>📋 ОБЫЧНЫЕ</h3>
                        <p>Назначенные задачи</p>
                        <p>Без звука</p>
                        <p>Каждые 30 мин</p>
                    </div>
                </div>
            </section>

            <section class="section">
                <h2><span class="icon">🎮</span>Кнопки управления</h2>
                <div class="controls-grid">
                    <div class="control-item">
                        <div class="button">Открыть</div>
                        <p>Перейти к задаче</p>
                    </div>
                    <div class="control-item">
                        <div class="button">15мин</div>
                        <p>Напомнить позже</p>
                    </div>
                    <div class="control-item">
                        <div class="button">1ч</div>
                        <p>Напомнить через час</p>
                    </div>
                    <div class="control-item">
                        <div class="button">Готово</div>
                        <p>Больше не показывать</p>
                    </div>
                    <div class="control-item">
                        <div class="button">✕</div>
                        <p>Закрыть окно</p>
                    </div>
                    <div class="control-item">
                        <div class="button">📌</div>
                        <p>Закрепить окно</p>
                    </div>
                </div>

                <div class="tip-box">
                    <h3>💡 Совет</h3>
                    <p>Окна уведомлений можно перетаскивать мышью. Используйте "Готово" для выполненных задач.</p>
                </div>
            </section>

            <section class="section">
                <h2><span class="icon">📊</span>Системный трей</h2>
                <p>Программа работает через иконку возле часов. Правый клик открывает меню:</p>
                <div class="tray-menu">
                    <ul>
                        <li><strong>Проверить сейчас</strong> - обновить список задач</li>
                        <li><strong>Пауза на 1 час / до завтра</strong> - временно отключить</li>
                        <li><strong>Возобновить</strong> - включить уведомления</li>
                        <li><strong>Открыть Planfix</strong> - перейти на сайт</li>
                        <li><strong>Справка</strong> - открыть это окно</li>
                        <li><strong>Выход</strong> - закрыть программу</li>
                    </ul>
                </div>

                <h3>Цвет иконки:</h3>
                <div class="tray-colors">
                    <div class="tray-color red">🔴 Просрочено</div>
                    <div class="tray-color orange">🟠 Срочно</div>
                    <div class="tray-color green">🟢 Всё в порядке</div>
                    <div class="tray-color gray">⚫ На паузе</div>
                </div>
            </section>

            <section class="section">
                <h2><span class="icon">⚙️</span>Настройка</h2>
                <p>Для работы с Planfix нужны API ключ и адрес вашей системы. Эти данные настраиваются в файле config.ini рядом с программой.</p>
                
                <h3>Параметры времени показа уведомлений:</h3>
                <div class="tray-menu">
                    <ul>
                        <li><strong>check_interval</strong> - как часто проверять задачи (в секундах, по умолчанию 300 = 5 минут)</li>
                        <li><strong>notify_overdue</strong> - показывать просроченные задачи (true/false)</li>
                        <li><strong>notify_urgent</strong> - показывать срочные задачи (true/false)</li>
                        <li><strong>notify_current</strong> - показывать обычные задачи (true/false)</li>
                        <li><strong>max_total_windows</strong> - максимум окон одновременно (по умолчанию 10)</li>
                        <li><strong>max_windows_per_category</strong> - максимум окон одного типа (по умолчанию 5)</li>
                    </ul>
                </div>
            </section>

            <section class="section">
                <h2><span class="icon">🔧</span>Решение проблем</h2>
                
                <div class="troubleshooting-item">
                    <h4>❌ Нет уведомлений</h4>
                    <ul>
                        <li>Проверьте иконку в трее - программа запущена?</li>
                        <li>Попробуйте "Проверить сейчас"</li>
                        <li>Убедитесь что у вас есть активные задачи</li>
                    </ul>
                </div>

                <div class="troubleshooting-item">
                    <h4>🌐 Ошибка подключения</h4>
                    <ul>
                        <li>Проверьте интернет соединение</li>
                        <li>Запустите самодиагностику из меню трея и отправьте результаты в IT-поддержку</li>
                        <li>Обратитесь в IT-поддержку</li>
                    </ul>
                </div>

                <div class="troubleshooting-item">
                    <h4>⚠️ Программа не запускается</h4>
                    <ul>
                        <li>Проверьте настройки в config.ini</li>
                        <li>Запустите от имени администратора</li>
                        <li>Запустите самодиагностику из меню трея и отправьте результаты в IT-поддержку</li>
                        <li>Обратитесь в IT-поддержку</li>
                    </ul>
                </div>
            </section>

            <section class="section">
                <h2><span class="icon">❓</span>Часто задаваемые вопросы</h2>
                
                <div class="faq-item">
                    <h4>Можно ли изменить время напоминаний?</h4>
                    <p>Да, в файле config.ini можно настроить интервал проверки задач. По умолчанию проверка происходит каждые 5 минут.</p>
                </div>

                <div class="faq-item">
                    <h4>Будет ли программа работать, если я закрою все окна?</h4>
                    <p>Да, программа продолжит работать в фоне через системный трей, даже если все окна уведомлений закрыты.</p>
                </div>

                <div class="faq-item">
                    <h4>Можно ли отключить уведомления для определенного типа задач?</h4>
                    <p>Да, в config.ini можно отдельно включить/выключить уведомления для текущих, срочных или просроченных задач.</p>
                </div>

                <div class="faq-item">
                    <h4>Что делать, если уведомлений слишком много?</h4>
                    <p>Используйте кнопку "Пауза" в меню трея или нажимайте "Готово" для задач, которые не требуют напоминаний.</p>
                </div>
            </section>
        </main>
    </div>
</body>
</html>"""

            # Создаем временный HTML файл
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as f:
                f.write(help_html)
                temp_file_path = f.name

            # Открываем в браузере
            webbrowser.open(f"file://{temp_file_path}")

            success("Справка открыта в браузере", "UI")
            info(f"Временный файл справки: {temp_file_path}", "UI")

        except Exception as e:
            error(f"Ошибка открытия справки: {e}", "UI", exc_info=True)

    def _handle_diagnostic(self):
        """Обработка запуска диагностики"""
        try:
            debug("Запуск диагностики системы", "UI")

            if not DIAGNOSTIC_AVAILABLE:
                error("Модуль диагностики недоступен", "UI")
                return

            # Запускаем диагностику в отдельном потоке, чтобы не блокировать UI
            def run_diagnostic_thread():
                try:
                    info("Запуск диагностики в фоновом потоке", "UI")
                    summary = run_diagnostic()
                    if summary:
                        success("Диагностика завершена успешно", "UI")
                    else:
                        warning("Диагностика завершена с ошибками", "UI")
                except Exception as e:
                    error(f"Ошибка выполнения диагностики: {e}", "UI", exc_info=True)

            import threading
            diagnostic_thread = threading.Thread(target=run_diagnostic_thread, daemon=True)
            diagnostic_thread.start()

            success("Диагностика запущена в фоне", "UI")

        except Exception as e:
            error(f"Ошибка запуска диагностики: {e}", "UI", exc_info=True)

    def _handle_quit(self):
        """Обработка выхода"""
        try:
            debug("Обработка команды 'Выход'", "UI")
            if self.on_quit:
                self.on_quit()
            else:
                warning("Callback для выхода не установлен", "UI")
        except Exception as e:
            error(f"Ошибка обработки выхода: {e}", "UI", exc_info=True)

    def stop(self):
        """Останавливает трей"""
        try:
            info("Остановка системного трея", "UI")
            if self.tray_icon:
                self.tray_icon.stop()
                success("Системный трей остановлен", "UI")
        except Exception as e:
            error(f"Ошибка остановки системного трея: {e}", "UI", exc_info=True)


# ===== ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ МОДУЛЯ =====


def test_toast_notification():
    """Тестирует Toast уведомления с файловым логированием"""
    # Настраиваем логирование для тестов
    from file_logger import setup_logging, get_logs_directory, startup

    setup_logging(debug_mode=True, console_debug=True)

    startup("Тестирование Toast уведомлений с файловым логированием")

    def on_open_task(task_id: str):
        info(f"Тест: Открыть задачу #{task_id}", "TEST")

    def on_close_notification(task_id: str, reason: str):
        info(f"Тест: Закрыто уведомление #{task_id}, причина: {reason}", "TEST")

    # Создаем менеджер
    info("=== СОЗДАНИЕ МЕНЕДЖЕРА ===", "TEST")
    manager = ToastManager()
    manager.on_open_task = on_open_task
    manager.on_close_notification = on_close_notification
    success("ToastManager создан и настроен", "TEST")

    # Показываем тестовые уведомления
    info("=== СОЗДАНИЕ ТЕСТОВЫХ УВЕДОМЛЕНИЙ ===", "TEST")

    manager.show_notification(
        title="🔴 ПРОСРОЧЕНО: Тестовая задача",
        message="📅 01.12.2024\n👤 Тестовый пользователь",
        category="overdue",
        task_id="123",
    )

    manager.show_notification(
        title="🟡 СРОЧНО: Другая задача",
        message="📅 Сегодня\n👤 Другой пользователь",
        category="urgent",
        task_id="456",
    )

    # Добавляем еще несколько для тестирования каскада
    for i in range(3, 8):
        manager.show_notification(
            title=f"📋 Обычная задача {i}",
            message=f"📅 Задача номер {i}\n👤 Пользователь {i}",
            category="current",
            task_id=str(100 + i),
        )

    success("Создано тестовых уведомлений: 7", "TEST")
    info("Взаимодействуйте с уведомлениями для тестирования функций", "TEST")
    info("Закройте все окна для завершения теста", "TEST")

    startup(f"Логи тестирования сохранены в: {get_logs_directory()}")

    # Запускаем GUI
    manager.run()


if __name__ == "__main__":
    test_toast_notification()
