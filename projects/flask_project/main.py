from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)

with app.app_context():
    db.create_all()

    # Create a new user
    user = User(name='Alice', age=30)
    db.session.add(user)
    db.session.commit()

    # Retrieve all users
    users = User.query.all()
    for user in users:
        print(f"User: {user.name}, Age: {user.age}")

    # Update a user's age
    user_to_update = User.query.filter_by(name='Alice').first()
    if user_to_update:
        user_to_update.age = 31
        db.session.commit()
        print(f"Updated user: {user_to_update.name}, New Age: {user_to_update.age}")

    # Delete a user
    user_to_delete = User.query.filter_by(name='Alice').first()
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        print(f"Deleted user: {user_to_delete.name}")
