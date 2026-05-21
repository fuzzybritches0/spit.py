import sys

try:
    with open(path, "r") as f:
        print(f.read())
except Exception as exception:
    print(f"ERROR: {type(exception).__name__}: {exception}")
    sys.exit(1)
