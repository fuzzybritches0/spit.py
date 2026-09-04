#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Characterization tests for the streaming render pipeline (Process ->
PatternProcessing -> pattern_methods -> Part/Code).

The screen contract these tests pin down, and the bugs (P0 symptom c) they
reproduce:

- a `~~~~~` (5-tilde) fence run at the start of a line opens a code block
  (`Code` widget), the same kind of fence closes it. The pairing rule must
  be CommonMark's: a fence closes against the open fence of the SAME
  character and AT LEAST its length; every other fence-looking run is
  literal content. The old rule closed only on exact equality and, on a
  mismatch, pushed the foreign fence onto code_fences and kept it there -
  so a `~~~~ stderr ~~~~` run (run.py's STDERR_HEADER) inside the
  `~~~~~text` hint block poisoned the stack: the block never closed, the
  closing `~~~~~` of tool_end went into the wrong entry, and everything
  after the first mismatch arrived inside the wrong container. This is
  the confirmed cause of the garbled streamed tool output.
- the render of one and the same message must be independent of how the
  stream was split into callbacks (chunk-split invariance): every prefix
  callback advances the state machine without changing the final screen.

stub_textual.py stands in for the Textual backbone (TRAPS #19); the
pipeline itself runs for real. "The screen" is the ordered list of
(widget kind, final markdown source) the Process mounted.
"""
import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import stub_textual  # noqa: E402

stub_textual.install()

from spit_app.chat.message.content.process.containers.code import Code  # noqa: E402
from spit_app.chat.message.content.process.containers.part import Part  # noqa: E402
from spit_app.chat.message.content.process.process import Process  # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def make_process(scontent="content", role="assistant", name=None, hint=None):
    stub_textual.FakeApp(tools={name or "x": {"output_type_hint": hint}})
    message = types.SimpleNamespace(message={"role": role})
    if name:
        message.message["name"] = name
    chat = types.SimpleNamespace(chat_view=None)
    process = Process(chat, message, scontent)
    process.parent = types.SimpleNamespace(message=message)
    return process


def screen(process):
    out = []
    for child in process.children:
        if isinstance(child, Code):
            out.append(("Code", child.children[0].source))
        elif isinstance(child, Part):
            out.append(("Part", child.source))
    return out


async def drive_async(content, sizes, scontent="content", role="assistant",
                      name=None, hint=None):
    process = make_process(scontent, role, name, hint)
    pos = 0
    for size in sizes:
        pos = min(pos + size, len(content))
        await process.process(content[:pos])
        if pos >= len(content):
            break
    await process.finish(content)
    return screen(process)


def drive(content, chunk=None, **kwargs):
    if isinstance(chunk, int):
        sizes = [chunk] * len(content)
    else:
        sizes = [len(content)]
    return asyncio.run(drive_async(content, sizes, **kwargs))


async def drive_splits_async(content, splits, **kwargs):
    process = make_process(**kwargs)
    for split in splits:
        await process.process(content[:split])
    await process.finish(content)
    return screen(process)


def drive_splits(content, splits, **kwargs):
    return asyncio.run(drive_splits_async(content, splits, **kwargs))



print("=== 1. plain text: one Part, exact text, split independent ===")
PLAIN = "hello world, nothing special here"
check("t1-oneshot", drive(PLAIN), [("Part", PLAIN)])
for chunk in (1, 2, 3, 7, len(PLAIN)):
    check(f"t1-chunk-{chunk}", drive(PLAIN, chunk), [("Part", PLAIN)])

print("=== 2. a balanced ~~~~~ fence block renders as one Code widget ===")
FENCED = "intro\n~~~~~\ncode\n~~~~~\nend"
FENCED_SCREEN = [("Part", "intro\n"),
                 ("Code", "~~~~~\ncode\n~~~~~"),
                 ("Part", "\nend")]
check("t2-oneshot", drive(FENCED), FENCED_SCREEN)
for chunk in (1, 2, 3, 5, 11, len(FENCED)):
    check(f"t2-chunk-{chunk}", drive(FENCED, chunk), FENCED_SCREEN)
check("t2-two-splits", min([drive_splits(FENCED, [i]) == FENCED_SCREEN
                            for i in range(1, len(FENCED))]), True)

print("=== 3. mixed fence lengths: pairing, not equality (P0 symptom c) ===")
# a 4-tilde run inside a 5-tilde block is literal content and must NOT
# poison the open-block stack (the old code pushed it and the block
# never closed); a 4-tilde block stays open against a shorter ~~~ fence.
MIX = [
    ("4-in-5", "~~~~~text\nx\n~~~~ stderr ~~~~\ny\n~~~~~\n",
     [("Part", ""), ("Code", "~~~~~text\nx\n~~~~ stderr ~~~~\ny\n~~~~~"),
      ("Part", "\n")]),
    ("3-in-4", "~~~~\nx\n~~~\ny\n~~~~\n",
     [("Part", ""), ("Code", "~~~~\nx\n~~~\ny\n~~~~"), ("Part", "\n")]),
    ("backtick-in-tilde", "~~~~~text\n```\ncode\n```\nend\n~~~~~\n",
     [("Part", ""), ("Code", "~~~~~text\n```\ncode\n```\nend\n~~~~~"),
      ("Part", "\n")]),
    ("two-blocks", "a\n~~~~~\nx\n~~~~~\nb\n~~~~\ny\n~~~~\nc\n",
     [("Part", "a\n"), ("Code", "~~~~~\nx\n~~~~~"),
      ("Part", "\nb\n"), ("Code", "~~~~\ny\n~~~~"), ("Part", "\nc\n")]),
]
for name, content, expected in MIX:
    check(f"t3-{name}-oneshot", drive(content), expected)
    worst = min([drive_splits(content, [i]) == expected
                 for i in range(1, len(content))])
    check(f"t3-{name}-two-splits", worst, True)

print("=== 4. streamed tool response: run_command shape (hint + STDERR_HEADER) ===")
# the exact text run.run() streams for run_command (OUTPUT_TYPE_HINT text):
# tool_start prepends ~~~~~text\n, tool_end appends \n~~~~~, and the
# stderr block from run.py (STDERR_HEADER) crosses the fences.
TOOL_CONTENT = ("Running process...\n\nout line one\nout line two\n"
                "\n~~~~ stderr ~~~~\nerror line\n"
                "\nProcess exited with code 1.")
TOOL_SCREEN = [("Part", ""),
               ("Code", "~~~~~text\n" + TOOL_CONTENT + "\n~~~~~"),
               ("Part", "")]


def drive_tool(chunks):
    process = make_process(scontent="content", role="tool",
                           name="run_command", hint="text")
    async def go():
        pos = 0
        for size in chunks:
            pos = min(pos + size, len(TOOL_CONTENT))
            await process.process(TOOL_CONTENT[:pos])
        await process.finish(TOOL_CONTENT)
        return screen(process)
    return asyncio.run(go())


check("t4-tool-oneshot", drive_tool([len(TOOL_CONTENT)]), TOOL_SCREEN)
for chunk in (1, 5, 13, 26):
    check(f"t4-tool-chunk-{chunk}", drive_tool([chunk] * 200), TOOL_SCREEN)
check("t4-tool-all-two-splits",
      min([drive_tool([i, len(TOOL_CONTENT)]) == TOOL_SCREEN
           for i in range(1, len(TOOL_CONTENT))]), True)
# the opening hint fence appears exactly once no matter the chunk sizes
for chunk in (1, 2, 7):
    scr = drive_tool([chunk] * 500)
    joined = "".join(s for _, s in scr)
    check(f"t4-open-fence-once-{chunk}", joined.count("~~~~~text"), 1)

print("=== 5. tool-call render through the pipeline (P0 symptoms a+b, screen side) ===")


def drive_toolcall(args, chunk):
    process = make_process(scontent="tool_calls")
    async def go():
        part = {"name": "f", "arguments": ""}
        pos = 0
        while pos < len(args):
            pos = min(pos + chunk, len(args))
            part["arguments"] = args[:pos]
            await process.process(part)
        part["arguments"] = args
        await process.finish(part)
        return screen(process)
    return asyncio.run(go())


TWO_ARGS = '{"a":"b","c":"d"}'
TWO_ARGS_SCREEN = [
    ("Part", "\n### function: `f`\n#### arguments:\n`a`\n"),
    ("Code", "~~~~~\nb\n~~~~~"),
    ("Part", "\n`c`\n"),
    ("Code", "~~~~~\nd\n~~~~~"),
    ("Part", "\n"),
]
check("t5-toolcall-oneshot", drive_toolcall(TWO_ARGS, len(TWO_ARGS)),
      TWO_ARGS_SCREEN)
for chunk in (1, 2, 3, 5, 9, len(TWO_ARGS)):
    check(f"t5-toolcall-chunk-{chunk}", drive_toolcall(TWO_ARGS, chunk),
          TWO_ARGS_SCREEN)
check("t5-toolcall-all-two-splits",
      min([drive_toolcall(TWO_ARGS, i) == TWO_ARGS_SCREEN
           for i in range(1, len(TWO_ARGS))]), True)

EMPTY_ARGS_SCREEN = [("Part",
                      "\n### function: `lsterm`\n#### arguments:\n")]


def drive_empty():
    process = make_process(scontent="tool_calls")
    async def go():
        part = {"name": "lsterm", "arguments": ""}
        await process.process(part)
        part["arguments"] = "{}"
        await process.finish(part)
        return screen(process)
    return asyncio.run(go())


check("t5-empty-args-screen", drive_empty(), EMPTY_ARGS_SCREEN)

print("=== 6. an argument value containing ~~~~ fences stays literal (checklist: write_file with ~~~~) ===")
TILDE_ARGS = '{"a":"~~~~ stderr ~~~~"}'
TILDE_SCREEN = [
    ("Part", "\n### function: `f`\n#### arguments:\n`a`\n"),
    ("Code", "~~~~~\n~~~~ stderr ~~~~\n~~~~~"),
    ("Part", "\n"),
]
check("t6-tilde-oneshot", drive_toolcall(TILDE_ARGS, len(TILDE_ARGS)),
      TILDE_SCREEN)
check("t6-tilde-all-two-splits",
      min([drive_toolcall(TILDE_ARGS, i) == TILDE_SCREEN
           for i in range(1, len(TILDE_ARGS))]), True)

DASH_ARGS = '{"a":"----\\n---- diff ----"}'
DASH_SCREEN = [
    ("Part", "\n### function: `f`\n#### arguments:\n`a`\n"),
    ("Code", "~~~~~\n----\n---- diff ----\n~~~~~"),
    ("Part", "\n"),
]
check("t6-dash-oneshot", drive_toolcall(DASH_ARGS, len(DASH_ARGS)),
      DASH_SCREEN)
check("t6-dash-all-two-splits",
      min([drive_toolcall(DASH_ARGS, i) == DASH_SCREEN
           for i in range(1, len(DASH_ARGS))]), True)

print("=== 7. value with newlines ends balanced; no Part starts inside a block ===")
NL_ARGS = '{"a":"line one\\nline two"}'
NL_SCREEN = [
    ("Part", "\n### function: `f`\n#### arguments:\n`a`\n"),
    ("Code", "~~~~~\nline one\nline two\n~~~~~"),
    ("Part", "\n"),
]
check("t7-newline-oneshot", drive_toolcall(NL_ARGS, len(NL_ARGS)), NL_SCREEN)
check("t7-newline-all-two-splits",
      min([drive_toolcall(NL_ARGS, i) == NL_SCREEN
           for i in range(1, len(NL_ARGS))]), True)

print("=== 8. catch-up at finish: unfocused message renders identically ===")
check("t8-catchup-tool", drive_splits(TOOL_CONTENT, [], scontent="content",
                                      role="tool", name="run_command",
                                      hint="text"), TOOL_SCREEN)
check("t8-catchup-fenced", drive_splits(FENCED, [], scontent="content"),
      FENCED_SCREEN)

print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
