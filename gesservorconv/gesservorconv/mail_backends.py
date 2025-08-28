from django.core.mail.backends.filebased import EmailBackend

from datetime import datetime
from os.path import join

from typing import Self


class MotorEmailDesarrollo(EmailBackend):
    def _get_filename(self: Self):
        """Devuelve un nombre de archivo único."""
        if self._fname is None:
            timestamp: str = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname: str = "%s-%s.eml" % (timestamp, abs(id(self)))
            self._fname: str = join(self.file_path, fname)
        return self._fname
