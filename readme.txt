# Новая структура проекта: planfix_reminder_modular

```
planfix_reminder_modular/
├── main.py                # Точка входа (150-200 строк)
├── config_manager.py      # Управление конфигом (200 строк)
├── planfix_api.py         # API и обработка задач (300 строк)
├── ui_components.py       # Toast и системный трей (400 строк)
├── task_tracker.py        # Отслеживание задач (100 строк)
├── config.ini            # Конфигурация
├── requirements.txt      # Зависимости
└── tools/                # Вспомогательные инструменты
    ├── diagnostics.py    # Диагностика системы
    ├── filter_finder.py  # Поиск фильтров
    └── user_tester.py    # Тестирование пользователей
```

## Зависимости между модулями:

```
main.py
  ├── config_manager.py
  ├── planfix_api.py
  ├── ui_components.py
  └── task_tracker.py
```

Модули НЕ зависят друг от друга напрямую - только через main.py