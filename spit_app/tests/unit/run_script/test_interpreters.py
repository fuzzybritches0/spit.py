#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for what `run_script` hands to `Run`.

Two things went wrong when the tool was tuned in line with `run_command`, and
both were invisible because no test covered this tool:

  * `separate_stderr` was added to DESC -- so the model may set it -- but it was
    never passed to `Run`: the switch was wired to nothing and every call
    interleaved the two streams whatever the model asked for.
  * `wrap_script(script)` went in front of the script for *every* interpreter.
    The wrapper is bash (`EXIT_CODE=${?}`, `export -p`, `pwd -P`). Handed to
    python3 or perl it is a SyntaxError on the trailer line, and both parse the
    whole file before executing any of it, so the script's own output never
    appeared at all -- the tool was broken for the two interpreters besides bash
    that its own default allowed list names.

These tests pin the call the tool makes: the payload per interpreter, the
switches, the settings, the content-or-path `script` and the refusals.
`stub_run.py` explains why `Run` is a spy here; `test_delivery.py` takes the
recorded payloads to the real interpreters.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import spit_app.tools.run_script as run_script                   # noqa: E402
from spit_app.arguments import expand_arguments                  # noqa: E402
from spit_app.tools.run.run import STATE_HEADER, wrap_script     # noqa: E402
from stub_run import build, call, stub_app                       # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def with_interpreters(present, fn):
    """Run `fn` with `shutil.which` answering for exactly the names in `present`."""
    saved = run_script.shutil.which
    run_script.shutil.which = lambda name: (f"/usr/bin/{name}"
                                            if name in present else None)
    try:
        return fn()
    finally:
        run_script.shutil.which = saved


BASH_SCRIPT = "echo rs-one-bash"
PY_SCRIPT = "print('rs-two-python')"
PERL_SCRIPT = "print 'rs-two-perl\\n';"
# `sh` is not in the default allowed list (the wrapper rule, decision 63), so a
# call that names it has to widen the setting first -- and sections 1-4 are
# about the payload and the switches, not about the setting. Section 9 is where
# the setting itself is what is under test.
WITH_SH = "bash, python3, perl, sh"

print("=== 1. bash gets the wrapper (state and exit code ride on it) ===")
run, text = build("bash", BASH_SCRIPT)
check("t1-built", run is not None, True)
check("t1-interpreter", run.cmd, "bash")
check("t1-payload-is-the-wrapper", run.script, wrap_script(BASH_SCRIPT))
check("t1-state-header", run.script.startswith(STATE_HEADER), True)
check("t1-trailer-present", "EXIT_CODE=" in run.script, True)
check("t1-script-survives", BASH_SCRIPT in run.script, True)
check("t1-tool-output-yields", "SPY-RAN-THIS" in text, True)

print()
print("=== 2. every other interpreter gets its script verbatim ===")
for interpreter, script, token in (("python3", PY_SCRIPT, "rs-two-python"),
                                   ("perl", PERL_SCRIPT, "rs-two-perl"),
                                   ("sh", "echo rs-two-sh", "rs-two-sh")):
    run, text = build(interpreter, script, allowed=WITH_SH)
    check(f"t2-{interpreter}-built", run is not None, True)
    check(f"t2-{interpreter}-verbatim", run.script, script)
    check(f"t2-{interpreter}-no-trailer", "EXIT_CODE" in run.script, False)
    check(f"t2-{interpreter}-no-state-header", "SPIT_STATE" in run.script, False)
    check(f"t2-{interpreter}-token-intact", token in run.script, True)

print()
print("=== 3. separate_stderr reaches Run, and matches what DESC promises ===")
declared = run_script.DESC["function"]["parameters"]["properties"]
check("t3-desc-declares-the-switch", "separate_stderr" in declared, True)
check("t3-desc-says-true-by-default",
      "Default: true" in declared["separate_stderr"]["description"], True)
run, text = build("python3", PY_SCRIPT)
check("t3-default-is-true", run.kwargs.get("separate_stderr"), True)
run, text = build("python3", PY_SCRIPT, separate_stderr=False)
check("t3-false-reaches-run", run.kwargs.get("separate_stderr"), False)
run, text = build("bash", BASH_SCRIPT, separate_stderr=True)
check("t3-true-reaches-run", run.kwargs.get("separate_stderr"), True)
run, text = build("sh", "echo rs-three-sh", allowed=WITH_SH,
                  separate_stderr=False)
check("t3-switch-applies-to-a-wrapped-call-too",
      run.kwargs.get("separate_stderr"), False)

