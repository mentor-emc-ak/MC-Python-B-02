import sys

def main():
    """
    Demonstrates command-line argument handling using sys.argv.
    Usage: python example_args.py <name>
    If no name is provided, prints usage and exits with status 1.
    """
    if len(sys.argv) < 2:
        print("Usage: python example_args.py <name>")
        sys.exit(1)

    name = sys.argv[1]
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()
