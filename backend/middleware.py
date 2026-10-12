import re
import time
import uuid
from contextvars import ContextVar

import structlog

REQUEST_ID_HEADER = "X-Request-ID"
# Принимаем request_id от клиента только в безопасном виде, иначе генерируем свой
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")

_current_request = ContextVar("current_request", default=None)

logger = structlog.get_logger(__name__)


def add_user_id(_, __, event_dict):
    """Добавляет user_id текущего запроса в момент записи лога.

    Basic-аутентификацию DRF выполняет уже после middleware и записывает пользователя
    в исходный request, поэтому user_id берётся здесь, а не при входе в middleware.
    """
    request = _current_request.get()
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        event_dict.setdefault("user_id", user.pk)
    return event_dict


class RequestContextMiddleware:
    """Добавляет в логи запроса request_id и user_id."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(REQUEST_ID_HEADER, "")
        if not REQUEST_ID_PATTERN.match(request_id):
            request_id = uuid.uuid4().hex

        # Контекст сбрасывается в начале запроса, а не в конце: Django пишет лог 4xx/5xx
        # (django.request) уже после выхода из middleware, и в нём тоже нужен request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        _current_request.set(request)
        started = time.monotonic()

        response = self.get_response(request)

        response[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_finished",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=round((time.monotonic() - started) * 1000),
        )
        return response
