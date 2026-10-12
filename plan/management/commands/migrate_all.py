from pathlib import Path

import structlog
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from plan.clickhouse import get_client

logger = structlog.get_logger(__name__)


def read_statements(path: Path) -> list[str]:
    return [statement.strip() for statement in path.read_text().split(";") if statement.strip()]


class Command(BaseCommand):
    help = "Применяет миграции Postgres и схему ClickHouse."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False, verbosity=options["verbosity"])

        schema = settings.BASE_DIR / "clickhouse" / "init.sql"
        client = get_client()
        try:
            for statement in read_statements(schema):
                client.command(statement)
        finally:
            client.close()
        logger.info("clickhouse_schema_applied", schema=schema.name)
