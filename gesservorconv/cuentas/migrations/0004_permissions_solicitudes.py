from django.apps.registry import Apps
from django.contrib.auth.models import Group, Permission
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation
from django.db.models.query import QuerySet

from solicitudes.models import (
    SolicitudServicio,
    ComitenteSolicitud,
    ResponsableSolicitud,
    PropuestaCompromisos,
    DecisionResponsableTecnicoPropuesta,
    DecisionComitentePropuesta
)

COMITENTE: str = 'comitente'
RESPONSABLE_TECNICO: str = 'responsable_tecnico'
SECRETARIO: str = 'secretario'


def forwards_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Grupo: type[Group] = apps.get_model('auth', 'Group')
    Permiso: type[Permission] = apps.get_model('auth', 'Permission')
    db_alias: str = schema_editor.connection.alias
    comitente: Grupo = Grupo.objects.using(db_alias).get(
        name=COMITENTE
    )
    permisos_comitente: QuerySet[Permiso] = \
        Permiso.objects.filter(
            codename__in=[
                f'view_{SolicitudServicio.__name__.lower()}',
                f'add_{SolicitudServicio.__name__.lower()}',
                f'change_{SolicitudServicio.__name__.lower()}',
                f'view_{ComitenteSolicitud.__name__.lower()}',
                f'add_{ComitenteSolicitud.__name__.lower()}',
                f'change_{ComitenteSolicitud.__name__.lower()}',
                f'view_{ResponsableSolicitud.__name__.lower()}',
                f'add_{ResponsableSolicitud.__name__.lower()}',
                f'change_{ResponsableSolicitud.__name__.lower()}',
                f'view_{PropuestaCompromisos.__name__.lower()}',
                f'view_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'change_{DecisionComitentePropuesta.__name__.lower()}'
            ]
        )
    comitente.permissions.add(*permisos_comitente)
    responsable_tecnico: Grupo = Grupo.objects.using(db_alias).get(
        name=RESPONSABLE_TECNICO
    )
    permisos_responsable: QuerySet[Permiso] = \
        Permiso.objects.filter(
            codename__in=[
                f'view_{SolicitudServicio.__name__.lower()}',
                f'view_{ComitenteSolicitud.__name__.lower()}',
                f'view_{ResponsableSolicitud.__name__.lower()}',
                f'add_{ResponsableSolicitud.__name__.lower()}',
                f'change_{ResponsableSolicitud.__name__.lower()}',
                f'view_{PropuestaCompromisos.__name__.lower()}',
                f'add_{PropuestaCompromisos.__name__.lower()}',
                f'view_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'change_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'view_{DecisionComitentePropuesta.__name__.lower()}'
            ]
        )
    responsable_tecnico.permissions.add(*permisos_responsable)
    secretario: Grupo = Grupo.objects.using(db_alias).get(
        name=SECRETARIO
    )


def reverse_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Grupo: type[Group] = apps.get_model('auth', 'Group')
    Permiso: type[Permission] = apps.get_model('auth', 'Permission')
    db_alias: str = schema_editor.connection.alias
    comitente: Grupo = Grupo.objects.using(db_alias).get(
        name=COMITENTE
    )
    permisos_comitente: QuerySet[Permiso] = \
        Permiso.objects.filter(
            codename__in=[
                f'view_{SolicitudServicio.__name__.lower()}',
                f'add_{SolicitudServicio.__name__.lower()}',
                f'change_{SolicitudServicio.__name__.lower()}',
                f'view_{ComitenteSolicitud.__name__.lower()}',
                f'add_{ComitenteSolicitud.__name__.lower()}',
                f'change_{ComitenteSolicitud.__name__.lower()}',
                f'view_{ResponsableSolicitud.__name__.lower()}',
                f'add_{ResponsableSolicitud.__name__.lower()}',
                f'change_{ResponsableSolicitud.__name__.lower()}',
                f'view_{PropuestaCompromisos.__name__.lower()}',
                f'view_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'change_{DecisionComitentePropuesta.__name__.lower()}'
            ]
        )
    comitente.permissions.remove(*permisos_comitente)
    responsable_tecnico: Grupo = Grupo.objects.using(db_alias).get(
        name=RESPONSABLE_TECNICO
    )
    permisos_responsable: QuerySet[Permiso] = \
        Permiso.objects.filter(
            codename__in=[
                f'view_{SolicitudServicio.__name__.lower()}',
                f'view_{ComitenteSolicitud.__name__.lower()}',
                f'view_{ResponsableSolicitud.__name__.lower()}',
                f'add_{ResponsableSolicitud.__name__.lower()}',
                f'change_{ResponsableSolicitud.__name__.lower()}',
                f'view_{PropuestaCompromisos.__name__.lower()}',
                f'add_{PropuestaCompromisos.__name__.lower()}',
                f'view_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'change_{DecisionResponsableTecnicoPropuesta.__name__.lower()}',
                f'view_{DecisionComitentePropuesta.__name__.lower()}'
            ]
        )
    responsable_tecnico.permissions.add(*permisos_responsable)
    secretario: Grupo = Grupo.objects.using(db_alias).get(
        name=SECRETARIO
    )


class Migration(migrations.Migration):

    initial: bool = False

    dependencies: list[tuple[str, str]] = [
        ('cuentas', '0003_add_groups'),
        ('cuentas', '0002_initial'),
        ('solicitudes', '0001_initial')
    ]

    operations: list[Operation] = [
        migrations.RunPython(
            forwards_func,
            reverse_func
        ),
    ]
