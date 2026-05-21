import os
import sys
import shutil

if not os.path.exists(path):
    print(f"ERROR: `{path}` does not exist!")
    sys.exit(1)
if os.path.isfile(path):
    try:
        os.remove(path)
        print(f"`{path}` removed.")
    except Exception as exception:
        print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
        sys.exit(1)
elif os.path.isdir(path):
    try:
        shutil.rmtree(path)
        print(f"`{path}` removed.")
    except Exception as exception:
        print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
        sys.exit(1)
