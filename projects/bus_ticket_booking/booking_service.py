"""Booking creation, lookup, cancellation, tickets and reports."""

import os
from datetime import datetime

import bus_service
import config
import database
import seat_service
import utils
from models import Booking, Passenger


class BookingError(Exception):
    """Raised when a booking cannot be created, found or cancelled."""


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

def apply_promo(amount, promo_code):
    """Return ``(discount, normalised_code)`` for a promo code.

    An unknown or empty code simply means no discount -- it is never an error.
    """
    if not promo_code:
        return 0.0, None
    code = promo_code.strip().upper()
    percent = config.PROMO_CODES.get(code)
    if not percent:
        return 0.0, None
    return round(amount * percent / 100.0, 2), code


def quote(bus, seat_count, promo_code=None):
    """Price a prospective booking without touching the database."""
    gross = round(bus.fare * seat_count, 2)
    discount, code = apply_promo(gross, promo_code)
    return {
        "fare_per_seat": bus.fare,
        "seat_count": seat_count,
        "gross": gross,
        "discount": discount,
        "promo_code": code,
        "total": round(gross - discount, 2),
    }


def _next_reference(connection):
    """Generate the next BK##### reference inside an open transaction."""
    row = connection.execute(
        "SELECT COALESCE(MAX(id), 0) AS last FROM bookings").fetchone()
    return "{}{}".format(config.BOOKING_PREFIX,
                         config.BOOKING_START_NUMBER + row["last"] + 1)


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------

def create_booking(bus_id, travel_date, seat_numbers, passengers,
                   contact_phone=None, promo_code=None):
    """Create a confirmed booking atomically.

    passengers : list of dicts / Passenger objects carrying name, age, gender,
                 phone and seat_number.

    The whole thing runs in one exclusive transaction: availability is
    re-checked with the write lock already held, then the booking and its
    passengers are written.  Any failure rolls everything back, so a partial
    booking can never leave seats marked as taken.
    """
    bus = bus_service.get_bus(bus_id)
    if bus is None:
        raise BookingError("No bus found with ID {}.".format(bus_id))
    if not bus.is_active():
        raise BookingError("This bus is no longer in service.")
    if utils.parse_date(travel_date) is None:
        raise BookingError("Travel date must use the DD-MM-YYYY format.")
    if utils.parse_date(travel_date) < datetime.now().date():
        raise BookingError("Travel date cannot be in the past.")
    if not bus.runs_on(travel_date):
        raise BookingError("This bus does not operate on {} ({}).".format(
            travel_date, bus.operating_days))

    seat_numbers = [int(n) for n in seat_numbers]
    if not 1 <= len(seat_numbers) <= config.MAX_SEATS_PER_BOOKING:
        raise BookingError("You may book between 1 and {} seats at a time."
                           .format(config.MAX_SEATS_PER_BOOKING))

    people = [p if isinstance(p, dict) else vars(p) for p in passengers]
    if len(people) != len(seat_numbers):
        raise BookingError("Passenger details are missing for some seats.")

    pricing = quote(bus, len(seat_numbers), promo_code)
    contact_phone = contact_phone or people[0].get("phone")
    booked_at = utils.now_string()

    with database.exclusive_transaction() as connection:
        # Re-validate with the write lock held -- this is the check that makes
        # double booking impossible.
        try:
            seat_service.validate_seat_selection(
                bus_id, seat_numbers, travel_date, connection=connection)
        except seat_service.SeatError as exc:
            raise BookingError(str(exc))

        reference = _next_reference(connection)
        cursor = connection.execute(
            """INSERT INTO bookings (booking_reference, bus_id, travel_date,
                                     contact_phone, seat_count, fare_per_seat,
                                     discount, promo_code, total_amount,
                                     booking_status, booking_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (reference, bus_id, travel_date, contact_phone, len(seat_numbers),
             pricing["fare_per_seat"], pricing["discount"],
             pricing["promo_code"], pricing["total"],
             config.STATUS_CONFIRMED, booked_at),
        )
        booking_id = cursor.lastrowid

        connection.executemany(
            """INSERT INTO passengers (booking_id, seat_number, name, age,
                                       gender, phone)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(booking_id, int(person["seat_number"]), person["name"],
              int(person["age"]), person["gender"], person["phone"])
             for person in people],
        )

    return get_booking_by_reference(reference)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def _hydrate(row):
    """Turn a bookings row into a Booking with its passengers and bus."""
    booking = Booking.from_row(row)
    passenger_rows = database.query_all(
        "SELECT * FROM passengers WHERE booking_id = ? ORDER BY seat_number",
        (booking.id,))
    booking.passengers = [Passenger.from_row(r) for r in passenger_rows]
    booking.bus = bus_service.get_bus(booking.bus_id)
    return booking


def get_booking_by_reference(reference):
    """Look up one booking by its BK##### reference (case-insensitive)."""
    row = database.query_one(
        "SELECT * FROM bookings WHERE UPPER(booking_reference) = ?",
        ((reference or "").strip().upper(),))
    return _hydrate(row) if row else None


