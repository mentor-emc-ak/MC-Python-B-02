from sqlalchemy import Column, Integer, String
from sqlalchemy.ext import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    age = Column(Integer, nullable=False)
