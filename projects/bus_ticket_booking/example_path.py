import sys

def main():
    """
    Prints the list of directories where Python searches for modules.
    This helps debug module import issues or understand Python's path resolution.
    """
    print("Python module search paths:")
    for path in sys.path:
        print(f"  - {path}")

if __name__ == "__main__":
    main()
