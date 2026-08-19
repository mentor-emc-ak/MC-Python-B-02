import time
from datetime import datetime

reminders = []

print("=== Multi-Reminder Application ===")
print("Add reminders anytime. Press Ctrl+C to exit.\n")

while True:
    current_time = datetime.now().strftime("%H:%M")
    
    # Check for triggered reminders
    for reminder in reminders[:]:
        message, reminder_time = reminder
        if current_time == reminder_time:
            print(f"\n🔔 REMINDER: {message} (Time: {reminder_time})")
            reminders.remove(reminder)
    
    # Prompt to add new reminder
    message = input("Enter reminder message: ")
    time_input = input("Enter time (HH:MM): ")
    
    reminders.append((message, time_input))
    print(f"Added: '{message}' at {time_input}\n")
    time.sleep(1)
