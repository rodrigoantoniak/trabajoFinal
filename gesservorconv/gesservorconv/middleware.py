from django.conf import settings
from django.http import HttpRequest, HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware, logger
from django.urls import get_callable
from django.utils.log import log_response
from typing import Self


class MiddlewareVistaCsrf(CsrfViewMiddleware):
    def _reject(
        self: Self,
        request: HttpRequest,
        reason: str
    ) -> HttpResponseForbidden:
        response: HttpResponseForbidden = get_callable(
            settings.CSRF_FAILURE_VIEW
        )(
            request,
            reason=reason
        )
        log_response(
            "Forbidden (%s): %s",
            reason,
            request.build_absolute_uri(),
            response=response,
            request=request,
            logger=logger,
        )
        return response
