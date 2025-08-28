from django.conf import settings

import logging
import traceback

from autobahn.twisted.websocket import ConnectionDeny
from importlib import import_module
from twisted.internet.address import UNIXAddress
from twisted.internet.protocol import Protocol
from typing import Self

from daphne.ws_protocol import WebSocketFactory, WebSocketProtocol


logger = logging.getLogger("daphne.ws_protocol")


class ProtocoloWebSocket(WebSocketProtocol):
    def applicationCreateWorked(self: Self, application_queue) -> None:
        self.application_queue = application_queue
        self.application_queue.put_nowait({"type": "websocket.connect"})
        usuario: str
        for clave, igual, valor in (
            [
                cookie.partition("=") for cookie
                in self.request.headers["cookie"].split("; ")
            ]
        ):
            if clave == settings.SESSION_COOKIE_NAME:
                SessionStore = import_module(
                    settings.SESSION_ENGINE
                ).SessionStore
                sesion = SessionStore(
                    session_key=valor
                )
                id_usuario: int = sesion.load().get(
                    "_auth_user_id", "0"
                )
                if id_usuario == "0":
                    usuario = "anonymous user"
                    break
                else:
                    usuario = f'user {id_usuario}'
                    break
        else:
            usuario = "anonymous user"
        self.server.log_action(
            "websocket",
            "connecting",
            {
                "path": (
                    f'ws://{self.request.headers["host"]}'
                    f'{self.request.path}'
                ),
                "client": (
                    "%s:%s" % tuple(self.client_addr)
                    if self.client_addr else None
                ),
                "user": usuario,
                "status": self.state,
                "browser": self.request.headers["user-agent"],
            },
        )

    def onOpen(self: Self) -> None:
        logger.debug("WebSocket %s open and established", self.client_addr)
        usuario: str
        for clave, igual, valor in (
            [
                cookie.partition("=") for cookie
                in self.request.headers["cookie"].split("; ")
            ]
        ):
            if clave == settings.SESSION_COOKIE_NAME:
                SessionStore = import_module(
                    settings.SESSION_ENGINE
                ).SessionStore
                sesion = SessionStore(
                    session_key=valor
                )
                id_usuario: int = sesion.load().get(
                    "_auth_user_id", "0"
                )
                if id_usuario == "0":
                    usuario = "anonymous user"
                    break
                else:
                    usuario = f'user {id_usuario}'
                    break
        else:
            usuario = "anonymous user"
        self.server.log_action(
            "websocket",
            "connected",
            {
                "path": (
                    f'ws://{self.request.headers["host"]}'
                    f'{self.request.path}'
                ),
                "client": (
                    "%s:%s" % tuple(self.client_addr)
                    if self.client_addr else None
                ),
                "status": self.state,
                "browser": self.request.headers["user-agent"],
                "user": usuario,
            },
        )

    def onClose(self: Self, wasClean: bool, code: int, reason: str) -> None:
        self.server.protocol_disconnected(self)
        logger.debug("WebSocket closed for %s", self.client_addr)
        usuario: str
        for clave, igual, valor in (
            [
                cookie.partition("=") for cookie
                in self.request.headers["cookie"].split("; ")
            ]
        ):
            if clave == settings.SESSION_COOKIE_NAME:
                SessionStore = import_module(
                    settings.SESSION_ENGINE
                ).SessionStore
                sesion = SessionStore(
                    session_key=valor
                )
                id_usuario: int = sesion.load().get(
                    "_auth_user_id", "0"
                )
                if id_usuario == "0":
                    usuario = "anonymous user"
                    break
                else:
                    usuario = f'user {id_usuario}'
                    break
        else:
            usuario = "anonymous user"
        if not self.muted and hasattr(self, "application_queue"):
            self.application_queue.put_nowait(
                {"type": "websocket.disconnect", "code": code}
            )
        self.server.log_action(
            "websocket",
            "disconnected",
            {
                "path": (
                    f'ws://{self.request.headers["host"]}'
                    f'{self.request.path}'
                ),
                "client": (
                    "%s:%s" % tuple(self.client_addr)
                    if self.client_addr else None
                ),
                "status": code,
                "browser": self.request.headers["user-agent"],
                "user": usuario,
            },
        )

    def serverReject(self: Self) -> None:
        self.handshake_deferred.errback(
            ConnectionDeny(code=403, reason="Access denied")
        )
        del self.handshake_deferred
        self.server.protocol_disconnected(self)
        logger.debug("WebSocket %s rejected by application", self.client_addr)
        usuario: str
        for clave, igual, valor in (
            [
                cookie.partition("=") for cookie
                in self.request.headers["cookie"].split("; ")
            ]
        ):
            if clave == settings.SESSION_COOKIE_NAME:
                SessionStore = import_module(
                    settings.SESSION_ENGINE
                ).SessionStore
                sesion = SessionStore(
                    session_key=valor
                )
                id_usuario: int = sesion.load().get(
                    "_auth_user_id", "0"
                )
                if id_usuario == "0":
                    usuario = "anonymous user"
                    break
                else:
                    usuario = f'user {id_usuario}'
                    break
        else:
            usuario = "anonymous user"
        self.server.log_action(
            "websocket",
            "rejected",
            {
                "path": (
                    f'ws://{self.request.headers["host"]}'
                    f'{self.request.path}'
                ),
                "client": (
                    "%s:%s" % tuple(self.client_addr)
                    if self.client_addr else None
                ),
                "browser": self.request.headers["user-agent"],
                "user": usuario,
            },
        )


class FabricaWebSocket(WebSocketFactory):
    protocol: type[ProtocoloWebSocket] = ProtocoloWebSocket

    def buildProtocol(
        self: Self,
        addr: UNIXAddress
    ) -> Protocol:
        try:
            protocol: Protocol = super().buildProtocol(addr)
            protocol.factory = self
            return protocol
        except Exception:
            logger.error("Cannot build protocol: %s" % traceback.format_exc())
            raise
