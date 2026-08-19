import csv

students = [
    ["name", "age", "grade"],
    ["Akhshy", 9, "A"],
    ["Nandha", 14, "A"],
    ["Suresh", 12, "C"]
]

with open("students.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerows(students)

with open("students.csv", "r", newline="") as file:
    reader = csv.reader(file)
    for row in reader:
        print(row)
