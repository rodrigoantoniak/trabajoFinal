# daphne.server.py
import asyncio  # isort:skip
import os  # isort:skip
import sys  # isort:skip
import warnings  # isort:skip
from concurrent.futures import ThreadPoolExecutor  # isort:skip
from twisted.internet import asyncioreactor  # isort:skip


twisted_loop = asyncio.new_event_loop()
if "ASGI_THREADS" in os.environ:
    twisted_loop.set_default_executor(
        ThreadPoolExecutor(max_workers=int(os.environ["ASGI_THREADS"]))
    )

current_reactor = sys.modules.get("twisted.internet.reactor", None)
if current_reactor is not None:
    if not isinstance(current_reactor, asyncioreactor.AsyncioSelectorReactor):
        warnings.warn(
            "Something has already installed a non-asyncio Twisted reactor. Attempting to uninstall it; "
            + "you can fix this warning by importing daphne.server early in your codebase or "
            + "finding the package that imports Twisted and importing it later on.",
            UserWarning,
            stacklevel=2,
        )
        del sys.modules["twisted.internet.reactor"]
        asyncioreactor.install(twisted_loop)
else:
    asyncioreactor.install(twisted_loop)

import logging
import time
from concurrent.futures import CancelledError
from functools import partial

from twisted.internet import defer, reactor
from twisted.internet.endpoints import serverFromString
from twisted.logger import STDLibLogObserver, globalLogBeginner
from twisted.web import http

from typing import Any, Optional, Self

from .http_protocol import FabricaHTTP
from .ws_protocol import FabricaWebSocket


logger: logging.Logger = logging.getLogger("daphne.server")


