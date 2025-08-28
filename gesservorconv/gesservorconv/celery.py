from logging import Formatter, Handler, Logger, root, StreamHandler
import os
from pathlib import Path
from sys import stdout
from typing import Any

from celery import Celery
from celery.signals import after_setup_logger

from .logging import Filtro, Formateador, ManejadorArchivosTiempoRotativo


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gesservorconv.settings')

app: Celery = Celery('gesservorconv')

app.config_from_object('django.conf:settings', namespace='CELERY')


@after_setup_logger.connect
def on_after_setup_logger(**kwargs: dict[str, Any]) -> None:
    BASE_DIR: Path = Path(__file__).resolve().parent
    simple_formatter: Formatter = Formateador(
        fmt='{levelname} {message}',
        style='{'
    )
    verbose_formatter: Formatter = Formateador(
        fmt='{levelname} {asctime} {module}'
        ' {process:d} {thread:d} {message}',
        datefmt='%d/%m/%Y %H:%M:%S',
        style='{'
    )
    file_handler: Handler = ManejadorArchivosTiempoRotativo(
        filename=os.path.join(BASE_DIR, 'log/celery.log'),
        when='MIDNIGHT', backupCount=0, encoding='utf-8',
        delay=False, utc=False
    )
    file_handler.setFormatter(verbose_formatter)
    file_handler.setLevel('INFO')
    console_handler: Handler = StreamHandler(stdout)
    console_handler.addFilter(Filtro())
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel('INFO')
    for logger in [
        logger for nombre, logger
        in root.manager.loggerDict.items()
        if (
            nombre.startswith('celery') and
            isinstance(logger, Logger)
        )
    ]:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False


app.autodiscover_tasks()
