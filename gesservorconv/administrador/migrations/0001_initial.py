import django.contrib.postgres.fields.hstore
from django.contrib.postgres.operations import HStoreExtension
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name='Configuracion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('opciones', django.contrib.postgres.fields.hstore.HStoreField(verbose_name='Opciones de Configuración')),
                ('actual', models.BooleanField(verbose_name='Si es Configuración actual')),
            ],
            options={
                'verbose_name': 'Configuración',
                'verbose_name_plural': 'Configuraciones',
                'db_table': 'configuraciones',
            },
        ),
        migrations.AddConstraint(
            model_name='configuracion',
            constraint=models.UniqueConstraint(condition=models.Q(('actual', True)), fields=('actual',), name='configuracion_actual_unica'),
        ),
    ]
