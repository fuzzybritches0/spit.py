def get_permissions(stat_result):
    """Get human-readable permissions string."""
    mode = stat_result.st_mode
    perms = ""
    perms += "r" if mode & stat.S_IRUSR else "-"
    perms += "w" if mode & stat.S_IWUSR else "-"
    perms += "x" if mode & stat.S_IXUSR else "-"
    perms += "r" if mode & stat.S_IRGRP else "-"
    perms += "w" if mode & stat.S_IWGRP else "-"
    perms += "x" if mode & stat.S_IXGRP else "-"
    perms += "r" if mode & stat.S_IROTH else "-"
    perms += "w" if mode & stat.S_IWOTH else "-"
    perms += "x" if mode & stat.S_IXOTH else "-"
    return perms

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    
    stat_result = path.stat()
    is_symlink = path.is_symlink()
    symlink_target = None
    if is_symlink:
        try:
            symlink_target = str(path.resolve())
        except:
            symlink_target = "broken"
    
    owner, group = get_owner_group(stat_result)
    file_type = get_file_type(stat_result)
    permissions = get_permissions(stat_result)
    permissions_octal = oct(stat_result.st_mode)[-3:]
    size = stat_result.st_size
    mtime = datetime.fromtimestamp(stat_result.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    atime = datetime.fromtimestamp(stat_result.st_atime).strftime('%Y-%m-%d %H:%M:%S')
    ctime = datetime.fromtimestamp(stat_result.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
    inode = stat_result.st_ino
    hard_links = stat_result.st_nlink
    
    # Build metadata dictionary
    metadata = {
        "path": str(path),
        "exists": True,
        "type": file_type,
        "size": size,
        "size_human": human_readable_size(size),
        "permissions": permissions,
        "permissions_octal": permissions_octal,
        "owner": owner,
        "group": group,
        "modified": mtime,
        "accessed": atime,
        "created": ctime,
        "inode": inode,
        "hard_links": hard_links,
        "is_symlink": is_symlink,
        "symlink_target": symlink_target,
        "is_file": stat_result.st_mode & stat.S_ISREG(stat_result.st_mode),
        "is_directory": stat_result.st_mode & stat.S_ISDIR(stat_result.st_mode),
        "is_block_device": stat_result.st_mode & stat.S_ISBLK(stat_result.st_mode),
        "is_char_device": stat_result.st_mode & stat.S_ISCHR(stat_result.st_mode),
        "is_fifo": stat_result.st_mode & stat.S_ISFIFO(stat_result.st_mode),
        "is_socket": stat_result.st_mode & stat.S_ISSOCK(stat_result.st_mode),
    }
    
    if format == "json":
        print("```json")
        print(json.dumps(metadata, indent=2))
        print("```")
    else:
        # Text output
        print("```")
        print(f"File: {path}")
        print(f"Exists: Yes")
        print(f"Type: {file_type}")
        print(f"Size: {human_readable_size(size)} ({size} bytes)")
        print(f"Permissions: {permissions} ({permissions_octal})")
        print(f"Owner: {owner}:{group}")
        print(f"Modified: {mtime}")
        print(f"Accessed: {atime}")
        print(f"Created: {ctime}")
        print(f"Inode: {inode}")
        print(f"Hard Links: {hard_links}")
        print(f"Is Symlink: {'Yes' if is_symlink else 'No'}")
        if is_symlink:
            print(f"Symlink Target: {symlink_target}")
        print(f"Is File: {metadata['is_file']}")
        print(f"Is Directory: {metadata['is_directory']}")
        print(f"Is Block Device: {metadata['is_block_device']}")
        print(f"Is Char Device: {metadata['is_char_device']}")
        print(f"Is FIFO: {metadata['is_fifo']}")
        print(f"Is Socket: {metadata['is_socket']}")
        print("```")

except PermissionError:
    print(f"ERROR: Permission denied: `{path}`")
    sys.exit(1)
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
