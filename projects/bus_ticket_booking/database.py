"""SQLite access layer: connections, schema creation and sample data.

Everything above this module talks to the database through ``get_connection``
so there is exactly one place that knows about file paths, pragmas and the
schema.
"""

import os
import sqlite3
from contextlib import contextmanager

import config

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
# Note on seat availability (the single most important design decision):
#
#   * ``seats`` stores the *physical* inventory of a bus -- one row per seat,
#     created once when the bus is created.  Its ``status`` says whether the
#     seat exists/is serviceable at all (ACTIVE or BLOCKED by an admin).
#   * Whether a seat is taken on a *particular day* is NOT stored here.  It is
#     derived by joining ``passengers`` to ``bookings`` and filtering on
#     bus_id + travel_date + booking_status = 'CONFIRMED'.
#
# That is what makes seat 12 booked on 20-08-2026 and still free on
# 21-08-2026, and it means cancelling a booking frees its seats automatically
# without any extra bookkeeping.

SCHEMA = """
CREATE TABLE IF NOT EXISTS buses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_number      TEXT    NOT NULL UNIQUE,
    bus_name        TEXT    NOT NULL,
    bus_type        TEXT    NOT NULL,
    source          TEXT    NOT NULL,
    destination     TEXT    NOT NULL,
    departure_time  TEXT    NOT NULL,
    arrival_time    TEXT    NOT NULL,
    total_seats     INTEGER NOT NULL CHECK (total_seats > 0),
    fare            REAL    NOT NULL CHECK (fare > 0),
    operating_days  TEXT    NOT NULL DEFAULT 'Daily',
    status          TEXT    NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS seats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_id      INTEGER NOT NULL,
    seat_number INTEGER NOT NULL,
    seat_type   TEXT    NOT NULL DEFAULT 'Window',
    status      TEXT    NOT NULL DEFAULT 'ACTIVE',
    UNIQUE (bus_id, seat_number),
    FOREIGN KEY (bus_id) REFERENCES buses (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference TEXT    NOT NULL UNIQUE,
    bus_id            INTEGER NOT NULL,
    travel_date       TEXT    NOT NULL,
    contact_phone     TEXT    NOT NULL,
    seat_count        INTEGER NOT NULL,
    fare_per_seat     REAL    NOT NULL,
    discount          REAL    NOT NULL DEFAULT 0,
    promo_code        TEXT,
    total_amount      REAL    NOT NULL,
    booking_status    TEXT    NOT NULL DEFAULT 'CONFIRMED',
    booking_date      TEXT    NOT NULL,
    cancelled_date    TEXT,
    FOREIGN KEY (bus_id) REFERENCES buses (id)
);

CREATE TABLE IF NOT EXISTS passengers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id  INTEGER NOT NULL,
    seat_number INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    age         INTEGER NOT NULL,
    gender      TEXT    NOT NULL,
    phone       TEXT    NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
);

-- Speeds up the availability lookup, which runs on every seat map render.
CREATE INDEX IF NOT EXISTS idx_bookings_lookup
    ON bookings (bus_id, travel_date, booking_status);
CREATE INDEX IF NOT EXISTS idx_passengers_booking
    ON passengers (booking_id);

-- A booked seat must be unique per (bus, date).  SQLite cannot express that
-- across two tables, so booking_service enforces it inside a transaction and
-- this partial index guards the rest.
CREATE UNIQUE INDEX IF NOT EXISTS idx_passenger_seat_per_booking
    ON passengers (booking_id, seat_number);
"""


