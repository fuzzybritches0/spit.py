#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for spit_app.arguments.coerce().

Run from anywhere: the path fix-up below makes spit_app importable.
Regression coverage for the bug where a schema union such as
"type": ["string", "array"] made a decoder serialise the list as text, so
read_files got the string '["a", "b"]' and opened it as one filename.
"""
import os
import sys

# repo root is four levels up: arguments/ <- unit/ <- tests/ <- spit_app/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.arguments import coerce, declared_types, unwrap  # noqa: E402

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


# "path" as tools/read_files.py declares it; "diff" as a plain string parameter
PROPS = {
    "path":    {"type": ["string", "array"]},
    "paths":   {"type": "array", "items": {"type": "string"}},
    "diff":    {"type": "string"},
    "flag":    {"type": "boolean"},
    "count":   {"type": "integer"},
    "target":  {"anyOf": [{"type": "string"}, {"type": "array"}]},
}

print("=== 1. The original bug: JSON array handed over as text ===")
check("t1-two-files", coerce({"path": '["a.txt", "b.txt"]'}, PROPS),
      {"path": ["a.txt", "b.txt"]})
check("t1-padded", coerce({"path": '  ["a.txt","b.txt"]  '}, PROPS),
      {"path": ["a.txt", "b.txt"]})
check("t1-single-element", coerce({"path": '["only.txt"]'}, PROPS),
      {"path": ["only.txt"]})
check("t1-empty-array", coerce({"path": "[]"}, PROPS), {"path": []})

print()
print("=== 2. Same array in Python repr form (single quotes, not JSON) ===")
check("t2-repr", coerce({"path": "['a.txt', 'b.txt']"}, PROPS),
      {"path": ["a.txt", "b.txt"]})

print()
print("=== 3. A plain path for a string-or-array parameter stays a string ===")
check("t3-plain", coerce({"path": "/home/kurt/text1.txt"}, PROPS),
      {"path": "/home/kurt/text1.txt"})

print()
print("=== 4. Real filenames that only look like containers ===")
check("t4-bracket-name", coerce({"path": "[v2].txt"}, PROPS), {"path": "[v2].txt"})
check("t4-broken-json", coerce({"path": "[1,"}, PROPS), {"path": "[1,"})
check("t4-unclosed", coerce({"path": '{"a": 1'}, PROPS), {"path": '{"a": 1'})

print()
print("=== 5. A string-only parameter keeps JSON text verbatim ===")
check("t5-object-text", coerce({"diff": '{"a": 1}'}, PROPS), {"diff": '{"a": 1}'})
check("t5-array-text", coerce({"diff": "[1, 2, 3]"}, PROPS), {"diff": "[1, 2, 3]"})

print()
print("=== 6. Array-only parameter: a bare scalar is one element ===")
check("t6-scalar", coerce({"paths": "a.txt"}, PROPS), {"paths": ["a.txt"]})
check("t6-list", coerce({"paths": '["a.txt", "b.txt"]'}, PROPS),
      {"paths": ["a.txt", "b.txt"]})

print()
print("=== 7. String-only parameter: a one-element list is that string ===")
check("t7-one", coerce({"diff": ["--- a\n"]}, PROPS), {"diff": "--- a\n"})
check("t7-many-left-alone", coerce({"diff": ["a", "b"]}, PROPS), {"diff": ["a", "b"]})

print()
print("=== 8. Scalars and unknown properties are never touched ===")
check("t8-bool", coerce({"flag": True, "count": 3}, PROPS), {"flag": True, "count": 3})
check("t8-unknown", coerce({"mystery": '["a"]'}, PROPS), {"mystery": '["a"]'})

print()
print("=== 9. anyOf is flattened like a type list ===")
check("t9-anyof-text", coerce({"target": '["a", "b"]'}, PROPS),
      {"target": ["a", "b"]})
check("t9-anyof-string", coerce({"target": "a"}, PROPS), {"target": "a"})

print()
print("=== 10. Nested containers survive the unwrap ===")
check("t10-nested", coerce({"path": '[{"a": [1, 2]}]'}, PROPS),
      {"path": [{"a": [1, 2]}]})

print()
print("=== 11. declared_types() and unwrap() directly ===")
check("t11-union", declared_types(PROPS, "path"), ["array", "string"])
check("t11-scalar", declared_types(PROPS, "diff"), ["string"])
check("t11-anyof", declared_types(PROPS, "target"), ["array", "string"])
check("t11-absent", declared_types(PROPS, "nope"), [])
check("t11-no-type", declared_types({"x": {"description": "d"}}, "x"), [])
check("t11-unwrap-list", unwrap('["a"]'), ["a"])
check("t11-unwrap-dict", unwrap('{"a": 1}'), {"a": 1})
check("t11-unwrap-none", unwrap("plain"), None)
check("t11-unwrap-scalar-json", unwrap("42"), None)

print()
print("=== 12. coerce() mutates and returns the same dict, keys preserved ===")
args = {"path": '["a", "b"]', "show_line_numbers": True}
check("t12-identity", coerce(args, PROPS) is args, True)
check("t12-keys", sorted(args.keys()), ["path", "show_line_numbers"])

print()
print("=== 13. Empty arguments are fine ===")
check("t13-empty", coerce({}, PROPS), {})

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
