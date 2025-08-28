from django.http import HttpRequest, HttpResponseForbidden
from django.template.loader import get_template
from django.views.generic import View


class Vista403(View):
    def get(
        self,
        request: HttpRequest,
        exception: Exception
    ) -> HttpResponseForbidden:
        return HttpResponseForbidden(
            get_template(
                'administrador/403.html'
            ).render(
                context={
                    'exception': exception.args[0]
                },
                request=request
            )
        )
