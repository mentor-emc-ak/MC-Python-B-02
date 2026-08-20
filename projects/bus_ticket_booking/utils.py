"""Terminal helpers and input validation.

Nothing in here touches the database.  It is pure presentation + validation so
that the service layer stays testable without a terminal.
"""

import os
import re
import sys
from datetime import datetime, date

import config

# ---------------------------------------------------------------------------
# Unicode safety
# ---------------------------------------------------------------------------
# Some Windows consoles use a code page that cannot encode the rupee sign or
# box-drawing glyphs.  We probe stdout once at import time and fall back to
# plain ASCII instead of letting the program die with UnicodeEncodeError.

def _terminal_supports(text):
    """Return True when *text* can actually be written to this terminal."""
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


UNICODE_OK = _terminal_supports(config.CURRENCY)
CURRENCY = config.CURRENCY if UNICODE_OK else "Rs."


def money(amount):
    """Format a number as currency, e.g. 1700 -> '₹1700.00'."""
    return "{}{:,.2f}".format(CURRENCY, float(amount))


# ---------------------------------------------------------------------------
# Screen helpers
# ---------------------------------------------------------------------------

def clear_screen():
    """Clear the terminal on both POSIX and Windows."""
    os.system("cls" if os.name == "nt" else "clear")


def header(title, width=None):
    """Print a centred section heading framed by '=' rules."""
    width = width or config.SCREEN_WIDTH
    print("=" * width)
    print(title.center(width))
    print("=" * width)


def subheader(title, width=None):
    width = width or config.SCREEN_WIDTH
    print()
    print(title)
    print("-" * width)


def info(message):
    print("[i] " + message)


def success(message):
    print("[OK] " + message)


def error(message):
    print("[!] " + message)


def pause(message="Press Enter to continue..."):
    """Block until the user acknowledges, so output is not scrolled away."""
    try:
        input("\n" + message)
    except (EOFError, KeyboardInterrupt):
        print()


def print_table(headers, rows, aligns=None):
    """Render an ASCII table without any third-party dependency.

    headers : list of column titles
    rows    : list of row sequences (values are str()-ed)
    aligns  : optional list of 'l' or 'r' per column
    """
    rows = [[("" if c is None else str(c)) for c in row] for row in rows]
    headers = [str(h) for h in headers]
    aligns = aligns or ["l"] * len(headers)

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    rule = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def render(cells):
        parts = []
        for i, cell in enumerate(cells):
            if aligns[i] == "r":
                parts.append(" " + cell.rjust(widths[i]) + " ")
            else:
                parts.append(" " + cell.ljust(widths[i]) + " ")
        return "|" + "|".join(parts) + "|"

    print(rule)
    print(render(headers))
    print(rule)
    if not rows:
        span = len(rule) - 2
        print("|" + "no records found".center(span) + "|")
    for row in rows:
        print(render(row))
    print(rule)


# ---------------------------------------------------------------------------
# Input helpers -- every one of these loops until the value is valid, and
# every one of them accepts a blank line as "go back" when allow_blank is set.
# ---------------------------------------------------------------------------

class Cancelled(Exception):
    """Raised when the user backs out of a prompt with a blank line."""


def _read(prompt):
    """Read a line, converting Ctrl-C / Ctrl-D into a clean cancel."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Cancelled()


def ask_text(prompt, allow_blank=False, max_length=100):
    """Ask for non-empty text."""
    while True:
        value = _read(prompt)
        if not value:
            if allow_blank:
                raise Cancelled()
            error("Input cannot be empty. Please try again.")
            continue
        if len(value) > max_length:
            error("Input is too long (max {} characters).".format(max_length))
            continue
        return value


def ask_name(prompt):
    """Ask for a person's name: letters, spaces, dots and apostrophes only."""
    while True:
        value = ask_text(prompt)
        if len(value) < 2:
            error("Name must be at least 2 characters long.")
            continue
        if not re.match(r"^[A-Za-z][A-Za-z .'-]*$", value):
            error("Name may only contain letters, spaces, dots and hyphens.")
            continue
        return value


def ask_int(prompt, minimum=None, maximum=None, allow_blank=False):
    """Ask for an integer inside an optional range."""
    while True:
        raw = _read(prompt)
        if not raw and allow_blank:
            raise Cancelled()
        try:
            value = int(raw)
        except ValueError:
            error("Invalid input. Please enter a valid number.")
            continue
        if minimum is not None and value < minimum:
            error("Value must be at least {}.".format(minimum))
            continue
        if maximum is not None and value > maximum:
            error("Value must not be greater than {}.".format(maximum))
            continue
        return value


