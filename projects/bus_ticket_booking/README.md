# Bus Ticket Booking System (Terminal, Python 3 + SQLite)

A complete command-line bus booking application: browse and search buses, pick
seats from an ASCII seat map, enter passenger details, pay (simulated), get an
e-ticket, look up bookings by phone number, cancel them, and manage the fleet
from an admin panel. Data lives in a local SQLite file, so nothing is lost when
you exit.

## Requirements

Python 3.7 or newer. **No `pip install` is needed** — the project uses only the
standard library (`sqlite3`, `dataclasses`, `datetime`, `unittest`).
`requirements.txt` is intentionally empty of packages.

## Running it

```bash
cd bus_ticket_booking
python main.py          # or: python3 main.py
```

On the first run, `bus_booking.db` is created automatically and seeded with six
sample buses (Chennai→Bangalore, Chennai→Madurai, Chennai→Coimbatore,
Bangalore→Chennai, Chennai→Pondicherry, Madurai→Chennai) with different types,
capacities and fares. Delete `bus_booking.db` at any time to start over.

Admin password (in `config.py`): `admin123`.

## Project layout

```
bus_ticket_booking/
├── main.py             # terminal UI + main menu (entry point)
├── admin.py            # admin panel: fleet CRUD, bookings, reports
├── bus_service.py      # bus listing, search, validation, CRUD
├── seat_service.py     # seat inventory, per-date availability, seat map
├── booking_service.py  # booking creation/lookup/cancel, tickets, reports
├── database.py         # connections, schema, transactions, sample data
├── models.py           # Bus / Seat / Booking / Passenger data classes
├── utils.py            # input validation + terminal helpers (tables, etc.)
├── config.py           # all tunable settings and constants
├── test_booking.py     # 38 unit tests for the important scenarios
├── requirements.txt
└── bus_booking.db      # created on first run
```

Business logic never prints, and the UI never writes SQL — that split is what
makes the same services reusable from a web or GUI front end later.

## How the database works

Four tables (`buses`, `seats`, `bookings`, `passengers`) with foreign keys on.

* `buses` — one row per scheduled service.
* `seats` — the **physical** inventory of a bus, created once when the bus is
  created (one row per seat, typed Window/Aisle). Its `status` only says whether
  the seat exists / is serviceable.
* `bookings` — one row per reservation: reference (`BK10001`…), bus, travel
  date, contact phone, amount, `booking_status`, `booking_date`,
  `cancelled_date`.
* `passengers` — one row per traveller, carrying the seat they occupy.

All queries are parameterised (`?` placeholders); no SQL is ever built by string
concatenation.

## How seat availability works (the key design decision)

Occupancy is **not** stored on the seat row. A seat is considered booked only
when a *confirmed* booking holds it for that specific bus **and** travel date:

```sql
SELECT p.seat_number
  FROM passengers p JOIN bookings b ON b.id = p.booking_id
 WHERE b.bus_id = ? AND b.travel_date = ? AND b.booking_status = 'CONFIRMED'
```

Consequences that fall out for free:

* Bus 1 / 20-08-2026 / seat 12 booked does **not** affect 21-08-2026 — seat 12
  is available again on the next date.
* Cancelling a booking frees its seats instantly: the row's status flips to
  `CANCELLED` (it is never deleted, and a cancellation timestamp is stored), so
  the query above stops returning those seats.
* Seat numbers are scoped per bus — seat 5 on bus 1 has nothing to do with seat
  5 on bus 2.

**No double booking.** `create_booking` runs inside a `BEGIN IMMEDIATE`
transaction (`database.exclusive_transaction`): the write lock is taken *first*,
then availability is re-checked with that lock held, then the booking and its
passengers are inserted. Any failure rolls the whole thing back, so a partial
booking can never leave seats looking occupied — `test_failed_booking_leaves_no_partial_data`
covers exactly that case.

## Seat map

Pure ASCII, so it renders in terminals with no emoji or Unicode support:

```
        WINDOW  AISLE  WINDOW
        ---------------------
Row 1   [01]  [02]  [03]
Row 2   [04]  [05]  [06]
Row 3   [07]  [08]  [09]
Row 4   [10]  [11]  [XX]

Legend:  [12] available   [XX] booked   [--] not in service
```

The rupee sign is probed against `stdout.encoding` at start-up and falls back to
`Rs.` on consoles that cannot encode it, so the app never dies with a
`UnicodeEncodeError`.

## Example session — booking a ticket

