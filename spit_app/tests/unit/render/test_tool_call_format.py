#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Characterization tests for the tool-call arguments formatter (tool_call.py).

The formatter turns the raw JSON text a model streams for a tool call into
the on-screen Markdown of `process/tool_call.py`. Its public contract is:

- ToolCall({"name": ..., "arguments": ...}).tool_call_arguments() may be
  called repeatedly while "arguments" grows (the streaming path: llamacpp
  accumulates fragments and the callback re-processes the cumulative text),
  and must also work called once with the complete JSON (the save path in
  text_area_tool.py);
- every call returns the full render so far; the render must only ever
  grow - characters already returned are never rewritten or dropped;
- the final render is independent of how the JSON was split across calls;
- each argument renders as: `key` fence value fence - the `~~~~~` fences
  are the shared code-block language of the render pipeline, and EVERY
  render must contain an even number of them. An odd count leaves the
  last value inside an unclosed code block and shifts every later fence
  (this is the P0 stray-fence bug: the old code never emitted the closing
  fence of the last value, and leaked the top-level `}` whenever the
  object closed while a key was still expected, as it does for `{}`);
- the top-level brackets are invisible; a nested container is a value and
  renders as raw JSON, fenced like any other value;
- inside JSON strings, escape pairs decode to what the model meant: \\n
  renders as a real newline, \\t as a tab, \\" as a quote, \\\\ as one
  backslash; backslash + anything else renders as both characters. The old
  whole-string post-pass could not tell a JSON escape from the formatter's
  own emitted newlines and ate fence newlines after backslash-heavy values
  (P0 symptom a), and its single-character quote-escape test broke on
  values ending in a backslash (P0 symptom b, second path).

