#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for path expansion in spit_app.arguments.

open() does not expand a leading ~ -- it looks for a directory literally named
"~" -- so read_files("~/notes.txt") reported FileNotFoundError, which reads
like a missing file rather than like an argument that was never resolved. A
model writes ~ because every shell example it has ever read uses it.

Expansion is opt-in per tool through PATH_ARGS, so that a ~ in a grep pattern
or in the body of write_file stays the character the caller meant.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.arguments import expand_arguments, expand_path  # noqa: E402
from spit_app.tools.read_files import DESC, EXEC              # noqa: E402
from spit_app.tools.run.run import get_args                   # noqa: E402

DEFAULTS = {"encoding": "utf-8", "show_line_numbers": False}
PATH_TOOLS = ["delete_lines", "diff", "file_info", "find_files", "grep",
              "insert_line", "list_directory", "patch", "read_files", "remove",
              "search_replace", "write_file"]

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected and type(got) is type(expected):
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


# os.path.expanduser() reads HOME, so a temporary home is all that is needed;
# it is restored even if a check below raises.
saved_home = os.environ.get("HOME")

try:
    print("=== 1. ~ and ~user and $VAR ===")
    with tempfile.TemporaryDirectory() as home:
        os.environ["HOME"] = home
        check("t1-tilde", expand_path("~/notes.txt"), os.path.join(home, "notes.txt"))
        check("t1-tilde-only", expand_path("~"), home)
        os.environ["SPIT_HOME"] = home
        check("t1-var-set", expand_path("$SPIT_HOME/notes.txt"),
              os.path.join(home, "notes.txt"))
        check("t1-var-unset-left-alone", expand_path("$NOT_SET_ANYWHERE/x"),
              "$NOT_SET_ANYWHERE/x")
        check("t1-plain-untouched", expand_path("/etc/hosts"), "/etc/hosts")
        check("t1-relative-untouched", expand_path("fixtures/a.txt"),
              "fixtures/a.txt")
        check("t1-list", expand_path(["~/a.txt", "b.txt"]),
              [os.path.join(home, "a.txt"), "b.txt"])
        check("t1-non-string", expand_path(7), 7)
        check("t1-none", expand_path(None), None)

        print()
        print("=== 2. Only the arguments a tool declares are expanded ===")
        arguments = {"path": "~/a.txt", "pattern": "~/not-a-path", "count": 3}
        expand_arguments(arguments, ["path"])
        check("t2-path", arguments["path"], os.path.join(home, "a.txt"))
        check("t2-pattern-untouched", arguments["pattern"], "~/not-a-path")
        check("t2-count-untouched", arguments["count"], 3)

        list_arguments = {"path": ["~/a.txt", "~/b.txt"]}
        expand_arguments(list_arguments, ["path"])
        check("t2-list", list_arguments["path"],
              [os.path.join(home, "a.txt"), os.path.join(home, "b.txt")])
        check("t2-no-path-args", expand_arguments({"path": "~/a"}, None),
              {"path": "~/a"})

        print()
        print("=== 3. Every path tool declares PATH_ARGS its schema knows ===")
        for name in PATH_TOOLS:
            module = importlib.import_module(f"spit_app.tools.{name}")
            properties = module.DESC["function"]["parameters"]["properties"]
            declared = getattr(module, "PATH_ARGS", [])
            check(f"t3-{name}-declares", bool(declared), True)
            for argument in declared:
                check(f"t3-{name}-{argument}-in-schema", argument in properties, True)

        print()
        print("=== 4. The real script reads a ~ path once it is expanded ===")
        with tempfile.TemporaryDirectory() as sandbox_home:
            target = os.path.join(sandbox_home, "one.txt")
            with open(target, "w") as handle:
                handle.write("expanded\n")
            os.environ["HOME"] = sandbox_home
            env = dict(os.environ)
            env["HOME"] = sandbox_home

            arguments = json.loads(json.dumps({"path": "~/one.txt"}))
            expand_arguments(arguments, DESC["function"]["parameters"]
                             ["properties"].keys())
            head = get_args(arguments, DEFAULTS)
            proc = subprocess.run([EXEC["interpreter"]], input=head + EXEC["script"],
                                  capture_output=True, text=True, cwd=sandbox_home,
                                  env=env)
            check("t4-rc", proc.returncode, 0)
            check("t4-content", "expanded" in proc.stdout, True)
            check("t4-no-tilde-left", "~" not in proc.stdout, True)

            print()
            print("=== 5. Control: without expansion the same call fails ===")
            head = get_args({"path": "~/one.txt"}, DEFAULTS)
            proc = subprocess.run([EXEC["interpreter"]], input=head + EXEC["script"],
                                  capture_output=True, text=True, cwd=sandbox_home,
                                  env=env)
            check("t5-fails", proc.returncode, 1)
            check("t5-error-is-not-found", "FileNotFoundError" in proc.stdout, True)
finally:
    if saved_home is None:
        os.environ.pop("HOME", None)
    else:
        os.environ["HOME"] = saved_home
    os.environ.pop("SPIT_HOME", None)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
