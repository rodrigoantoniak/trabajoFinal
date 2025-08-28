from django.http import HttpRequest, HttpResponseNotFound
from django.template.loader import get_template
from django.views.generic import View


class Vista404(View):
    def get(
        self,
        request: HttpRequest,
        exception: Exception
    ) -> HttpResponseNotFound:
        return HttpResponseNotFound(
            get_template(
                'administrador/404.html'
            ).render(
                context={
                    'exception': exception.args[0]
                },
                request=request
            )
        )
