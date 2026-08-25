import sys
import os

def format_content(content):
    if not show_line_numbers:
        return content
    lines = content.splitlines()
    if not lines:
        return content
    width = len(str(len(lines)))
    return "\n".join(f"{n:>{width}}\t{line}" for n, line in enumerate(lines, 1))

try:
    results = {}
    for p in path:
        try:
            with open(p, "r", encoding=encoding) as f:
                content = f.read()
                results[p] = {
                    "success": True,
                    "content": content,
                    "display": format_content(content),
                    "size": len(content),
                    "error": None
                }
        except Exception as e:
            results[p] = {
                "success": False,
                "content": None,
                "size": 0,
                "error": f"{type(e).__name__}: {e}"
            }
    if len(path) == 1:
        result = results[path[0]]
        if result["success"]:
            print(f"File: `{path[0]}`")
            print(f"Size: `{result['size']} bytes`")
            print("")
            print(result["display"])
            print("")
        else:
            print(f"ERROR: `{result['error']}`")
            sys.exit(1)
    else:
        print(f"Reading {len(path)} file(s):\n")
        for p in path:
            result = results[p]
            print(f"File: `{p}`")
            if result["success"]:
                print(f"Size: `{result['size']} bytes`")
                print("")
                print(result["display"])
                print("")
            else:
                print(f"ERROR: `{result['error']}`")
        print(f"Total: {len(path)} file(s) processed, {sum(1 for r in results.values() if r['success'])} successful")
except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
