from sqlalchemy import select

from database import SessionLocal
from model import User
from projects.python_orm_project.crud import create_user, delete_user, get_user_by_name, get_users, update_user_age

def main():

    print("Creating a new user...")
    new_user = create_user("Alice", 30)
    print(f"Created user: {new_user.name}, Age: {new_user.age}")

    print("\nRetrieving user by name...")
    user = get_user_by_name("Alice")
    if user:
        print(f"Retrieved user: {user.name}, Age: {user.age}")
        
    while True:
        print("\nOptions:")
        print("1. Create a new user")
        print("2. Get user by name")
        print("3. Get all users")
        print("4. Update user age")
        print("5. Delete user")
        print("6. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            name = input("Enter name: ")
            age = int(input("Enter age: "))
            new_user = create_user(name, age)
            print(f"Created user: {new_user.name}, Age: {new_user.age}")

        elif choice == "2":
            name = input("Enter name to retrieve: ")
            user = get_user_by_name(name)
            if user:
                print(f"Retrieved user: {user.name}, Age: {user.age}")
            else:
                print("User not found.")

        elif choice == "3":
            users = get_users()
            if users:
                for user in users:
                    print(f"User: {user.name}, Age: {user.age}")
            else:
                print("No users found.")

        elif choice == "4":
            name = input("Enter name of the user to update: ")
            new_age = int(input("Enter new age: "))
            updated_user = update_user_age(name, new_age)
            if updated_user:
                print(f"Updated user: {updated_user.name}, New Age: {updated_user.age}")
            else:
                print("User not found.")

        elif choice == "5":
            name = input("Enter name of the user to delete: ")
            deleted_user = delete_user(name)
            if deleted_user:
                print(f"Deleted user: {deleted_user.name}")
            else:
                print("User not found.")

        elif choice == "6":
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")


