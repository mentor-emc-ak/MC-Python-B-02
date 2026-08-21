import sqlite3

connection = sqlite3.connect("mydatabase.db")
cursor = connection.cursor()


def create_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER
    )
    """)


def create_user(name, age):
    cursor.execute("INSERT INTO users (name, age) VALUES (?, ?)", (name, age))
    connection.commit()

def read_users():
    cursor.execute("SELECT * FROM users")
    # User.query.all()
    return cursor.fetchall()

def read_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

def update_user(user_id, name, age):
    cursor.execute("UPDATE users SET name = ?, age = ? WHERE id = ?", (name, age, user_id))
    connection.commit()

def update_user_by_name(user_name, age):
    cursor.execute("UPDATE users SET age = ? WHERE name = ?", (age, user_name))
    connection.commit()

def delete_user(user_id):
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    connection.commit()

def read_all_teenager():
    cursor.execute("SELECT * FROM users WHERE age >= 13 AND age < 18")
    return cursor.fetchall()


connection.close()
