from django.apps.registry import Apps
from django.conf import settings
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation
from django.db.models import Q
from django_celery_beat.models import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask
)

from pytz import timezone


def forwards_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    PlanificacionCron: CrontabSchedule = apps.get_model(
        'django_celery_beat',
        'CrontabSchedule'
    )
    PlanificacionIntervalo: IntervalSchedule = apps.get_model(
        'django_celery_beat',
        'IntervalSchedule'
    )
    TareaPeriodica: PeriodicTask = apps.get_model(
        'django_celery_beat',
        'PeriodicTask'
    )
    db_alias: str = schema_editor.connection.alias
    plan_ocho: PlanificacionCron = PlanificacionCron(
        hour="8,20", minute="0",
        timezone=timezone(settings.TIME_ZONE)
    )
    plan_minuto: PlanificacionIntervalo = PlanificacionIntervalo(
        every=60, period=IntervalSchedule.SECONDS
    )
    PlanificacionCron.objects.using(db_alias).bulk_create(
        [
            plan_ocho
        ]
    )
    PlanificacionIntervalo.objects.using(db_alias).bulk_create(
        [
            plan_minuto
        ]
    )
    suspender_solicitudes: PeriodicTask = TareaPeriodica(
        interval=plan_minuto,
        name='Suspender solicitudes',
        task='solicitudes.tasks.suspender_solicitudes',
    )
    sugerir_convenios: PeriodicTask = TareaPeriodica(
        crontab=plan_ocho,
        name='Sugerir convenios',
        task='servicios.tasks.sugerir_convenios',
    )
    TareaPeriodica.objects.using(db_alias).bulk_create(
        [
            suspender_solicitudes,
            sugerir_convenios
        ]
    )


def reverse_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    PlanificacionCron: CrontabSchedule = apps.get_model(
        'django_celery_beat',
        'CrontabSchedule'
    )
    PlanificacionIntervalo: IntervalSchedule = apps.get_model(
        'django_celery_beat',
        'IntervalSchedule'
    )
    TareaPeriodica: PeriodicTask = apps.get_model(
        'django_celery_beat',
        'PeriodicTask'
    )
    db_alias: str = schema_editor.connection.alias
    TareaPeriodica.objects.using(db_alias).filter(
        name__in=[
            'Suspender solicitudes'
            'Sugerir convenios'
        ]
    ).delete()
    PlanificacionIntervalo.objects.using(db_alias).filter(
        Q(
            every=60, period=IntervalSchedule.SECONDS
        )
    ).delete()
    PlanificacionCron.objects.using(db_alias).filter(
        Q(
            hour="8,20", minute="0",
            timezone=timezone(settings.TIME_ZONE)
        )
    ).delete()


class Migration(migrations.Migration):

    initial = False

    dependencies: list[tuple[str, str]] = [
        ('solicitudes', '0001_initial'),
        ('firmas', '0001_initial'),
        ('servicios', '0001_initial'),
        ('django_celery_beat', '0019_alter_periodictasks_options'),
    ]

    operations: list[Operation] = [
        migrations.RunPython(
            forwards_func,
            reverse_func
        )
    ]
