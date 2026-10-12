from unittest.mock import Mock, patch

import pytest
from django.test import Client

from backend.health import check_postgres

pytestmark = pytest.mark.django_db

URL = "/health/"


def ok():
    return Mock(return_value=None)


def down(message):
    return Mock(side_effect=ConnectionError(message))


def get_health(postgres, clickhouse):
    # CHECKS хранит ссылки на функции, поэтому подменяем сам словарь
    with patch.dict("backend.health.CHECKS", {"postgres": postgres, "clickhouse": clickhouse}):
        return Client().get(URL)


def test_all_databases_available():
    response = get_health(postgres=ok(), clickhouse=ok())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "databases": {"postgres": "ok", "clickhouse": "ok"}}


def test_clickhouse_unavailable():
    response = get_health(postgres=ok(), clickhouse=down("clickhouse down"))

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "databases": {"postgres": "ok", "clickhouse": "unavailable"},
    }


def test_postgres_unavailable():
    response = get_health(postgres=down("postgres down"), clickhouse=ok())

    assert response.status_code == 503
    assert response.json()["databases"] == {"postgres": "unavailable", "clickhouse": "ok"}


def test_only_get_allowed():
    assert Client().post(URL).status_code == 405


def test_real_postgres_check():
    """Проверка Postgres работает на настоящей тестовой базе."""
    response = get_health(postgres=check_postgres, clickhouse=ok())

    assert response.json()["databases"]["postgres"] == "ok"