def ask_float(prompt, minimum=None, maximum=None):
    """Ask for a decimal number (used for fares)."""
    while True:
        raw = _read(prompt)
        try:
            value = float(raw)
        except ValueError:
            error("Invalid input. Please enter a valid amount.")
            continue
        if minimum is not None and value < minimum:
            error("Amount must be greater than or equal to {}.".format(minimum))
            continue
        if maximum is not None and value > maximum:
            error("Amount must not be greater than {}.".format(maximum))
            continue
        return value


def ask_choice(prompt, options):
    """Ask the user to pick one of *options* by its number.  Returns the value."""
    for index, option in enumerate(options, start=1):
        print("  {}. {}".format(index, option))
    index = ask_int(prompt, minimum=1, maximum=len(options))
    return options[index - 1]


def ask_yes_no(prompt):
    """Ask a yes/no question.  Returns True for yes."""
    while True:
        value = _read(prompt).lower()
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        error("Please answer Y or N.")


def ask_phone(prompt):
    """Ask for a 10-digit Indian mobile number."""
    while True:
        value = _read(prompt)
        digits = re.sub(r"[\s-]", "", value)
        if not digits.isdigit():
            error("Phone number must contain digits only.")
            continue
        if len(digits) != config.PHONE_LENGTH:
            error("Phone number must be exactly {} digits.".format(config.PHONE_LENGTH))
            continue
        if digits[0] in "012345":
            error("Phone number must start with a digit between 6 and 9.")
            continue
        return digits


def ask_time(prompt):
    """Ask for a HH:MM time and return it normalised (e.g. '9:5' -> '09:05')."""
    while True:
        value = _read(prompt)
        parsed = parse_time(value)
        if parsed is None:
            error("Invalid time. Please use the 24-hour HH:MM format, e.g. 21:30.")
            continue
        return parsed


def ask_date(prompt, allow_past=False):
    """Ask for a DD-MM-YYYY travel date."""
    while True:
        value = _read(prompt)
        parsed = parse_date(value)
        if parsed is None:
            error("Invalid date. Please use the DD-MM-YYYY format, e.g. 20-08-2026.")
            continue
        if not allow_past:
            if parsed < date.today():
                error("Travel date cannot be in the past.")
                continue
            days_ahead = (parsed - date.today()).days
            if days_ahead > config.MAX_ADVANCE_BOOKING_DAYS:
                error("Bookings open only {} days in advance.".format(
                    config.MAX_ADVANCE_BOOKING_DAYS))
                continue
        return parsed.strftime(config.DATE_FORMAT)


def ask_gender(prompt):
    """Accept M/F/O or the full word and return a canonical value."""
    shortcuts = {"m": "Male", "f": "Female", "o": "Other"}
    while True:
        value = _read(prompt).lower()
        if value in shortcuts:
            return shortcuts[value]
        for gender in config.GENDERS:
            if value == gender.lower():
                return gender
        error("Please enter Male, Female or Other (or M/F/O).")


# ---------------------------------------------------------------------------
# Pure parsing / formatting helpers (no I/O -- easy to unit test)
# ---------------------------------------------------------------------------

def parse_date(value):
    """Return a datetime.date for a DD-MM-YYYY string, else None."""
    try:
        return datetime.strptime(value.strip(), config.DATE_FORMAT).date()
    except (ValueError, AttributeError):
        return None


def parse_time(value):
    """Return a normalised 'HH:MM' string, or None when invalid."""
    if not value:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})$", value.strip())
    if not match:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return "{:02d}:{:02d}".format(hours, minutes)


def travel_duration(departure, arrival):
    """Human-readable duration between two HH:MM strings.

    Handles overnight journeys: 21:30 -> 06:00 is 8h 30m, not negative.
    """
    dep, arr = parse_time(departure), parse_time(arrival)
    if dep is None or arr is None:
        return "N/A"
    dep_minutes = int(dep[:2]) * 60 + int(dep[3:])
    arr_minutes = int(arr[:2]) * 60 + int(arr[3:])
    delta = arr_minutes - dep_minutes
    if delta <= 0:
        delta += 24 * 60          # journey crosses midnight
    return "{}h {:02d}m".format(delta // 60, delta % 60)


def weekday_name(date_string):
    """Return the weekday ('Mon'...) for a DD-MM-YYYY string, or None."""
    parsed = parse_date(date_string)
    return parsed.strftime("%a") if parsed else None


def now_string():
    """Current timestamp in the configured display format."""
    return datetime.now().strftime(config.DATETIME_FORMAT)
