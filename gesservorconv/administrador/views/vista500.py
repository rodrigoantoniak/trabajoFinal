from django.http import HttpRequest, HttpResponseServerError
from django.template.loader import get_template
from django.views.generic import View


class Vista500(View):
    def get(
        self,
        request: HttpRequest,
    ) -> HttpResponseServerError:
        return HttpResponseServerError(
            get_template(
                'administrador/500.html'
            ).render(
                request=request
            )
        )
