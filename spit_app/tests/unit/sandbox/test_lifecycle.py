#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the life cycle of the processes a call starts.

The reader used to wait for end-of-file, and end-of-file belongs to everyone
holding the write end of the pipe -- including a background process the command
started and forgot about. Measured here as control: a bash that backgrounds a
three second sleep and exits in milliseconds keeps the read busy for the full
three seconds. Substitute a server for the sleep and the call never returns, with
no timeout watching, because the command itself finished at once.

It is invisible inside bwrap, where --die-with-parent tears the sandbox down with
the call; these tests run sandbox=False precisely so the process table is honest.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.common import kill_process_group  # noqa: E402
from spit_app.tools.run.run import wrap_script           # noqa: E402
from stub_app import run_as_file                         # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(path: str) -> int:
    for _ in range(100):
        if os.path.exists(path):
            text = open(path).read().strip()
            if text:
                return int(text)
        time.sleep(0.02)
    raise AssertionError("no pid written to " + path)


print("=== 1. Control: a background process keeps a plain read busy ===")
with tempfile.TemporaryDirectory() as tmp:
    started = time.time()
    proc = subprocess.Popen(["bash", "-c", "sleep 3 & echo hi"],
                            stdout=subprocess.PIPE, text=True)
    out = proc.stdout.read()
    waited = time.time() - started
    check("t1-read-was-held", waited >= 2.5, True)
    check("t1-output-there", "hi" in out, True)

print()
print("=== 2. Through Run, the command ends the call ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    pidfile = os.path.join(home, "bg.pid")
    command = "sleep 3 & echo $! > %s; echo hi" % pidfile
    out, leftovers, elapsed = run_as_file(wrap_script(command), home, root)
    pid = read_pid(pidfile)
    check("t2-returned-quickly", elapsed < 1.5, True)
    check("t2-output-there", "hi" in out, True)
    check("t2-report-line", "Process exited with code 0" in out, True)
    check("t2-no-leftover-script", leftovers, [])
    time.sleep(0.3)
    check("t2-straggler-stopped", alive(pid), False)

print()
print("=== 3. kill_process_group reaches the children, and is safe ===")
with tempfile.TemporaryDirectory() as tmp:
    pidfile = os.path.join(tmp, "bg.pid")
    proc = subprocess.Popen(["bash", "-c",
                             "sleep 30 & echo $! > %s; wait" % pidfile],
                            stdout=subprocess.DEVNULL, start_new_session=True)
    pid = read_pid(pidfile)
    time.sleep(0.2)
    check("t3-child-running", alive(pid), True)
    kill_process_group(proc)
    proc.wait(timeout=5)
    check("t3-shell-stopped", alive(proc.pid), False)
    check("t3-child-stopped", alive(pid), False)
    kill_process_group(proc)          # idempotent on an already dead group
    check("t3-idempotent", True, True)

print()
print("=== 4. Something that setsid-s itself is left alone on purpose ===")
if shutil.which("setsid"):
    with tempfile.TemporaryDirectory() as tmp:
        pidfile = os.path.join(tmp, "detached.pid")
        proc = subprocess.Popen(["bash", "-c",
                                 "setsid sleep 30 & echo $! > %s; sleep 0.4" % pidfile],
                                stdout=subprocess.DEVNULL, start_new_session=True)
        pid = read_pid(pidfile)
        proc.wait(timeout=5)
        kill_process_group(proc)
        check("t4-detached-survives", alive(pid), True)
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.2)
        check("t4-cleaned-up", alive(pid), False)
else:
    print("  setsid not available here; escape-hatch check skipped")

print()
print("=== 5. Foreground output still arrives complete and in order ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    out, leftovers, elapsed = run_as_file(
        wrap_script("echo one; sleep 0.2; echo two"), home, root)
    check("t5-both-lines", "one" in out and "two" in out, True)
    check("t5-order", out.index("one") < out.index("two"), True)
    check("t5-report-line", "Process exited with code 0" in out, True)
    out, leftovers, elapsed = run_as_file(wrap_script("exit 4"), home, root)
    check("t5-exit-code", "Process exited with code 4" in out, True)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
