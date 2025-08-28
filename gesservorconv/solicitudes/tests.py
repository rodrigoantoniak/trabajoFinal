from django.test import TestCase
from django.db.migrations.recorder import MigrationRecorder
from typing import Self


class TestMigraciones(TestCase):
    def setUp(self: Self) -> None:
        pass

    def migracion_aplicada(self: Self, name: str) -> None:
        self.assertTrue(
            MigrationRecorder.Migration.objects.filter(
                app="solicitudes",
                name=name
            ).exists(),
            f"La migración '{name}' para la aplicación 'solicitudes'"
            " no ha sido ejecutada"
        )

    def test_migracion_0001_applicada(self: Self) -> None:
        self.migracion_aplicada("0001_initial")

    def test_migracion_0002_applicada(self: Self) -> None:
        self.migracion_aplicada("0002_crons")
