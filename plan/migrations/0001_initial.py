import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Factory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="внешний идентификатор ЗМК")),
                ("name", models.CharField(max_length=255, verbose_name="наименование ЗМК")),
            ],
        ),
        migrations.CreateModel(
            name="FactoryUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("factory", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="factory_users", to="plan.factory")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="factory_links", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("user", "factory"), name="unique_factory_user")],
            },
        ),
        migrations.CreateModel(
            name="WorkVolume",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start", models.DateField(verbose_name="начальная дата")),
                ("finish", models.DateField(verbose_name="конечная дата")),
                ("weight", models.PositiveIntegerField(verbose_name="вес, кг")),
                ("created", models.DateField(default=django.utils.timezone.localdate, verbose_name="дата создания")),
                ("factory", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_volumes", to="plan.factory")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("factory", "start", "finish"), name="unique_work_volume_period")],
            },
        ),
    ]
