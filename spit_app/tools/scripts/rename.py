import os
import sys
import shutil

def err(message):
    print(f"ERROR: {message}")
    sys.exit(1)

def describe(source, is_link, is_directory):
    if is_link:
        return "symlink"
    if is_directory:
        return "directory"
    return "file"

try:
    if not old_path or not new_path:
        err("`old_path` and `new_path` are both required and must not be empty.")
    source = str(old_path)
    target = str(new_path)
    if not os.path.lexists(source):
        err(f"Source does not exist: `{source}`")
    if os.path.abspath(source) == os.path.abspath(target):
        err("`old_path` and `new_path` name the same path.")
    if os.path.lexists(target):
        err(f"Target already exists: `{target}` - rename never overwrites.")
    is_link = os.path.islink(source)
    is_directory = not is_link and os.path.isdir(source)
    if is_directory:
        source_abs = os.path.abspath(source)
        target_abs = os.path.abspath(target)
        if target_abs == source_abs or target_abs.startswith(source_abs + os.sep):
            err(f"Cannot move a directory into itself: `{target}` is inside `{source}`.")
    target_parent = os.path.dirname(os.path.abspath(target))
    if not os.path.isdir(target_parent):
        err(f"Target directory does not exist: `{target_parent}` - create it first (e.g. `mkdir -p` via run_command).")
    kind = describe(source, is_link, is_directory)
    if dry_run:
        print("DRY RUN: nothing moved.")
        print(f"Would rename {kind} `{source}` to `{target}`.")
    else:
        # os.rename first (atomic on the same filesystem); shutil.move adds
        # the cross-filesystem fallback but never rewrites content either way
        try:
            shutil.move(source, target)
        except OSError as exception:
            err(f"Rename failed: `{type(exception).__name__}: {exception}`")
        print(f"Renamed {kind} `{source}` to `{target}`.")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