```
========================================================================
                       BUS TICKET BOOKING SYSTEM
========================================================================

  1. View All Buses
  2. Search Buses
  3. View Bus Details
  4. Book a Ticket
  5. View My Bookings
  6. Cancel a Booking
  7. Admin - Manage Buses
  8. Exit

Enter your choice: 2

========================================================================
                              SEARCH BUSES
========================================================================
Enter source: chennai
Enter destination: BANGALORE
Enter travel date (DD-MM-YYYY, blank to skip): 25-08-2026
Enter bus type (blank for any):

[OK] Found 1 bus(es).
+----+------------+-----------------+------------+----------------------+-------+-------+----------+---------+------------+
| ID | Bus Number | Bus Name        | Type       | Route                | Dep   | Arr   | Duration |    Fare | Seats Left |
+----+------------+-----------------+------------+----------------------+-------+-------+----------+---------+------------+
|  1 | TN01AB1234 | Chennai Express | AC Sleeper | Chennai -> Bangalore | 21:30 | 06:00 | 8h 30m   | ₹850.00 |      40/40 |
+----+------------+-----------------+------------+----------------------+-------+-------+----------+---------+------------+

Enter your choice: 4
Enter Bus ID (blank to go back): 1
Enter travel date (DD-MM-YYYY): 25-08-2026

SEAT LAYOUT - Chennai Express on 25-08-2026
------------------------------------------------------------------------
        WINDOW  AISLE  WINDOW
        ---------------------
Row 1   [01]  [02]  [03]
...
How many seats would you like to book? (1-6): 2
Select seat 1: 12
   Seat 12 (Window) selected.
Select seat 2: 13
   Seat 13 (Aisle) selected.

Selected seats: 12, 13

PASSENGER INFORMATION
------------------------------------------------------------------------

Passenger 1 (Seat 12)
  Name: Rahul Kumar
  Age: 28
  Gender (Male/Female/Other): M
  Phone: 9876543210

Passenger 2 (Seat 13)
  Name: Priya Kumar
  Age: 25
  Gender (Male/Female/Other): F
  Phone: 9876543211

Do you have a promo code? (Y/N): n

========================================================================
                             BOOKING SUMMARY
========================================================================
Bus         : Chennai Express
Bus Number  : TN01AB1234
From        : Chennai
To          : Bangalore
Travel Date : 25-08-2026
Departure   : 21:30
Arrival     : 06:00
Duration    : 8h 30m

Passengers:
  1. Rahul Kumar (28, Male) - Seat 12
  2. Priya Kumar (25, Female) - Seat 13
------------------------------------------------------------------------
Fare per seat   : ₹850.00
Number of seats : 2
------------------------------------------------------------------------
TOTAL AMOUNT    : ₹1,700.00
------------------------------------------------------------------------
Confirm booking? (Y/N): Y

PAYMENT
------------------------------------------------------------------------
  1. UPI
  2. Credit / Debit Card
  3. Net Banking
  4. Pay at counter
Choose a payment method: 1
[OK] Payment accepted.

[OK] Booking confirmed! Your Booking ID is BK10001.
```

## Example session — my bookings and cancellation

```
Enter your choice: 5
Enter phone number: 9876543210

+---+------------+-----------------+----------------------+-------------+--------+-----------+-----------+
| # | Booking ID | Bus             | Route                | Travel Date | Seats  | Amount    | Status    |
+---+------------+-----------------+----------------------+-------------+--------+-----------+-----------+
| 1 | BK10001    | Chennai Express | Chennai -> Bangalore | 25-08-2026  | 12, 13 | ₹1,700.00 | CONFIRMED |
+---+------------+-----------------+----------------------+-------------+--------+-----------+-----------+

Enter your choice: 6
Enter Booking ID (e.g. BK10001): bk10001
... full ticket is printed ...
Are you sure you want to cancel this booking? (Y/N): Y
[OK] Booking BK10001 cancelled successfully.
[i] Seats 12 and 13 are now available for 25-08-2026.
```

## Admin panel

`7` on the main menu, password `admin123`:

1. Add Bus (validates number, same source/destination, seats > 0, fare > 0,
   HH:MM times) — the seat layout is generated automatically
2. View Buses (including inactive ones)
3. Update Bus (blank input keeps the current value; shrinking seats is refused
   when higher-numbered seats are booked)
4. Delete Bus (a bus with confirmed bookings is marked INACTIVE, never deleted,
   so historical tickets keep pointing at real data)
5. View All Bookings
6. Admin Dashboard / Revenue Report
7. Daily Booking Report
8. Exit Admin

## Extra features included

Window/Aisle seat typing · AC / Non-AC / Sleeper / Seater types · operating-day
schedules · sorting by departure time, fare or name · search by bus type ·
promo codes (`FIRST10`, `TRAVEL20`, `WEEKEND5`) · simulated payment · printable
e-tickets saved to `tickets/BK10001.txt` · booking history including cancelled
bookings · admin dashboard, revenue report and daily booking report.

## Tests

```bash
python -m unittest test_booking -v
```

38 tests covering: sample-data seeding, seat-map generation, per-date
availability, seat-belongs-to-bus scoping, double-booking rejection, duplicate
seats in one request, past dates, rollback on a partially invalid booking,
booking-reference sequencing, promo discounts, lookup by phone/reference,
cancellation freeing seats and preserving history, re-booking a cancelled seat,
bus validation rules, case-insensitive search, and the date/time helpers. They
run against a temporary database, so your real `bus_booking.db` is untouched.

## Start the application

```bash
python main.py
```
