"""Bus Ticket Booking System -- terminal entry point.

Run with:  python main.py

This module owns the terminal only: every rule about seats, prices and
availability lives in the *_service modules.
"""

import sys

import admin
import booking_service
import bus_service
import config
import database
import seat_service
import utils
from utils import Cancelled


# ---------------------------------------------------------------------------
# Shared rendering helpers
# ---------------------------------------------------------------------------

def show_bus_table(buses, travel_date=None):
    """Print a bus list with seats available (for a date when given)."""
    rows = []
    for bus in buses:
        summary = bus_service.bus_summary(bus, travel_date)
        rows.append([bus.id, bus.bus_number, bus.bus_name, bus.bus_type,
                     bus.route, bus.departure_time, bus.arrival_time,
                     bus.duration, utils.money(bus.fare),
                     "{}/{}".format(summary["available"], summary["total"])])
    utils.print_table(
        ["ID", "Bus Number", "Bus Name", "Type", "Route", "Dep", "Arr",
         "Duration", "Fare", "Seats Left"], rows,
        aligns=["r", "l", "l", "l", "l", "l", "l", "l", "r", "r"])
    if travel_date:
        utils.info("Seats shown are for travel date {}.".format(travel_date))


def choose_sort():
    """Ask how the bus list should be ordered."""
    print("Sort buses by:")
    label = utils.ask_choice("Choose: ",
                             ["Departure time", "Fare (low to high)", "Name"])
    return {"Departure time": "departure", "Fare (low to high)": "fare",
            "Name": "name"}[label]


def show_bus_details(bus, travel_date=None):
    """Print the full detail card for one bus."""
    utils.header("BUS DETAILS")
    available = (seat_service.available_seat_count(bus.id, travel_date)
                 if travel_date else None)
    details = [
        ("Bus Name", bus.bus_name),
        ("Bus Number", bus.bus_number),
        ("Bus Type", bus.bus_type),
        ("Source", bus.source),
        ("Destination", bus.destination),
        ("Departure Time", bus.departure_time),
        ("Arrival Time", bus.arrival_time),
        ("Travel Duration", bus.duration),
        ("Operating Days", bus.operating_days),
        ("Fare per Seat", utils.money(bus.fare)),
        ("Total Seats", bus.total_seats),
        ("Status", bus.status),
    ]
    if travel_date:
        details += [
            ("Travel Date", travel_date),
            ("Available Seats", available),
            ("Occupied Seats", bus.total_seats - available),
        ]
    for label, value in details:
        print("  {:<16}: {}".format(label, value))


# ---------------------------------------------------------------------------
# Menu option 1 -- View all buses
# ---------------------------------------------------------------------------

def view_all_buses():
    utils.header("ALL AVAILABLE BUSES")
    sort_by = choose_sort()
    buses = bus_service.list_buses(sort_by=sort_by)
    if not buses:
        utils.info("No buses are currently in service.")
        return
    print()
    show_bus_table(buses)


# ---------------------------------------------------------------------------
# Menu option 2 -- Search buses
# ---------------------------------------------------------------------------

