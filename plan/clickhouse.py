"""Запись объема работы."""

from datetime import date
from uuid import UUID

import clickhouse_connect
from django.conf import settings

WORK_VOLUME_RECORD_TABLE = "work_volume_record"
WORK_VOLUME_RECORD_COLUMNS = ("factory", "start", "finish", "weight", "author", "created")


def get_client(**kwargs):
    config = settings.CLICKHOUSE
    return clickhouse_connect.get_client(
        host=config["HOST"],
        port=config["PORT"],
        username=config["USER"],
        password=config["PASSWORD"],
        database=config["DATABASE"],
        **kwargs,
    )


def insert_work_volume_record(
    factory: UUID, start: date, finish: date, weight: int, author: int, created: date
) -> None:
    client = get_client()
    try:
        client.insert(
            WORK_VOLUME_RECORD_TABLE,
            [[factory, start, finish, weight, author, created]],
            column_names=WORK_VOLUME_RECORD_COLUMNS,
        )
    finally:
        client.close()
