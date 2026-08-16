"""Admin console: fleet management, booking overview and reports.

Authentication is deliberately minimal (a password in config.py) but it is
funnelled through ``authenticate`` so it can be replaced with a real user
table without touching any of the menu code.
"""

import booking_service
import bus_service
import config
import utils
from utils import Cancelled


def authenticate():
    """Ask for the admin password.  Returns True when access is granted."""
    utils.header("ADMIN LOGIN")
    for attempt in range(config.ADMIN_MAX_ATTEMPTS, 0, -1):
        try:
            password = utils.ask_text("Enter admin password (blank to cancel): ",
                                      allow_blank=True)
        except Cancelled:
            return False
        if password == config.ADMIN_PASSWORD:
            utils.success("Welcome, admin.")
            return True
        utils.error("Incorrect password. {} attempt(s) left.".format(attempt - 1))
    return False


# ---------------------------------------------------------------------------
# Fleet management
# ---------------------------------------------------------------------------

def _collect_bus_data(existing=None):
    """Prompt for bus fields.  With *existing*, blank keeps the old value."""
    keep = " (blank = keep current)" if existing else ""

    def current(attr):
        return " [{}]".format(getattr(existing, attr)) if existing else ""

    def text(label, attr):
        prompt = "{}{}{}: ".format(label, current(attr), keep)
        if existing:
            try:
                return utils.ask_text(prompt, allow_blank=True)
            except Cancelled:
                return None
        return utils.ask_text(prompt)

    data = {}
    data["bus_number"] = text("Bus Number", "bus_number")
    data["bus_name"] = text("Bus Name", "bus_name")

    print("\nBus types:")
    try:
        data["bus_type"] = utils.ask_choice("Choose bus type: ",
                                            list(config.BUS_TYPES))
    except Cancelled:
        data["bus_type"] = None

    data["source"] = text("Source", "source")
    data["destination"] = text("Destination", "destination")

    for label, attr in (("Departure Time (HH:MM)", "departure_time"),
                        ("Arrival Time (HH:MM)", "arrival_time")):
        if existing:
            raw = None
            try:
                raw = utils.ask_text("{} [{}] (blank = keep): ".format(
                    label, getattr(existing, attr)), allow_blank=True)
            except Cancelled:
                pass
            data[attr] = utils.parse_time(raw) if raw else None
            if raw and data[attr] is None:
                utils.error("Invalid time ignored; keeping the current value.")
        else:
            data[attr] = utils.ask_time(label + ": ")

    if existing:
        try:
            data["total_seats"] = utils.ask_int(
                "Total Seats [{}] (blank = keep): ".format(existing.total_seats),
                minimum=1, maximum=100, allow_blank=True)
        except Cancelled:
            data["total_seats"] = None
    else:
        data["total_seats"] = utils.ask_int("Total Seats: ", minimum=1,
                                            maximum=100)

    if existing:
        try:
            raw = utils.ask_text("Fare [{}] (blank = keep): ".format(
                existing.fare), allow_blank=True)
            data["fare"] = float(raw)
        except (Cancelled, ValueError):
            data["fare"] = None
    else:
        data["fare"] = utils.ask_float("Fare ({}): ".format(utils.CURRENCY),
                                       minimum=1)

    try:
        data["operating_days"] = utils.ask_text(
            "Operating Days (Daily or Mon,Wed,Fri){}: ".format(keep),
            allow_blank=True)
    except Cancelled:
        data["operating_days"] = None if existing else "Daily"

    return {k: v for k, v in data.items() if v not in (None, "")}


def add_bus_screen():
    """Admin option 1: add a bus."""
    utils.header("ADD NEW BUS")
    try:
        data = _collect_bus_data()
    except Cancelled:
        utils.info("Cancelled.")
        return
    try:
        bus_id = bus_service.add_bus(data)
    except bus_service.BusError as exc:
        utils.error(str(exc))
        return
    utils.success("Bus added with ID {} and its seat layout was created."
                  .format(bus_id))


def view_buses_screen():
    """Admin option 2: list every bus, including inactive ones."""
    utils.header("ALL BUSES (ADMIN)")
    buses = bus_service.list_buses(active_only=False, sort_by="id")
    rows = [[b.id, b.bus_number, b.bus_name, b.bus_type, b.route,
             b.departure_time, b.arrival_time, b.total_seats,
             utils.money(b.fare), b.operating_days, b.status]
            for b in buses]
    utils.print_table(
        ["ID", "Number", "Name", "Type", "Route", "Dep", "Arr", "Seats",
         "Fare", "Days", "Status"], rows)


