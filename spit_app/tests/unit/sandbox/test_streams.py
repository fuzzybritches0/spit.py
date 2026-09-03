#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for how the two output streams reach the caller.

A tool result is one string, so separating the streams has to be encoded in the
text. The choice here is a labelled stderr block at the end, shown only when there
is stderr -- which leaves a clean run byte-for-byte as it was. The alternative, a
prefix on every stderr line, keeps the interleaving but pollutes copy-paste and
mangles progress bars. Both pipes are drained concurrently, because a pipe holds
about 64 KB and a command writing more to one nobody reads stops writing: that is
a deadlock with the child waiting for us.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.run import STDERR_HEADER, wrap_script  # noqa: E402
from stub_app import run_as_file                              # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


print("=== 1. A clean run looks exactly as it did before ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    out, _, _ = run_as_file(wrap_script("echo hello"), home, root,
                            separate_stderr=True)
    check("t1-no-header", STDERR_HEADER in out, False)
    check("t1-output", "hello" in out, True)
    check("t1-report", "Process exited with code 0" in out, True)

print()
print("=== 2. stderr is reported apart, after the output ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    command = "echo out-line; echo err-line >&2; echo out-two"
    out, _, _ = run_as_file(wrap_script(command), home, root, separate_stderr=True)
    check("t2-header-present", STDERR_HEADER in out, True)
    check("t2-both-there", "out-line" in out and "err-line" in out, True)
    head, _, tail = out.partition(STDERR_HEADER)
    check("t2-stderr-after-header", "err-line" in tail, True)
    check("t2-no-stderr-leaking-up", "err-line" in head, False)
    check("t2-order-of-stdout", head.index("out-line") < head.index("out-two"), True)

print()
print("=== 3. Both streams noisy at once does not deadlock ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    command = ("head -c 1048576 /dev/zero | tr '\\0' 'o'; "
               "head -c 1048576 /dev/zero | tr '\\0' 'e' >&2")
    out, _, _ = run_as_file(wrap_script(command), home, root, separate_stderr=True)
    head, _, tail = out.partition(STDERR_HEADER)
    check("t3-stdout-megabyte", head.count("o") >= 1048576, True)
    check("t3-stderr-megabyte", tail.count("e") >= 1048576, True)

print()
print("=== 4. Merged mode interleaves and shows no header ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    # distinctive tokens: single letters collide with the boilerplate the
    # transport adds around the output ("Running process...", "exited with code")
    command = "echo mm-one; echo mm-two >&2; echo mm-three"
    out, _, _ = run_as_file(wrap_script(command), home, root, separate_stderr=False)
    check("t4-no-header", STDERR_HEADER in out, False)
    check("t4-all-there", all(x in out for x in ("mm-one", "mm-two", "mm-three")),
          True)
    check("t4-order-preserved",
          out.index("mm-one") < out.index("mm-two") < out.index("mm-three"), True)

print()
print("=== 5. Exit codes survive both modes ===")
with tempfile.TemporaryDirectory() as root:
    home = os.path.join(root, "h")
    os.makedirs(home)
    for separate in (True, False):
        out, _, _ = run_as_file(wrap_script("echo x >&2; exit 9"), home, root,
                                separate_stderr=separate)
        check(f"t5-rc-{separate}", "Process exited with code 9" in out, True)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
