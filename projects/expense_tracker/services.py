from datetime import date
from typing import Optional, Union

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Budget, Category, Expense


class NotFoundError(Exception):
    pass


class DuplicateCategoryError(Exception):
    pass


# --- Categories ---

def add_category(session: Session, name: str) -> Category:
    existing = session.scalar(select(Category).where(Category.name == name))
    if existing:
        raise DuplicateCategoryError(f"Category {name!r} already exists")
    category = Category(name=name)
    session.add(category)
    session.commit()
    return category


def list_categories(session: Session) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)))


def rename_category(session: Session, category_id: int, new_name: str) -> Category:
    category = session.get(Category, category_id)
    if not category:
        raise NotFoundError(f"No category with id {category_id}")
    category.name = new_name
    session.commit()
    return category


def delete_category(session: Session, category_id: int) -> None:
    category = session.get(Category, category_id)
    if not category:
        raise NotFoundError(f"No category with id {category_id}")
    session.delete(category)
    session.commit()


# --- Expenses ---

def add_expense(
    session: Session,
    amount: float,
    category_id: int,
    description: str = "",
    spent_on: Optional[date] = None,
) -> Expense:
    category = session.get(Category, category_id)
    if not category:
        raise NotFoundError(f"No category with id {category_id}")
    expense = Expense(
        amount=amount,
        category_id=category_id,
        description=description,
        spent_on=spent_on or date.today(),
    )
    session.add(expense)
    session.commit()
    return expense


def get_expense(session: Session, expense_id: int) -> Expense:
    expense = session.get(Expense, expense_id)
    if not expense:
        raise NotFoundError(f"No expense with id {expense_id}")
    return expense


def list_expenses(
    session: Session,
    start: Optional[date] = None,
    end: Optional[date] = None,
    category_id: Optional[int] = None,
) -> list[Expense]:
    stmt = select(Expense).order_by(Expense.spent_on.desc(), Expense.id.desc())
    if start:
        stmt = stmt.where(Expense.spent_on >= start)
    if end:
        stmt = stmt.where(Expense.spent_on <= end)
    if category_id is not None:
        stmt = stmt.where(Expense.category_id == category_id)
    return list(session.scalars(stmt))


def update_expense(
    session: Session,
    expense_id: int,
    amount: Optional[float] = None,
    description: Optional[str] = None,
    spent_on: Optional[date] = None,
    category_id: Optional[int] = None,
) -> Expense:
    expense = get_expense(session, expense_id)
    if amount is not None:
        expense.amount = amount
    if description is not None:
        expense.description = description
    if spent_on is not None:
        expense.spent_on = spent_on
    if category_id is not None:
        if not session.get(Category, category_id):
            raise NotFoundError(f"No category with id {category_id}")
        expense.category_id = category_id
    session.commit()
    return expense


def delete_expense(session: Session, expense_id: int) -> None:
    expense = get_expense(session, expense_id)
    session.delete(expense)
    session.commit()


# --- Summaries & budgets ---

def spend_by_category(session: Session, month: Optional[str] = None) -> dict[str, float]:
    """Totals per category. `month` filters as 'YYYY-MM'."""
    stmt = (
        select(Category.name, func.coalesce(func.sum(Expense.amount), 0.0))
        .outerjoin(Expense, Expense.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    if month:
        stmt = stmt.where(func.strftime("%Y-%m", Expense.spent_on) == month)
    return {name: total for name, total in session.execute(stmt)}


def monthly_totals(session: Session, year: int) -> list[tuple[str, float]]:
    stmt = (
        select(func.strftime("%Y-%m", Expense.spent_on), func.sum(Expense.amount))
        .where(func.strftime("%Y", Expense.spent_on) == str(year))
        .group_by(func.strftime("%Y-%m", Expense.spent_on))
        .order_by(func.strftime("%Y-%m", Expense.spent_on))
    )
    return [(month, total or 0.0) for month, total in session.execute(stmt)]


def set_budget(session: Session, category_id: int, monthly_limit: float) -> Budget:
    category = session.get(Category, category_id)
    if not category:
        raise NotFoundError(f"No category with id {category_id}")
    # query rather than category.budget: a Budget created elsewhere in the
    # session doesn't refresh the parent's relationship attribute
    budget = session.scalar(select(Budget).where(Budget.category_id == category_id))
    if budget:
        budget.monthly_limit = monthly_limit
    else:
        budget = Budget(category_id=category_id, monthly_limit=monthly_limit)
        session.add(budget)
    session.commit()
    return budget


def budget_status(session: Session, month: str) -> list[dict]:
    """Per-budgeted-category: limit, spent and remaining for the given 'YYYY-MM'."""
    statuses = []
    for budget in session.scalars(select(Budget)):
        spent = session.scalar(
            select(func.sum(Expense.amount)).where(
                Expense.category_id == budget.category_id,
                func.strftime("%Y-%m", Expense.spent_on) == month,
            )
        )
        spent = spent or 0.0
        statuses.append(
            {
                "category": budget.category.name,
                "limit": budget.monthly_limit,
                "spent": spent,
                "remaining": budget.monthly_limit - spent,
            }
        )
    return statuses


def over_budget_categories(session: Session, month: str) -> list[dict]:
    return [s for s in budget_status(session, month) if s["remaining"] < 0]
