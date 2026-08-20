"""Tests for the important booking scenarios.

Run with:  python -m unittest test_booking -v

The suite points config.DB_PATH at a temporary file, so your real
bus_booking.db is never touched.
"""

import os
import tempfile
import unittest
from datetime import date, timedelta

import config

# Redirect the database *before* importing anything that reads config.DB_PATH
# at call time (all modules read it lazily, so this is enough).
_TMP_DIR = tempfile.mkdtemp(prefix="bus_test_")
config.DB_PATH = os.path.join(_TMP_DIR, "test.db")

import booking_service          # noqa: E402
import bus_service              # noqa: E402
import database                 # noqa: E402
import seat_service             # noqa: E402
import utils                    # noqa: E402


def future_date(days=3):
    """A valid travel date a few days from now."""
    return (date.today() + timedelta(days=days)).strftime(config.DATE_FORMAT)


def passenger(seat, name="Test User", phone="9876543210"):
    return {"name": name, "age": 30, "gender": "Male", "phone": phone,
            "seat_number": seat}


class BookingTestCase(unittest.TestCase):
    """Fresh, seeded database for every test."""

    def setUp(self):
        database.reset_database()
        database.initialize_database()
        # Pick buses that run every day so the tests never depend on which
        # weekday they happen to be executed on.
        self.daily_buses = [b for b in bus_service.list_buses(sort_by="id")
                            if b.operating_days.lower() == "daily"]
        self.bus = self.daily_buses[0]
        self.travel_date = future_date()

    def tearDown(self):
        database.reset_database()


class TestSetup(BookingTestCase):

    def test_sample_buses_are_seeded(self):
        buses = bus_service.list_buses(active_only=False)
        self.assertGreaterEqual(len(buses), 5)

    def test_every_bus_has_its_seat_layout(self):
        for bus in bus_service.list_buses(active_only=False):
            self.assertEqual(len(seat_service.get_seats(bus.id)),
                             bus.total_seats)


class TestSeatAvailability(BookingTestCase):

    def test_all_seats_free_on_a_fresh_date(self):
        self.assertEqual(
            seat_service.available_seat_count(self.bus.id, self.travel_date),
            self.bus.total_seats)

    def test_booking_marks_seats_occupied(self):
        booking_service.create_booking(
            self.bus.id, self.travel_date, [12, 13],
            [passenger(12), passenger(13, "Second User")])
        self.assertFalse(
            seat_service.is_seat_available(self.bus.id, 12, self.travel_date))
        self.assertEqual(
            seat_service.available_seat_count(self.bus.id, self.travel_date),
            self.bus.total_seats - 2)

    def test_availability_is_per_travel_date(self):
        """Seat 12 booked on day A must still be free on day B."""
        day_a, day_b = future_date(3), future_date(4)
        booking_service.create_booking(self.bus.id, day_a, [12],
                                       [passenger(12)])
        self.assertFalse(seat_service.is_seat_available(self.bus.id, 12, day_a))
        self.assertTrue(seat_service.is_seat_available(self.bus.id, 12, day_b))

    def test_seat_belongs_to_the_selected_bus(self):
        other = self.daily_buses[1]
        booking_service.create_booking(self.bus.id, self.travel_date, [5],
                                       [passenger(5)])
        # Same seat number, different bus -> still available.
        self.assertTrue(
            seat_service.is_seat_available(other.id, 5, self.travel_date))

    def test_unknown_seat_number_is_rejected(self):
        with self.assertRaises(seat_service.SeatError):
            seat_service.validate_seat_selection(
                self.bus.id, [self.bus.total_seats + 1], self.travel_date)

    def test_seat_map_renders_without_unicode(self):
        booking_service.create_booking(self.bus.id, self.travel_date, [2],
                                       [passenger(2)])
        text = "\n".join(
            seat_service.render_seat_map(self.bus.id, self.travel_date))
        self.assertIn("[XX]", text)
        text.encode("ascii")            # would raise if a glyph slipped in


