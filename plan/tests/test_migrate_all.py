from unittest.mock import patch

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_applies_clickhouse_schema():
    with patch("plan.management.commands.migrate_all.get_client") as get_client:
        call_command("migrate_all", verbosity=0)

    client = get_client.return_value
    statements = [call.args[0] for call in client.command.call_args_list]
    assert len(statements) == 1
    assert statements[0].startswith("CREATE TABLE IF NOT EXISTS work_volume_record")
    client.close.assert_called_once()
