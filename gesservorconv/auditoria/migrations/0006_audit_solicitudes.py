from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('auditoria', '0005_solicitudes'),
        ('solicitudes', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' auditar_solicitudes() RETURNS TRIGGER'
                    ' AS $auditar_solicitudes$ BEGIN'
                    ' IF (TG_OP = \'INSERT\') THEN'
                    ' INSERT INTO auditoria_solicitudes(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), NULL, hstore(NEW));'
                    ' ELSIF (TG_OP = \'UPDATE\') THEN'
                    ' INSERT INTO auditoria_solicitudes(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), hstore(NEW));'
                    ' ELSIF (TG_OP = \'DELETE\') THEN'
                    ' INSERT INTO auditoria_solicitudes(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), NULL);'
                    ' END IF; RETURN NULL;'
                    ' END; $auditar_solicitudes$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_categorias'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON categorias FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_facultades'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON facultades FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_solicitudes_servicio'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON solicitudes_servicio FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_comitentes_solicitudes'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON comitentes_solicitud FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_responsables_solicitudes'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON responsables_solicitud FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_propuestas_compromisos'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON propuestas_compromisos FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_decisiones_comitentes_propuestas'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON decisiones_comitentes_propuesta FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_decisiones_responsables_tecnicos_propuestas'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON decisiones_responsables_tecnicos_propuesta'
                    ' FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_solicitudes();',
                    None
                ),
            ],
            reverse_sql=[
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_decisiones_responsables_tecnicos_propuestas ON'
                    ' decisiones_responsables_tecnicos_propuesta;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_decisiones_comitentes_propuestas ON'
                    ' decisiones_comitentes_propuesta;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_propuestas_compromisos ON'
                    ' propuestas_compromisos;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_responsables_solicitudes ON'
                    ' responsables_solicitud;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_comitentes_solicitud ON'
                    ' comitentes_solicitud;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_solicitudes_servicio ON'
                    ' solicitud_servicio;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_facultades ON'
                    ' facultades;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_categorias ON'
                    ' categorias;',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' auditar_solicitudes();',
                    None
                )
            ]
        )
    ]
