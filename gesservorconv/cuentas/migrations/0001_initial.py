from django.conf import settings
from django.db import migrations
from django.db.migrations.operations.base import Operation


class Migration(migrations.Migration):

    initial: bool = True

    dependencies: list[tuple[str, str]] = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length')
    ]

    operations: list[Operation] = [
        migrations.RunSQL(
            sql=[
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' hacer_mayuscula_apellido_y_nombre() RETURNS TRIGGER'
                    ' AS $mayuscula_apellido_y_nombre$ BEGIN'
                    ' NEW.last_name := UPPER(NEW.last_name);'
                    ' NEW.first_name := UPPER(NEW.first_name);'
                    ' RETURN NEW;'
                    ' END; $mayuscula_apellido_y_nombre$'
                    ' LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' mayuscula_apellido_y_nombre BEFORE'
                    ' INSERT OR UPDATE ON auth_user'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION'
                    ' hacer_mayuscula_apellido_y_nombre();',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' es_valido_cuil(BIGINT) RETURNS BOOLEAN'
                    ' AS $$ DECLARE cuil ALIAS FOR $1;'
                    ' aux BIGINT; factor SMALLINT; suma INT; BEGIN'
                    ' IF (cuil / 1000000000 NOT IN (20,23,24,27))'
                    ' THEN RETURN FALSE; END IF;'
                    ' aux := cuil / 10; factor := 2; suma := 0;'
                    ' WHILE (aux > 0) LOOP'
                    ' suma := suma + ((aux % 10) * factor);'
                    ' IF (factor = 7) THEN factor := 2; ELSE'
                    ' factor := factor + 1; END IF;'
                    ' aux := aux / 10;'
                    ' END LOOP;'
                    ' CASE (suma % 11)'
                    ' WHEN 0 THEN RETURN ((cuil % 10 = 0) AND'
                    ' (cuil / 1000000000 <> 23));'
                    ' WHEN 1 THEN RETURN FALSE;'
                    ' ELSE RETURN ((cuil % 10 = (11 - (suma % 11))) AND'
                    ' ((cuil / 1000000000 <> 23) OR (cuil % 10 IN (3,4,9))));'
                    ' END CASE; END; $$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' es_valido_cuit(BIGINT) RETURNS BOOLEAN'
                    ' AS $$ DECLARE cuit ALIAS FOR $1;'
                    ' aux BIGINT; factor SMALLINT; suma INT; BEGIN'
                    ' IF (cuit / 1000000000 NOT IN (30,33,34))'
                    ' THEN RETURN FALSE; END IF;'
                    ' aux := cuit / 10; factor := 2; suma := 0;'
                    ' WHILE (aux > 0) LOOP'
                    ' suma := suma + ((aux % 10) * factor);'
                    ' IF (factor = 7) THEN factor := 2; ELSE'
                    ' factor := factor + 1; END IF;'
                    ' aux := aux / 10;'
                    ' END LOOP;'
                    ' CASE (suma % 11)'
                    ' WHEN 0 THEN RETURN ((cuit % 10 = 0) AND'
                    ' (cuit / 1000000000 <> 33));'
                    ' WHEN 1 THEN RETURN FALSE;'
                    ' ELSE RETURN ((cuit % 10 = (11 - (suma % 11))) AND'
                    ' ((cuit / 1000000000 <> 33) OR (cuit % 10 IN (3,9))));'
                    ' END CASE; END; $$ LANGUAGE PLpgSQL;',
                    None
                )
            ],
            reverse_sql=[
                (
                    'DROP FUNCTION IF EXISTS'
                    ' es_valido_cuit(BIGINT);',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' es_valido_cuil(BIGINT);',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' mayuscula_apellido_y_nombre ON'
                    ' auth_user',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' hacer_mayuscula_apellido_y_nombre();',
                    None
                )
            ],
        )
    ]
