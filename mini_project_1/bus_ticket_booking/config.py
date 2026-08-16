"""Central configuration.

Every tunable value lives here so the rest of the application never has to
hard-code a path, a password or a magic number.
"""

import os

# --- Paths -----------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bus_booking.db")
TICKETS_DIR = os.path.join(BASE_DIR, "tickets")

# --- Admin -----------------------------------------------------------------
# Deliberately simple for v1.  All admin access goes through
# admin.authenticate(), so swapping this for hashed credentials or a users
# table later only touches that one function.
ADMIN_PASSWORD = "admin123"
ADMIN_MAX_ATTEMPTS = 3

# --- Formats ---------------------------------------------------------------
DATE_FORMAT = "%d-%m-%Y"        # 20-08-2026
TIME_FORMAT = "%H:%M"           # 21:30
DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"

# --- Booking rules ---------------------------------------------------------
BOOKING_PREFIX = "BK"
BOOKING_START_NUMBER = 10000    # first reference becomes BK10001
MAX_SEATS_PER_BOOKING = 6
MAX_ADVANCE_BOOKING_DAYS = 90
SEATS_PER_ROW = 3               # terminal seat map: [win][aisle][win]

# Passenger validation limits
MIN_AGE = 1
MAX_AGE = 120
PHONE_LENGTH = 10
GENDERS = ("Male", "Female", "Other")

# Booking statuses
STATUS_CONFIRMED = "CONFIRMED"
STATUS_CANCELLED = "CANCELLED"

# Bus statuses
BUS_ACTIVE = "ACTIVE"
BUS_INACTIVE = "INACTIVE"

BUS_TYPES = (
    "AC Sleeper",
    "AC Seater",
    "Non-AC Sleeper",
    "Non-AC Seater",
    "Volvo Multi-Axle",
)

# --- Promo codes (simple discount simulation) ------------------------------
PROMO_CODES = {
    "FIRST10": 10,      # 10% off
    "TRAVEL20": 20,     # 20% off
    "WEEKEND5": 5,      # 5% off
}

# --- UI --------------------------------------------------------------------
CURRENCY = "₹"     # ₹
APP_TITLE = "BUS TICKET BOOKING SYSTEM"
SCREEN_WIDTH = 72
