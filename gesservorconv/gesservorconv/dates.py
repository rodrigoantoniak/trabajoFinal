from django.conf import settings

from matplotlib.dates import (
    YEARLY,
    MONTHLY,
    DAILY,
    HOURLY,
    MINUTELY,
    DAYS_PER_YEAR,
    DAYS_PER_MONTH,
    HOURS_PER_DAY,
    MINUTES_PER_DAY,
    AutoDateFormatter,
    AutoDateLocator,
    num2date
)

from babel.dates import format_skeleton
from datetime import datetime, tzinfo
import pytz
from typing import Optional, Self


class Ubicador(AutoDateLocator):
    def __init__(
        self: Self,
        tz: Optional[tzinfo] = None,
        minticks: int = 5,
        maxticks: Optional[int | dict[int]] = None,
        interval_multiples: bool = True
    ):
        super(AutoDateLocator, self).__init__(tz=tz)
        self._freq = YEARLY
        self._freqs = [YEARLY, MONTHLY, DAILY, HOURLY, MINUTELY]
        self.minticks = minticks
        self.maxticks = {
            YEARLY: 11,
            MONTHLY: 12,
            DAILY: 11,
            HOURLY: 12,
            MINUTELY: 11
        }
        if maxticks is not None:
            try:
                self.maxticks.update(maxticks)
            except TypeError:
                self.maxticks = dict.fromkeys(self._freqs, maxticks)
        self.interval_multiples = interval_multiples
        self.intervald = {
            YEARLY:   [1, 2, 4, 5, 10, 20, 40, 50, 100, 200, 400, 500,
                       1000, 2000, 4000, 5000, 10000],
            MONTHLY:  [1, 2, 3, 4, 6],
            DAILY:    [1, 2, 3, 7, 14, 21],
            HOURLY:   [1, 2, 3, 4, 6, 12],
            MINUTELY: [1, 5, 10, 15, 30],
        }
        if interval_multiples:
            self.intervald[DAILY] = [1, 2, 4, 7, 14]
        self._byranges = [
            None,
            range(1, 13),
            range(1, 32),
            range(0, 24),
            range(0, 60)
        ]


class Formateador(AutoDateFormatter):
    def __init__(
        self: Self,
        locator: AutoDateLocator,
        tz: Optional[tzinfo],
        defaultfmt: str,
        *,
        usetex: Optional[bool] = None
    ) -> None:
        self._locator = locator
        self._tz = tz if tz else pytz.timezone(settings.TIME_ZONE)
        self.defaultfmt = defaultfmt
        self._usetex = False
        # https://unicode.org/reports/tr35/tr35-dates.html#table-date-field-symbol-table
        self.scaled = {
            DAYS_PER_YEAR: 'y',
            DAYS_PER_MONTH: 'yM',
            1: 'yMd',
            1 / HOURS_PER_DAY: 'h',
            1 / MINUTES_PER_DAY: 'hm'
        }

    def __call__(
        self: Self,
        x: datetime,
        pos: Optional[float] = None
    ) -> str:
        locator_unit_scale: float | int
        try:
            locator_unit_scale = float(self._locator._get_unit())
        except AttributeError:
            locator_unit_scale = 1
        fmt: str = next(
            (
                fmt for scale, fmt in sorted(self.scaled.items())
                if scale >= locator_unit_scale
            ),
            'yMd'
        )
        result: str = ''
        if locator_unit_scale < 1:
            result += format_skeleton(
                'yMd', num2date(x),
                self._tz, True, self.defaultfmt
            ) + ' '
        if isinstance(fmt, str):
            result += format_skeleton(
                fmt, num2date(x),
                self._tz, True, self.defaultfmt
            )
            return result
        raise TypeError(f'Unexpected type passed to {self!r}.')
