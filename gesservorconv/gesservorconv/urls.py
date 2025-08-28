"""
URL configuration for servorges project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import URLPattern, URLResolver, include, path, re_path
from django.views.generic.base import TemplateView

from .views import (
    VistaJQuery,
    VistaSelect2CSS,
    VistaSelect2JS,
    VistaSelect2JSes,
    VistaArchivos
)

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        '',
        TemplateView.as_view(
            template_name='gesservorconv/indice.html',
            http_method_names=['get', 'head', 'options']
        ),
        name='indice'
    ),
    path('', include('favicon.urls')),
    path(
        'dinamico/js/jquery.min.js',
        VistaJQuery.as_view(),
        name='jquery'
    ),
    path(
        'dinamico/css/select2.min.css',
        VistaSelect2CSS.as_view(),
        name='select2_css'
    ),
    path(
        'dinamico/js/select2.full.min.js',
        VistaSelect2JS.as_view(),
        name='select2_js'
    ),
    path(
        'dinamico/js/i18n/es.js',
        VistaSelect2JSes.as_view(),
        name='select2_js_es'
    ),
    path('cuenta/', include('cuentas.urls')),
    path('cuenta/', include('solicitudes.urls')),
    path('cuenta/', include('firmas.urls')),
    path('cuenta/', include('servicios.urls')),
    re_path(r'archivos/(?P<dir>.*[^\/])$', VistaArchivos.as_view()),
    path('', include('auditoria.urls'))
]
