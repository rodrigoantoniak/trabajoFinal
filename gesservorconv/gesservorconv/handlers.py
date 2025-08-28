from django import setup
from django.conf import settings
from django.core.exceptions import (
    ImproperlyConfigured,
    MiddlewareNotUsed,
    RequestAborted,
    RequestDataTooBig
)
from django.core.handlers.asgi import ASGIRequest
from django.core.handlers.base import BaseHandler
from django.core.handlers.wsgi import get_script_name, WSGIRequest
from django.core.signals import request_started
from django.http import (
    FileResponse,
    HttpHeaders,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError
)
from django.urls import set_script_prefix, set_urlconf, URLResolver
from django.utils.asyncio import aclosing
from django.utils.deprecation import MiddlewareMixin
from django.utils.log import log_response
from django.utils.module_loading import import_string

from asgiref.sync import ThreadSensitiveContext, sync_to_async
from collections.abc import Callable, Iterable, Mapping
from logging import getLogger, Logger
from sys import exc_info
from tempfile import SpooledTemporaryFile
from types import TracebackType
from typing import Any, Optional, ParamSpecArgs, ParamSpecKwargs, Self

from .exception import convert_exception_to_response


class ManejadorBase(BaseHandler):
    def load_middleware(self: Self, is_async: bool = False):
        logger: Logger = getLogger("django.request")
        self._view_middleware: list[
            Callable[[HttpRequest], HttpResponse]
        ] = []
        self._template_response_middleware: list[
            Callable[[HttpRequest], HttpResponse]
        ] = []
        self._exception_middleware: list[
            Callable[[HttpRequest], HttpResponse]
        ] = []
        get_response: HttpResponse = (
            self._get_response_async
            if is_async
            else self._get_response
        )
        handler: Callable[
            [HttpRequest], HttpResponse
        ] = convert_exception_to_response(get_response)
        handler_is_async: bool = is_async
        for middleware_path in reversed(settings.MIDDLEWARE):
            middleware: type[MiddlewareMixin] = import_string(middleware_path)
            middleware_can_sync: bool = getattr(
                middleware,
                "sync_capable",
                True
            )
            middleware_can_async: bool = getattr(
                middleware,
                "async_capable",
                False
            )
            middleware_is_async: bool
            if not middleware_can_sync and not middleware_can_async:
                raise RuntimeError(
                    f"Middleware {middleware_path} must have at least one of "
                    "sync_capable/async_capable set to True."
                )
            elif not handler_is_async and middleware_can_sync:
                middleware_is_async = False
            else:
                middleware_is_async = middleware_can_async
            adapted_handler: Callable[[HttpRequest], HttpResponse]
            mw_instance: MiddlewareMixin
            try:
                adapted_handler = self.adapt_method_mode(
                    middleware_is_async,
                    handler,
                    handler_is_async,
                    debug=settings.DEBUG,
                    name="middleware %s" % middleware_path,
                )
                mw_instance = middleware(adapted_handler)
            except MiddlewareNotUsed as exc:
                if settings.DEBUG:
                    if str(exc):
                        logger.debug(
                            "MiddlewareNotUsed(%r): %s",
                            middleware_path,
                            exc
                        )
                    else:
                        logger.debug(
                            "MiddlewareNotUsed: %r",
                            middleware_path
                        )
                continue
            else:
                handler = adapted_handler

            if mw_instance is None:
                raise ImproperlyConfigured(
                    "Middleware factory %s returned None." % middleware_path
                )

            if hasattr(mw_instance, "process_view"):
                self._view_middleware.insert(
                    0,
                    self.adapt_method_mode(is_async, mw_instance.process_view),
                )
            if hasattr(mw_instance, "process_template_response"):
                self._template_response_middleware.append(
                    self.adapt_method_mode(
                        is_async, mw_instance.process_template_response
                    ),
                )
            if hasattr(mw_instance, "process_exception"):
                self._exception_middleware.append(
                    self.adapt_method_mode(
                        False, mw_instance.process_exception
                    ),
                )
            handler = convert_exception_to_response(mw_instance)
            handler_is_async = middleware_is_async
        handler = self.adapt_method_mode(is_async, handler, handler_is_async)
        self._middleware_chain: Callable[
            [HttpRequest], HttpResponse
        ] = handler

    def get_response(
        self: Self,
        request: HttpRequest
    ) -> HttpResponse:
        set_urlconf(settings.ROOT_URLCONF)
        response: HttpResponse = self._middleware_chain(request)
        response._resource_closers.append(request.close)
        if response.status_code >= 400:
            log_response(
                "%s: %s",
                response.reason_phrase,
                request.build_absolute_uri(),
                response=response,
                request=request,
            )
        return response

    async def get_response_async(
        self: Self,
        request: HttpRequest
    ) -> HttpResponse:
        set_urlconf(settings.ROOT_URLCONF)
        response: HttpResponse = await self._middleware_chain(request)
        response._resource_closers.append(request.close)
        if response.status_code >= 400:
            await sync_to_async(log_response, thread_sensitive=False)(
                "%s: %s",
                response.reason_phrase,
                request.build_absolute_uri(),
                response=response,
                request=request,
            )
        return response