class TestBookingCreation(BookingTestCase):

    def test_booking_reference_is_generated_and_sequential(self):
        first = booking_service.create_booking(
            self.bus.id, self.travel_date, [1], [passenger(1)])
        second = booking_service.create_booking(
            self.bus.id, self.travel_date, [2], [passenger(2)])
        self.assertEqual(first.booking_reference, "BK10001")
        self.assertEqual(second.booking_reference, "BK10002")

    def test_total_amount_matches_fare_times_seats(self):
        booking = booking_service.create_booking(
            self.bus.id, self.travel_date, [3, 4],
            [passenger(3), passenger(4, "Priya")])
        self.assertAlmostEqual(booking.total_amount, self.bus.fare * 2, places=2)
        self.assertEqual(booking.seat_count, 2)
        self.assertEqual(booking.seat_numbers, [3, 4])

    def test_double_booking_the_same_seat_is_refused(self):
        booking_service.create_booking(self.bus.id, self.travel_date, [12],
                                       [passenger(12)])
        with self.assertRaises(booking_service.BookingError):
            booking_service.create_booking(self.bus.id, self.travel_date, [12],
                                           [passenger(12, "Someone Else")])

    def test_duplicate_seat_in_one_request_is_refused(self):
        with self.assertRaises(booking_service.BookingError):
            booking_service.create_booking(
                self.bus.id, self.travel_date, [7, 7],
                [passenger(7), passenger(7)])

    def test_past_travel_date_is_refused(self):
        yesterday = (date.today() - timedelta(days=1)).strftime(
            config.DATE_FORMAT)
        with self.assertRaises(booking_service.BookingError):
            booking_service.create_booking(self.bus.id, yesterday, [1],
                                           [passenger(1)])

    def test_failed_booking_leaves_no_partial_data(self):
        """A rejected booking must not reserve any of its seats."""
        booking_service.create_booking(self.bus.id, self.travel_date, [12],
                                       [passenger(12)])
        before = seat_service.available_seat_count(self.bus.id, self.travel_date)
        with self.assertRaises(booking_service.BookingError):
            # seat 14 is free but seat 12 is taken -> the whole booking fails
            booking_service.create_booking(
                self.bus.id, self.travel_date, [14, 12],
                [passenger(14), passenger(12)])
        after = seat_service.available_seat_count(self.bus.id, self.travel_date)
        self.assertEqual(before, after)
        self.assertTrue(
            seat_service.is_seat_available(self.bus.id, 14, self.travel_date))

    def test_promo_code_discount_is_applied(self):
        booking = booking_service.create_booking(
            self.bus.id, self.travel_date, [9], [passenger(9)],
            promo_code="first10")
        self.assertEqual(booking.promo_code, "FIRST10")
        self.assertAlmostEqual(booking.total_amount, self.bus.fare * 0.9,
                               places=2)

    def test_unknown_bus_is_refused(self):
        with self.assertRaises(booking_service.BookingError):
            booking_service.create_booking(9999, self.travel_date, [1],
                                           [passenger(1)])


class TestLookupAndCancellation(BookingTestCase):

    def setUp(self):
        super().setUp()
        self.booking = booking_service.create_booking(
            self.bus.id, self.travel_date, [12, 13],
            [passenger(12, "Rahul Kumar"),
             passenger(13, "Priya Kumar", "9876543211")])

    def test_lookup_by_phone_number(self):
        found = booking_service.bookings_for_phone("9876543210")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].booking_reference,
                         self.booking.booking_reference)

    def test_lookup_finds_a_co_passengers_number_too(self):
        self.assertEqual(len(booking_service.bookings_for_phone("9876543211")), 1)

    def test_lookup_by_reference_is_case_insensitive(self):
        found = booking_service.get_booking_by_reference(
            self.booking.booking_reference.lower())
        self.assertIsNotNone(found)

    def test_cancellation_frees_the_seats(self):
        booking_service.cancel_booking(self.booking.booking_reference)
        self.assertTrue(
            seat_service.is_seat_available(self.bus.id, 12, self.travel_date))
        self.assertTrue(
            seat_service.is_seat_available(self.bus.id, 13, self.travel_date))

    def test_cancellation_keeps_the_history_row(self):
        cancelled = booking_service.cancel_booking(
            self.booking.booking_reference)
        self.assertEqual(cancelled.booking_status, config.STATUS_CANCELLED)
        self.assertIsNotNone(cancelled.cancelled_date)
        self.assertIsNotNone(booking_service.get_booking_by_reference(
            self.booking.booking_reference))

    def test_cancelled_seat_can_be_rebooked(self):
        booking_service.cancel_booking(self.booking.booking_reference)
        new_booking = booking_service.create_booking(
            self.bus.id, self.travel_date, [12],
            [passenger(12, "New Traveller")])
        self.assertEqual(new_booking.seat_numbers, [12])

    def test_cancelling_twice_is_refused(self):
        booking_service.cancel_booking(self.booking.booking_reference)
        with self.assertRaises(booking_service.BookingError):
            booking_service.cancel_booking(self.booking.booking_reference)

    def test_unknown_reference_is_refused(self):
        with self.assertRaises(booking_service.BookingError):
            booking_service.cancel_booking("BK99999")

    def test_ticket_can_be_saved_to_a_file(self):
        path = booking_service.save_ticket(self.booking)
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as handle:
            self.assertIn(self.booking.booking_reference, handle.read())
        os.remove(path)


