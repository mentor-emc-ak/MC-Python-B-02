import time
from datetime import datetime

alarm_time = input("What time should the alarm ring ? ")

print("Alarm is set :", alarm_time)

while True:
    current_time = datetime.now().strftime("%H:%M")
    if current_time == alarm_time:
        print("Wake up! It's time!")
        break
    time.sleep(1)

