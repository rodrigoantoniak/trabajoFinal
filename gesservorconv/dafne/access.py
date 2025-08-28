from datetime import datetime
from logging import Logger
from typing import Any, Dict, Optional, Self


# daphne.access.AccessLogGenerator
class GeneradorLogAcceso:
    def __init__(self: Self, logger: Logger) -> None:
        self.logger: Logger = logger

    def __call__(
        self: Self,
        protocol: str,
        action: str,
        details: Dict[str, Any]
    ):
        if protocol == "http" and action == "complete":
            self.write_entry(
                host=details["client"],
                date=datetime.now(),
                request="%(method)s %(path)s" % details,
                status=details["status"],
                length=details["size"],
                ident=details["browser"],
                user=details["user"]
            )
        elif protocol == "websocket" and action == "connecting":
            self.write_entry(
                host=details["client"],
                date=datetime.now(),
                request="WSCONNECTING %(path)s" % details,
                status=details["status"],
                ident=details["browser"],
                user=details["user"]
            )
        elif protocol == "websocket" and action == "rejected":
            self.write_entry(
                host=details["client"],
                date=datetime.now(),
                request="WSREJECT %(path)s" % details,
                status="3003",
                ident=details["browser"],
                user=details["user"]
            )
        elif protocol == "websocket" and action == "connected":
            self.write_entry(
                host=details["client"],
                date=datetime.now(),
                request="WSCONNECT %(path)s" % details,
                status=details["status"],
                ident=details["browser"],
                user=details["user"]
            )
        elif protocol == "websocket" and action == "disconnected":
            self.write_entry(
                host=details["client"],
                date=datetime.now(),
                request="WSDISCONNECT %(path)s" % details,
                status=details["status"],
                ident=details["browser"],
                user=details["user"]
            )

    def write_entry(
        self: Self,
        host: str,
        date: str,
        request: str,
        status: Optional[str] = None,
        length: Optional[str] = None,
        ident: Optional[str] = None,
        user: Optional[str] = None
    ):
        self.logger.info(
            '%s { %s } (%s) [%s] "%s" %s %s',
            host,
            ident or "-",
            user or "-",
            date.strftime("%d/%m/%Y %H:%M:%S"),
            request,
            status or "-",
            length or "-"
        )
