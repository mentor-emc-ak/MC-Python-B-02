# Code Journal

## Knowledge

- `projects/expense_tracker/models.py` - Expense's date column is named `spent_on`, NOT `date`: in a Python class body, `date: Mapped[date] = mapped_column(...)` fails on 3.9 because the attribute name shadows the `datetime.date` import when SQLAlchemy evaluates annotations. #decision
- `projects/expense_tracker/services.py` - `set_budget` queries Budget by FK directly instead of via `category.budget`: creating a Budget without assigning `.category` leaves the parent's relationship attribute stale-None, causing duplicate INSERTs against the unique constraint.
- `projects/expense_tracker/db.py` - DB path resolution: arg > `EXPENSE_TRACKER_DB` env var > `./expense_tracker.db`. Tests use in-memory SQLite with `StaticPool`.
- Repo runs system Python 3.9.6 (Xcode CLT); PEP 604 unions (`X | None`) are not allowed anywhere - use `typing.Optional`.

## Log

- 2026-08-22 - `projects/expense_tracker/` - built terminal expense tracker: SQLAlchemy 2.x models (Category/Expense/Budget), service layer, menu-loop CLI, CSV export, budget warnings, ASCII-bar reports; 20 pytest tests passing against in-memory SQLite. Found+fixed set_budget stale-relationship bug during TDD-ish test run. #feature #bugfix
