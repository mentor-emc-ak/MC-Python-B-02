from sqlalchemy import select

from database import SessionLocal
from model import User

def create_user(name: str, age: int):
    session = SessionLocal()
    new_user = User(name=name, age=age)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    session.close()
    return new_user

def get_user_by_name(name: str):
    session = SessionLocal()
    stmt = select(User).where(User.name == name)
    user = session.execute(stmt).scalar_one_or_none()
    session.close()
    return user

def get_users():
    session = SessionLocal()
    stmt = select(User)
    users = session.execute(stmt).scalars().all()
    session.close()
    return users

def update_user_age(name: str, new_age: int):
    session = SessionLocal()
    stmt = select(User).where(User.name == name)
    user = session.execute(stmt).scalar_one_or_none()
    if user:
        user.age = new_age
        session.commit()
        session.refresh(user)
    session.close()
    return user

def delete_user(name: str):
    session = SessionLocal()
    stmt = select(User).where(User.name == name)
    user = session.execute(stmt).scalar_one_or_none()
    if user:
        session.delete(user)
        session.commit()
    session.close()
    return user

