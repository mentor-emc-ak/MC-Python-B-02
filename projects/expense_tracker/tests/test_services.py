import csv
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .. import services
from ..export import export_expenses
from ..models import Base


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    yield s
    s.close()


def make_category(session, name="Food"):
    return services.add_category(session, name)


class TestCategories:
    def test_add_and_list(self, session):
        cat = make_category(session)
        assert cat.id is not None
        assert [c.name for c in services.list_categories(session)] == ["Food"]

    def test_duplicate_raises(self, session):
        make_category(session)
        with pytest.raises(services.DuplicateCategoryError):
            make_category(session)

    def test_rename(self, session):
        cat = make_category(session)
        renamed = services.rename_category(session, cat.id, "Groceries")
        assert renamed.name == "Groceries"

    def test_rename_missing(self, session):
        with pytest.raises(services.NotFoundError):
            services.rename_category(session, 999, "Nope")

    def test_delete_cascades_expenses(self, session):
        cat = make_category(session)
        services.add_expense(session, 10.0, cat.id)
        services.delete_category(session, cat.id)
        assert services.list_categories(session) == []
        assert services.list_expenses(session) == []


class TestExpenses:
    def test_add_defaults_to_today(self, session):
        cat = make_category(session)
        expense = services.add_expense(session, 12.5, cat.id, "lunch")
        assert expense.amount == 12.5
        assert expense.spent_on == date.today()
        assert expense.category.name == "Food"

    def test_add_unknown_category(self, session):
        with pytest.raises(services.NotFoundError):
            services.add_expense(session, 10.0, 999)

    def test_update_partial_fields(self, session):
        cat = make_category(session)
        other = services.add_category(session, "Travel")
        expense = services.add_expense(session, 10.0, cat.id, "snack")
        updated = services.update_expense(
            session, expense.id, amount=15.0, category_id=other.id
        )
        assert updated.amount == 15.0
        assert updated.description == "snack"
        assert updated.category.name == "Travel"

    def test_update_missing(self, session):
        with pytest.raises(services.NotFoundError):
            services.update_expense(session, 42, amount=1.0)

    def test_delete(self, session):
        cat = make_category(session)
        expense = services.add_expense(session, 5.0, cat.id)
        services.delete_expense(session, expense.id)
        assert services.list_expenses(session) == []

    def test_list_filters_by_date_range(self, session):
        cat = make_category(session)
        services.add_expense(session, 1.0, cat.id, spent_on=date(2026, 7, 1))
        services.add_expense(session, 2.0, cat.id, spent_on=date(2026, 8, 15))
        services.add_expense(session, 4.0, cat.id, spent_on=date(2026, 9, 30))

        rows = services.list_expenses(
            session, start=date(2026, 7, 31), end=date(2026, 9, 1)
        )
        assert [r.amount for r in rows] == [2.0]

    def test_list_filter_by_category(self, session):
        food = make_category(session)
        travel = services.add_category(session, "Travel")
        services.add_expense(session, 1.0, food.id)
        services.add_expense(session, 2.0, travel.id)
        rows = services.list_expenses(session, category_id=travel.id)
        assert [r.category_id for r in rows] == [travel.id]


class TestSummaries:
    def seed(self, session):
        food = services.add_category(session, "Food")
        fun = services.add_category(session, "Fun")
        services.add_expense(session, 10.0, food.id, spent_on=date(2026, 7, 2))
        services.add_expense(session, 5.0, food.id, spent_on=date(2026, 8, 3))
        services.add_expense(session, 20.0, fun.id, spent_on=date(2026, 8, 9))
        return food, fun

    def test_spend_by_category_all_time(self, session):
        self.seed(session)
        totals = services.spend_by_category(session)
        assert totals == {"Food": 15.0, "Fun": 20.0}

    def test_spend_by_category_month_filter(self, session):
        self.seed(session)
        totals = services.spend_by_category(session, month="2026-08")
        assert totals == {"Food": 5.0, "Fun": 20.0}

    def test_monthly_totals(self, session):
        self.seed(session)
        rows = services.monthly_totals(session, 2026)
        assert rows == [("2026-07", 10.0), ("2026-08", 25.0)]


class TestBudgets:
    def test_set_then_update_budget(self, session):
        cat = make_category(session)
        budget = services.set_budget(session, cat.id, 100.0)
        assert budget.monthly_limit == 100.0
        again = services.set_budget(session, cat.id, 250.0)
        assert again.monthly_limit == 250.0
        assert again.id == budget.id

    def test_set_budget_unknown_category(self, session):
        with pytest.raises(services.NotFoundError):
            services.set_budget(session, 123, 50.0)

    def test_budget_status_and_over_budget(self, session):
        cat = make_category(session)
        services.set_budget(session, cat.id, 40.0)
        services.add_expense(session, 25.0, cat.id, spent_on=date(2026, 8, 1))
        services.add_expense(session, 20.0, cat.id, spent_on=date(2026, 8, 2))

        status = services.budget_status(session, "2026-08")[0]
        assert status["spent"] == 45.0
        assert status["remaining"] == -5.0
        over = services.over_budget_categories(session, "2026-08")
        assert len(over) == 1 and over[0]["category"] == "Food"

        assert services.over_budget_categories(session, "2026-07") == []


class TestExport:
    def test_export_writes_csv(self, session, tmp_path):
        cat = make_category(session)
        services.add_expense(
            session, 7.25, cat.id, description="coffee", spent_on=date(2026, 8, 1)
        )
        path = tmp_path / "out.csv"
        count = export_expenses(session, str(path))
        assert count == 1

        with open(path) as f:
            rows = list(csv.reader(f))
        assert rows[0] == ["id", "date", "category", "description", "amount"]
        assert rows[1][2] == "Food"
        assert rows[1][4] == "7.25"

    def test_export_respects_range(self, session, tmp_path):
        cat = make_category(session)
        services.add_expense(session, 1.0, cat.id, spent_on=date(2026, 7, 1))
        services.add_expense(session, 2.0, cat.id, spent_on=date(2026, 8, 1))
        path = tmp_path / "out.csv"
        count = export_expenses(
            session, str(path), start=date(2026, 8, 1), end=date(2026, 8, 31)
        )
        assert count == 1
