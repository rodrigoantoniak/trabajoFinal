from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

from ..models import ResponsableTecnico
from ..forms import FormularioResponsable


class VistaRegistroResponsable(LoginRequiredMixin, generic.CreateView):
    model: type[ResponsableTecnico] = ResponsableTecnico
    template_name: str = 'cuentas/registrar_responsable.html'
    form_class: type[FormularioResponsable] = FormularioResponsable
    success_url: str = reverse_lazy('cuentas:perfil')
    login_url: str = reverse_lazy('cuentas:iniciar_sesion')

    def form_valid(self, form: FormularioResponsable) -> HttpResponse:
        responsable_tecnico: ResponsableTecnico = ResponsableTecnico(
            usuario_responsable=self.request.user,
            cuil_responsable=form.cleaned_data['cuil_responsable'],
            firma_digital_responsable=False
        )
        if form.cleaned_data['firma_digital_responsable']:
            responsable_tecnico.firma_digital_responsable = True
        responsable_tecnico.save()
        return HttpResponseRedirect(self.success_url)
