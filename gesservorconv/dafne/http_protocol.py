from django.conf import settings

from importlib import import_module
import logging
import traceback
from typing import Any, Optional, Self

from twisted.internet.address import UNIXAddress
from twisted.internet.interfaces import IProtocolNegotiationFactory
from twisted.web import http
from zope.interface import implementer

from daphne.http_protocol import HTTPFactory, WebRequest

logger = logging.getLogger("daphne.http_protocol")


class PeticionWeb(WebRequest):
    def handle_reply(
        self: Self,
        message: dict[str, Any]
    ) -> None:
        if self.finished or self.channel is None:
            return
        if "type" not in message:
            raise ValueError("Message has no type defined")
        if message["type"] == "http.response.start":
            if self._response_started:
                raise ValueError("HTTP response has already been started")
            self._response_started = True
            if "status" not in message:
                raise ValueError(
                    "Specifying a status code is required for a"
                    " Response message."
                )
            self.setResponseCode(message["status"])
            for header, value in message.get("headers", {}):
                self.responseHeaders.addRawHeader(header, value)
            if (
                self.server.server_name and
                not self.responseHeaders.hasHeader("server")
            ):
                self.setHeader(b"server", self.server.server_name.encode())
            logger.debug(
                "HTTP %s response started for %s",
                message["status"],
                self.client_addr
            )
        elif message["type"] == "http.response.body":
            if not self._response_started:
                raise ValueError(
                    "HTTP response has not yet been started but got %s"
                    % message["type"]
                )
            # Write out body
            http.Request.write(self, message.get("body", b""))
            # End if there's no more content
            if not message.get("more_body", False):
                self.finish()
                logger.debug("HTTP response complete for %s", self.client_addr)
                try:
                    uri = self.uri.decode("ascii")
                except UnicodeDecodeError:
                    uri = repr(self.uri)
                try:

                    SessionStore = import_module(
                        settings.SESSION_ENGINE
                    ).SessionStore
                    clave_sesion: Optional[bytes] = self.getCookie(
                        settings.SESSION_COOKIE_NAME.encode(
                            "utf-8"
                        )
                    )
                    usuario: str
                    if not clave_sesion:
                        usuario = "anonymous user"
                    else:
                        sesion = SessionStore(
                            session_key=clave_sesion.decode()
                        )
                        # sesion.load() conflicto async
                        id_usuario: int = sesion.load().get(
                            "_auth_user_id", 0
                        )
                        if id_usuario == 0:
                            usuario = "anonymous user"
                        else:
                            usuario = f'user {id_usuario}'
                except Exception:
                    usuario = "anonymous user"
                try:
                    self.server.log_action(
                        "http",
                        "complete",
                        {
                            "path": (
                                f'{self.client_scheme}://'
                                f'{self.getHeader("Host")}'
                                f'{uri}'
                            ),
                            "status": self.code,
                            "method": self.method.decode("ascii", "replace"),
                            "client": (
                                "%s:%s" % tuple(self.client_addr)
                                if self.client_addr
                                else None
                            ),
                            "user": usuario,
                            "browser": self.getHeader("User-Agent"),
                            "time_taken": self.duration(),
                            "size": self.sentLength,
                        },
                    )
                except Exception:
                    logger.error(traceback.format_exc())
            else:
                logger.debug("HTTP response chunk for %s", self.client_addr)
        else:
            raise ValueError(
                "Cannot handle message type %s!" % message["type"]
            )


@implementer(IProtocolNegotiationFactory)
class FabricaHTTP(HTTPFactory):
    def buildProtocol(
        self: Self,
        addr: UNIXAddress
    ) -> http.HTTPChannel:
        try:
            protocol: http.HTTPChannel = http.HTTPFactory.buildProtocol(
                self,
                addr
            )
            protocol.requestFactory: type[PeticionWeb] = PeticionWeb
            return protocol
        except Exception:
            logger.error("Cannot build protocol: %s" % traceback.format_exc())
            raise