def get_connection():
    """Open a configured connection.

    Rows come back as ``sqlite3.Row`` (dict-like), foreign keys are enforced,
    and a busy timeout keeps concurrent terminals from failing instantly.
    """
    connection = sqlite3.connect(config.DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def transaction():
    """Run a block of statements atomically.

    Commits on success, rolls back on any exception, and always closes the
    connection.
    """
    connection = get_connection()
    try:
        with connection:                      # sqlite3 commits/rolls back here
            yield connection
    finally:
        connection.close()


@contextmanager
def exclusive_transaction():
    """Like ``transaction`` but takes the write lock up front.

    ``BEGIN IMMEDIATE`` means the availability check and the insert that
    follows it cannot be interleaved with another process's booking, so two
    terminals can never sell the same seat.
    """
    connection = get_connection()
    connection.isolation_level = None         # we drive BEGIN/COMMIT ourselves
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
        except Exception:
            connection.execute("ROLLBACK")
            raise
        else:
            connection.execute("COMMIT")
    finally:
        connection.close()


def query_all(sql, params=()):
    """Run a SELECT and return every row (parameterised -- never f-strings)."""
    connection = get_connection()
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def query_one(sql, params=()):
    """Run a SELECT and return the first row, or None."""
    connection = get_connection()
    try:
        return connection.execute(sql, params).fetchone()
    finally:
        connection.close()


def execute(sql, params=()):
    """Run a single INSERT/UPDATE/DELETE and return the cursor's lastrowid."""
    with transaction() as connection:
        cursor = connection.execute(sql, params)
        return cursor.lastrowid


# ---------------------------------------------------------------------------
# Sample data -- inserted only the first time the database is created
# ---------------------------------------------------------------------------

SAMPLE_BUSES = [
    # bus_number, name, type, source, destination, dep, arr, seats, fare, days
    ("TN01AB1234", "Chennai Express", "AC Sleeper", "Chennai", "Bangalore",
     "21:30", "06:00", 40, 850.0, "Daily"),
    ("TN02CD5678", "Green Travels", "AC Seater", "Chennai", "Madurai",
     "22:00", "05:30", 36, 700.0, "Daily"),
    ("TN03EF9012", "Kovai Star", "Non-AC Sleeper", "Chennai", "Coimbatore",
     "20:15", "05:45", 30, 620.0, "Mon,Wed,Fri,Sun"),
    ("KA05GH3456", "Silicon Rider", "Volvo Multi-Axle", "Bangalore", "Chennai",
     "23:00", "05:15", 45, 950.0, "Daily"),
    ("TN07IJ7890", "Pondy Breeze", "Non-AC Seater", "Chennai", "Pondicherry",
     "07:45", "11:00", 27, 320.0, "Sat,Sun"),
    ("TN09KL2468", "Madurai Meenakshi", "AC Sleeper", "Madurai", "Chennai",
     "21:00", "05:00", 33, 780.0, "Daily"),
]


def _seat_type(seat_number):
    """Window seats sit at the edges of a row, the middle one is the aisle."""
    position = (seat_number - 1) % config.SEATS_PER_ROW
    return "Aisle" if position == 1 else "Window"


def create_seats(connection, bus_id, total_seats):
    """Create the physical seat rows for a bus (1..total_seats)."""
    rows = [(bus_id, number, _seat_type(number))
            for number in range(1, total_seats + 1)]
    connection.executemany(
        "INSERT OR IGNORE INTO seats (bus_id, seat_number, seat_type) "
        "VALUES (?, ?, ?)",
        rows,
    )


def _insert_sample_buses(connection):
    """Insert the demo fleet together with their seat maps."""
    for bus in SAMPLE_BUSES:
        cursor = connection.execute(
            """INSERT INTO buses (bus_number, bus_name, bus_type, source,
                                  destination, departure_time, arrival_time,
                                  total_seats, fare, operating_days, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            bus + (config.BUS_ACTIVE,),
        )
        create_seats(connection, cursor.lastrowid, bus[7])


def initialize_database(seed=True):
    """Create the schema if needed and seed sample buses on a fresh database.

    Safe to call on every start-up: it is completely idempotent.
    """
    with transaction() as connection:
        connection.executescript(SCHEMA)
        if seed:
            existing = connection.execute(
                "SELECT COUNT(*) AS n FROM buses").fetchone()["n"]
            if existing == 0:
                _insert_sample_buses(connection)


def reset_database():
    """Delete the database file entirely.  Used by the test suite."""
    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
