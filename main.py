# x = 1 # integer
# greetings = "Hello World !" # string
# is_present =  True # Boolean
# students = ['edward', 'nalina', 'rahman', 1, False, True, 3.22] # list
#             #  0.        1.       2.      3.   4.    5.
# my_details = {"name": "akhshy", "is_mentor": True} # dict
#             #   key     value       key       value
# # commented lines / commented word
# '''this is also commented line'''

# print(type(greetings)) # output
# print(type(x))
# print(type(students[4]))
# print(type(my_details['name']))
# print(type(1.11111))

# user_name = input("Hello what is your name ? ")
# user_age = int(input("May I know your age ? "))
# movie_ticket_rate = input("How much did you spend for spiderman ")

# print(type(user_name))
# print(type(user_age))

# movie_ticket_rate = float(movie_ticket_rate)

# print("Hello", user_name, " !")
# print("You're ", user_age, "years old")
# print("You have spent", movie_ticket_rate, "rupees on movie")



# Comparison Operators

# a = 10
# b = 5

# print(a + b)
# print(a - b)
# print(a * b)
# print(a / b)
# print(a % b)
# print(a ** b)
# print(a < b)
# print(a > b)
# print(a == b)

# x = 2
# y = 2

# print(x <= y)
# print(x >= y)
# print(x != y)


# Logical Operators
# and
# or
# not

# print(True and True)
# print(False and True)
# print(True and False)
# print(False and False)


# print(True or True)
# print(False or True)
# print(True or False)
# print(False or False)


# print(not True)
# print(not False)


# num1 = int(input("Enter first number: ")) # 10
# num2 = int(input("Enter second number: ")) # 20

# print(num1 + num2)

# age = int(input("What is your age ?"))

# if age >= 18:
#     print("Adult")
# else:
#     print("Minor")


# user_input = int(input("Enter a number, I will find if it is even / odd"))

# print(user_input % 2)

# if user_input % 2 == 0:
#     print("Even")
# else:
#     print("Odd")


# x = 0
# print(type(x))

# print(bool(x))


# while True:
#     username = input("Enter username: ")
#     password = input("Enter password: ")

#     if username == 'admin':
#         print("Trying to login into admin account")
#         if password == 'admin@123':
#             print("Logged into Admin account")
#             break
#         else:
#             print("Wrong password")

#     elif username == 'user' and password == 'user@123':
#         print("Logged into User account")
#     elif username == 'staff' and password == 'staff@123':
#         print("Logged into Staff account")
#     else:
#         print("login failed")

# for i in range(6):
# for i in [1, 2, 3, 4, 5]:
#     if i == 0:
#         print("within the i == 0 condition")
#         continue

#     print("Try #", i)
#     print("---------------------------------")
#     username = input("Enter username: ")
#     password = input("Enter password: ")

#     if username == 'admin':
#         print("Trying to login into admin account")
#         if password == 'admin@123':
#             print("Logged into Admin account")
#             break
#         else:
#             print("Wrong password")

#     elif username == 'user' and password == 'user@123':
#         print("Logged into User account")
#     elif username == 'staff' and password == 'staff@123':
#         print("Logged into Staff account")
#     else:
#         print("login failed")

#     print("---------------------------------")
#     print("---------------------------------")



# print(list(range(6)))




# name = "akhshy"

# for i in name:
#     print(i)



# while True:
#     no_of_pedestrians = int(input("enter number of pedestrians : "))
#     current_time = int(input("railway time only hours"))

#     if current_time > 24:
#         print("invalid time...")
#         continue

#     if current_time > 20 or current_time < 6:
#         print("signal is off, take care of yourself")
#         continue

#     signal = "green"

#     if no_of_pedestrians > 0:
#         signal = "red"

#     if signal == "red":
#         print("pedestrians can walk")
#     else:
#         print("cars are moving")






























