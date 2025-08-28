from daphne.cli import CommandLineInterface, DEFAULT_HOST, DEFAULT_PORT
from daphne.endpoints import build_endpoint_description_strings
from daphne.utils import import_by_path

from asgiref.compatibility import guarantee_single_callable
from channels.routing import ProtocolTypeRouter
import logging
import sys
from typing import ParamSpec, Self

from .access import GeneradorLogAcceso
from .server import Servidor


class InterfazLineaComando(CommandLineInterface):
    server_class: type[Servidor] = Servidor

    def run(self: Self, args: ParamSpec) -> None:
        logger: logging.Logger = logging.getLogger("daphne")
        args: ParamSpec = self.parser.parse_args(args)
        logging.basicConfig(
            level={
                0: logging.WARN,
                1: logging.INFO,
                2: logging.DEBUG,
                3: logging.DEBUG,
            }[args.verbosity],
            format=args.log_fmt,
        )
        sys.path.insert(0, ".")
        application: ProtocolTypeRouter = import_by_path(args.application)
        application = guarantee_single_callable(application)
        if not any(
            [
                args.host,
                args.port is not None,
                args.unix_socket,
                args.file_descriptor is not None,
                args.socket_strings,
            ]
        ):
            args.host = DEFAULT_HOST
            args.port = DEFAULT_PORT
        elif args.host and args.port is None:
            args.port = DEFAULT_PORT
        elif args.port is not None and not args.host:
            args.host = DEFAULT_HOST
        endpoints: tuple[str] = build_endpoint_description_strings(
            host=args.host,
            port=args.port,
            unix_socket=args.unix_socket,
            file_descriptor=args.file_descriptor,
        )
        endpoints = sorted(args.socket_strings + endpoints)
        logger.info("Starting server at {}".format(", ".join(endpoints)))
        self.server: Servidor = self.server_class(
            application=application,
            endpoints=endpoints,
            http_timeout=args.http_timeout,
            ping_interval=args.ping_interval,
            ping_timeout=args.ping_timeout,
            websocket_timeout=args.websocket_timeout,
            websocket_connect_timeout=args.websocket_connect_timeout,
            websocket_handshake_timeout=args.websocket_connect_timeout,
            application_close_timeout=args.application_close_timeout,
            action_logger=GeneradorLogAcceso(logger),
            root_path=args.root_path,
            verbosity=args.verbosity,
            proxy_forwarded_address_header=self._get_forwarded_host(args=args),
            proxy_forwarded_port_header=self._get_forwarded_port(args=args),
            proxy_forwarded_proto_header=(
                "X-Forwarded-Proto" if args.proxy_headers else None
            ),
            server_name=args.server_name,
        )
        self.server.run()