tool_call.py imports nothing - system python3 runs this suite directly
(TRAPS #19).
"""
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.chat.message.content.process.tool_call import ToolCall  # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


HEADER = "\n### function: `f`\n#### arguments:\n"


def render(arguments):
    return ToolCall({"name": "f", "arguments": arguments}).tool_call_arguments()


def render_streamed(arguments, sizes):
    """The streaming path: the growing cumulative string re-renders per callback."""
    part = {"name": "f", "arguments": ""}
    tc = ToolCall(part)
    prev = ""
    pos = 0
    for n in sizes:
        pos = min(pos + n, len(arguments))
        part["arguments"] = arguments[:pos]
        now = tc.tool_call_arguments()
        if not now.startswith(prev):
            return "REWRITE:" + now
        prev = now
        if pos >= len(arguments):
            return now
    return prev


SHAPES = {
    "empty-object": ("{}", HEADER),
    "one-arg": ('{"a":"b"}', HEADER + "`a`\n~~~~~\nb\n~~~~~\n"),
    "two-args": ('{"a":"b","c":"d"}',
                 HEADER + "`a`\n~~~~~\nb\n~~~~~\n`c`\n~~~~~\nd\n~~~~~\n"),
    "number-arg": ('{"n":123}', HEADER + "`n`\n~~~~~\n123\n~~~~~\n"),
    "true-null": ('{"b":true,"z":null}',
                  HEADER + "`b`\n~~~~~\ntrue\n~~~~~\n`z`\n~~~~~\nnull\n~~~~~\n"),
    "empty-string-value": ('{"a":""}', HEADER + "`a`\n~~~~~\n\n~~~~~\n"),
    "empty-then-filled": ('{"a":"","b":"z"}',
                          HEADER + "`a`\n~~~~~\n\n~~~~~\n`b`\n~~~~~\nz\n~~~~~\n"),
    "nested-object": ('{"o":{"x":1}}', HEADER + "`o`\n~~~~~\n{\"x\":1}\n~~~~~\n"),
    "nested-empty": ('{"o":{}}', HEADER + "`o`\n~~~~~\n{}\n~~~~~\n"),
    "array": ('{"a":[1,2]}', HEADER + "`a`\n~~~~~\n[1,2]\n~~~~~\n"),
    "array-strings": ('{"a":["p","q"]}',
                      HEADER + "`a`\n~~~~~\n[\"p\",\"q\"]\n~~~~~\n"),
    "array-objects": ('{"a":[{"x":1},{"y":2}]}',
                      HEADER + "`a`\n~~~~~\n[{\"x\":1},{\"y\":2}]\n~~~~~\n"),
    "newline-in-value": ('{"a":"x\\ny"}', HEADER + "`a`\n~~~~~\nx\ny\n~~~~~\n"),
    "tab-in-value": ('{"a":"x\\ty"}', HEADER + "`a`\n~~~~~\nx\ty\n~~~~~\n"),
    "quote-in-value": ('{"a":"x\\"y"}', HEADER + "`a`\n~~~~~\nx\"y\n~~~~~\n"),
    "backslash-in-value": ('{"a":"c:\\\\dir\\\\sub"}',
                           HEADER + "`a`\n~~~~~\nc:\\dir\\sub\n~~~~~\n"),
    "backslash-end-value": ('{"a":"c:\\\\dir\\\\"}',
                            HEADER + "`a`\n~~~~~\nc:\\dir\\\n~~~~~\n"),
    "backslash-then-escaped-n": ('{"a":"c:\\\\ny"}',
                                 HEADER + "`a`\n~~~~~\nc:\\ny\n~~~~~\n"),
    "escaped-backslash-then-newline": ('{"a":"x\\\\\\ny"}',
                                       HEADER + "`a`\n~~~~~\nx\\\ny\n~~~~~\n"),
    "unknown-escape": ('{"a":"q\\u1234"}', HEADER + "`a`\n~~~~~\nq\\u1234\n~~~~~\n"),
    "tilde-in-value": ('{"a":"~~~~ stderr ~~~~"}',
                       HEADER + "`a`\n~~~~~\n~~~~ stderr ~~~~\n~~~~~\n"),
    "unicode": ('{"a":"h\u00e9llo\u2192"}', HEADER + "`a`\n~~~~~\nh\u00e9llo\u2192\n~~~~~\n"),
    "space-after-colon": ('{"a": "b"}', HEADER + "`a`\n~~~~~\nb\n~~~~~\n"),
    "space-after-comma": ('{"a":"b", "c":"d"}',
                          HEADER + "`a`\n~~~~~\nb\n~~~~~\n `c`\n~~~~~\nd\n~~~~~\n"),
    "braces-inside-string": ('{"a":"{ }","b":"[x]"}',
                             HEADER + "`a`\n~~~~~\n{ }\n~~~~~\n`b`\n~~~~~\n[x]\n~~~~~\n"),
    "second-arg-path": ('{"cmd":"ls","path":"C:\\\\tmp\\\\"}',
                        HEADER + "`cmd`\n~~~~~\nls\n~~~~~\n`path`\n~~~~~\nC:\\tmp\\\n~~~~~\n"),
    "colon-in-string": ('{"a":"x:y"}', HEADER + "`a`\n~~~~~\nx:y\n~~~~~\n"),
    "comma-in-string": ('{"a":"x,y"}', HEADER + "`a`\n~~~~~\nx,y\n~~~~~\n"),
}

print("=== 1. whole-string render, one golden per shape ===")
for name, (arguments, expected) in SHAPES.items():
    check(f"t1-{name}", render(arguments), expected)

print("=== 2. empty arguments render nothing after the header (no stray }) ===")
check("t2-empty-oneshot", render("{}"), HEADER)
check("t2-empty-streamed", render_streamed("{}", [1, 1]), HEADER)
part = {"name": "f", "arguments": "{"}
tc = ToolCall(part)
tc.tool_call_arguments()
part["arguments"] = "{}"
check("t2-empty-streamed-across-calls", tc.tool_call_arguments(), HEADER)
check("t2-brace-never-ends-an-empty-render", "{}" in render("{}")[len(HEADER):], False)

print("=== 3. fence parity: even \\n~~~~~\\n, and no 4-tilde separator left ===")
for name, (arguments, expected) in SHAPES.items():
    check(f"t3-parity-{name}", render(arguments).count("\n~~~~~\n") % 2, 0)
    check(f"t3-parity-golden-{name}", expected.count("\n~~~~~\n") % 2, 0)
    check(f"t3-no-4tilde-{name}", render(arguments).count("\n~~~~\n"), 0)

print("=== 4. streaming: 1-char, 2-char, and random splits end at the golden ===")
for name, (arguments, expected) in SHAPES.items():
    check(f"t4-one-char-{name}", render_streamed(arguments, [1] * len(arguments)),
          expected)
    check(f"t4-two-char-{name}", render_streamed(arguments, [2] * len(arguments)),
          expected)
    rnd = random.Random(20250904)
    sizes = [rnd.randint(1, 7) for _ in range(len(arguments))]
    check(f"t4-random-{name}", render_streamed(arguments, sizes), expected)

print("=== 5. the render only ever grows: no call rewrites an earlier one ===")
for name, (arguments, expected) in SHAPES.items():
    part = {"name": "f", "arguments": ""}
    tc = ToolCall(part)
    prev = ""
    rewrote = ""
    for pos in range(len(arguments) + 1):
        part["arguments"] = arguments[:pos]
        now = tc.tool_call_arguments()
        if not now.startswith(prev):
            rewrote = f"at {pos}: {prev!r} -> {now!r}"
            break
        prev = now
    check(f"t5-monotonic-{name}", rewrote, "")

print("=== 6. the save path: one call with complete JSON (text_area_tool.py) ===")
saved = {"name": "write_file", "arguments": '{"path":"a b.txt","content":"x\\ny"}'}
check("t6-save-path",
      ToolCall(saved).tool_call_arguments(),
      "\n### function: `write_file`\n#### arguments:\n`path`\n~~~~~\na b.txt\n~~~~~"
      "\n`content`\n~~~~~\nx\ny\n~~~~~\n")

print("=== 7. a tool call that streamed no arguments fragment does not crash ===")
part = {"name": "lsterm"}
tc = ToolCall(part)
try:
    check("t7-no-arguments", tc.tool_call_arguments(),
          "\n### function: `lsterm`\n#### arguments:\n")
except KeyError as e:
    check("t7-no-arguments", f"KeyError {e}", "no exception")

print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
