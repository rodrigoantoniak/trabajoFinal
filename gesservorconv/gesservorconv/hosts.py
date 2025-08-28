from typing import Optional
from django.conf import settings

from django_hosts import patterns, host

puerto: Optional[str] = '8000' if settings.DEBUG else None
urls_apis: str = 'gesservorconv.apis'
urls_administrador: str = 'administrador.urls'
nombre_apis6: str = 'apis6'
nombre_apis4: str = 'apis'
nombre_administrador6: str = 'administrador6'
nombre_administrador4: str = 'administrador'
host_patterns: list[host] = patterns(
    '',
    host(
        r'\[::\]',
        urls_apis,
        name=nombre_apis6,
        port=puerto
    ),
    host(
        r'0\.0\.0\.0',
        urls_apis,
        name=nombre_apis4,
        port=puerto
    ),
    host(
        r'\[::1\]',
        urls_administrador,
        name=nombre_administrador6,
        port=puerto
    ),
    host(
        r'127\.0\.0\.1',
        urls_administrador,
        name=nombre_administrador4,
        port=puerto
    ),
    host(
        r'localhost',
        settings.ROOT_URLCONF,
        name=settings.DEFAULT_HOST,
        port=puerto
    )
)
