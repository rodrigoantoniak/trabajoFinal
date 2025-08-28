import logging
import sys
from functools import wraps

from asgiref.sync import iscoroutinefunction, sync_to_async

from django.conf import settings
from django.core.signals import got_request_exception
from django.core.exceptions import (
    BadRequest,
    PermissionDenied,
    RequestDataTooBig,
    SuspiciousOperation,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.http import Http404, HttpRequest, HttpResponse
from django.http.multipartparser import MultiPartParserError
from django.urls import get_resolver, get_urlconf, URLResolver
from django.utils.log import log_response
from django.views.debug import (
    technical_404_response,
    technical_500_response
)

from collections.abc import Callable


def convert_exception_to_response(
    get_response: Callable[[HttpRequest], HttpResponse]
) -> Callable[[HttpRequest], HttpResponse]:
    if iscoroutinefunction(get_response):
        @wraps(get_response)
        async def inner(request: HttpRequest) -> HttpResponse:
            response: HttpResponse
            try:
                response = await get_response(request)
            except Exception as exc:
                response = await sync_to_async(
                    response_for_exception, thread_sensitive=False
                )(request, exc)
            return response
        return inner
    else:
        @wraps(get_response)
        def inner(request: HttpRequest) -> HttpResponse:
            response: HttpResponse
            try:
                response = get_response(request)
            except Exception as exc:
                response = response_for_exception(request, exc)
            return response
        return inner


def response_for_exception(
    request: HttpRequest,
    exc: Exception
) -> HttpResponse:
    response: HttpResponse
    if isinstance(exc, Http404):
        if settings.DEBUG:
            response = technical_404_response(request, exc)
        else:
            response = get_exception_response(
                request, get_resolver(get_urlconf()), 404, exc
            )
    elif isinstance(exc, PermissionDenied):
        response = get_exception_response(
            request, get_resolver(get_urlconf()), 403, exc
        )
        log_response(
            "Forbidden (Permission denied): %s",
            request.build_absolute_uri(),
            response=response,
            request=request,
            exception=exc,
        )
    elif isinstance(exc, MultiPartParserError):
        response = get_exception_response(
            request, get_resolver(get_urlconf()), 400, exc
        )
        log_response(
            "Bad request (Unable to parse request body): %s",
            request.build_absolute_uri(),
            response=response,
            request=request,
            exception=exc,
        )
    elif isinstance(exc, BadRequest):
        if settings.DEBUG:
            response = technical_500_response(
                request, *sys.exc_info(), status_code=400
            )
        else:
            response = get_exception_response(
                request, get_resolver(get_urlconf()), 400, exc
            )
        log_response(
            "%s: %s",
            str(exc),
            request.build_absolute_uri(),
            response=response,
            request=request,
            exception=exc,
        )
    elif isinstance(exc, SuspiciousOperation):
        if isinstance(
            exc,
            (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent)
        ):
            request._mark_post_parse_error()
        security_logger = logging.getLogger(
            "django.security.%s" % exc.__class__.__name__
        )
        security_logger.error(
            str(exc),
            exc_info=exc,
            extra={"status_code": 400, "request": request},
        )
        if settings.DEBUG:
            response = technical_500_response(
                request, *sys.exc_info(), status_code=400
            )
        else:
            response = get_exception_response(
                request, get_resolver(get_urlconf()), 400, exc
            )
    else:
        got_request_exception.send(sender=None, request=request)
        response = handle_uncaught_exception(
            request, get_resolver(get_urlconf()), sys.exc_info()
        )
        log_response(
            "%s: %s",
            response.reason_phrase,
            request.build_absolute_uri(),
            response=response,
            request=request,
            exception=exc,
        )
    if not getattr(response, "is_rendered", True) and callable(
        getattr(response, "render", None)
    ):
        response = response.render()
    return response


def get_exception_response(
    request: HttpRequest,
    resolver: URLResolver,
    status_code: int,
    exception: Exception
) -> HttpResponse:
    response: HttpResponse
    try:
        callback: Callable[
            [HttpRequest, Exception], HttpResponse
        ] = resolver.resolve_error_handler(
            status_code
        )
        response = callback(request, exception=exception)
    except Exception:
        got_request_exception.send(sender=None, request=request)
        response = handle_uncaught_exception(request, resolver, sys.exc_info())
    return response


def handle_uncaught_exception(
    request: HttpRequest,
    resolver: URLResolver,
    exc_info
) -> HttpResponse:
    if settings.DEBUG_PROPAGATE_EXCEPTIONS:
        raise
    if settings.DEBUG:
        return technical_500_response(request, *exc_info)
    callback: Callable[
        [HttpRequest], HttpResponse
    ] = resolver.resolve_error_handler(500)
    return callback(request)
