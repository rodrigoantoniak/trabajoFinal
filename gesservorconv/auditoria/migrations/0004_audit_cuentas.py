from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('auditoria', '0003_cuentas'),
        ('cuentas', '0002_initial')
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' auditar_cuentas() RETURNS TRIGGER'
                    ' AS $auditar_cuentas$ BEGIN'
                    ' IF (TG_OP = \'INSERT\') THEN'
                    ' INSERT INTO auditoria_cuentas(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), NULL, hstore(NEW));'
                    ' ELSIF (TG_OP = \'UPDATE\') THEN'
                    ' INSERT INTO auditoria_cuentas(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), hstore(NEW));'
                    ' ELSIF (TG_OP = \'DELETE\') THEN'
                    ' INSERT INTO auditoria_cuentas(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), NULL);'
                    ' END IF; RETURN NULL;'
                    ' END; $auditar_cuentas$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_responsables_tecnicos'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON responsables_tecnicos FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_cuentas();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_comitentes'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON comitentes FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_cuentas();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_secretarios'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON secretarios FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_cuentas();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_notificaciones'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON notificaciones FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_cuentas();',
                    None
                ),
            ],
            reverse_sql=[
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_notificaciones ON'
                    ' notificaciones;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_secretarios ON'
                    ' secretarios;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_comitentes ON'
                    ' comitentes;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_responsables_tecnicos ON'
                    ' responsables_tecnicos;',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' auditar_cuentas();',
                    None
                )
            ]
        )
    ]
