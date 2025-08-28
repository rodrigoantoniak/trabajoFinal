import auditoria.models.auditoria
import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0002_audit_django'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cuentas',
            fields=[
                ('id_auditoria', models.BigAutoField(primary_key=True, serialize=False, verbose_name='Identificador de Auditoría')),
                ('tabla_auditoria', auditoria.models.auditoria.OIDField(verbose_name='Tabla en Auditoría')),
                ('tiempo_auditoria', models.DateTimeField(verbose_name='Tiempo de Auditoría')),
                ('viejo_auditoria', django.contrib.postgres.fields.hstore.HStoreField(null=True, verbose_name='Valores viejos de auditoría')),
                ('nuevo_auditoria', django.contrib.postgres.fields.hstore.HStoreField(null=True, verbose_name='Valores nuevos de auditoría')),
            ],
            options={
                'verbose_name': 'Acción en Tabla de Cuentas',
                'verbose_name_plural': 'Acciones en Tablas de Cuentas',
            },
        ),
        migrations.AddConstraint(
            model_name='cuentas',
            constraint=models.CheckConstraint(check=models.Q(('viejo_auditoria__isnull', False), ('nuevo_auditoria__isnull', False), _connector='OR'), name='auditoria_cuentas_no_nula'),
        ),
    ]