class Servidor:
    def __init__(
        self: Self,
        application,
        endpoints = None,
        signal_handlers: bool = True,
        action_logger: Optional[logging.Logger] = None,
        http_timeout: Optional[int] = None,
        request_buffer_size: int = 8192,
        websocket_timeout: int = 86400,
        websocket_connect_timeout: int = 20,
        ping_interval: int = 20,
        ping_timeout: int = 30,
        root_path: str = "",
        proxy_forwarded_address_header = None,
        proxy_forwarded_port_header = None,
        proxy_forwarded_proto_header = None,
        verbosity: int = 1,
        websocket_handshake_timeout: int = 5,
        application_close_timeout: int = 10,
        ready_callable = None,
        server_name: str = "daphne",
    ):
        self.application = application
        self.endpoints = endpoints or []
        self.listeners = []
        self.listening_addresses = []
        self.signal_handlers: bool = signal_handlers
        self.action_logger: Optional[logging.Logger] = action_logger
        self.http_timeout: Optional[int] = http_timeout
        self.ping_interval: int = ping_interval
        self.ping_timeout: int = ping_timeout
        self.request_buffer_size: int = request_buffer_size
        self.proxy_forwarded_address_header = proxy_forwarded_address_header
        self.proxy_forwarded_port_header = proxy_forwarded_port_header
        self.proxy_forwarded_proto_header = proxy_forwarded_proto_header
        self.websocket_timeout: int = websocket_timeout
        self.websocket_connect_timeout: int = websocket_connect_timeout
        self.websocket_handshake_timeout: int = websocket_handshake_timeout
        self.application_close_timeout: int = application_close_timeout
        self.root_path: str = root_path
        self.verbosity: int = verbosity
        self.abort_start: bool = False
        self.ready_callable = ready_callable
        self.server_name: str = server_name
        if not self.endpoints:
            logger.error(
                "No endpoints. This server will not listen on anything."
            )
            sys.exit(1)

    def run(self: Self) -> None:
        self.connections: dict[str, Any] = {}
        self.http_factory: FabricaHTTP = FabricaHTTP(self)
        self.ws_factory: FabricaWebSocket = FabricaWebSocket(
            self, server=self.server_name
        )
        self.ws_factory.setProtocolOptions(
            autoPingTimeout=self.ping_timeout,
            allowNullOrigin=True,
            openHandshakeTimeout=self.websocket_handshake_timeout,
        )
        if self.verbosity <= 1:
            globalLogBeginner.beginLoggingTo(
                [lambda _: None], redirectStandardIO=False, discardBuffer=True
            )
        else:
            globalLogBeginner.beginLoggingTo([STDLibLogObserver(__name__)])
        if http.H2_ENABLED:
            logger.info("HTTP/2 support enabled")
        else:
            logger.info(
                "HTTP/2 support not enabled"
                " (install the http2 and tls Twisted extras)"
            )
        reactor.callLater(1, self.application_checker)
        reactor.callLater(2, self.timeout_checker)
        for socket_description in self.endpoints:
            logger.info("Configuring endpoint %s", socket_description)
            ep = serverFromString(reactor, str(socket_description))
            listener = ep.listen(self.http_factory)
            listener.addCallback(self.listen_success)
            listener.addErrback(self.listen_error)
            self.listeners.append(listener)
        asyncio.set_event_loop(reactor._asyncioEventloop)
        if self.verbosity >= 3:
            asyncio.get_event_loop().set_debug(True)
        reactor.addSystemEventTrigger(
            "before",
            "shutdown",
            self.kill_all_applications
        )
        if not self.abort_start:
            if self.ready_callable:
                self.ready_callable()
            reactor.run(installSignalHandlers=self.signal_handlers)

    def listen_success(self, port):
        if hasattr(port, "getHost"):
            host = port.getHost()
            if hasattr(host, "host") and hasattr(host, "port"):
                self.listening_addresses.append((host.host, host.port))
                logger.info(
                    "Listening on TCP address %s:%s",
                    port.getHost().host,
                    port.getHost().port,
                )

    def listen_error(self, failure):
        logger.critical("Listen failure: %s", failure.getErrorMessage())
        self.stop()

    def stop(self):
        if reactor.running:
            reactor.stop()
        else:
            self.abort_start = True

    def protocol_connected(self, protocol):
        if protocol in self.connections:
            raise RuntimeError(
                "Protocol %r was added to main list twice!" % protocol
            )
        self.connections[protocol] = {"connected": time.time()}

    def protocol_disconnected(self, protocol):
        if "disconnected" not in self.connections[protocol]:
            self.connections[protocol]["disconnected"] = time.time()

    def create_application(self, protocol, scope):
        assert "application_instance" not in self.connections[protocol]
        input_queue = asyncio.Queue()
        scope.setdefault("asgi", {"version": "3.0"})
        application_instance = self.application(
            scope=scope,
            receive=input_queue.get,
            send=partial(self.handle_reply, protocol),
        )
        if protocol not in self.connections:
            return None
        self.connections[protocol][
            "application_instance"
        ] = asyncio.ensure_future(
            application_instance,
            loop=asyncio.get_event_loop(),
        )
        return input_queue

    async def handle_reply(self, protocol, message):
        if protocol not in self.connections or self.connections[protocol].get(
            "disconnected", None
        ):
            return
        try:
            self.check_headers_type(message)
        except ValueError:
            protocol.basic_error(500, b"Server Error", "Server Error")
            raise
        protocol.handle_reply(message)

    @staticmethod
    def check_headers_type(message):
        if not message["type"] == "http.response.start":
            return
        for k, v in message.get("headers", []):
            if not isinstance(k, bytes):
                raise ValueError(
                    "Header name '{}' expected to be `bytes`, but got `{}`".format(
                        k, type(k)
                    )
                )
            if not isinstance(v, bytes):
                raise ValueError(
                    "Header value '{}' expected to be `bytes`, but got `{}`".format(
                        v, type(v)
                    )
                )

    def application_checker(self):
        for protocol, details in list(self.connections.items()):
            disconnected = details.get("disconnected", None)
            application_instance = details.get("application_instance", None)
            if (
                disconnected
                and time.time() - disconnected > self.application_close_timeout
            ):
                if application_instance and not application_instance.done():
                    logger.warning(
                        "Application instance %r for connection %s took too long to shut down and was killed.",
                        application_instance,
                        repr(protocol),
                    )
                    application_instance.cancel()
            if application_instance and application_instance.done():
                try:
                    exception = application_instance.exception()
                except (CancelledError, asyncio.CancelledError):
                    # Future cancellation. We can ignore this.
                    pass
                else:
                    if exception:
                        if isinstance(exception, KeyboardInterrupt):
                            self.stop()
                        else:
                            logger.error(
                                "Exception inside application: %s",
                                exception,
                                exc_info=exception,
                            )
                            if not disconnected:
                                protocol.handle_exception(exception)
                del self.connections[protocol]["application_instance"]
                application_instance = None
            if not application_instance and disconnected:
                del self.connections[protocol]
        reactor.callLater(1, self.application_checker)

    def kill_all_applications(self):
        wait_for = []
        for details in self.connections.values():
            application_instance = details["application_instance"]
            if not application_instance.done():
                application_instance.cancel()
                wait_for.append(application_instance)
        logger.info("Killed %i pending application instances", len(wait_for))
        wait_deferred = defer.Deferred.fromFuture(asyncio.gather(*wait_for))
        wait_deferred.addErrback(lambda x: None)
        return wait_deferred

    def timeout_checker(self):
        for protocol in list(self.connections.keys()):
            protocol.check_timeouts()
        reactor.callLater(2, self.timeout_checker)

    def log_action(self, protocol, action, details):
        if self.action_logger:
            self.action_logger(protocol, action, details)
