from django.db import migrations


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('sessions', '0001_initial'),
        ('auditoria', '0001_initial')
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                (
                    'CREATE OR REPLACE FUNCTION'
                    ' auditar_django() RETURNS TRIGGER'
                    ' AS $auditar_django$ BEGIN'
                    ' IF (TG_OP = \'INSERT\') THEN'
                    ' INSERT INTO auditoria_django(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), NULL, hstore(NEW));'
                    ' ELSIF (TG_OP = \'UPDATE\') THEN'
                    ' INSERT INTO auditoria_django(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), hstore(NEW));'
                    ' ELSIF (TG_OP = \'DELETE\') THEN'
                    ' INSERT INTO auditoria_django(tabla_auditoria,'
                    ' tiempo_auditoria, viejo_auditoria, nuevo_auditoria)'
                    ' VALUES(TG_RELID, now(), hstore(OLD), NULL);'
                    ' END IF; RETURN NULL;'
                    ' END; $auditar_django$ LANGUAGE PLpgSQL;',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_auth_user'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_user FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_auth_group'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_group FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_auth_user_groups'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_user_groups FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_auth_permission'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_permission FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_auth_group_permissions'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_group_permissions FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER'
                    ' auditar_auth_user_user_permissions'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON auth_user_user_permissions FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                ),
                (
                    'CREATE OR REPLACE TRIGGER auditar_contenttype'
                    ' AFTER INSERT OR UPDATE OR DELETE'
                    ' ON django_content_type FOR EACH ROW'
                    ' EXECUTE FUNCTION auditar_django();',
                    None
                )
            ],
            reverse_sql=[
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_contenttype ON'
                    ' django_content_type;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_user_user_permissions ON'
                    ' auth_user_user_permissions;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_group_permissions ON'
                    ' auth_group_permissions;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_permission ON'
                    ' auth_permission;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_user_groups ON'
                    ' auth_user_groups;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_group ON'
                    ' auth_user;',
                    None
                ),
                (
                    'DROP TRIGGER IF EXISTS'
                    ' auditar_auth_user ON'
                    ' auth_user;',
                    None
                ),
                (
                    'DROP FUNCTION IF EXISTS'
                    ' auditar_django();',
                    None
                )
            ]
        )
    ]
