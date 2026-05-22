import sys
import os
import stat
import pwd
import grp
from pathlib import Path
from datetime import datetime

def human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.1f} {units[unit_index]}"

def get_owner_group(stat_result):
    try:
        owner = pwd.getpwuid(stat_result.st_uid).pw_name
    except KeyError:
        owner = str(stat_result.st_uid)
    try:
        group = grp.getgrgid(stat_result.st_gid).gr_name
    except KeyError:
        group = str(stat_result.st_gid)
    return owner, group

def get_file_type(stat_result):
    mode = stat_result.st_mode
    if stat.S_ISBLK(mode):
        return "block"
    elif stat.S_ISCHR(mode):
        return "char"
    elif stat.S_ISFIFO(mode):
        return "fifo"
    elif stat.S_ISSOCK(mode):
        return "socket"
    elif stat.S_ISLNK(mode):
        return "link"
    elif stat.S_ISREG(mode):
        return "file"
    elif stat.S_ISDIR(mode):
        return "dir"
    else:
        return "unknown"

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    if not path.is_dir():
        print(f"ERROR: Path is not a directory: `{path}`")
        sys.exit(1)
    print(f"Directory listing for: `{path}`")
    print("\n")
    if recursive:
        print("| Path | Size | Type | Owner | Modified |")
    else:
        print("| Name | Size | Type | Owner | Modified |")
    print("|------|------|------|-------|----------|")
    entries = []
    if recursive:
        for root, dirs, files in os.walk(path):
            if not show_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            for d in dirs:
                dir_path = Path(root) / d
                entries.append((dir_path, True))
            for f in files:
                file_path = Path(root) / f
                entries.append((file_path, False))
    else:
        for entry in path.iterdir():
            if not show_hidden and entry.name.startswith('.'):
                continue
            entries.append((entry, entry.is_dir()))
    entries.sort(key=lambda x: (not x[1], x[0].name.lower()))
    max_results = max(1, min(10000, max_results))
    count = len(entries)
    note = False
    if count > max_results:
        entries = entries[0:max_results]
        note = True
    for entry, is_dir in entries:
        try:
            stat_result = entry.stat()
            size = stat_result.st_size
            mtime = datetime.fromtimestamp(stat_result.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            perms = oct(stat_result.st_mode)[-3:]
            is_symlink = entry.is_symlink()
            owner, group = get_owner_group(stat_result)
            file_type = get_file_type(stat_result)
            try:
                relative_path = entry.relative_to(path)
            except ValueError:
                relative_path = entry.name
            if is_dir:
                name = str(relative_path) + "/"
                size_str = "<DIR>"
            else:
                name = str(relative_path)
                size_str = human_readable_size(size)
            type_str = file_type
            if is_symlink:
                type_str += " @ "
                try:
                    target = entry.resolve()
                    if target.exists():
                        type_str += f"-> {target}"
                    else:
                        type_str += "-> broken"
                except:
                    type_str += "-> ?"
            print(f"| {name} | {size_str} | {type_str} | {owner}:{group} | {mtime} |")
        except PermissionError:
            name = str(entry.relative_to(path)) if not entry.is_dir() else str(entry.relative_to(path)) + "/"
            if entry.is_dir():
                name = str(entry.relative_to(path)) + "/"
            print(f"| {name} | <DENIED> | | | |")
        except Exception as e:
            name = str(entry.relative_to(path)) if not entry.is_dir() else str(entry.relative_to(path)) + "/"
            if entry.is_dir():
                name = str(entry.relative_to(path)) + "/"
            print(f"| {name} | <ERROR> | | | |")
    print(f"\nTotal entries: {len(entries)}")
    if note:
        print(f"\nNOTE: Showing `{max_results}` of `{count}` entries (use `max_results={count}` for all)")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