class ManejadorWSGI(ManejadorBase):
    request_class: type[WSGIRequest] = WSGIRequest

    def __init__(
        self: Self,
        *args: ParamSpecArgs,
        **kwargs: ParamSpecKwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.load_middleware()

    def __call__(
        self: Self,
        environ: tuple[str, Any],
        start_response: Callable[[str, HttpHeaders], None]
    ) -> HttpResponse:
        set_script_prefix(get_script_name(environ))
        request_started.send(sender=self.__class__, environ=environ)
        request: WSGIRequest = self.request_class(environ)
        response: HttpResponse = self.get_response(request)
        response._handler_class = self.__class__
        status: str = "%d %s" % (
            response.status_code,
            response.reason_phrase
        )
        response_headers: HttpHeaders = [
            *response.items(),
            *(
                ("Set-Cookie", c.output(header=""))
                for c in response.cookies.values()
            ),
        ]
        start_response(status, response_headers)
        if (
            getattr(response, "file_to_stream", None) is not None and
            environ.get("wsgi.file_wrapper")
        ):
            response.file_to_stream.close = response.close
            response = environ["wsgi.file_wrapper"](
                response.file_to_stream, response.block_size
            )
        return response


class ManejadorASGI(ManejadorBase):
    request_class: type[ASGIRequest] = ASGIRequest
    chunk_size: int = 2**16

    def __init__(self: Self) -> None:
        super().__init__()
        self.load_middleware(is_async=True)

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[(), dict[str, Any]],
        send: Callable[[dict[str, Any]], None]
    ):
        if scope["type"] != "http":
            raise ValueError(
                "Django can only handle ASGI/HTTP connections,"
                f" not {scope['type']}."
            )
        async with ThreadSensitiveContext():
            await self.handle(scope, receive, send)

    async def handle(
        self: Self,
        scope: Mapping[str, str],
        receive: Callable[(), dict[str, Any]],
        send: Callable[[dict[str, Any]], None]
    ) -> None:
        try:
            body_file: SpooledTemporaryFile = await self.read_body(receive)
        except RequestAborted:
            return
        set_script_prefix(self.get_script_prefix(scope))
        await sync_to_async(
            request_started.send,
            thread_sensitive=True
        )(
            sender=self.__class__, scope=scope
        )
        request, error_response = self.create_request(scope, body_file)
        if request is None:
            body_file.close()
            await self.send_response(error_response, send)
            return
        response: HttpResponse = await self.get_response_async(request)
        response._handler_class = self.__class__
        if isinstance(response, FileResponse):
            response.block_size = self.chunk_size
        await self.send_response(response, send)

    async def read_body(
        self: Self,
        receive: Callable[(), dict[str, Any]]
    ) -> SpooledTemporaryFile:
        body_file: SpooledTemporaryFile = SpooledTemporaryFile(
            max_size=settings.FILE_UPLOAD_MAX_MEMORY_SIZE, mode="w+b"
        )
        while True:
            message: dict[str, Any] = await receive()
            if message["type"] == "http.disconnect":
                body_file.close()
                raise RequestAborted()
            if "body" in message:
                body_file.write(message["body"])
            if not message.get("more_body", False):
                break
        body_file.seek(0)
        return body_file

    def create_request(
        self: Self,
        scope: Mapping[str, str],
        body_file: SpooledTemporaryFile
    ) -> tuple[Optional[ASGIRequest], Optional[HttpResponse]]:
        logger: Logger = getLogger("django.request")
        try:
            return self.request_class(scope, body_file), None
        except UnicodeDecodeError:
            logger.warning(
                "Bad Request (UnicodeDecodeError)",
                exc_info=exc_info(),
                extra={"status_code": 400},
            )
            return None, HttpResponseBadRequest()
        except RequestDataTooBig:
            return None, HttpResponse("413 Payload too large", status=413)

    def handle_uncaught_exception(
        self: Self,
        request: ASGIRequest,
        resolver: URLResolver,
        exc_info: tuple[type[BaseException], BaseException, TracebackType]
    ) -> HttpResponseServerError:
        return HttpResponseServerError(
            exc_info[2]
            if settings.DEBUG
            else "Internal Server Error"
        )

    async def send_response(
        self: Self,
        response: HttpResponse,
        send: Callable[[dict[str, Any]], None]
    ) -> None:
        response_headers: HttpHeaders = []
        for header, value in response.items():
            if isinstance(header, str):
                header = header.encode("ascii")
            if isinstance(value, str):
                value = value.encode("latin1")
            response_headers.append((bytes(header), bytes(value)))
        for c in response.cookies.values():
            response_headers.append(
                (b"Set-Cookie", c.output(header="").encode("ascii").strip())
            )
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": response_headers,
            }
        )
        if response.streaming:
            async with aclosing(response.__aiter__()) as content:
                async for part in content:
                    for chunk, _ in self.chunk_bytes(part):
                        await send(
                            {
                                "type": "http.response.body",
                                "body": chunk,
                                "more_body": True,
                            }
                        )
            await send({"type": "http.response.body"})
        else:
            for chunk, last in self.chunk_bytes(response.content):
                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": not last,
                    }
                )
        await sync_to_async(response.close, thread_sensitive=True)()

    @classmethod
    def chunk_bytes(
        cls: type[Self],
        data: Optional[bytes]
    ) -> Iterable[Optional[bytes], bool]:
        position: int = 0
        if not data:
            yield data, True
            return
        while position < len(data):
            yield (
                data[position: position+cls.chunk_size],
                (position + cls.chunk_size) >= len(data),
            )
            position += cls.chunk_size

    def get_script_prefix(
        self: Self,
        scope: Mapping[str, str]
    ) -> str:
        if settings.FORCE_SCRIPT_NAME:
            return settings.FORCE_SCRIPT_NAME
        return scope.get("root_path", "") or ""


def obtener_aplicacion_wsgi():
    setup(set_prefix=False)
    return ManejadorWSGI()


def obtener_aplicacion_asgi():
    setup(set_prefix=False)
    return ManejadorASGI()
