balance = 0
wrong_attempt = 0

print("Welcome to EMC ATM machine")
print("Let's set up your pin first")

while True:
    atm_pin = int(input("Create your 4 digit pin: "))

    if len(atm_pin) != 4:
        print("Pin must be exactly 4 digits, please try again...")
        continue

    confirm_pin = input("Confirm your pin: ")

    if confirm_pin != atm_pin:
        print("Pins did not match, please try again...")
        continue

    atm_pin = int(atm_pin)
    print("Your pin has been set successfully")
    break

while True:
    if wrong_attempt == 3:
        print("Your account is locked")
        break

    print("")
    print("---------------------------------\n")
    print("---------------------------------")
    print("Welcome to EMC ATM machine")
    print("1. Check Balance")
    print("2. Deposit Money")
    print("3. Withdraw Money")

    options = int(input("What do you want to do ? "))
    user_pin = int(input("Please enter your pin to continue"))

    if user_pin != atm_pin:
        print("Pin did not match, please try again...")
        wrong_attempt = wrong_attempt + 1
        continue

    if options == 1:
        print("Your balance is", balance)

    if options == 2:
        deposit_amount = int(input("How much are you going to deposit ? "))
        if deposit_amount < 0:
            print("Please enter valid amount")
            continue
        balance = balance + deposit_amount
        print(f"Here is your current balance: {balance}")
        print("Here is your current balance:", balance)

    if options == 3:
        withdraw_amount = int(input("How much are you going to deposit ? "))
        if withdraw_amount < 0:
            print("Please enter valid amount")
            continue

        if withdraw_amount > balance:
            print("Your do not have sufficient balance")
            continue
        
        balance = balance - withdraw_amount
        print("Here is your withdrawal amount, enjoy.....")
        print("Your latest balance:", balance)

