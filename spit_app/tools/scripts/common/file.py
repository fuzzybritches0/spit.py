import json
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
        return "block_device"
    elif stat.S_ISCHR(mode):
        return "char_device"
    elif stat.S_ISFIFO(mode):
        return "fifo"
    elif stat.S_ISSOCK(mode):
        return "socket"
    elif stat.S_ISLNK(mode):
        return "symlink"
    elif stat.S_ISREG(mode):
        return "file"
    elif stat.S_ISDIR(mode):
        return "directory"
    else:
        return "unknown"
