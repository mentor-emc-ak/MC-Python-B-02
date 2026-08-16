"""Business logic for buses: listing, searching, creating, updating, deleting.

No printing happens here -- main.py and admin.py own the terminal.
"""

import sqlite3

import config
import database
import seat_service
import utils
from models import Bus


class BusError(Exception):
    """Raised when bus data is invalid or a bus cannot be modified."""


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def list_buses(active_only=True, sort_by="departure"):
    """All buses, optionally only the ones in service.

    sort_by: 'departure' | 'fare' | 'name' | 'id'
    """
    order = {
        "departure": "departure_time ASC",
        "fare": "fare ASC",
        "name": "bus_name ASC",
        "id": "id ASC",
    }.get(sort_by, "departure_time ASC")

    sql = "SELECT * FROM buses"
    params = ()
    if active_only:
        sql += " WHERE status = ?"
        params = (config.BUS_ACTIVE,)
    sql += " ORDER BY " + order          # whitelisted above, never user input

    return [Bus.from_row(row) for row in database.query_all(sql, params)]


def get_bus(bus_id):
    """One bus by id, or None."""
    row = database.query_one("SELECT * FROM buses WHERE id = ?", (bus_id,))
    return Bus.from_row(row) if row else None


def get_bus_or_raise(bus_id):
    """One bus by id, raising BusError when it does not exist."""
    bus = get_bus(bus_id)
    if bus is None:
        raise BusError("No bus found with ID {}.".format(bus_id))
    return bus


def search_buses(source=None, destination=None, travel_date=None,
                 bus_type=None, active_only=True):
    """Case-insensitive search on route, type and operating day.

    ``travel_date`` filters out buses that do not run on that weekday; the
    caller normally also shows availability for that date.
    """
    sql = "SELECT * FROM buses WHERE 1 = 1"
    params = []

    if active_only:
        sql += " AND status = ?"
        params.append(config.BUS_ACTIVE)
    if source:
        sql += " AND LOWER(source) LIKE ?"
        params.append("%{}%".format(source.strip().lower()))
    if destination:
        sql += " AND LOWER(destination) LIKE ?"
        params.append("%{}%".format(destination.strip().lower()))
    if bus_type:
        sql += " AND LOWER(bus_type) LIKE ?"
        params.append("%{}%".format(bus_type.strip().lower()))

    sql += " ORDER BY departure_time ASC"
    buses = [Bus.from_row(row) for row in database.query_all(sql, tuple(params))]

    if travel_date:
        buses = [bus for bus in buses if bus.runs_on(travel_date)]
    return buses