class TestBusManagement(BookingTestCase):

    def valid_bus(self, **overrides):
        data = {"bus_number": "TN99ZZ0001", "bus_name": "Test Liner",
                "bus_type": "AC Seater", "source": "Salem",
                "destination": "Erode", "departure_time": "08:00",
                "arrival_time": "11:30", "total_seats": 12, "fare": 250,
                "operating_days": "Daily"}
        data.update(overrides)
        return data

    def test_add_bus_creates_its_seats(self):
        bus_id = bus_service.add_bus(self.valid_bus())
        self.assertEqual(len(seat_service.get_seats(bus_id)), 12)

    def test_same_source_and_destination_is_refused(self):
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(destination="Salem"))

    def test_empty_bus_number_is_refused(self):
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(bus_number="   "))

    def test_non_positive_seats_and_fare_are_refused(self):
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(total_seats=0))
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(fare=0))

    def test_bad_time_format_is_refused(self):
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(departure_time="25:99"))

    def test_duplicate_bus_number_is_refused(self):
        bus_service.add_bus(self.valid_bus())
        with self.assertRaises(bus_service.BusError):
            bus_service.add_bus(self.valid_bus(bus_name="Copycat"))

    def test_search_is_case_insensitive(self):
        results = bus_service.search_buses("chennai", "BANGALORE")
        self.assertTrue(results)
        self.assertTrue(all(r.source.lower() == "chennai" for r in results))

    def test_bus_with_bookings_is_deactivated_not_deleted(self):
        booking_service.create_booking(self.bus.id, self.travel_date, [1],
                                       [passenger(1)])
        self.assertEqual(bus_service.delete_bus(self.bus.id), "DEACTIVATED")
        self.assertIsNotNone(bus_service.get_bus(self.bus.id))

    def test_operating_days_filter(self):
        bus_id = bus_service.add_bus(self.valid_bus(operating_days="Mon"))
        bus = bus_service.get_bus(bus_id)
        monday = date.today()
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        self.assertTrue(bus.runs_on(monday.strftime(config.DATE_FORMAT)))
        self.assertFalse(
            bus.runs_on((monday + timedelta(days=1)).strftime(config.DATE_FORMAT)))


class TestUtilities(unittest.TestCase):
    """Pure helpers -- no database needed."""

    def test_overnight_duration(self):
        self.assertEqual(utils.travel_duration("21:30", "06:00"), "8h 30m")

    def test_same_day_duration(self):
        self.assertEqual(utils.travel_duration("07:45", "11:00"), "3h 15m")

    def test_time_parsing(self):
        self.assertEqual(utils.parse_time("9:05"), "09:05")
        self.assertIsNone(utils.parse_time("24:00"))
        self.assertIsNone(utils.parse_time("abc"))

    def test_date_parsing(self):
        self.assertIsNotNone(utils.parse_date("20-08-2026"))
        self.assertIsNone(utils.parse_date("2026-08-20"))
        self.assertIsNone(utils.parse_date("31-02-2026"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
