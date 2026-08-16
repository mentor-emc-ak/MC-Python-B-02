# Computer will choose a wining number
# We have guess it, helper number computer should 
# help us saying "go higher" or "go lower"

import random

game_number = random.randint(1, 100)
attempts = 0

while True:
    print("Lets begin... !!")
    user_number = int(input("Enter your guessing number... "))
    attempts = attempts + 1

    if user_number > game_number:
        print("Go lower...")
    elif user_number < game_number:
        print("Go higher")
    else:
        print("You found the correct number, attempts:", attempts)
        break



