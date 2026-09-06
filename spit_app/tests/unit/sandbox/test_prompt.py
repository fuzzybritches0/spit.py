#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for what the model is told about run_command.

PROMPT is the only thing the model reads about this tool. Everything the code
does to a background process, to the two streams, or to the state of the next
call is invisible to it otherwise, so a fact that is not in the string is a fact
the model does not know: it kept writing `&` and expecting a survivor, because
nothing had ever told it the group is killed when the call ends.

These check that the facts are present, not how they are phrased. The markers
come from the code that produces them -- STDERR_HEADER, the schema's own argument
names -- so changing one there fails here, which is the point: a prompt that
describes yesterday's behaviour is worse than no prompt.
"""
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import spit_app.tools.run_command as run_command          # noqa: E402
from spit_app.tools.run.run import STDERR_HEADER          # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


PROMPT = run_command.PROMPT
properties = run_command.DESC["function"]["parameters"]["properties"]

print("=== 1. It reaches the model at all ===")
# work.py reads the prompt out of SETTINGS, not out of the module attribute, so
# a SETTINGS that no longer points at PROMPT means the model reads the old text
check("t1-settings-carries-prompt", run_command.SETTINGS["prompt"]["value"], PROMPT)
check("t1-not-empty", len(PROMPT) > len("Use this function to run Shell commands"),
      True)

print()
print("=== 2. A background process does not survive the call ===")
lower = PROMPT.lower()
check("t2-backgrounding-named", "&" in PROMPT, True)
check("t2-terminal-and-setsid", "terminal" in lower and "setsid" in PROMPT, True)
# the two halves of the reason: the group is stopped, and --die-with-parent
# makes the same symptom disappear inside bwrap
check("t2-process-group", "process group" in lower, True)
check("t2-die-with-parent", "--die-with-parent" in PROMPT, True)

print()
print("=== 3. The stderr block is described by its real marker ===")
check("t3-marker-quoted", STDERR_HEADER in PROMPT, True)
check("t3-after-the-output", "after" in lower, True)
check("t3-only-when-there-is-some", "only" in lower, True)
check("t3-argument-named", "separate_stderr" in PROMPT and
      "separate_stderr" in properties, True)

print()
print("=== 4. What carries over to the next call ===")
check("t4-export-carries", "`export`" in PROMPT and "cd" in PROMPT, True)
check("t4-tilde-and-var", "~" in PROMPT and "$VAR" in PROMPT, True)

print()
print("=== 5. Placeholders: only PROMPT_INST is substituted ===")
# work.py replaces [setting] in PROMPT_INST alone, so a bracket token added to
# PROMPT would reach the model literally -- and PROMPT_INST without its [timeout]
# would silently stop telling the model the limit.
check("t5-prompt-has-no-tokens", re.search(r"\[\w+\]", PROMPT), None)
check("t5-timeout-token-intact", "[timeout]" in run_command.PROMPT_INST, True)

print()
print("=== 6. work.py owns the break between the two strings ===")
# work.py puts the line break in front of PROMPT_INST (and a blank line between
# two tools), so PROMPT is prose that ends with a full stop and PROMPT_INST
# starts with its sentence. The old contract was the opposite -- "PROMPT must
# end with a newline, work.py joins with no separator" -- and these two checks
# pinned it; a trailing break now, when the break comes from work.py, would
# reach the model as a blank line in the middle of one tool's section. The
# assembly itself is pinned by tests/unit/prompt/test_prompt_assembly.py, which
# drives the real prompt() over every tool in the tree.
check("t6-prompt-carries-no-trailing-whitespace", PROMPT, PROMPT.rstrip())
check("t6-prompt_inst_starts_its_own_line", run_command.PROMPT_INST.startswith("\n"),
      False)

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
