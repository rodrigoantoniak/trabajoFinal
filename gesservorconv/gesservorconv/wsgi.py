"""
WSGI config for servorges project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from .handlers import ManejadorWSGI, obtener_aplicacion_wsgi

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gesservorconv.settings')

application: ManejadorWSGI = obtener_aplicacion_wsgi()
