import structlog
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .clickhouse import insert_work_volume_record
from .constants import (
    ERROR_FACTORY_NOT_FOUND,
    ERROR_REQUIRED_FIELDS,
    GROUP_FACTORY_MANAGER,
    GROUP_FACTORY_REPRESENTATIVE,
)
from .models import Factory, FactoryUser, WorkVolume
from .serializers import ErrorResponseSerializer, WorkVolumeRequestSerializer, WorkVolumeResponseSerializer

logger = structlog.get_logger(__name__)


def error_response(http_status: int, error_code: int, detail) -> Response:
    return Response({"errorCode": error_code, "detail": detail}, status=http_status)


def factory_not_found() -> Response:
    return error_response(status.HTTP_404_NOT_FOUND, ERROR_FACTORY_NOT_FOUND, "ЗМК не найден.")


def in_group(user, group_name: str) -> bool:
    return user.groups.filter(name=group_name).exists()


class WorkVolumeListView(APIView):
    """Сохранение объема работ."""

    @extend_schema(
        summary="Сохранить объем работ",
        description="`start` и `finish` — unix timestamp (секунды, UTC).",
        request=WorkVolumeRequestSerializer,
        responses={
            201: WorkVolumeResponseSerializer,
            401: OpenApiResponse(description="Не аутентифицирован"),
            403: OpenApiResponse(description="Пользователь не входит ни в одну из групп"),
            404: OpenApiResponse(
                ErrorResponseSerializer,
                description="errorCode=174: ЗМК не существует или представитель не привязан к нему",
            ),
            406: OpenApiResponse(
                ErrorResponseSerializer,
                description="errorCode=279: не заполнены обязательные поля",
            ),
        },
    )
    def post(self, request):
        serializer = WorkVolumeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.info("work_volume_invalid_request", errors=serializer.errors)
            return error_response(status.HTTP_406_NOT_ACCEPTABLE, ERROR_REQUIRED_FIELDS, serializer.errors)
        data = serializer.validated_data

        factory = Factory.objects.filter(pk=data["factory"]).first()
        if factory is None:
            logger.info("work_volume_factory_not_found", factory_id=data["factory"])
            return factory_not_found()

        user = request.user
        if in_group(user, GROUP_FACTORY_REPRESENTATIVE):
            # Представитель может сохранять объем только своего ЗМК
            if not FactoryUser.objects.filter(user=user, factory=factory).exists():
                logger.info("work_volume_factory_not_linked", factory_id=factory.pk)
                return factory_not_found()
        elif not in_group(user, GROUP_FACTORY_MANAGER):
            logger.warning("work_volume_forbidden", factory_id=factory.pk)
            return Response(status=status.HTTP_403_FORBIDDEN)

        work_volume = self.save_work_volume(factory, data)
        return Response(
            {
                "id": work_volume.id,
                "factory": factory.id,
                "start": work_volume.start,
                "finish": work_volume.finish,
                "weight": work_volume.weight,
                "created": work_volume.created,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    @transaction.atomic
    def save_work_volume(factory: Factory, data: dict) -> WorkVolume:
        """Создает/обновляет объем работы и добавляет запись объема работы.

        Запись в ClickHouse выполняется последней: при ее ошибке изменения в Postgres откатываются.
        """
        today = timezone.localdate()
        log = logger.bind(
            factory_id=factory.pk,
            start=str(data["start"]),
            finish=str(data["finish"]),
            weight=data["weight"],
        )
        work_volume, is_new = WorkVolume.objects.update_or_create(
            factory=factory,
            start=data["start"],
            finish=data["finish"],
            defaults={"weight": data["weight"], "created": today},
        )
        try:
            insert_work_volume_record(
                factory=factory.external_id,
                start=data["start"],
                finish=data["finish"],
                weight=data["weight"],
                author=data["author"].pk,
                created=today,
            )
        except Exception as exc:
            # Traceback пишет Django (django.request) с тем же request_id, здесь — контекст отката
            log.error("work_volume_record_failed", error=repr(exc))
            raise
        log.info("work_volume_saved", work_volume_id=work_volume.pk, action="created" if is_new else "updated")
        return work_volume
