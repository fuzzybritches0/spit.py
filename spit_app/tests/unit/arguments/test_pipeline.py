#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""End-to-end check of the argument path: schema -> coerce -> get_args -> script.

This exercises the real production pieces rather than a stand-in: the DESC of
tools/read_files.py, the injector get_args() that turns arguments into the
Python head prepended to the tool script, and the script itself. The blob fed
in is what a decoder that cannot type a union emits -- `path` as JSON *text*.
Test 3 runs the same call *without* coercion and asserts it breaks, so the
suite cannot quietly pass again if coerce() is dropped from tool_call.py.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.arguments import coerce                        # noqa: E402
from spit_app.tools.run.run import get_args                  # noqa: E402
from spit_app.tools.read_files import DESC, EXEC             # noqa: E402

PROPERTIES = DESC["function"]["parameters"]["properties"]
DEFAULTS = {"encoding": "utf-8", "show_line_numbers": False}

pass_ = 0
fail_ = 0


def check(name, condition, detail=""):
    global pass_, fail_
    if condition:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}" + (f"\n  {detail}" if detail else ""))


def run(arguments: dict, cwd: str):
    """Run the tool script exactly as ToolCall.call() hands it to the sandbox."""
    head = get_args(arguments, DEFAULTS)
    proc = subprocess.run([EXEC["interpreter"]], input=head + EXEC["script"],
                          capture_output=True, text=True, cwd=cwd)
    return proc


def blob(value) -> str:
    """An arguments blob: `value` is what json.loads() will hand back for path.

    Passing json.dumps([...]) reproduces the exact defect -- the list arriving
    as text because the decoder had no type to encode it with.
    """
    return json.dumps({"path": value, "encoding": "utf-8",
                       "show_line_numbers": False})

print("=== 1. Coerced call reads every file in the array ===")
with tempfile.TemporaryDirectory() as tmp:
    files = []
    for name, body in (("one.txt", "alpha\n"), ("two.txt", "beta\n")):
        full = os.path.join(tmp, name)
        with open(full, "w") as handle:
            handle.write(body)
        files.append(full)

    arguments = json.loads(blob(json.dumps(files)))
    check("t1-still-text-before-coerce", isinstance(arguments["path"], str))
    coerce(arguments, PROPERTIES)
    check("t1-is-list-after-coerce", isinstance(arguments["path"], list))

    proc = run(arguments, tmp)
    check("t1-rc", proc.returncode == 0, f"rc={proc.returncode} err={proc.stderr}")
    check("t1-count", "Reading 2 file(s)" in proc.stdout, proc.stdout)
    check("t1-success", "2 successful" in proc.stdout, proc.stdout)
    check("t1-alpha", "alpha" in proc.stdout, proc.stdout)
    check("t1-beta", "beta" in proc.stdout, proc.stdout)

    print()
    print("=== 2. A single string path still works ===")
    arguments = json.loads(blob(files[0]))
    coerce(arguments, PROPERTIES)
    check("t2-stays-string", isinstance(arguments["path"], str))
    proc = run(arguments, tmp)
    check("t2-rc", proc.returncode == 0, f"rc={proc.returncode} err={proc.stderr}")
    check("t2-name", files[0] in proc.stdout, proc.stdout)
    check("t2-alpha", "alpha" in proc.stdout, proc.stdout)

print()
print("=== 3. Control: without coerce() the very same call fails ===")
with tempfile.TemporaryDirectory() as tmp:
    full = os.path.join(tmp, "one.txt")
    with open(full, "w") as handle:
        handle.write("alpha\n")
    arguments = json.loads(blob(json.dumps([full])))
    proc = run(arguments, tmp)
    check("t3-fails", proc.returncode == 1,
          f"expected rc=1 without coercion, got {proc.returncode}: {proc.stdout}")
    check("t3-error-mentions-array", "[" in proc.stdout and "one.txt" in proc.stdout,
          proc.stdout)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
