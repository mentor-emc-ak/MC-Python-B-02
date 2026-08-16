"""Seat inventory, per-date availability and the terminal seat map.

The rule enforced here, and nowhere else, is:

    a seat is occupied only for the (bus, travel_date) combination on which a
    CONFIRMED booking holds it.
"""

import config
import database
from models import Seat


class SeatError(Exception):
    """Raised when a seat is missing, blocked or already taken."""


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def get_seats(bus_id):
    """Every physical seat of a bus, ordered by seat number."""
    rows = database.query_all(
        "SELECT * FROM seats WHERE bus_id = ? ORDER BY seat_number", (bus_id,))
    return [Seat.from_row(row) for row in rows]


def get_seat(bus_id, seat_number):
    """One seat of one bus, or None when the number does not exist there."""
    row = database.query_one(
        "SELECT * FROM seats WHERE bus_id = ? AND seat_number = ?",
        (bus_id, seat_number))
    return Seat.from_row(row) if row else None


# ---------------------------------------------------------------------------
# Availability (bus + date)
# ---------------------------------------------------------------------------

BOOKED_SEATS_SQL = """
    SELECT p.seat_number
      FROM passengers p
      JOIN bookings  b ON b.id = p.booking_id
     WHERE b.bus_id = ?
       AND b.travel_date = ?
       AND b.booking_status = ?
"""


def booked_seat_numbers(bus_id, travel_date, connection=None):
    """Set of seat numbers taken on this bus for this date.

    Pass an open *connection* to run inside an in-flight transaction, which is
    how booking creation re-checks availability just before it writes.
    """
    params = (bus_id, travel_date, config.STATUS_CONFIRMED)
    if connection is not None:
        rows = connection.execute(BOOKED_SEATS_SQL, params).fetchall()
    else:
        rows = database.query_all(BOOKED_SEATS_SQL, params)
    return {row["seat_number"] for row in rows}


def blocked_seat_numbers(bus_id):
    """Seats an admin has taken out of service on this bus."""
    rows = database.query_all(
        "SELECT seat_number FROM seats WHERE bus_id = ? AND status <> 'ACTIVE'",
        (bus_id,))
    return {row["seat_number"] for row in rows}


def seat_status_map(bus_id, travel_date):
    """Map ``seat_number -> 'AVAILABLE' | 'BOOKED' | 'BLOCKED'``."""
    booked = booked_seat_numbers(bus_id, travel_date)
    statuses = {}
    for seat in get_seats(bus_id):
        if seat.seat_number in booked:
            statuses[seat.seat_number] = "BOOKED"
        elif seat.status.upper() != "ACTIVE":
            statuses[seat.seat_number] = "BLOCKED"
        else:
            statuses[seat.seat_number] = "AVAILABLE"
    return statuses


def available_seat_numbers(bus_id, travel_date):
    """Sorted list of seat numbers that can still be booked."""
    statuses = seat_status_map(bus_id, travel_date)
    return sorted(n for n, s in statuses.items() if s == "AVAILABLE")


def available_seat_count(bus_id, travel_date):
    """How many seats remain on this bus for this date."""
    return len(available_seat_numbers(bus_id, travel_date))


def is_seat_available(bus_id, seat_number, travel_date):
    """True when the seat exists, belongs to the bus, and is free that day."""
    seat = get_seat(bus_id, seat_number)
    if seat is None or seat.status.upper() != "ACTIVE":
        return False
    return seat_number not in booked_seat_numbers(bus_id, travel_date)


def validate_seat_selection(bus_id, seat_numbers, travel_date, connection=None):
    """Raise SeatError unless every requested seat can be booked.

    Checks, in order: duplicates in the request, the seat exists on this bus,
    the seat is in service, and the seat is free for this travel date.
    """
    if not seat_numbers:
        raise SeatError("No seats were selected.")
    if len(set(seat_numbers)) != len(seat_numbers):
        raise SeatError("The same seat was selected more than once.")

    existing = {s.seat_number: s for s in get_seats(bus_id)}
    booked = booked_seat_numbers(bus_id, travel_date, connection=connection)

    for number in seat_numbers:
        seat = existing.get(number)
        if seat is None:
            raise SeatError(
                "Seat {} does not exist on this bus.".format(number))
        if seat.status.upper() != "ACTIVE":
            raise SeatError("Seat {} is not available for booking.".format(number))
        if number in booked:
            raise SeatError(
                "Seat {} is already booked. Please select another seat.".format(
                    number))
    return True


# ---------------------------------------------------------------------------
# Seat map rendering
# ---------------------------------------------------------------------------

def render_seat_map(bus_id, travel_date, per_row=None):
    """Return the seat layout as a list of printable lines.

    Uses ASCII only -- ``[12]`` free, ``[XX]`` booked, ``[--]`` out of service
    -- so it renders identically in terminals without emoji or Unicode
    support.
    """
    per_row = per_row or config.SEATS_PER_ROW
    statuses = seat_status_map(bus_id, travel_date)
    numbers = sorted(statuses)
    if not numbers:
        return ["  (this bus has no seat layout)"]

    symbols = {"BOOKED": "[XX]", "BLOCKED": "[--]"}
    lines = [
        "        WINDOW  AISLE  WINDOW",
        "        ---------------------",
    ]
    for start in range(0, len(numbers), per_row):
        chunk = numbers[start:start + per_row]
        cells = [symbols.get(statuses[n], "[{:02d}]".format(n)) for n in chunk]
        lines.append("Row {:<3}  {}".format(start // per_row + 1,
                                            "  ".join(cells)))
    lines.append("")
    lines.append("Legend:  [12] available   [XX] booked   [--] not in service")
    return lines


def print_seat_map(bus_id, travel_date):
    """Print the seat map plus a one-line availability summary."""
    for line in render_seat_map(bus_id, travel_date):
        print(line)
    free = available_seat_numbers(bus_id, travel_date)
    print("Available seats ({}): {}".format(
        len(free), ", ".join(str(n) for n in free) if free else "none"))
