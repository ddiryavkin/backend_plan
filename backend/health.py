import structlog
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from plan.clickhouse import get_client

HEALTH_TIMEOUT_SECONDS = 2
STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

logger = structlog.get_logger(__name__)


def check_postgres() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_clickhouse() -> None:
    client = get_client(connect_timeout=HEALTH_TIMEOUT_SECONDS, send_receive_timeout=HEALTH_TIMEOUT_SECONDS)
    try:
        client.command("SELECT 1")
    finally:
        client.close()


CHECKS = {
    "postgres": check_postgres,
    "clickhouse": check_clickhouse,
}

HealthResponseSerializer = inline_serializer(
    name="HealthResponse",
    fields={
        "status": serializers.ChoiceField(choices=[STATUS_OK, STATUS_UNAVAILABLE]),
        "databases": serializers.DictField(child=serializers.ChoiceField(choices=[STATUS_OK, STATUS_UNAVAILABLE])),
    },
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Доступность баз данных",
        tags=["health"],
        auth=[],
        responses={
            200: OpenApiResponse(HealthResponseSerializer, description="Postgres и ClickHouse доступны"),
            503: OpenApiResponse(HealthResponseSerializer, description="Хотя бы одна база недоступна"),
        },
    )
    def get(self, request):
        results = {}
        for name, check in CHECKS.items():
            try:
                check()
                results[name] = STATUS_OK
            except Exception as exc:
                logger.error("health_check_failed", database=name, error=repr(exc))
                results[name] = STATUS_UNAVAILABLE

        healthy = all(result == STATUS_OK for result in results.values())
        return Response(
            {"status": STATUS_OK if healthy else STATUS_UNAVAILABLE, "databases": results},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
