from django.test import TestCase
from django.db.migrations.recorder import MigrationRecorder
from typing import Self


class TestMigraciones(TestCase):
    def setUp(self: Self) -> None:
        pass

    def migracion_aplicada(self: Self, name: str) -> None:
        self.assertTrue(
            MigrationRecorder.Migration.objects.filter(
                app="auditoria",
                name=name
            ).exists(),
            f"La migración '{name}' para la aplicación 'auditoria'"
            " no ha sido ejecutada"
        )

    def test_migracion_0001_applicada(self: Self) -> None:
        self.migracion_aplicada("0001_initial")

    def test_migracion_0002_applicada(self: Self) -> None:
        self.migracion_aplicada("0002_audit_django")

    def test_migracion_0003_applicada(self: Self) -> None:
        self.migracion_aplicada("0003_cuentas")

    def test_migracion_0004_applicada(self: Self) -> None:
        self.migracion_aplicada("0004_audit_cuentas")

    def test_migracion_0005_applicada(self: Self) -> None:
        self.migracion_aplicada("0005_solicitudes")

    def test_migracion_0006_applicada(self: Self) -> None:
        self.migracion_aplicada("0006_audit_solicitudes")