def search_buses():
    """Search by source, destination, date and (optionally) bus type."""
    utils.header("SEARCH BUSES")
    utils.info("Leave a field blank to ignore it. Press Enter on the date to "
               "skip it.")
    try:
        source = input("Enter source: ").strip()
        destination = input("Enter destination: ").strip()
        travel_date = None
        raw_date = input("Enter travel date (DD-MM-YYYY, blank to skip): ").strip()
        if raw_date:
            parsed = utils.parse_date(raw_date)
            if parsed is None:
                utils.error("Invalid date format; ignoring the date filter.")
            else:
                travel_date = parsed.strftime(config.DATE_FORMAT)
        bus_type = input("Enter bus type (blank for any): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise Cancelled()

    buses = bus_service.search_buses(source, destination, travel_date, bus_type)
    print()
    if not buses:
        utils.info("No buses matched your search. Try a different route or date.")
        return
    utils.success("Found {} bus(es).".format(len(buses)))
    show_bus_table(buses, travel_date)


# ---------------------------------------------------------------------------
# Menu option 3 -- View bus details
# ---------------------------------------------------------------------------

def prompt_for_bus():
    """Ask for a bus ID and return the Bus, or None when it is invalid."""
    buses = bus_service.list_buses()
    if not buses:
        utils.info("No buses are currently in service.")
        return None
    show_bus_table(buses)
    bus_id = utils.ask_int("\nEnter Bus ID (blank to go back): ", minimum=1,
                           allow_blank=True)
    bus = bus_service.get_bus(bus_id)
    if bus is None or not bus.is_active():
        utils.error("No active bus found with ID {}.".format(bus_id))
        return None
    return bus


def view_bus_details():
    utils.header("VIEW BUS DETAILS")
    bus = prompt_for_bus()
    if bus is None:
        return
    travel_date = utils.ask_date("Enter travel date (DD-MM-YYYY): ")
    if not bus.runs_on(travel_date):
        utils.error("This bus does not operate on {} (runs: {}).".format(
            travel_date, bus.operating_days))
        return
    print()
    show_bus_details(bus, travel_date)
    utils.subheader("SEAT LAYOUT")
    seat_service.print_seat_map(bus.id, travel_date)
    if utils.ask_yes_no("\nContinue to seat selection? (Y/N): "):
        book_ticket(bus=bus, travel_date=travel_date)


# ---------------------------------------------------------------------------
# Menu option 4 -- Book a ticket
# ---------------------------------------------------------------------------

def select_seats(bus, travel_date):
    """Interactive seat picking.  Returns the chosen seat numbers."""
    available = seat_service.available_seat_numbers(bus.id, travel_date)
    if not available:
        utils.error("Sorry, this bus is fully booked on {}.".format(travel_date))
        return []

    maximum = min(len(available), config.MAX_SEATS_PER_BOOKING)
    count = utils.ask_int(
        "\nHow many seats would you like to book? (1-{}): ".format(maximum),
        minimum=1, maximum=maximum)

    chosen = []
    while len(chosen) < count:
        number = utils.ask_int("Select seat {}: ".format(len(chosen) + 1),
                               minimum=1)
        if number in chosen:
            utils.error("You have already selected seat {}. Pick another one."
                        .format(number))
            continue
        seat = seat_service.get_seat(bus.id, number)
        if seat is None:
            utils.error("Seat {} does not exist on this bus. Valid seats are "
                        "1-{}.".format(number, bus.total_seats))
            continue
        if number not in available:
            utils.error("Seat {} is already booked. Please select another seat."
                        .format(number))
            continue
        chosen.append(number)
        print("   Seat {} ({}) selected.".format(number, seat.seat_type))

    print("\nSelected seats: {}".format(", ".join(str(n) for n in chosen)))
    return chosen


def collect_passengers(seat_numbers):
    """Ask for the details of one passenger per selected seat."""
    utils.subheader("PASSENGER INFORMATION")
    passengers = []
    for index, seat_number in enumerate(seat_numbers, start=1):
        print("\nPassenger {} (Seat {})".format(index, seat_number))
        passengers.append({
            "name": utils.ask_name("  Name: "),
            "age": utils.ask_int("  Age: ", minimum=config.MIN_AGE,
                                 maximum=config.MAX_AGE),
            "gender": utils.ask_gender("  Gender (Male/Female/Other): "),
            "phone": utils.ask_phone("  Phone: "),
            "seat_number": seat_number,
        })
    return passengers


def show_booking_summary(bus, travel_date, passengers, pricing):
    """Print the pre-confirmation summary."""
    utils.header("BOOKING SUMMARY")
    print("Bus         : {}".format(bus.bus_name))
    print("Bus Number  : {}".format(bus.bus_number))
    print("From        : {}".format(bus.source))
    print("To          : {}".format(bus.destination))
    print("Travel Date : {}".format(travel_date))
    print("Departure   : {}".format(bus.departure_time))
    print("Arrival     : {}".format(bus.arrival_time))
    print("Duration    : {}".format(bus.duration))
    print("\nPassengers:")
    for index, person in enumerate(passengers, start=1):
        print("  {}. {} ({}, {}) - Seat {}".format(
            index, person["name"], person["age"], person["gender"],
            person["seat_number"]))
    print("-" * config.SCREEN_WIDTH)
    print("Fare per seat   : {}".format(utils.money(pricing["fare_per_seat"])))
    print("Number of seats : {}".format(pricing["seat_count"]))
    if pricing["discount"]:
        print("Discount ({:<8}): -{}".format(pricing["promo_code"],
                                             utils.money(pricing["discount"])))
    print("-" * config.SCREEN_WIDTH)
    print("TOTAL AMOUNT    : {}".format(utils.money(pricing["total"])))
    print("-" * config.SCREEN_WIDTH)


def simulate_payment(amount):
    """A stand-in for a real payment gateway."""
    utils.subheader("PAYMENT")
    method = utils.ask_choice("Choose a payment method: ",
                              ["UPI", "Credit / Debit Card", "Net Banking",
                               "Pay at counter"])
    utils.info("Processing {} via {}...".format(utils.money(amount), method))
    utils.success("Payment accepted.")
    return method


def book_ticket(bus=None, travel_date=None):
    """The full booking flow: bus -> date -> seats -> passengers -> confirm."""
    if bus is None:
        utils.header("BOOK A TICKET")
        bus = prompt_for_bus()
        if bus is None:
            return
    if travel_date is None:
        travel_date = utils.ask_date("Enter travel date (DD-MM-YYYY): ")

    if not bus.runs_on(travel_date):
        utils.error("{} does not operate on {} (runs: {}).".format(
            bus.bus_name, travel_date, bus.operating_days))
        return

    utils.subheader("SEAT LAYOUT - {} on {}".format(bus.bus_name, travel_date))
    seat_service.print_seat_map(bus.id, travel_date)

    seat_numbers = select_seats(bus, travel_date)
    if not seat_numbers:
        return

    passengers = collect_passengers(seat_numbers)

    promo_code = None
    if utils.ask_yes_no("\nDo you have a promo code? (Y/N): "):
        promo_code = utils.ask_text("Enter promo code: ")
        _, applied = booking_service.apply_promo(bus.fare, promo_code)
        if applied is None:
            utils.error("'{}' is not a valid promo code; continuing without a "
                        "discount.".format(promo_code))
            promo_code = None

    pricing = booking_service.quote(bus, len(seat_numbers), promo_code)
    print()
    show_booking_summary(bus, travel_date, passengers, pricing)

    if not utils.ask_yes_no("Confirm booking? (Y/N): "):
        utils.info("Booking cancelled. The selected seats are still available.")
        return

    simulate_payment(pricing["total"])

    try:
        booking = booking_service.create_booking(
            bus_id=bus.id, travel_date=travel_date, seat_numbers=seat_numbers,
            passengers=passengers, contact_phone=passengers[0]["phone"],
            promo_code=promo_code)
    except booking_service.BookingError as exc:
        utils.error(str(exc))
        utils.info("No seats were reserved. Please try again.")
        return

    print()
    utils.success("Booking confirmed! Your Booking ID is {}."
                  .format(booking.booking_reference))
    print()
    print(booking_service.format_ticket(booking))
    if utils.ask_yes_no("\nSave this ticket as a text file? (Y/N): "):
        path = booking_service.save_ticket(booking)
        utils.success("Ticket saved to {}".format(path))


# ---------------------------------------------------------------------------
# Menu option 5 -- My bookings
# ---------------------------------------------------------------------------

def my_bookings():
    utils.header("MY BOOKINGS")
    phone = utils.ask_phone("Enter phone number: ")
    bookings = booking_service.bookings_for_phone(phone)
    if not bookings:
        utils.info("No bookings were found for {}.".format(phone))
        return

    rows = [[index, b.booking_reference,
             b.bus.bus_name if b.bus else "-",
             b.bus.route if b.bus else "-",
             b.travel_date, b.seats_display,
             utils.money(b.total_amount), b.booking_status]
            for index, b in enumerate(bookings, start=1)]
    print()
    utils.print_table(
        ["#", "Booking ID", "Bus", "Route", "Travel Date", "Seats", "Amount",
         "Status"], rows)

    if not utils.ask_yes_no("\nView the full details of one booking? (Y/N): "):
        return
    index = utils.ask_int("Enter the row number: ", minimum=1,
                          maximum=len(bookings))
    booking = bookings[index - 1]
    print()
    print(booking_service.format_ticket(booking))
    if not booking.is_cancelled():
        if utils.ask_yes_no("\nSave this ticket as a text file? (Y/N): "):
            utils.success("Ticket saved to {}".format(
                booking_service.save_ticket(booking)))


# ---------------------------------------------------------------------------
# Menu option 6 -- Cancel a booking
# ---------------------------------------------------------------------------

def cancel_booking():
    utils.header("CANCEL A BOOKING")
    reference = utils.ask_text("Enter Booking ID (e.g. BK10001): ")
    booking = booking_service.get_booking_by_reference(reference)
    if booking is None:
        utils.error("No booking found with ID {}.".format(reference))
        return
    if booking.is_cancelled():
        utils.info("Booking {} was already cancelled on {}.".format(
            booking.booking_reference, booking.cancelled_date))
        return

    print()
    print(booking_service.format_ticket(booking))
    if not utils.ask_yes_no(
            "\nAre you sure you want to cancel this booking? (Y/N): "):
        utils.info("Your booking is unchanged.")
        return

    seats = booking.seat_numbers
    try:
        booking_service.cancel_booking(booking.booking_reference)
    except booking_service.BookingError as exc:
        utils.error(str(exc))
        return

    seat_list = " and ".join([", ".join(str(s) for s in seats[:-1]),
                              str(seats[-1])]).strip(", ") if seats else "-"
    utils.success("Booking {} cancelled successfully."
                  .format(booking.booking_reference))
    utils.info("Seats {} are now available for {}.".format(
        seat_list, booking.travel_date))


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = [
    ("View All Buses", view_all_buses),
    ("Search Buses", search_buses),
    ("View Bus Details", view_bus_details),
    ("Book a Ticket", book_ticket),
    ("View My Bookings", my_bookings),
    ("Cancel a Booking", cancel_booking),
    ("Admin - Manage Buses", admin.admin_menu),
]


def print_main_menu():
    utils.clear_screen()
    utils.header(config.APP_TITLE)
    print()
    for index, (label, _) in enumerate(MENU, start=1):
        print("  {}. {}".format(index, label))
    print("  {}. Exit".format(len(MENU) + 1))
    print()


def main():
    """Application loop: set up the database, then serve the menu forever."""
    database.initialize_database()

    while True:
        print_main_menu()
        try:
            choice = utils.ask_int("Enter your choice: ", minimum=1,
                                   maximum=len(MENU) + 1)
        except Cancelled:
            print("\nGoodbye!")
            return

        if choice == len(MENU) + 1:
            utils.clear_screen()
            utils.header("THANK YOU FOR USING " + config.APP_TITLE)
            print("\nHave a safe journey!\n")
            return

        utils.clear_screen()
        try:
            MENU[choice - 1][1]()
        except Cancelled:
            utils.info("Cancelled. Returning to the main menu.")
        except Exception as exc:            # last-resort guard: never crash
            utils.error("Something went wrong: {}".format(exc))
        if choice != len(MENU):             # the admin menu pauses on its own
            utils.pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")
        sys.exit(0)
