# Backend / Plan

Сохранение объема работ ЗМК за период. Django + DRF, Postgres, ClickHouse.

Нужны Python 3.11+ и Docker.

## Запуск в Docker

```bash
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser
```

Миграции Postgres и схему ClickHouse применяет одноразовый сервис `migrate`
(`python manage.py migrate_all`), приложение стартует после него.

Остановить: `docker compose down`

## Локальный запуск

```bash
uv sync
cp .env.example .env
docker compose up -d postgres clickhouse
uv run python manage.py migrate_all
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Без `uv`: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

## Адреса

- Swagger: http://localhost:8000/api/docs/ (Authorize → `basicAuth`)
- Админка: http://localhost:8000/admin/
- Healthcheck: http://localhost:8000/health/

## Тестовые данные

Создает ЗМК, менеджера (`manager` / `manager`) и представителя ЗМК (`rep` / `rep`).
В Docker команду запускать через `docker compose exec backend`.

```bash
python manage.py shell -c "
from django.contrib.auth.models import User, Group
from plan.models import Factory, FactoryUser

factory = Factory.objects.create(name='ЗМК №1')
manager = User.objects.create_user('manager', password='manager')
manager.groups.add(Group.objects.get(name='Менеджер по взаимодействию с ЗМК'))
rep = User.objects.create_user('rep', password='rep')
rep.groups.add(Group.objects.get(name='Представитель ЗМК'))
FactoryUser.objects.create(user=rep, factory=factory)
print('factory:', factory.id, 'manager:', manager.id, 'rep:', rep.id)
"
```

## Тесты и линтер

```bash
uv sync --group dev
docker compose up -d postgres
uv run pytest
uv run pre-commit install
```
