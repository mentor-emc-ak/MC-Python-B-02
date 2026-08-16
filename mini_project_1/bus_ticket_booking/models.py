"""Plain data objects mapped from database rows.

These classes carry no SQL.  They exist so the rest of the code can say
``bus.duration`` instead of juggling raw ``sqlite3.Row`` tuples.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import utils


def _fields_from_row(cls, row):
    """Build a dataclass from a sqlite3.Row, ignoring unknown columns."""
    names = {f for f in cls.__dataclass_fields__}
    data = {key: row[key] for key in row.keys() if key in names}
    return cls(**data)


@dataclass
class Bus:
    """A scheduled bus service."""

    id: int
    bus_number: str
    bus_name: str
    bus_type: str
    source: str
    destination: str
    departure_time: str
    arrival_time: str
    total_seats: int
    fare: float
    operating_days: str = "Daily"
    status: str = "ACTIVE"

    @classmethod
    def from_row(cls, row):
        return _fields_from_row(cls, row)

    @property
    def route(self):
        return "{} -> {}".format(self.source, self.destination)

    @property
    def duration(self):
        """Journey length, handling overnight services."""
        return utils.travel_duration(self.departure_time, self.arrival_time)

    def runs_on(self, date_string):
        """Does this bus operate on the given DD-MM-YYYY date?

        ``operating_days`` is either 'Daily' or a comma separated list of
        three-letter weekday names, e.g. 'Mon,Wed,Fri'.
        """
        if self.operating_days.strip().lower() in ("daily", "all", ""):
            return True
        weekday = utils.weekday_name(date_string)
        if weekday is None:
            return True
        allowed = {d.strip().lower()[:3]
                   for d in self.operating_days.split(",") if d.strip()}
        return weekday.lower()[:3] in allowed

    def is_active(self):
        return self.status.upper() == "ACTIVE"


@dataclass
class Seat:
    """One physical seat belonging to a bus."""

    id: int
    bus_id: int
    seat_number: int
    seat_type: str = "Window"
    status: str = "ACTIVE"

    @classmethod
    def from_row(cls, row):
        return _fields_from_row(cls, row)


@dataclass
class Passenger:
    """A traveller occupying one seat of a booking."""

    name: str
    age: int
    gender: str
    phone: str
    seat_number: int
    id: Optional[int] = None
    booking_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        return _fields_from_row(cls, row)


@dataclass
class Booking:
    """A confirmed or cancelled reservation on one bus for one date."""

    id: int
    booking_reference: str
    bus_id: int
    travel_date: str
    contact_phone: str
    seat_count: int
    fare_per_seat: float
    total_amount: float
    booking_status: str
    booking_date: str
    discount: float = 0.0
    promo_code: Optional[str] = None
    cancelled_date: Optional[str] = None
    passengers: List[Passenger] = field(default_factory=list)
    bus: Optional[Bus] = None

    @classmethod
    def from_row(cls, row):
        return _fields_from_row(cls, row)

    @property
    def seat_numbers(self):
        return sorted(p.seat_number for p in self.passengers)

    @property
    def seats_display(self):
        return ", ".join(str(n) for n in self.seat_numbers) or "-"

    def is_cancelled(self):
        return self.booking_status.upper() == "CANCELLED"
