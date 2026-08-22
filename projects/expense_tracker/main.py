from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from . import services
from .db import make_session_factory
from .export import export_expenses


def prompt_amount(label: str = "Amount") -> float:
    while True:
        raw = input(f"{label}: ").strip()
        try:
            value = float(raw)
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Enter a positive number, e.g. 12.50")


def prompt_date(label: str = "Date (YYYY-MM-DD, blank = today)") -> date:
    while True:
        raw = input(f"{label}: ").strip()
        if not raw:
            return date.today()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("Use the format YYYY-MM-DD, e.g. 2026-08-22")


def prompt_int(label: str) -> Optional[int]:
    raw = input(label).strip()
    if not raw:
        return None
    return int(raw)


def choose_category(session: Session) -> Optional[int]:
    categories = services.list_categories(session)
    if not categories:
        print("No categories yet — add one first.")
        return None
    for category in categories:
        budget_note = ""
        if category.budget:
            budget_note = f" (budget {category.budget.monthly_limit:.2f}/month)"
        print(f"  [{category.id}] {category.name}{budget_note}")
    return prompt_int("Category id: ")


def warn_over_budget(session: Session, spent_on: date) -> None:
    month = spent_on.strftime("%Y-%m")
    over = services.over_budget_categories(session, month)
    for status in over:
        print(
            f"WARNING: '{status['category']}' is over budget for {month} "
            f"(spent {status['spent']:.2f} of {status['limit']:.2f})"
        )


def add_expense_flow(session: Session) -> None:
    category_id = choose_category(session)
    if category_id is None:
        return
    amount = prompt_amount()
    description = input("Description (optional): ").strip()
    spent_on = prompt_date()
    expense = services.add_expense(
        session,
        amount=amount,
        category_id=category_id,
        description=description,
        spent_on=spent_on,
    )
    print(f"Added expense #{expense.id}")
    warn_over_budget(session, expense.spent_on)


def show_expense(expense) -> None:
    print(
        f"  #{expense.id:<4} {expense.spent_on} "
        f"{expense.category.name:<15} {expense.amount:>10.2f}  {expense.description}"
    )


def list_expenses_flow(session: Session) -> None:
    use_filters = input("Filter? [y/N]: ").strip().lower() == "y"
    start = end = None
    category_id = None
    if use_filters:
        start = prompt_date("Start date (YYYY-MM-DD, blank = none)")
        end = prompt_date("End date (YYYY-MM-DD, blank = none)")
        category_id = choose_category(session)
    expenses = services.list_expenses(session, start=start, end=end, category_id=category_id)
    if not expenses:
        print("No expenses found.")
        return
    total = 0.0
    for expense in expenses:
        show_expense(expense)
        total += expense.amount
    print(f"  {len(expenses)} expense(s), total {total:.2f}")


def update_expense_flow(session: Session) -> None:
    expense_id = prompt_int("Expense id to update: ")
    if expense_id is None:
        return
    try:
        expense = services.get_expense(session, expense_id)
    except services.NotFoundError as exc:
        print(exc)
        return
    print("Leave a field blank to keep it unchanged.")
    show_expense(expense)

    raw = input(f"Amount [{expense.amount}]: ").strip()
    amount = float(raw) if raw else None
    raw = input(f"Description [{expense.description}]: ").strip()
    description = raw or None
    raw = input(f"Date YYYY-MM-DD [{expense.spent_on}]: ").strip()
    spent_on = (
        datetime.strptime(raw, "%Y-%m-%d").date() if raw else None
    )
    category_id = choose_category(session) if input("Change category? [y/N]: ").strip().lower() == "y" else None

    updated = services.update_expense(
        session,
        expense_id,
        amount=amount,
        description=description,
        spent_on=spent_on,
        category_id=category_id,
    )
    print("Updated:")
    show_expense(updated)
    warn_over_budget(session, updated.spent_on)


def delete_expense_flow(session: Session) -> None:
    expense_id = prompt_int("Expense id to delete: ")
    if expense_id is None:
        return
    try:
        services.delete_expense(session, expense_id)
    except services.NotFoundError as exc:
        print(exc)
        return
    print(f"Deleted expense #{expense_id}")


