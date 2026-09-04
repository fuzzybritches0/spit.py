#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for what run_command carries from one call to the next.

The trailer used to write `declare` -- every shell variable, not just the ones
the command exported -- and sandbox_env.sh replayed it with its errors thrown
away:

    ~/.sandbox_env: line 2: BASHOPTS: readonly variable
    ~/.sandbox_env: line 10: BASH_VERSINFO: readonly variable
    ~/.sandbox_env: line 17: EUID: readonly variable

which is why the redirect hiding them mattered: it hid everything else too. The
state is now the exported environment written as `export NAME=value`, minus
STATE_EXCLUDE, plus the working directory in a file of its own -- exports
persisted, so a working directory that did not was an arbitrary asymmetry.

Each "call" is the real chain: sandbox_env.sh running bash on a script file with
an empty stdin, exactly as Run builds it, against a HOME in a temporary
directory. The environment passed in is a minimal one so that the developer's own
shell cannot decide a result.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tools.run.run import wrap_script  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
SANDBOX_ENV_SH = os.path.join(REPO_ROOT, "spit_app", "tools", "run", "sandbox_env.sh")

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def call(home: str, command: str, cwd: str = None):
    """One run_command call: sandbox_env.sh -> bash -> script file, empty stdin."""
    script = os.path.join(home, ".spit_cmd.sh")
    with open(script, "w") as handle:
        handle.write(wrap_script(command))
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home}
    proc = subprocess.run(["bash", SANDBOX_ENV_SH, "bash", script],
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, env=env,
                          cwd=cwd or home)
    os.remove(script)
    return proc


def state(home: str) -> str:
    path = os.path.join(home, ".sandbox_env")
    return open(path).read() if os.path.exists(path) else ""


def value(dump: str, name: str) -> str:
    """The value the state restores for `name`, or None when it restores none."""
    for line in dump.splitlines():
        if line.startswith(f"export {name}="):
            return line.split("=", 1)[1]
    return None


print("=== 1. What the trailer writes ===")
with tempfile.TemporaryDirectory() as home:
    target = os.path.join(home, "workdir")
    os.mkdir(target)
    proc = call(home, f"export SPIT_A=1; cd {target}")
    check("t1-rc", proc.returncode, 0)
    dump = state(home)
    check("t1-export-line", value(dump, "SPIT_A"), '"1"')
    check("t1-internals-excluded",
          any(line.startswith("export BASH") or "BASHOPTS" in line
              or "SHELLOPTS" in line or "SHLVL" in line for line in dump.splitlines()),
          False)
    check("t1-home-excluded", value(dump, "HOME"), None)
    check("t1-cwd-saved", open(os.path.join(home, ".sandbox_cwd")).read().strip(),
          target)
    check("t1-no-stray-tmp", os.path.exists(os.path.join(home, ".sandbox_env.tmp")),
          False)

print()
print("=== 2. The next call sees the exports and the directory ===")
with tempfile.TemporaryDirectory() as home:
    target = os.path.join(home, "workdir")
    os.mkdir(target)
    call(home, f"export SPIT_A=1; cd {target}")
    proc = call(home, 'echo "A=[$SPIT_A] cwd=[$(pwd)]"')
    check("t2-export-visible", "A=[1]" in proc.stdout, True)
    check("t2-cwd-restored", target in proc.stdout, True)
    check("t2-no-noise-on-stderr", proc.stderr.strip(), "")

print()
print("=== 3. Accumulation: a later call does not wipe an earlier export ===")
with tempfile.TemporaryDirectory() as home:
    call(home, "export SPIT_A=1")
    call(home, "export SPIT_B=2")
    proc = call(home, 'echo "A=[$SPIT_A] B=[$SPIT_B]"')
    check("t3-first-still-there", "A=[1]" in proc.stdout, True)
    check("t3-second-there", "B=[2]" in proc.stdout, True)

print()
print("=== 4. Updated and unset values follow the command ===")
with tempfile.TemporaryDirectory() as home:
    call(home, "export SPIT_A=1")
    call(home, "export SPIT_A=9")
    proc = call(home, 'echo "A=[$SPIT_A]"')
    check("t4-updated", "A=[9]" in proc.stdout, True)
    call(home, "unset SPIT_A")
    proc = call(home, 'echo "A=[$SPIT_A]"')
    check("t4-unset-gone", "A=[]" in proc.stdout, True)

print()
print("=== 5. Values with spaces, quotes and a dollar sign survive ===")
with tempfile.TemporaryDirectory() as home:
    call(home, "export SPIT_V='two words'; export SPIT_L='$NOT_A_REAL_VAR'")
    proc = call(home, 'echo "V=[$SPIT_V] L=[$SPIT_L]"')
    check("t5-spaces", "V=[two words]" in proc.stdout, True)
    check("t5-dollar-not-reexpanded", "L=[$NOT_A_REAL_VAR]" in proc.stdout, True)

print()
print("=== 6. Control: the old full dump errors when replayed ===")
with tempfile.TemporaryDirectory() as home:
    legacy = os.path.join(home, ".sandbox_env")
    subprocess.run(["bash", "-c", "export SPIT_OLD=1; declare > \"$1\"", "x", legacy],
                   check=True)
    check("t6-legacy-has-internals", "BASHOPTS" in open(legacy).read(), True)
    noisy = subprocess.run(["bash", "-c", 'source "$1"', "x", legacy],
                           capture_output=True, text=True)
    check("t6-old-reader-errors", "readonly variable" in noisy.stderr, True)
    quiet = subprocess.run(["bash", "-c", 'source <(grep "^export " "$1")', "x", legacy],
                           capture_output=True, text=True)
    check("t6-new-reader-silent", quiet.stderr.strip(), "")
    check("t6-new-reader-ignores-it", quiet.returncode, 0)

print()
print("=== 7. A command that rewrites HOME cannot move the next call ===")
with tempfile.TemporaryDirectory() as home:
    call(home, "export HOME=/somewhere/else; export SPIT_C=3")
    dump = state(home)
    check("t7-home-not-persisted", value(dump, "HOME"), None)
    proc = call(home, 'echo "C=[$SPIT_C] home=[$HOME]"')
    check("t7-still-uses-the-sandbox-home", home in proc.stdout, True)
    check("t7-other-exports-still-work", "C=[3]" in proc.stdout, True)

print()
print("=== 8. A vanished working directory is not an error ===")
with tempfile.TemporaryDirectory() as home:
    target = os.path.join(home, "temp-workdir")
    os.mkdir(target)
    call(home, f"cd {target}")
    os.rmdir(target)
    proc = call(home, 'echo "cwd=[$(pwd)]"')
    check("t8-rc", proc.returncode, 0)
    check("t8-falls-back-to-home", home in proc.stdout, True)
    check("t8-no-noise", proc.stderr.strip(), "")

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
