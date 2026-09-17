# Wargame Stats

Веб-приложение для сбора и отображения статистики игр в варгеймы.

## Стек

- Python 3
- Flask
- PostgreSQL
- SQLAlchemy
- Flask-Migrate

## Требования

- Python 3.11+
- PostgreSQL

## Установка

```bash
git clone https://github.com/Yatsenko-Egor/wargame_stats.git
cd wargame_stats

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# заполнить .env значениями
```

## Миграции

```bash
flask --app run.py db upgrade
```

## Запуск

```bash
python run.py
```

Приложение доступно по адресу `http://127.0.0.1:5000`.

## Структура проекта

```
app/
├── auth/          — регистрация, вход, сессии
├── profile/       — публичный профиль игрока
├── templates/     — Jinja2-шаблоны
└── static/        — CSS, JS
migrations/        — миграции Alembic
config.py          — конфигурация
run.py             — точка входа
```