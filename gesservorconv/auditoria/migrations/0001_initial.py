import auditoria.models.auditoria
from django.conf import settings
import django.contrib.postgres.fields.hstore
from django.contrib.postgres.operations import (
    HStoreExtension,
    UnaccentExtension
)
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL)
    ]

    operations = [
        HStoreExtension(),
        UnaccentExtension(),
        migrations.CreateModel(
            name='Django',
            fields=[
                ('id_auditoria', models.BigAutoField(primary_key=True, serialize=False, verbose_name='Identificador de Auditoría')),
                ('tabla_auditoria', auditoria.models.auditoria.OIDField(verbose_name='Tabla en Auditoría')),
                ('tiempo_auditoria', models.DateTimeField(verbose_name='Tiempo de Auditoría')),
                ('viejo_auditoria', django.contrib.postgres.fields.hstore.HStoreField(null=True, verbose_name='Valores viejos de auditoría')),
                ('nuevo_auditoria', django.contrib.postgres.fields.hstore.HStoreField(null=True, verbose_name='Valores nuevos de auditoría')),
            ],
            options={
                'verbose_name': 'Acción en Tabla de Django',
                'verbose_name_plural': 'Acciones en Tablas de Django',
            },
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('uuid_log', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identificador único universal de Log')),
                ('cliente_log', models.CharField(verbose_name='Cliente de Log')),
                ('tiempo_log', models.DateTimeField(verbose_name='Tiempo de Log')),
                ('navegador_log', models.CharField(verbose_name='Navegador de Log')),
                ('usuario_log', models.IntegerField(null=True, verbose_name='Usuario de Log')),
                ('mensaje_log', models.CharField(verbose_name='Mensaje de Log')),
            ],
            options={
                'db_table': 'logs',
            },
        ),
        migrations.AddConstraint(
            model_name='django',
            constraint=models.CheckConstraint(check=models.Q(('viejo_auditoria__isnull', False), ('nuevo_auditoria__isnull', False), _connector='OR'), name='auditoria_django_no_nula'),
        ),
        migrations.RunSQL(
            sql=[
                (
                    'CREATE TABLE IF NOT EXISTS logs ('
                    'cliente_log VARCHAR,'
                    'tiempo_log TIMESTAMP WITH TIME ZONE,'
                    'navegador_log VARCHAR,'
                    'usuario_log INTEGER REFERENCES auth_user (id),'
                    'mensaje_log VARCHAR,'
                    'PRIMARY KEY (cliente_log, tiempo_log)'
                    ');',
                    None
                )
            ],
            reverse_sql=[
                (
                    'DROP TABLE IF EXISTS logs;'
                )
            ]
        )
    ]
