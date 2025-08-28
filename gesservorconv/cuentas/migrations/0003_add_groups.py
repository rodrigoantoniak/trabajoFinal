from django.apps.registry import Apps
from django.contrib.auth.models import Group
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation


COMITENTE: str = 'comitente'
RESPONSABLE_TECNICO: str = 'responsable_tecnico'
SECRETARIO: str = 'secretario'


def forwards_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Grupo: type[Group] = apps.get_model('auth', 'Group')
    db_alias: str = schema_editor.connection.alias
    Grupo.objects.using(db_alias).bulk_create(
        [
            Grupo(name=COMITENTE),
            Grupo(name=RESPONSABLE_TECNICO),
            Grupo(name=SECRETARIO),
        ]
    )


def reverse_func(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor
) -> None:
    Grupo: type[Group] = apps.get_model('auth', 'Group')
    db_alias: str = schema_editor.connection.alias
    Grupo.objects.using(db_alias).filter(
        name__in=[
            COMITENTE,
            RESPONSABLE_TECNICO,
            SECRETARIO
        ]
    ).delete()


class Migration(migrations.Migration):

    initial: bool = False

    dependencies: list[tuple[str, str]] = [
        ('sessions', '0001_initial'),
        ('cuentas', '0002_initial')
    ]

    operations: list[Operation] = [
        migrations.RunPython(
            forwards_func,
            reverse_func
        ),
        migrations.RunSQL(
            sql=[
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' validar_comitente_nuevo() RETURNS TRIGGER'
                    ' AS $validar_comitente_nuevo$ DECLARE cuit BIGINT;'
                    ' BEGIN'
                    ' IF EXISTS (SELECT 1 from auth_user'
                    ' WHERE (id = NEW.usuario_comitente_id) AND'
                    ' (is_staff OR is_superuser)) THEN'
                    ' RAISE EXCEPTION \'No se puede asignar'
                    ' como comitente a administradores ni staff\';'
                    ' END IF;'
                    ' IF NOT es_valido_cuil(NEW.cuil_comitente) THEN'
                    ' RAISE EXCEPTION \'El CUIL del comiente'
                    ' no es válido\';'
                    ' END IF;'
                    ' FOREACH cuit IN ARRAY'
                    ' NEW.cuit_organizaciones_comitente'
                    ' LOOP IF NOT es_valido_cuit(cuit) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del comiente no es válido\';'
                    ' END IF; END LOOP;'
                    ' IF ((SELECT array_agg(c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_comitente)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_comitente)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE) <>'
                    ' (SELECT array_agg(DISTINCT c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_comitente)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_comitente)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE)) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del comiente es repetido\';'
                    ' END IF;'
                    ' RETURN NEW;'
                    ' END; $validar_comitente_nuevo$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' validar_responsable_nuevo() RETURNS TRIGGER'
                    ' AS $validar_responsable_nuevo$ DECLARE cuit BIGINT;'
                    ' BEGIN'
                    ' IF EXISTS (SELECT 1 from auth_user'
                    ' WHERE (id = NEW.usuario_responsable_id) AND'
                    ' (is_staff OR is_superuser)) THEN'
                    ' RAISE EXCEPTION \'No se puede asignar'
                    ' como responsable técnico a administradores ni staff\';'
                    ' END IF;'
                    ' IF NOT es_valido_cuil(NEW.cuil_responsable) THEN'
                    ' RAISE EXCEPTION \'El CUIL del responsable técnico'
                    ' no es válido\';'
                    ' END IF;'
                    ' FOREACH cuit IN ARRAY'
                    ' NEW.cuit_organizaciones_responsable'
                    ' LOOP IF NOT es_valido_cuit(cuit) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del responsable técnico no es válido\';'
                    ' END IF; END LOOP;'
                    ' IF ((SELECT array_agg(c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_responsable)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_responsable)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE) <>'
                    ' (SELECT array_agg(DISTINCT c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_responsable)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_responsable)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE)) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del responsable técnico es repetido\';'
                    ' END IF;'
                    ' RETURN NEW;'
                    ' END; $validar_responsable_nuevo$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' validar_comitente_existente() RETURNS TRIGGER'
                    ' AS $validar_comitente_existente$ DECLARE cuit BIGINT;'
                    ' BEGIN'
                    ' IF (NEW.usuario_comitente_id <>'
                    ' OLD.usuario_comitente_id) THEN'
                    ' RAISE EXCEPTION \'No se puede cambiar'
                    ' el usuario correspondiente al comitente\';'
                    ' END IF;'
                    ' IF NOT es_valido_cuil(NEW.cuil_comitente) THEN'
                    ' RAISE EXCEPTION \'El CUIL del comiente'
                    ' no es válido\';'
                    ' END IF;'
                    ' FOREACH cuit IN ARRAY'
                    ' NEW.cuit_organizaciones_comitente'
                    ' LOOP IF NOT es_valido_cuit(cuit) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del comiente no es válido\';'
                    ' END IF; END LOOP;'
                    ' IF ((SELECT array_agg(c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_comitente)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_comitente)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE) <>'
                    ' (SELECT array_agg(DISTINCT c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_comitente)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_comitente)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE)) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del comiente es repetido\';'
                    ' END IF;'
                    ' RETURN NEW;'
                    ' END; $validar_comitente_existente$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' validar_responsable_existente() RETURNS TRIGGER'
                    ' AS $validar_responsable_existente$ DECLARE cuit BIGINT;'
                    ' BEGIN'
                    ' IF (NEW.usuario_responsable_id <>'
                    ' OLD.usuario_responsable_id) THEN'
                    ' RAISE EXCEPTION \'No se puede cambiar'
                    ' el usuario correspondiente al responsable técnico\';'
                    ' END IF;'
                    ' IF NOT es_valido_cuil(NEW.cuil_responsable) THEN'
                    ' RAISE EXCEPTION \'El CUIL del responsable técnico'
                    ' no es válido\';'
                    ' END IF;'
                    ' FOREACH cuit IN ARRAY'
                    ' NEW.cuit_organizaciones_responsable'
                    ' LOOP IF NOT es_valido_cuit(cuit) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del responsable técnico no es válido\';'
                    ' END IF; END LOOP;'
                    ' IF ((SELECT array_agg(c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_responsable)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_responsable)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE) <>'
                    ' (SELECT array_agg(DISTINCT c ORDER BY c) FROM'
                    ' unnest(NEW.cuit_organizaciones_responsable)'
                    ' WITH ORDINALITY AS co(c,ic) INNER JOIN'
                    ' unnest(NEW.habilitado_organizaciones_responsable)'
                    ' WITH ORDINALITY AS ho(h,ih) ON co.ic=ho.ih WHERE'
                    ' h IS TRUE)) THEN'
                    ' RAISE EXCEPTION \'Al menos un CUIT de las organizaciones'
                    ' del responsable técnico es repetido\';'
                    ' END IF;'
                    ' RETURN NEW;'
                    ' END; $validar_responsable_existente$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' nuevo_comitente() RETURNS TRIGGER'
                    ' AS $nuevo_comitente$ BEGIN'
                    ' IF ((NEW.habilitado_comitente IS TRUE) OR'
                    ' (array_position'
                    '(NEW.habilitado_organizaciones_comitente, TRUE)'
                    ' IS NOT NULL)) THEN'
                    ' INSERT INTO auth_user_groups(user_id,'
                    ' group_id) SELECT NEW.usuario_comitente_id,'
                    ' id FROM auth_group WHERE (name = %(comitente)s)'
                    ' ON CONFLICT DO NOTHING;'
                    ' END IF;'
                    ' IF ((NEW.habilitado_comitente IS NOT TRUE) AND'
                    ' (array_position'
                    '(NEW.habilitado_organizaciones_comitente, TRUE)'
                    ' IS NULL)) THEN'
                    ' DELETE FROM auth_user_groups WHERE'
                    ' (user_id = NEW.usuario_comitente_id)'
                    ' AND (group_id IN (SELECT id FROM auth_group'
                    ' WHERE name = %(comitente)s));'
                    ' END IF;'
                    ' RETURN NULL;'
                    ' END; $nuevo_comitente$ LANGUAGE PLpgSQL;',
                    {'comitente': COMITENTE}
                ),

                (
                    'CREATE OR REPLACE FUNCTION'
                    ' nuevo_responsable() RETURNS TRIGGER'
                    ' AS $nuevo_responsable$ BEGIN'
                    ' IF ((NEW.habilitado_responsable IS TRUE) OR'
                    ' (array_position'
                    '(NEW.habilitado_organizaciones_responsable, TRUE)'
                    ' IS NOT NULL)) THEN'
                    ' INSERT INTO auth_user_groups(user_id,'
                    ' group_id) SELECT NEW.usuario_responsable_id,'
                    ' id FROM auth_group WHERE (name = %(responsable)s)'
                    ' ON CONFLICT DO NOTHING;'
                    ' END IF;'
                    ' IF ((NEW.habilitado_responsable IS NOT TRUE) AND'
                    ' (array_position'
                    '(NEW.habilitado_organizaciones_responsable, TRUE)'
                    ' IS NULL)) THEN'
                    ' DELETE FROM auth_user_groups WHERE'
                    ' (user_id = NEW.usuario_responsable_id)'
                    ' AND (group_id IN (SELECT id FROM auth_group'
                    ' WHERE name = %(responsable)s));'
                    ' END IF;'
                    ' RETURN NULL;'
                    ' END; $nuevo_responsable$ LANGUAGE PLpgSQL;',
                    {'responsable': RESPONSABLE_TECNICO}
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' viejo_comitente() RETURNS TRIGGER'
                    ' AS $viejo_comitente$ BEGIN'
                    ' DELETE FROM auth_user_groups WHERE'
                    ' (user_id = OLD.usuario_comitente_id)'
                    ' AND (group_id IN (SELECT id FROM auth_group'
                    ' WHERE name = %(comitente)s)); RETURN NULL;'
                    ' END; $viejo_comitente$ LANGUAGE PLpgSQL;',
                    {'comitente': COMITENTE}
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' viejo_responsable() RETURNS TRIGGER'
                    ' AS $viejo_responsable$ BEGIN'
                    ' DELETE FROM auth_user_groups WHERE'
                    ' (user_id = OLD.usuario_responsable_id)'
                    ' AND (group_id IN (SELECT id FROM auth_group'
                    ' WHERE name = %(responsable)s)); RETURN NULL;'
                    ' END; $viejo_responsable$ LANGUAGE PLpgSQL;',
                    {'responsable': RESPONSABLE_TECNICO}
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' validar_comitente_nuevo BEFORE'
                    ' INSERT ON comitentes'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' validar_comitente_nuevo();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' validar_responsable_nuevo BEFORE'
                    ' INSERT ON responsables_tecnicos'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' validar_responsable_nuevo();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' validar_comitente_existente BEFORE'
                    ' UPDATE ON comitentes'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' validar_comitente_existente();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' validar_responsable_existente BEFORE'
                    ' UPDATE ON responsables_tecnicos'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' validar_responsable_existente();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' nuevo_comitente AFTER'
                    ' INSERT OR UPDATE ON comitentes'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' nuevo_comitente();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' nuevo_responsable AFTER'
                    ' INSERT OR UPDATE ON responsables_tecnicos'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' nuevo_responsable();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' viejo_comitente AFTER'
                    ' DELETE ON comitentes'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' viejo_comitente();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' viejo_responsable AFTER'
                    ' DELETE ON responsables_tecnicos'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' viejo_responsable();',
                    None
                )
            ],
            reverse_sql=[
                (
                    'DROP TRIGGER IF EXISTS'
                    ' validar_responsable_existente ON'
                    ' responsables_tecnicos;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' validar_comitente_existente ON'
                    ' comitentes;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' validar_responsable_nuevo ON'
                    ' responsables_tecnicos;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' validar_comitente_nuevo ON'
                    ' comitentes;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' nuevo_responsable ON'
                    ' responsables_tecnicos',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' nuevo_comitente ON'
                    ' comitentes',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' viejo_responsable ON'
                    ' responsables_tecnicos',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' viejo_comitente ON'
                    ' comitentes',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' validar_responsable_existente();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' validar_comitente_existente();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' validar_responsable_nuevo();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' validar_comitente_nuevo();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' nuevo_responsable();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' nuevo_comitente();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' viejo_responsable();',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' viejo_comitente();',
                    None
                )
            ],
        )
    ]
