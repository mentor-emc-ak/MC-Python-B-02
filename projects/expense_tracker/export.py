import csv
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Expense
from typing import Optional, Union


def export_expenses(
    session: Session,
    path: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> int:
    stmt = select(Expense).order_by(Expense.spent_on, Expense.id)
    if start:
        stmt = stmt.where(Expense.spent_on >= start)
    if end:
        stmt = stmt.where(Expense.spent_on <= end)
    expenses = session.scalars(stmt).all()

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "category", "description", "amount"])
        rows = [
            (e.id, e.spent_on.isoformat(), e.category.name, e.description, f"{e.amount:.2f}")
            for e in expenses
        ]
        writer.writerows(rows)
    return len(rows)
