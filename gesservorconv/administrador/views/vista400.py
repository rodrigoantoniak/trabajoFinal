from django.http import HttpRequest, HttpResponseBadRequest
from django.template.loader import get_template
from django.views.generic import View


class Vista400(View):
    def get(
        self,
        request: HttpRequest,
        exception: Exception
    ) -> HttpResponseBadRequest:
        return HttpResponseBadRequest(
            get_template(
                'administrador/400.html'
            ).render(
                context={
                    'exception': exception.args[0]
                },
                request=request
            )
        )
