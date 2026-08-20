import time

tasks = [
    "teach python master class",
    "complete my website work"
]

for task in tasks:
    print("Current Task: ", task)
    time.sleep(5) # 5 sec
    print("Task is completed")
    print("-----------------------")
