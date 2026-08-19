import os

# with open("README.md", "r") as file:
#     content = file.read()
#     print(content)

# with open("README.md", "w") as file:
#     file.write("Hello, Python\n")
#     file.write("This is another line added from script")

# with open("README.md", "a") as file:
#     file.write("\n New line that gets added")
#     file.write("\n This is another line added from script")


folder = os.listdir("./mini_project_1")

for filename in folder:
    print(filename)

if os.path.exists("example.py"):
    print("File exists")
try:
    os.rename("example.py", "another_example.py")
except FileNotFoundError:
    print("File not found")
