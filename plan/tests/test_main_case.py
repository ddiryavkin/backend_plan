"""Тесты сохранения объема работ.

Запись в ClickHouse заменена моком, Postgres — тестовая база pytest-django.
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from plan.constants import (
    ERROR_FACTORY_NOT_FOUND,
    ERROR_REQUIRED_FIELDS,
    GROUP_FACTORY_MANAGER,
    GROUP_FACTORY_REPRESENTATIVE,
)
from plan.models import Factory, FactoryUser, WorkVolume

pytestmark = pytest.mark.django_db

URL = "/work-volume-list/"
START_TS, START = 1735689600, date(2025, 1, 1)
FINISH_TS, FINISH = 1738281600, date(2025, 1, 31)
REQUIRED_FIELDS = ("factory", "start", "finish", "weight", "author")
UNKNOWN_FACTORY_ID = 999_999
BOTH_ROLES = ["manager", "representative"]
NEW_WEIGHT = 1500
UPDATED_WEIGHT = 2500
OLD_WEIGHT = 100
OLD_CREATED_DAYS_AGO = 10


@pytest.fixture
def clickhouse_insert():
    with patch("plan.views.insert_work_volume_record") as mock:
        yield mock


@pytest.fixture
def factory():
    return Factory.objects.create(name="ЗМК №1")


def make_user(django_user_model, username, group_name):
    user = django_user_model.objects.create_user(username=username, password="pass")
    user.groups.add(Group.objects.get_or_create(name=group_name)[0])
    return user


@pytest.fixture
def manager(django_user_model):
    return make_user(django_user_model, "manager", GROUP_FACTORY_MANAGER)


@pytest.fixture
def representative(django_user_model, factory):
    """Представитель, привязанный к factory."""
    user = make_user(django_user_model, "rep", GROUP_FACTORY_REPRESENTATIVE)
    FactoryUser.objects.create(user=user, factory=factory)
    return user


@pytest.fixture
def foreign_representative(django_user_model):
    """Представитель, не привязанный к factory."""
    return make_user(django_user_model, "foreign", GROUP_FACTORY_REPRESENTATIVE)


@pytest.fixture
def existing_volume(factory):
    return WorkVolume.objects.create(
        factory=factory,
        start=START,
        finish=FINISH,
        weight=OLD_WEIGHT,
        created=timezone.localdate() - timedelta(days=OLD_CREATED_DAYS_AGO),
    )


def payload(factory_id, author_id, weight=NEW_WEIGHT):
    return {
        "factory": factory_id,
        "start": START_TS,
        "finish": FINISH_TS,
        "weight": weight,
        "author": author_id,
    }


def post(user, data):
    client = APIClient()
    client.force_authenticate(user)
    return client.post(URL, data, format="json")


def assert_error(response, status_code, error_code, clickhouse_insert):
    """Ошибка и при этом ничего не сохранено."""
    assert response.status_code == status_code
    assert response.data["errorCode"] == error_code
    assert not WorkVolume.objects.exists()
    clickhouse_insert.assert_not_called()


def assert_record_saved(clickhouse_insert, factory, author, weight):
    clickhouse_insert.assert_called_once_with(
        factory=factory.external_id,
        start=START,
        finish=FINISH,
        weight=weight,
        author=author.pk,
        created=timezone.localdate(),
    )


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_field_returns_406(manager, factory, clickhouse_insert, missing):
    data = payload(factory.id, manager.id)
    del data[missing]

    assert_error(post(manager, data), 406, ERROR_REQUIRED_FIELDS, clickhouse_insert)


def test_fields_checked_before_factory(manager, clickhouse_insert):
    data = payload(UNKNOWN_FACTORY_ID, manager.id)
    del data["weight"]

    assert_error(post(manager, data), 406, ERROR_REQUIRED_FIELDS, clickhouse_insert)


@pytest.mark.parametrize("role", BOTH_ROLES)
def test_unknown_factory_returns_404(request, role, clickhouse_insert):
    user = request.getfixturevalue(role)

    response = post(user, payload(UNKNOWN_FACTORY_ID, user.id))

    assert_error(response, 404, ERROR_FACTORY_NOT_FOUND, clickhouse_insert)


def test_foreign_representative_returns_404(foreign_representative, factory, clickhouse_insert):
    response = post(foreign_representative, payload(factory.id, foreign_representative.id))

    assert_error(response, 404, ERROR_FACTORY_NOT_FOUND, clickhouse_insert)


@pytest.mark.parametrize("role", BOTH_ROLES)
def test_creates_work_volume(request, role, factory, clickhouse_insert):
    user = request.getfixturevalue(role)

    response = post(user, payload(factory.id, user.id, weight=NEW_WEIGHT))

    assert response.status_code == 201
    volume = WorkVolume.objects.get()
    assert (volume.factory, volume.start, volume.finish, volume.weight) == (factory, START, FINISH, NEW_WEIGHT)
    assert volume.created == timezone.localdate()
    assert_record_saved(clickhouse_insert, factory, user, weight=NEW_WEIGHT)


@pytest.mark.parametrize("role", BOTH_ROLES)
def test_updates_existing_work_volume(request, role, factory, existing_volume, clickhouse_insert):
    user = request.getfixturevalue(role)

    response = post(user, payload(factory.id, user.id, weight=UPDATED_WEIGHT))

    assert response.status_code == 201
    volume = WorkVolume.objects.get()
    assert volume.pk == existing_volume.pk
    assert volume.weight == UPDATED_WEIGHT
    assert volume.created == timezone.localdate()
    assert_record_saved(clickhouse_insert, factory, user, weight=UPDATED_WEIGHT)
