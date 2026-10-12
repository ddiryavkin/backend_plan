import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Factory(models.Model):
    """ЗМК."""

    external_id = models.UUIDField("внешний идентификатор ЗМК", default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField("наименование ЗМК", max_length=255)

    def __str__(self):
        return self.name


class FactoryUser(models.Model):
    """Пользователь завода."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="factory_links")
    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="factory_users")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "factory"], name="unique_factory_user")]

    def __str__(self):
        return f"{self.user} — {self.factory}"


class WorkVolume(models.Model):
    """Объем работы ЗМК за период."""

    factory = models.ForeignKey(Factory, on_delete=models.CASCADE, related_name="work_volumes")
    start = models.DateField("начальная дата")
    finish = models.DateField("конечная дата")
    weight = models.PositiveIntegerField("вес, кг")
    created = models.DateField("дата создания", default=timezone.localdate)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["factory", "start", "finish"], name="unique_work_volume_period"),
        ]

    def __str__(self):
        return f"{self.factory}: {self.start} — {self.finish}, {self.weight} кг"