def bus_summary(bus, travel_date=None):
    """Dict of display values for one bus, including seats left on a date."""
    total = bus.total_seats
    if travel_date:
        available = seat_service.available_seat_count(bus.id, travel_date)
    else:
        available = total - len(seat_service.blocked_seat_numbers(bus.id))
    return {
        "bus": bus,
        "available": available,
        "occupied": total - available,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_bus_data(data, bus_id=None):
    """Validate a bus payload, raising BusError on the first problem.

    Returns a cleaned dict ready to be written to the database.
    """
    cleaned = {}

    number = (data.get("bus_number") or "").strip().upper()
    if not number:
        raise BusError("Bus number cannot be empty.")
    duplicate = database.query_one(
        "SELECT id FROM buses WHERE UPPER(bus_number) = ?", (number,))
    if duplicate and duplicate["id"] != bus_id:
        raise BusError("Bus number {} is already registered.".format(number))
    cleaned["bus_number"] = number

    for key, label in (("bus_name", "Bus name"), ("bus_type", "Bus type"),
                       ("source", "Source"), ("destination", "Destination")):
        value = (data.get(key) or "").strip()
        if not value:
            raise BusError("{} cannot be empty.".format(label))
        cleaned[key] = value

    if cleaned["source"].lower() == cleaned["destination"].lower():
        raise BusError("Source and destination cannot be the same.")

    for key, label in (("departure_time", "Departure time"),
                       ("arrival_time", "Arrival time")):
        value = utils.parse_time(data.get(key))
        if value is None:
            raise BusError("{} must use the HH:MM format.".format(label))
        cleaned[key] = value

    try:
        seats = int(data.get("total_seats"))
    except (TypeError, ValueError):
        raise BusError("Total seats must be a whole number.")
    if seats <= 0:
        raise BusError("Total seats must be greater than zero.")
    cleaned["total_seats"] = seats

    try:
        fare = float(data.get("fare"))
    except (TypeError, ValueError):
        raise BusError("Fare must be a number.")
    if fare <= 0:
        raise BusError("Fare must be greater than zero.")
    cleaned["fare"] = round(fare, 2)

    cleaned["operating_days"] = (data.get("operating_days") or "Daily").strip()
    cleaned["status"] = (data.get("status") or config.BUS_ACTIVE).strip().upper()
    return cleaned


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def add_bus(data):
    """Create a bus and its seat map in one transaction.  Returns the new id."""
    cleaned = validate_bus_data(data)
    try:
        with database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO buses (bus_number, bus_name, bus_type, source,
                                      destination, departure_time, arrival_time,
                                      total_seats, fare, operating_days, status)
                   VALUES (:bus_number, :bus_name, :bus_type, :source,
                           :destination, :departure_time, :arrival_time,
                           :total_seats, :fare, :operating_days, :status)""",
                cleaned,
            )
            bus_id = cursor.lastrowid
            database.create_seats(connection, bus_id, cleaned["total_seats"])
            return bus_id
    except sqlite3.IntegrityError as exc:
        raise BusError("Could not save the bus: {}".format(exc))


def update_bus(bus_id, data):
    """Update a bus, growing or shrinking its seat map when needed."""
    bus = get_bus_or_raise(bus_id)
    merged = {
        "bus_number": bus.bus_number, "bus_name": bus.bus_name,
        "bus_type": bus.bus_type, "source": bus.source,
        "destination": bus.destination, "departure_time": bus.departure_time,
        "arrival_time": bus.arrival_time, "total_seats": bus.total_seats,
        "fare": bus.fare, "operating_days": bus.operating_days,
        "status": bus.status,
    }
    merged.update({k: v for k, v in data.items() if v not in (None, "")})
    cleaned = validate_bus_data(merged, bus_id=bus_id)

    new_total = cleaned["total_seats"]
    if new_total < bus.total_seats and _has_seats_above(bus_id, new_total):
        raise BusError(
            "Cannot shrink to {} seats: higher-numbered seats are booked."
            .format(new_total))

    with database.transaction() as connection:
        connection.execute(
            """UPDATE buses
                  SET bus_number = :bus_number, bus_name = :bus_name,
                      bus_type = :bus_type, source = :source,
                      destination = :destination,
                      departure_time = :departure_time,
                      arrival_time = :arrival_time,
                      total_seats = :total_seats, fare = :fare,
                      operating_days = :operating_days, status = :status
                WHERE id = :id""",
            dict(cleaned, id=bus_id),
        )
        if new_total > bus.total_seats:
            database.create_seats(connection, bus_id, new_total)
        elif new_total < bus.total_seats:
            connection.execute(
                "DELETE FROM seats WHERE bus_id = ? AND seat_number > ?",
                (bus_id, new_total))
    return True


def _has_seats_above(bus_id, seat_number):
    """True when a confirmed booking holds a seat above *seat_number*."""
    row = database.query_one(
        """SELECT COUNT(*) AS n
             FROM passengers p JOIN bookings b ON b.id = p.booking_id
            WHERE b.bus_id = ? AND b.booking_status = ? AND p.seat_number > ?""",
        (bus_id, config.STATUS_CONFIRMED, seat_number))
    return row["n"] > 0


def active_booking_count(bus_id):
    """Number of confirmed bookings still attached to a bus."""
    row = database.query_one(
        "SELECT COUNT(*) AS n FROM bookings WHERE bus_id = ? AND booking_status = ?",
        (bus_id, config.STATUS_CONFIRMED))
    return row["n"]


def delete_bus(bus_id, force=False):
    """Retire a bus.

    A bus with confirmed bookings is marked INACTIVE rather than deleted, so
    historical tickets keep pointing at real data.  ``force`` hard-deletes a
    bus that nobody has booked.
    """
    get_bus_or_raise(bus_id)
    if active_booking_count(bus_id) > 0:
        database.execute("UPDATE buses SET status = ? WHERE id = ?",
                         (config.BUS_INACTIVE, bus_id))
        return "DEACTIVATED"
    if force:
        database.execute("DELETE FROM buses WHERE id = ?", (bus_id,))
        return "DELETED"
    database.execute("UPDATE buses SET status = ? WHERE id = ?",
                     (config.BUS_INACTIVE, bus_id))
    return "DEACTIVATED"
