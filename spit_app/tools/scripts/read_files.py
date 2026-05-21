import sys
import os

try:
    if 'path' in dir():
        paths = [path]
    elif 'paths' in dir():
        paths = paths
    results = {}
    for p in paths:
        try:
            with open(p, "r", encoding=encoding) as f:
                content = f.read()
                results[p] = {
                    "success": True,
                    "content": content,
                    "size": len(content),
                    "error": None
                }
        except FileNotFoundError:
            results[p] = {
                "success": False,
                "content": None,
                "size": 0,
                "error": f"File not found: {p}"
            }
        except PermissionError:
            results[p] = {
                "success": False,
                "content": None,
                "size": 0,
                "error": f"Permission denied: {p}"
            }
        except UnicodeDecodeError:
            results[p] = {
                "success": False,
                "content": None,
                "size": 0,
                "error": f"Encoding error (try different encoding): {p}"
            }
        except Exception as e:
            results[p] = {
                "success": False,
                "content": None,
                "size": 0,
                "error": f"{type(e).__name__}: {e}"
            }
    if len(paths) == 1:
        result = results[paths[0]]
        if result["success"]:
            print(f"File: `{paths[0]}`")
            print(f"Size: `{result['size']} bytes`")
            print("~~~~")
            print(result["content"])
            print("~~~~")
        else:
            print(f"ERROR: `{result['error']}`")
            sys.exit(1)
    else:
        print(f"Reading {len(paths)} file(s):\n")
        for p in paths:
            result = results[p]
            print(f"File: `{p}`")
            if result["success"]:
                print(f"Size: `{result['size']} bytes`")
                print("~~~~")
                print(result["content"])
                print("~~~~")
            else:
                print(f"\nERROR: `{result['error']}`")
        print(f"\nTotal: {len(paths)} file(s) processed, {sum(1 for r in results.values() if r['success'])} successful")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
