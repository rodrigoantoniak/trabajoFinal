from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
from django.contrib.postgres.operations import BtreeGinExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cuentas', '0001_initial')
    ]

    operations = [
        BtreeGinExtension(),
        migrations.CreateModel(
            name='Comitente',
            fields=[
                ('usuario_comitente', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='Usuario de Comitente')),
                ('cuil_comitente', models.PositiveBigIntegerField(unique=True, verbose_name='CUIL de Comitente')),
                ('firma_digital_comitente', models.BooleanField(default=False, verbose_name='Si Comitente tiene firma digital')),
                ('habilitado_comitente', models.BooleanField(default=None, null=True, verbose_name='Si la persona física está habilitada como Comitente')),
                ('razones_sociales_comitente', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=64), size=None, verbose_name='Razones Sociales en Organizaciones de Comitente')),
                ('cuit_organizaciones_comitente', django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(unique=True), size=None, verbose_name='CUIT en Organizaciones de Comitente')),
                ('puestos_organizaciones_comitente', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=64), size=None, verbose_name='Puestos en Organizaciones de Comitente')),
                ('habilitado_organizaciones_comitente', django.contrib.postgres.fields.ArrayField(base_field=models.BooleanField(default=None, null=True), size=None, verbose_name='Si Comitente está habilitado por Organización')),
            ],
            options={
                'db_table': 'comitentes',
            },
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id_notificacion', models.BigAutoField(primary_key=True, serialize=False, verbose_name='Identificador de Notificación')),
                ('tiempo_notificacion', models.DateTimeField(auto_now=True, verbose_name='Tiempo de Notificación')),
                ('lectura_notificacion', models.DateTimeField(default=None, null=True, verbose_name='Tiempo de Notificación')),
                ('titulo_notificacion', models.CharField(verbose_name='Título de Notificación')),
                ('contenido_notificacion', models.TextField(verbose_name='Título de Notificación')),
                ('enlace_notificacion', models.CharField(verbose_name='Enlace de Notificación')),
            ],
            options={
                'verbose_name': 'notificación',
                'verbose_name_plural': 'notificaciones',
                'db_table': 'notificaciones',
            },
        ),
        migrations.CreateModel(
            name='ResponsableTecnico',
            fields=[
                ('usuario_responsable', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='Usuario de Responsable Técnico')),
                ('cuil_responsable', models.PositiveBigIntegerField(unique=True, verbose_name='CUIL de Responsable Técnico')),
                ('firma_digital_responsable', models.BooleanField(default=False, verbose_name='Si Responsable Técnico tiene firma digital')),
                ('habilitado_responsable', models.BooleanField(default=None, null=True, verbose_name='Si Responsable Técnico está habilitado')),
                ('razones_sociales_responsable', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=64), size=None, verbose_name='Razones Sociales en Organizaciones de Responsable Técnico')),
                ('cuit_organizaciones_responsable', django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(unique=True), size=None, verbose_name='CUIT en Organizaciones de Responsable Técnico')),
                ('puestos_organizaciones_responsable', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=64), size=None, verbose_name='Puestos en Organizaciones de Responsable Técnico')),
                ('habilitado_organizaciones_responsable', django.contrib.postgres.fields.ArrayField(base_field=models.BooleanField(default=None, null=True), size=None, verbose_name='Si Responsable Técnico está habilitado por Organización')),
            ],
            options={
                'verbose_name': 'responsable técnico',
                'verbose_name_plural': 'responsables técnicos',
                'db_table': 'responsables_tecnicos',
            },
        ),
        migrations.CreateModel(
            name='Secretario',
            fields=[
                ('usuario_secretario', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='Usuario de Secretario')),
                ('firma_digital_secretario', models.BooleanField(default=False, verbose_name='Si Secretario tiene firma digital')),
                ('habilitado_secretario', models.BooleanField(default=False, verbose_name='Si Secretario está habilitado')),
            ],
            options={
                'db_table': 'secretarios',
            },
        ),
        migrations.AddConstraint(
            model_name='secretario',
            constraint=models.UniqueConstraint(condition=models.Q(('habilitado_secretario', True)), fields=('habilitado_secretario',), name='secretario_habilitado_unico'),
        ),
        migrations.AddConstraint(
            model_name='responsabletecnico',
            constraint=models.CheckConstraint(check=models.Q(('razones_sociales_responsable__len', models.F('cuit_organizaciones_responsable__len')), ('razones_sociales_responsable__len', models.F('puestos_organizaciones_responsable__len')), ('razones_sociales_responsable__len', models.F('habilitado_organizaciones_responsable__len'))), name='arrays_responsable_mismo_tamanio'),
        ),
        migrations.AddField(
            model_name='notificacion',
            name='usuario_notificacion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Usuario de Notificación'),
        ),
        migrations.AddConstraint(
            model_name='comitente',
            constraint=models.CheckConstraint(check=models.Q(('razones_sociales_comitente__len', models.F('cuit_organizaciones_comitente__len')), ('razones_sociales_comitente__len', models.F('puestos_organizaciones_comitente__len')), ('razones_sociales_comitente__len', models.F('habilitado_organizaciones_comitente__len'))), name='arrays_comitente_mismo_tamanio'),
        ),
    ]
