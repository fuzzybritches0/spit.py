import sys
from pathlib import Path

file = path.split("/")[-1]
location = path.split("/")[:-1]
if location:
    location = Path("/".join(location))
    location.mkdir(parents=True, exist_ok=True)
    file = location / file
try:
    with open(file, "w") as f:
        f.write(content)
        print(f"{file} saved.")
except Exception as exception:
    print(f"ERROR: {type(exception).__name__}: {exception}")
    sys.exit(1)
