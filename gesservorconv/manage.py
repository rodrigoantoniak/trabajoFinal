#!/usr/bin/env python
"""Utilidad de Django por línea de comandos para tareas administrativas."""
import os
import sys


def main() -> None:
    """Ejecuta tareas administrativas."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gesservorconv.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Estás seguro de que está instalado "
            "y disponible en tu variable de entorno PYTHONPATH? ¿Te olvidaste "
            "de activar un entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
