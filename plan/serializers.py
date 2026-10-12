from datetime import UTC, date, datetime

from django.contrib.auth import get_user_model
from rest_framework import serializers


def timestamp_to_date(value: int) -> date:
    """Unix timestamp (секунды, UTC) -> дата."""
    try:
        return datetime.fromtimestamp(value, tz=UTC).date()
    except (OverflowError, OSError, ValueError) as exc:
        raise serializers.ValidationError("Некорректный unix timestamp.") from exc


class WorkVolumeRequestSerializer(serializers.Serializer):
    """Тело запроса POST /work-volume-list/."""

    factory = serializers.IntegerField()
    start = serializers.IntegerField()
    finish = serializers.IntegerField()
    weight = serializers.IntegerField(min_value=0)
    author = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())

    def validate_start(self, value):
        return timestamp_to_date(value)

    def validate_finish(self, value):
        return timestamp_to_date(value)


class WorkVolumeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    factory = serializers.IntegerField()
    start = serializers.DateField()
    finish = serializers.DateField()
    weight = serializers.IntegerField()
    created = serializers.DateField()


class ErrorResponseSerializer(serializers.Serializer):
    errorCode = serializers.IntegerField()
    detail = serializers.JSONField()