def categories_menu(session: Session) -> None:
    while True:
        print("\n--- Categories ---")
        print("  1) List   2) Add   3) Rename   4) Delete   0) Back")
        choice = input("> ").strip()
        if choice == "0":
            return
        elif choice == "1":
            categories = services.list_categories(session)
            if not categories:
                print("No categories yet.")
            for category in categories:
                print(f"  [{category.id}] {category.name}")
        elif choice == "2":
            name = input("Category name: ").strip()
            if not name:
                print("Name cannot be empty.")
                continue
            try:
                category = services.add_category(session, name)
            except services.DuplicateCategoryError as exc:
                print(exc)
                continue
            print(f"Added category [{category.id}] {category.name}")
        elif choice == "3":
            category_id = prompt_int("Category id to rename: ")
            new_name = input("New name: ").strip()
            try:
                services.rename_category(session, category_id, new_name)
                print("Renamed.")
            except services.NotFoundError as exc:
                print(exc)
        elif choice == "4":
            category_id = prompt_int("Category id to delete: ")
            confirm = input("This deletes its expenses too. Confirm? [y/N]: ")
            if confirm.strip().lower() != "y":
                print("Cancelled.")
                continue
            try:
                services.delete_category(session, category_id)
                print("Deleted.")
            except services.NotFoundError as exc:
                print(exc)
        else:
            print("Unknown option.")


def budgets_menu(session: Session) -> None:
    while True:
        print("\n--- Budgets ---")
        print("  1) Set/update budget   2) Show status   0) Back")
        choice = input("> ").strip()
        if choice == "0":
            return
        elif choice == "1":
            category_id = choose_category(session)
            if category_id is None:
                continue
            limit = prompt_amount("Monthly limit")
            services.set_budget(session, category_id, limit)
            print("Budget saved.")
        elif choice == "2":
            month = input("Month YYYY-MM (blank = current): ").strip()
            if not month:
                month = date.today().strftime("%Y-%m")
            statuses = services.budget_status(session, month)
            if not statuses:
                print("No budgets set yet.")
            for status in statuses:
                marker = "OVER!" if status["remaining"] < 0 else "ok"
                print(
                    f"  {status['category']:<15} {status['spent']:>10.2f} / "
                    f"{status['limit']:>10.2f}  remaining {status['remaining']:>10.2f}  [{marker}]"
                )
        else:
            print("Unknown option.")


def bar(value: float, max_value: float, width: int = 30) -> str:
    if max_value <= 0:
        return ""
    filled = round(value / max_value * width)
    return "#" * filled


def reports_menu(session: Session) -> None:
    while True:
        print("\n--- Summaries & Reports ---")
        print("  1) Spend by category (a month)   2) Monthly totals (a year)   0) Back")
        choice = input("> ").strip()
        if choice == "0":
            return
        elif choice == "1":
            month = input("Month YYYY-MM (blank = current): ").strip()
            if not month:
                month = date.today().strftime("%Y-%m")
            totals = services.spend_by_category(session, month=month)
            totals = {name: total for name, total in totals.items() if total > 0}
            if not totals:
                print(f"No spending recorded for {month}.")
                continue
            biggest = max(totals.values())
            grand = sum(totals.values())
            print(f"\nSpend by category — {month}  (total {grand:.2f})")
            for name, total in sorted(totals.items(), key=lambda kv: -kv[1]):
                pct = total / grand * 100
                print(f"  {name:<15} {total:>10.2f} {pct:>5.1f}%  {bar(total, biggest)}")
        elif choice == "2":
            year = prompt_int("Year (blank = current): ")
            year = year or date.today().year
            rows = services.monthly_totals(session, year)
            if not rows:
                print(f"No spending recorded in {year}.")
                continue
            biggest = max(total for _, total in rows)
            print(f"\nMonthly totals — {year}")
            for month, total in rows:
                print(f"  {month}  {total:>10.2f}  {bar(total, biggest)}")
        else:
            print("Unknown option.")


def export_flow(session: Session) -> None:
    path = input("Output CSV path (blank = expenses.csv): ").strip() or "expenses.csv"
    count = export_expenses(session, path)
    print(f"Exported {count} expense(s) to {path}")


MENU = """
=== Expense Tracker ===
  1) Add expense
  2) List expenses
  3) Update expense
  4) Delete expense
  5) Categories
  6) Budgets
  7) Summaries & reports
  8) Export CSV
  0) Quit
"""


def main(db_path=None) -> None:
    session_factory = make_session_factory(db_path)
    session = session_factory()
    actions = {
        "1": add_expense_flow,
        "2": list_expenses_flow,
        "3": update_expense_flow,
        "4": delete_expense_flow,
        "5": categories_menu,
        "6": budgets_menu,
        "7": reports_menu,
        "8": export_flow,
    }
    try:
        while True:
            print(MENU)
            choice = input("> ").strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if action is None:
                print("Unknown option.")
                continue
            try:
                action(session)
            except (services.NotFoundError, services.DuplicateCategoryError) as exc:
                print(f"Error: {exc}")
            except KeyboardInterrupt:
                print("\n(cancelled)")
    finally:
        session.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()