def get_booking(booking_id):
    row = database.query_one("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    return _hydrate(row) if row else None


def bookings_for_phone(phone, include_cancelled=True):
    """Every booking reachable from a phone number.

    Matches both the booking contact number and any passenger's number, so a
    passenger can find a ticket someone else paid for.
    """
    phone = (phone or "").strip()
    sql = """
        SELECT DISTINCT b.*
          FROM bookings b
          LEFT JOIN passengers p ON p.booking_id = b.id
         WHERE b.contact_phone = ? OR p.phone = ?
    """
    params = [phone, phone]
    if not include_cancelled:
        sql += " AND b.booking_status = ?"
        params.append(config.STATUS_CONFIRMED)
    sql += " ORDER BY b.id DESC"
    return [_hydrate(row) for row in database.query_all(sql, tuple(params))]


def all_bookings(status=None):
    """Every booking in the system, newest first (admin view)."""
    if status:
        rows = database.query_all(
            "SELECT * FROM bookings WHERE booking_status = ? ORDER BY id DESC",
            (status,))
    else:
        rows = database.query_all("SELECT * FROM bookings ORDER BY id DESC")
    return [_hydrate(row) for row in rows]


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

def cancel_booking(reference):
    """Cancel a booking by reference.

    The row is kept for history: only the status and cancellation timestamp
    change.  Because availability is derived from CONFIRMED bookings, the
    seats become free again the moment this commits.
    """
    booking = get_booking_by_reference(reference)
    if booking is None:
        raise BookingError("No booking found with ID {}.".format(reference))
    if booking.is_cancelled():
        raise BookingError("Booking {} is already cancelled."
                           .format(booking.booking_reference))

    database.execute(
        "UPDATE bookings SET booking_status = ?, cancelled_date = ? WHERE id = ?",
        (config.STATUS_CANCELLED, utils.now_string(), booking.id))
    return get_booking_by_reference(booking.booking_reference)


# ---------------------------------------------------------------------------
# Ticket rendering
# ---------------------------------------------------------------------------

def format_ticket(booking):
    """Return the printable ticket for a booking as a single string."""
    bus = booking.bus
    width = config.SCREEN_WIDTH
    lines = [
        "=" * width,
        "E-TICKET".center(width),
        "=" * width,
        "Booking ID   : {}".format(booking.booking_reference),
        "Status       : {}".format(booking.booking_status),
        "Booked On    : {}".format(booking.booking_date),
    ]
    if booking.cancelled_date:
        lines.append("Cancelled On : {}".format(booking.cancelled_date))
    if bus:
        lines += [
            "-" * width,
            "Bus          : {} ({})".format(bus.bus_name, bus.bus_type),
            "Bus Number   : {}".format(bus.bus_number),
            "From         : {}".format(bus.source),
            "To           : {}".format(bus.destination),
            "Travel Date  : {}".format(booking.travel_date),
            "Departure    : {}".format(bus.departure_time),
            "Arrival      : {}".format(bus.arrival_time),
            "Duration     : {}".format(bus.duration),
        ]
    lines.append("-" * width)
    lines.append("Passengers:")
    for index, passenger in enumerate(booking.passengers, start=1):
        lines.append("  {}. {} ({}, {}) - Seat {}".format(
            index, passenger.name, passenger.age, passenger.gender,
            passenger.seat_number))
    lines += [
        "-" * width,
        "Fare per seat : {}".format(utils.money(booking.fare_per_seat)),
        "Seats         : {}".format(booking.seat_count),
    ]
    if booking.discount:
        lines.append("Discount      : -{} ({})".format(
            utils.money(booking.discount), booking.promo_code))
    lines += [
        "TOTAL AMOUNT  : {}".format(utils.money(booking.total_amount)),
        "=" * width,
        "Please carry a valid photo ID. Happy journey!".center(width),
        "=" * width,
    ]
    return "\n".join(lines)


def save_ticket(booking):
    """Write the ticket to ``tickets/BK10001.txt`` and return the path."""
    os.makedirs(config.TICKETS_DIR, exist_ok=True)
    path = os.path.join(config.TICKETS_DIR,
                        "{}.txt".format(booking.booking_reference))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(format_ticket(booking) + "\n")
    return path


# ---------------------------------------------------------------------------
# Reports (admin dashboard)
# ---------------------------------------------------------------------------

def revenue_report():
    """Per-bus revenue and seat totals from confirmed bookings."""
    return database.query_all(
        """SELECT bu.bus_name, bu.bus_number,
                  COUNT(bo.id)            AS bookings,
                  COALESCE(SUM(bo.seat_count), 0)   AS seats,
                  COALESCE(SUM(bo.total_amount), 0) AS revenue
             FROM buses bu
             LEFT JOIN bookings bo
                    ON bo.bus_id = bu.id AND bo.booking_status = ?
            GROUP BY bu.id
            ORDER BY revenue DESC""",
        (config.STATUS_CONFIRMED,))


def daily_report(travel_date):
    """Bookings departing on one travel date."""
    return database.query_all(
        """SELECT bo.booking_reference, bu.bus_name, bu.bus_number,
                  bo.seat_count, bo.total_amount, bo.booking_status
             FROM bookings bo JOIN buses bu ON bu.id = bo.bus_id
            WHERE bo.travel_date = ?
            ORDER BY bo.id""",
        (travel_date,))


def totals():
    """Headline numbers for the admin dashboard."""
    row = database.query_one(
        """SELECT
             (SELECT COUNT(*) FROM buses)                              AS buses,
             (SELECT COUNT(*) FROM bookings)                           AS bookings,
             (SELECT COUNT(*) FROM bookings WHERE booking_status = ?)  AS confirmed,
             (SELECT COUNT(*) FROM bookings WHERE booking_status = ?)  AS cancelled,
             (SELECT COALESCE(SUM(total_amount), 0) FROM bookings
               WHERE booking_status = ?)                               AS revenue""",
        (config.STATUS_CONFIRMED, config.STATUS_CANCELLED,
         config.STATUS_CONFIRMED))
    return dict(row)
