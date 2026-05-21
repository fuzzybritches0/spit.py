import sys
from pathlib import Path

if append and prepend_newline:
    content = "\n" + content
file = path.split("/")[-1]
location = path.split("/")[:-1]
if location:
    location = Path("/".join(location))
    location.mkdir(parents=create_dirs, exist_ok=True)
    file = location / file
mode = "a" if append else "w"
try:
    with open(file, mode) as f:
        f.write(content)
        if mode == "a":
            print(f"`content` appended to `{file}`.")
        else:
            print(f"`content` saved to `{file}`.")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