def update_bus_screen():
    """Admin option 3: edit an existing bus."""
    view_buses_screen()
    try:
        bus_id = utils.ask_int("\nEnter Bus ID to update (blank to cancel): ",
                               minimum=1, allow_blank=True)
    except Cancelled:
        return
    bus = bus_service.get_bus(bus_id)
    if bus is None:
        utils.error("No bus found with ID {}.".format(bus_id))
        return
    try:
        data = _collect_bus_data(existing=bus)
        bus_service.update_bus(bus_id, data)
    except Cancelled:
        utils.info("Cancelled.")
        return
    except bus_service.BusError as exc:
        utils.error(str(exc))
        return
    utils.success("Bus {} updated.".format(bus_id))


def delete_bus_screen():
    """Admin option 4: retire a bus."""
    view_buses_screen()
    try:
        bus_id = utils.ask_int("\nEnter Bus ID to delete (blank to cancel): ",
                               minimum=1, allow_blank=True)
    except Cancelled:
        return
    bus = bus_service.get_bus(bus_id)
    if bus is None:
        utils.error("No bus found with ID {}.".format(bus_id))
        return
    active = bus_service.active_booking_count(bus_id)
    if active:
        utils.info("{} confirmed booking(s) exist; the bus will be marked "
                   "INACTIVE instead of deleted.".format(active))
    if not utils.ask_yes_no("Remove bus {} ({})? (Y/N): ".format(
            bus_id, bus.bus_name)):
        utils.info("Nothing was changed.")
        return
    outcome = bus_service.delete_bus(bus_id, force=(active == 0))
    utils.success("Bus {} {}.".format(bus_id, outcome.lower()))


def view_all_bookings_screen():
    """Admin option 5: every booking in the system."""
    utils.header("ALL BOOKINGS")
    bookings = booking_service.all_bookings()
    rows = [[b.booking_reference,
             b.bus.bus_name if b.bus else "-",
             b.travel_date, b.seats_display, b.contact_phone,
             utils.money(b.total_amount), b.booking_status]
            for b in bookings]
    utils.print_table(
        ["Booking ID", "Bus", "Travel Date", "Seats", "Phone", "Amount",
         "Status"], rows)


def dashboard_screen():
    """Admin option 6: headline numbers plus the revenue report."""
    utils.header("ADMIN DASHBOARD")
    stats = booking_service.totals()
    utils.print_table(
        ["Buses", "Bookings", "Confirmed", "Cancelled", "Revenue"],
        [[stats["buses"], stats["bookings"], stats["confirmed"],
          stats["cancelled"], utils.money(stats["revenue"])]])

    utils.subheader("Revenue by bus")
    rows = [[r["bus_name"], r["bus_number"], r["bookings"], r["seats"],
             utils.money(r["revenue"])]
            for r in booking_service.revenue_report()]
    utils.print_table(["Bus", "Number", "Bookings", "Seats", "Revenue"], rows,
                      aligns=["l", "l", "r", "r", "r"])


def daily_report_screen():
    """Admin option 7: bookings for a single travel date."""
    utils.header("DAILY BOOKING REPORT")
    try:
        travel_date = utils.ask_date("Enter travel date (DD-MM-YYYY): ",
                                     allow_past=True)
    except Cancelled:
        return
    rows = [[r["booking_reference"], r["bus_name"], r["bus_number"],
             r["seat_count"], utils.money(r["total_amount"]),
             r["booking_status"]]
            for r in booking_service.daily_report(travel_date)]
    utils.print_table(
        ["Booking ID", "Bus", "Number", "Seats", "Amount", "Status"], rows)


ADMIN_MENU = [
    ("Add Bus", add_bus_screen),
    ("View Buses", view_buses_screen),
    ("Update Bus", update_bus_screen),
    ("Delete Bus", delete_bus_screen),
    ("View All Bookings", view_all_bookings_screen),
    ("Admin Dashboard / Revenue Report", dashboard_screen),
    ("Daily Booking Report", daily_report_screen),
]


def admin_menu():
    """Run the admin section until the admin exits."""
    if not authenticate():
        utils.error("Admin access denied.")
        utils.pause()
        return

    while True:
        utils.clear_screen()
        utils.header("ADMIN PANEL")
        for index, (label, _) in enumerate(ADMIN_MENU, start=1):
            print("  {}. {}".format(index, label))
        print("  {}. Exit Admin".format(len(ADMIN_MENU) + 1))

        try:
            choice = utils.ask_int("\nEnter your choice: ", minimum=1,
                                   maximum=len(ADMIN_MENU) + 1)
        except Cancelled:
            return
        if choice == len(ADMIN_MENU) + 1:
            utils.info("Leaving the admin panel.")
            utils.pause()
            return

        utils.clear_screen()
        try:
            ADMIN_MENU[choice - 1][1]()
        except Cancelled:
            utils.info("Cancelled.")
        utils.pause()
