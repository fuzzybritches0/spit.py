#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the text-field helpers of spit_app.arguments.

The tool-call editor shows every argument in a TextArea, so the value has to
survive value -> text -> value. Rendering with str() left a list as
"['a.txt', 'b.txt']" -- single quotes, not JSON -- which json.dumps() then
stored as a string, reproducing in the editor the very defect coerce() repairs
downstream. The round-trip test below is what pins that down.

These helpers live outside the Textual module precisely so that they can be
tested here: Textual is not needed, and not installed in every environment.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.arguments import (field_parse, field_render, field_valid,  # noqa: E402
                               spec_types)

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected and type(got) is type(expected):
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r} ({type(got).__name__})"
              f"\n  expected: {expected!r} ({type(expected).__name__})")


UNION = {"type": ["string", "array"]}
ARRAY_ONLY = {"type": "array", "items": {"type": "string"}}
STRING = {"type": "string"}
BOOLEAN = {"type": "boolean"}
INTEGER = {"type": "integer"}
NUMBER = {"type": "number"}
ANYOF = {"anyOf": [{"type": "string"}, {"type": "array"}]}
BARE = {"description": "no type declared"}

print("=== 1. Rendering: JSON in both directions, never str() ===")
check("t1-list", field_render(["a.txt", "b.txt"]), '["a.txt", "b.txt"]')
check("t1-not-str", field_render(["a.txt"]) != str(["a.txt"]), True)
check("t1-dict", field_render({"a": 1}), '{"a": 1}')
check("t1-none-blank", field_render(None), "")
check("t1-false", field_render(False), "false")
check("t1-zero", field_render(0), "0")
check("t1-string", field_render("/tmp/a.txt"), "/tmp/a.txt")

print()
print("=== 2. Round-trip through the field for a string-or-array union ===")
for value in (["a.txt", "b.txt"], "/tmp/a.txt", [], {"nested": [1, 2]}):
    check(f"t2-roundtrip-{value!r}", field_parse(UNION, field_render(value)), value)

print()
print("=== 3. Parsing what a human types ===")
check("t3-union-array", field_parse(UNION, '["a", "b"]'), ["a", "b"])
check("t3-union-repr", field_parse(UNION, "['a', 'b']"), ["a", "b"])
check("t3-union-text", field_parse(UNION, "/tmp/a.txt"), "/tmp/a.txt")
check("t3-array-only-text", field_parse(ARRAY_ONLY, "a.txt"), ["a.txt"])
check("t3-array-only-json", field_parse(ARRAY_ONLY, '["a", "b"]'), ["a", "b"])
check("t3-anyof-array", field_parse(ANYOF, '["a"]'), ["a"])
check("t3-anyof-string", field_parse(ANYOF, "a"), "a")
check("t3-empty-is-none", field_parse(UNION, ""), None)

print()
print("=== 4. Scalars ===")
check("t4-int", field_parse(INTEGER, "5"), 5)
check("t4-number", field_parse(NUMBER, "1.5"), 1.5)
check("t4-true", field_parse(BOOLEAN, "true"), True)
check("t4-false", field_parse(BOOLEAN, "FALSE"), False)
check("t4-bad-int-stays-text", field_parse(INTEGER, "5x"), "5x")
check("t4-bad-bool-stays-text", field_parse(BOOLEAN, "maybe"), "maybe")

print()
print("=== 5. Validation drives the red background ===")
check("t5-union-array-ok", field_valid(UNION, '["a", "b"]'), True)
check("t5-union-text-ok", field_valid(UNION, "anything at all"), True)
check("t5-blank-ok", field_valid(INTEGER, ""), True)
check("t5-int-ok", field_valid(INTEGER, "42"), True)
check("t5-int-bad", field_valid(INTEGER, "forty"), False)
check("t5-number-ok", field_valid(NUMBER, "1.5"), True)
check("t5-number-bad", field_valid(NUMBER, "x"), False)
check("t5-bool-ok", field_valid(BOOLEAN, "True"), True)
check("t5-bool-bad", field_valid(BOOLEAN, "yes"), False)
check("t5-undeclared-ok", field_valid(BARE, "whatever"), True)
check("t5-array-only-bare-ok", field_valid(ARRAY_ONLY, "a.txt"), True)

print()
print("=== 6. spec_types reads every shape of declaration ===")
check("t6-string", spec_types(STRING), ["string"])
check("t6-union", spec_types(UNION), ["array", "string"])
check("t6-anyof", spec_types(ANYOF), ["array", "string"])
check("t6-bare", spec_types(BARE), [])
check("t6-none", spec_types(None), [])
check("t6-list", spec_types(["type", "string"]), [])

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