print()
print("=== 4. delivery and settings ===")
run, text = build("python3", PY_SCRIPT)
check("t4-script_delivered_as_file", run.kwargs["script_as_file"], True)
check("t4-default-sandbox-on", run.sandbox, True)
check("t4-default-timeout", run.timeout, 0)
run, text = build("bash", BASH_SCRIPT)
check("t4-file-delivery-for-bash-too", run.kwargs["script_as_file"], True)
built = call(stub_app({"run_script": {"sandbox": {"value": False},
                                      "timeout": {"value": 42}}}),
             interpreter="perl", script=PERL_SCRIPT)[1]
check("t4-user-sandbox-override", built[0].sandbox, False)
check("t4-user-timeout-override", built[0].timeout, 42)
check("t4-settings-restored-after-an-override",
      run_script.SETTINGS["sandbox"]["value"], True)

print()
print("=== 5. which interpreter actually runs ===")
# `python` appears in the allowed string here because section 9 is where the
# setting is under test; here the question is only the fallback, so the name has
# to be one the tool would accept at all in the first place.
PYTHON_ALLOWED = "bash, python, python3, perl"
run, text = with_interpreters({"python3"},
                              lambda: build("python", "print('rs-five')",
                                            allowed=PYTHON_ALLOWED))
check("t5-python-mapped-when-python-absent", run.cmd if run else None, "python3")
run, text = with_interpreters({"python", "python3"},
                              lambda: build("python", "print('rs-five')",
                                            allowed=PYTHON_ALLOWED))
check("t5-python-kept-when-present", run.cmd if run else None, "python")
# t5-unknown-interpreter-* pinned "cobol is not on PATH". A name outside the
# allowed list never reaches PATH now (section 9 refuses it), so the trio is
# re-pinned to what `not found` means today: allowed by the setting, missing on
# the machine. The refusal for a name outside the list is t9's, with its own
# wording checked there.
run, text = with_interpreters(set(), lambda: build("python3", PY_SCRIPT))
check("t5-allowed-but-missing-refused", run, None)
check("t5-allowed-but-missing-says-so", "not found" in text, True)
check("t5-allowed-but-missing-ran-nothing", "SPY-RAN-THIS" in text, False)

print()
print("=== 6. script is the script itself, or the path of a file ===")
with tempfile.TemporaryDirectory() as root:
    path = os.path.join(root, "t6-script.py")
    with open(path, "w") as handle:
        handle.write("print('rs-six-from-file')\n")
    run, text = build("python3", path)
    check("t6-file-read", run.script, "print('rs-six-from-file')\n")
    check("t6-says-where-it-came-from", f"Reading script from file `{path}`" in text,
          True)
    missing = os.path.join(root, "t6-no-such-script.py")
    run, text = build("python3", missing)
    check("t6-missing-path-is-code-not-a-file", run.script, missing)
    check("t6-missing-path-no-notice", "Reading script from file" in text, False)
    multi = "print('rs-six-a')\nprint('rs-six-b')\n"
    run, text = build("python3", multi)
    check("t6-multiline-is-code", run.script, multi)
    check("t6-multiline-no-notice", "Reading script from file" in text, False)
    empty = os.path.join(root, "t6-empty.py")
    open(empty, "w").close()
    run, text = build("python3", empty)
    check("t6-empty-file-refused", run, None)
    check("t6-empty-file-still-says-where", "Reading script from file" in text,
          True)

print()
print("=== 7. `script` is deliberately NOT a PATH_ARG ===")
# expand_arguments() rewrites ~ and $VARs, which for a script body is corruption,
# not convenience: `$HOME` inside a python script means the shell the script
# launches, not the app's home. Pinned so nobody "fixes" the path form by adding
# PATH_ARGS = ["script"].
os.environ["SPIT_RS_VAR"] = "rs-seven-expanded"
raw = 'print("$SPIT_RS_VAR")'
check("t7-tool-declares-no-path-args", hasattr(run_script, "PATH_ARGS"), False)
check("t7-expansion-would-rewrite-a-script",
      expand_arguments({"script": raw}, ["script"])["script"] != raw, True)
check("t7-the-script-reaches-the-interpreter-untouched",
      build("python3", raw)[0].script, raw)

print()
print("=== 8. Refusals build nothing ===")
for label, blank in (("empty", ""), ("whitespace", "  \n\t\n")):
    run, text = build("python3", blank)
    check(f"t8-{label}-refused", run, None)
    check(f"t8-{label}-says-so", "ERROR" in text and "empty" in text, True)
    check(f"t8-{label}-ran-nothing", "SPY-RAN-THIS" in text, False)

print()
print("=== 9. the `interpreters` setting decides what runs ===")
for name, script in (("bash", BASH_SCRIPT), ("python3", PY_SCRIPT),
                     ("perl", PERL_SCRIPT)):
    run, text = build(name, script)
    check(f"t9-default-list-allows-{name}", run is not None, True)
