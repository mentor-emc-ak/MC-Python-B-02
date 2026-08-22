from datetime import date
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    budget: Mapped[Optional["Budget"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"Category(id={self.id}, name={self.name!r})"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(200), default="")
    spent_on: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped[Category] = relationship(back_populates="expenses")

    def __repr__(self) -> str:
        return (
            f"Expense(id={self.id}, amount={self.amount}, "
            f"spent_on={self.spent_on}, category={self.category.name!r})"
        )


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    monthly_limit: Mapped[float] = mapped_column(Float)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped[Category] = relationship(back_populates="budget")
