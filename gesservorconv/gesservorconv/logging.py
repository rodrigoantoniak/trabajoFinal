from logging import (
    CRITICAL,
    ERROR,
    WARNING,
    INFO,
    DEBUG,
    NOTSET,
    Filter,
    Formatter,
    LogRecord
)
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, List, Self, Tuple


mapa_colores: Dict[Tuple[str, int], str] = {
    ('celery', NOTSET): '\x1b[4m',
    ('celery.beat', NOTSET): '\x1b[4;31m',
    ('celery.task', NOTSET): '\x1b[4;34m',
    ('celery.evcam', NOTSET): '\x1b[4;35m',
    ('celery.bootsteps', NOTSET): '\x1b[4;35m',
    ('celery.pool', NOTSET): '\x1b[4;35m',
    ('celery.redirected', NOTSET): '\x1b[4;35m',
    ('celery.app.base', NOTSET): '\x1b[4;32m',
    ('celery.app.control', NOTSET): '\x1b[4;32m',
    ('celery.app.builtins', NOTSET): '\x1b[4;32m',
    ('celery.app.trace', NOTSET): '\x1b[4;32m',
    ('celery.backends.base', NOTSET): '\x1b[4;36m',
    ('celery.concurrency.asynpool', NOTSET): '\x1b[4;36m',
    ('celery.concurrency.prefork', NOTSET): '\x1b[4;36m',
    ('celery.events.state', NOTSET): '\x1b[4;36m',
    ('celery.utils.functional', NOTSET): '\x1b[4;36m',
    ('celery.utils.dispatch.signal', NOTSET): '\x1b[4;36m',
    ('celery.worker', NOTSET): '\x1b[4;33m',
    ('celery.apps.worker', NOTSET): '\x1b[4;33m',
    ('celery.bin.worker', NOTSET): '\x1b[4;33m',
    ('celery.worker.strategy', NOTSET): '\x1b[4;33m',
    ('celery.worker.request', NOTSET): '\x1b[4;33m',
    ('celery.worker.pidbox', NOTSET): '\x1b[4;33m',
    ('celery.worker.loops', NOTSET): '\x1b[4;33m',
    ('celery.worker.control', NOTSET): '\x1b[4;33m',
    ('celery.worker.autoscale', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.tasks', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.mingle', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.gossip', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.control', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.consumer', NOTSET): '\x1b[4;33m',
    ('celery.worker.consumer.connection', NOTSET): '\x1b[4;33m',
    ('celery', DEBUG): '\x1b[2m',
    ('celery.beat', DEBUG): '\x1b[31m',
    ('celery.task', DEBUG): '\x1b[34m',
    ('celery.app.base', DEBUG): '\x1b[32m',
    ('celery.app.trace', DEBUG): '\x1b[32m',
    ('celery.app.control', DEBUG): '\x1b[32m',
    ('celery.app.builtins', DEBUG): '\x1b[32m',
    ('celery.backends.base', DEBUG): '\x1b[36m',
    ('celery.concurrency.asynpool', DEBUG): '\x1b[36m',
    ('celery.concurrency.prefork', DEBUG): '\x1b[36m',
    ('celery.events.state', DEBUG): '\x1b[36m',
    ('celery.utils.functional', DEBUG): '\x1b[36m',
    ('celery.utils.dispatch.signal', DEBUG): '\x1b[36m',
    ('celery.worker', DEBUG): '\x1b[33m',
    ('celery.apps.worker', DEBUG): '\x1b[33m',
    ('celery.bin.worker', DEBUG): '\x1b[33m',
    ('celery.worker.strategy', DEBUG): '\x1b[33m',
    ('celery.worker.request', DEBUG): '\x1b[33m',
    ('celery.worker.loops', DEBUG): '\x1b[33m',
    ('celery.worker.control', DEBUG): '\x1b[33m',
    ('celery.worker.autoscale', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.tasks', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.mingle', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.gossip', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.control', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.consumer', DEBUG): '\x1b[33m',
    ('celery.worker.consumer.connection', DEBUG): '\x1b[33m',
    ('celery', INFO): '\x1b[0m',
    ('celery.beat', INFO): '\x1b[91m',
    ('celery.task', INFO): '\x1b[94m',
    ('celery.app.base', INFO): '\x1b[92m',
    ('celery.app.trace', INFO): '\x1b[92m',
    ('celery.app.control', INFO): '\x1b[95m',
    ('celery.app.builtins', INFO): '\x1b[96m',
    ('celery.backends.base', INFO): '\x1b[96m',
    ('celery.concurrency.asynpool', INFO): '\x1b[96m',
    ('celery.concurrency.prefork', INFO): '\x1b[96m',
    ('celery.events.state', INFO): '\x1b[96m',
    ('celery.utils.functional', INFO): '\x1b[96m',
    ('celery.utils.dispatch.signal', INFO): '\x1b[96m',
    ('celery.worker', INFO): '\x1b[93m',
    ('celery.apps.worker', INFO): '\x1b[93m',
    ('celery.bin.worker', INFO): '\x1b[93m',
    ('celery.worker.strategy', INFO): '\x1b[93m',
    ('celery.worker.request', INFO): '\x1b[93m',
    ('celery.worker.pidbox', INFO): '\x1b[93m',
    ('celery.worker.loops', INFO): '\x1b[93m',
    ('celery.worker.control', INFO): '\x1b[93m',
    ('celery.worker.autoscale', INFO): '\x1b[93m',
    ('celery.worker.consumer.tasks', INFO): '\x1b[93m',
    ('celery.worker.consumer.mingle', INFO): '\x1b[93m',
    ('celery.worker.consumer.gossip', INFO): '\x1b[93m',
    ('celery.worker.consumer.control', INFO): '\x1b[93m',
    ('celery.worker.consumer.consumer', INFO): '\x1b[93m',
    ('celery.worker.consumer.connection', INFO): '\x1b[93m',
    ('celery', WARNING): '\x1b[1m',
    ('celery.beat', WARNING): '\x1b[1;31m',
    ('celery.task', WARNING): '\x1b[1;34m',
    ('celery.evcam', WARNING): '\x1b[1;35m',
    ('celery.bootsteps', WARNING): '\x1b[1;35m',
    ('celery.pool', WARNING): '\x1b[1;35m',
    ('celery.redirected', WARNING): '\x1b[1;35m',
    ('celery.app.base', WARNING): '\x1b[1;32m',
    ('celery.app.control', WARNING): '\x1b[1;32m',
    ('celery.app.builtins', WARNING): '\x1b[1;32m',
    ('celery.app.trace', WARNING): '\x1b[1;32m',
    ('celery.backends.base', WARNING): '\x1b[1;36m',
    ('celery.concurrency.asynpool', WARNING): '\x1b[1;36m',
    ('celery.concurrency.prefork', WARNING): '\x1b[1;36m',
    ('celery.events.state', WARNING): '\x1b[1;36m',
    ('celery.utils.functional', WARNING): '\x1b[1;36m',
    ('celery.utils.dispatch.signal', WARNING): '\x1b[1;36m',
    ('celery.worker', WARNING): '\x1b[1;33m',
    ('celery.apps.worker', WARNING): '\x1b[1;33m',
    ('celery.bin.worker', WARNING): '\x1b[1;33m',
    ('celery.worker.strategy', WARNING): '\x1b[1;33m',
    ('celery.worker.request', WARNING): '\x1b[1;33m',
    ('celery.worker.pidbox', WARNING): '\x1b[1;33m',
    ('celery.worker.loops', WARNING): '\x1b[1;33m',
    ('celery.worker.control', WARNING): '\x1b[1;33m',
    ('celery.worker.autoscale', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.tasks', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.mingle', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.gossip', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.control', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.consumer', WARNING): '\x1b[1;33m',
    ('celery.worker.consumer.connection', WARNING): '\x1b[1;33m',
    ('celery', ERROR): '\x1b[7m',
    ('celery.beat', ERROR): '\x1b[7;31m',
    ('celery.task', ERROR): '\x1b[7;34m',
    ('celery.evcam', ERROR): '\x1b[7;35m',
    ('celery.bootsteps', ERROR): '\x1b[7;35m',
    ('celery.pool', ERROR): '\x1b[7;35m',
    ('celery.redirected', ERROR): '\x1b[7;35m',
    ('celery.app.base', ERROR): '\x1b[7;32m',
    ('celery.app.control', ERROR): '\x1b[7;32m',
    ('celery.app.builtins', ERROR): '\x1b[7;32m',
    ('celery.app.trace', ERROR): '\x1b[7;32m',
    ('celery.backends.base', ERROR): '\x1b[7;36m',
    ('celery.concurrency.asynpool', ERROR): '\x1b[7;36m',
    ('celery.concurrency.prefork', ERROR): '\x1b[7;36m',
    ('celery.events.state', ERROR): '\x1b[7;36m',
    ('celery.utils.functional', ERROR): '\x1b[7;36m',
    ('celery.utils.dispatch.signal', ERROR): '\x1b[7;36m',
    ('celery.worker', ERROR): '\x1b[7;33m',
    ('celery.apps.worker', ERROR): '\x1b[7;33m',
    ('celery.bin.worker', ERROR): '\x1b[7;33m',
    ('celery.worker.strategy', ERROR): '\x1b[7;33m',
    ('celery.worker.request', ERROR): '\x1b[7;33m',
    ('celery.worker.pidbox', ERROR): '\x1b[7;33m',
    ('celery.worker.loops', ERROR): '\x1b[7;33m',
    ('celery.worker.control', ERROR): '\x1b[7;33m',
    ('celery.worker.autoscale', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.tasks', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.mingle', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.gossip', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.control', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.consumer', ERROR): '\x1b[7;33m',
    ('celery.worker.consumer.connection', ERROR): '\x1b[7;33m',
    ('celery', CRITICAL): '\x1b[1;7m',
    ('celery.beat', CRITICAL): '\x1b[1;7;31m',
    ('celery.task', CRITICAL): '\x1b[1;7;34m',
    ('celery.evcam', CRITICAL): '\x1b[1;7;35m',
    ('celery.bootsteps', CRITICAL): '\x1b[1;7;35m',
    ('celery.pool', CRITICAL): '\x1b[1;7;35m',
    ('celery.redirected', CRITICAL): '\x1b[1;7;35m',
    ('celery.app.base', CRITICAL): '\x1b[1;7;32m',
    ('celery.app.control', CRITICAL): '\x1b[1;7;32m',
    ('celery.app.builtins', CRITICAL): '\x1b[1;7;32m',
    ('celery.app.trace', CRITICAL): '\x1b[1;7;32m',
    ('celery.backends.base', CRITICAL): '\x1b[1;7;36m',
    ('celery.concurrency.asynpool', CRITICAL): '\x1b[1;7;36m',
    ('celery.concurrency.prefork', CRITICAL): '\x1b[1;7;36m',
    ('celery.events.state', CRITICAL): '\x1b[1;7;36m',
    ('celery.utils.functional', CRITICAL): '\x1b[1;7;36m',
    ('celery.utils.dispatch.signal', CRITICAL): '\x1b[1;7;36m',
    ('celery.worker', CRITICAL): '\x1b[1;7;33m',
    ('celery.apps.worker', CRITICAL): '\x1b[1;7;33m',
    ('celery.bin.worker', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.strategy', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.request', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.pidbox', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.loops', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.control', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.autoscale', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.tasks', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.mingle', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.gossip', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.control', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.consumer', CRITICAL): '\x1b[1;7;33m',
    ('celery.worker.consumer.connection', CRITICAL): '\x1b[1;7;33m',
}


class Filtro(Filter):
    def format(self: Self, record: LogRecord) -> bool:
        return record.levelno < ERROR


class Formateador(Formatter):
    def format(self: Self, record: LogRecord) -> str:
        record.message = (
            f'{mapa_colores[(record.name,record.levelno)]}'
            f'{record.getMessage()}\x1b[0m'
            if (record.name, record.levelno) in mapa_colores.keys()
            else record.getMessage()
        )
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s: str = self.formatMessage(record)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s


class ManejadorArchivosTiempoRotativo(
    TimedRotatingFileHandler
):
    def namer(self: Self, name: str) -> str:
        partes: List[str] = name.split(".")
        nombre: str = ".".join(partes[:-2])
        nombre = f"{nombre}_{partes[-1]}.{partes[-2]}"
        return nombre