run, text = build("cobol", "x = 1")
check("t9-outside-the-list-refused", run, None)
check("t9-refusal-says-not-allowed", "not an allowed interpreter" in text, True)
check("t9-refusal-names-the-setting", "`interpreters` setting" in text, True)
check("t9-refusal-lists-what-is-allowed", "bash, python3, perl" in text, True)
check("t9-refusal-ran-nothing", "SPY-RAN-THIS" in text, False)
check("t9-refusal-does-not-probe-path", "not found" in text, False)
check("t9-refusal-reads-no-script-file", "Reading script from file" in text, False)
# `sh` is the sharp case: it is installed on every machine that runs these
# tests and the default setting does not name it, so this is the check where the
# setting -- not PATH -- is what refuses. `cobol` above only proves the refusal
# is well-worded, because an uninstalled name is refused either way.
run, text = build("sh", "echo rs-nine")
check("t9-installed-but-unlisted-refused", run, None)
check("t9-unlisted-ran-nothing", "SPY-RAN-THIS" in text, False)
check("t9-unlisted-names-what-is-allowed", "bash, python3, perl" in text, True)
run, text = with_interpreters({"bash", "ruby"},
                              lambda: build("ruby", "puts 'rs-nine'",
                                            allowed="bash, ruby"))
check("t9-user-widening-opens-the-list", run.cmd if run else None, "ruby")
run, text = build("sh", "echo rs-nine", allowed=WITH_SH)
check("t9-widened-name-runs", run.cmd if run else None, "sh")
run, text = build("python3", PY_SCRIPT, allowed="bash")
check("t9-user-narrowing-holds", run, None)
check("t9-narrowing-lists-only-what-is-left", "allows bash." in text, True)

print()
print("=== 10. the name that is checked is the name that was asked ===")
run, text = with_interpreters({"python3"}, lambda: build("python", PY_SCRIPT))
check("t10-python-outside-the-list-refused", run, None)
check("t10-refusal-quotes-the-asked-name", "`python` is not an allowed" in text, True)
check("t10-the-fallback-did-not-answer-for-it", "python3 is not an allowed" in text,
      False)
run, text = with_interpreters({"python3"},
                              lambda: build("python", PY_SCRIPT,
                                            allowed="bash, python"))
check("t10-an-allowed-python-still-resolves", run.cmd if run else None, "python3")
check("t10-and-says-what-ran", "SPY-RAN-THIS" in text, True)

print()
print("=== 11. the shape of the setting string ===")
parse = run_script.allowed_interpreters
check("t11-default", parse(run_script.ALLOWED), ["bash", "python3", "perl"])
check("t11-no-commas", parse("bash python3"), ["bash", "python3"])
check("t11-one-per-line", parse("bash\npython3\nperl\n"), ["bash", "python3", "perl"])
check("t11-stray-and-empty-entries-dropped", parse(" bash ,,perl  "), ["bash", "perl"])
check("t11-empty-allows-nothing", parse(""), [])
run, text = build("python3", PY_SCRIPT, allowed="   ")
check("t11-blank-setting-refuses", run, None)
check("t11-blank-setting-says-why", "the setting is empty" in text, True)
check("t11-names-are-case-sensitive", parse("BASH"), ["BASH"])
run, text = build("bash", BASH_SCRIPT, allowed="BASH")
check("t11-a-name-is-a-name", run, None)
check("t11-typo-is-listed-back", "allows BASH." in text, True)
run, text = build("/usr/bin/python3", PY_SCRIPT)
check("t11-an-absolute-path-is-its-own-name", run, None)
# which() raises TypeError on anything that is not a name, so the pre-fix tool
# died with a traceback inside the tool on this call (measured: TypeError,
# "expected str, bytes or os.PathLike object, not list"). The refusal is the
# same refusal as any other name that is not on the list.
run, text = build(["python3"], PY_SCRIPT)
check("t11-a-value-that-is-not-a-name-is-refused", run, None)
check("t11-and-reaches-no-which", "not an allowed interpreter" in text, True)
# the same rule on the other side of the comparison: a settings file hand-edited
# into a list or a number is quoted back as the allow-list instead of raising
# AttributeError on .replace() inside the tool.
run, text = build("bash", BASH_SCRIPT, allowed=["bash"])
check("t11-a-malformed-setting-refuses", run, None)
check("t11-and-quotes-the-value-back", "['bash']" in text, True)
run, text = build("bash", BASH_SCRIPT, allowed=7)
check("t11-a-number-setting-refuses", run, None)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
