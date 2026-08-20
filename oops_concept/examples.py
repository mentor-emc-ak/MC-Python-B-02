# Classes

# class Student:
#     pass

# print("Hello World ")


# class Car:
#     def start_engine(self):
#         print("Car Engine Started")


# class Calculator:
#     def add(self, a, b):
#         return a + b

#     def sub(self, a, b):
#         return a - b

# Objects

# class Student:
#     def greetings(self):
#         print("Hello World !!")

# student1 = Student()
# student2 = Student()

# student1.greetings()
# student2.greetings()


# Attributes

# class Student:
#     def __init__(self, fname, lname):
#         self.fname = fname
#         self.lname = lname
#         print("Hello this is a constructor")

#     def greetings(self):
#         print("Greetings from", self.fname)

#     def full_name(self):
#         print(self.fname, self.lname)

#     def update_name(self, fname, lname):
#         self.fname = fname
#         self.lname = lname


# student1 = Student("Akhshy", "Ganesh")
# student1.greetings()

# student2 = Student("Suresh", "Edward")
# student2.greetings()


# student1.full_name()
# student2.full_name()

# student1.update_name("Agalya", "G")

# student1.full_name()



# Abstraction Class

# from abc import ABC

# class Human():
#     def __init__(self, fname, lname, age, gender, blood_group, phone_number):
#         self.fname = fname
#         self.lname = lname
#         self.age = age
#         self.gender = gender
#         self.blood_group = blood_group
#         self.phone_number = phone_number

#     def full_name(self):
#         print(self.fname, self.lname)


# class Customer(Human):

#     def role(self):
#         print(f"Hello, I am a {self.fname}, a customer of your company")

# class Employee(Human):

#     def role(self):
#         print(f"Hello, I am a {self.fname}, a employee of your company")

# customer = Customer("Agalya", "G", 12, "female", "o+", 9087991886)
# employee = Employee("Suresh", "Edward", 20, "male", "o-", 9087991886)

# customer.role()
# employee.role()

# customer.full_name()
# employee.full_name()



import random


class Human():

    def __init__(self, fname, lname, age, gender, blood_group, phone_number):
        self.id = random.randint(1000, 9999)
        self.fname = fname
        self.lname = lname
        self.age = age
        self.gender = gender
        self.blood_group = blood_group
        self.phone_number = phone_number

    def full_name(self):
        print(self.fname, self.lname)


class Customer(Human):

    def role(self):
        print(f"Hello, I am a {self.fname}, a customer of your company")

class Employee(Human):

    def role(self):
        print(f"Hello, I am a {self.fname}, a employee of your company")

def add_customer():
    fname = input("Enter your first name: ")
    lname = input("Enter your last name: ")
    age = int(input("Enter your age: "))
    gender = input("Enter your gender: ")
    blood_group = input("Enter your blood group: ")
    phone_number = input("Enter your phone number: ")
    return Customer(fname, lname, age, gender, blood_group, phone_number)

def add_employee():
    fname = input("Enter your first name: ")
    lname = input("Enter your last name: ")
    age = int(input("Enter your age: "))
    gender = input("Enter your gender: ")
    blood_group = input("Enter your blood group: ")
    phone_number = input("Enter your phone number: ")
    return Employee(fname, lname, age, gender, blood_group, phone_number)

def delete_customer(customers, customer_id):
    for customer in customers:
        if customer.id == customer_id:
            customers.remove(customer)
            print(f"Customer {customer.fname} with ID {customer.id} deleted successfully.")
            return
    print(f"No customer found with ID {customer_id}.")

def delete_employee(employees, employee_id):
    for employee in employees:
        if employee.id == employee_id:
            employees.remove(employee)
            print(f"Employee {employee.fname} with ID {employee.id} deleted successfully.")
            return
    print(f"No employee found with ID {employee_id}.")

def main():
    customers = []
    employees = []

    while True:
        print("\n1. Add Customer")
        print("2. Add Employee")
        print("3. Show Customers")
        print("4. Show Employees")
        print("5. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            customer = add_customer()
            customers.append(customer)
            print(f"Customer {customer.fname} added successfully with ID {customer.id}.")
        elif choice == '2':
            employee = add_employee()
            employees.append(employee)
            print(f"Employee {employee.fname} added successfully with ID {employee.id}.")
        elif choice == '3':
            print("\nCustomers:")
            for customer in customers:
                customer.full_name()
                customer.role()
        elif choice == '4':
            print("\nEmployees:")
            for employee in employees:
                employee.full_name()
                employee.role()
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")


main()
