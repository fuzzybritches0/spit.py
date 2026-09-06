#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Characterization tests for how `chat/work.py` assembles the system prompt.

The model reads this text and nothing else about the tools, so its shape is the
contract. Two breaks matter and both were broken:

  * PROMPT and PROMPT_INST ran into each other ("...hold paths.Timeout is set to
    0.") because `prompt()` concatenated them with no separator;
  * one tool's block ran into the NEXT tool's `## heading`, because the same
    `prompt()` concatenated the blocks too. In Markdown a `##` is only a heading
    at the start of a line, so with 18 of 19 tool prompts not ending in a
    newline the assembled prompt carried one heading and eighteen words with
    `##` in the middle of them -- the section boundaries the model is supposed
    to read were invisible. Measured on the real tool set before the fix:
    "1 of 19" headings started a line.

Both fixes live in `prompt()`/`prompt_inst()`, so the separator is owned by the
source and no longer by whether each tool author remembered a trailing newline.
These tests pin the assembled shape: exactly one line break between a tool's own
prompt and its instructions, exactly one blank line between tool blocks, every
heading at the start of a line, and a prompt that ends in newlines (or not)
rendering identically.
"""
import ast
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import stub_modules  # noqa: E402

stub_modules.install()

from spit_app.chat.work import Work, TOOL_PROMPT  # noqa: E402

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def work(tools, selected=None, tool_settings=None, chat_prompt="", prompts=None,
         has_image=True):
    """A Work whose prompt assembly runs for real, with everything else stubbed.

    `Work.__init__` builds an endpoint, which is not what is under test, so the
    attributes `prompt()` reads are set directly: the tool table, the chat's own
    selections, the user's tool settings and the chat prompt.
    """
    table = {}
    for name, spec in tools.items():
        table[name] = {
            "settings": {setting: {"value": value}
                         for setting, value in spec.get("settings", {}).items()},
            "requires_multimodal_image": spec.get("requires_multimodal_image", False),
        }
        if "prompt_inst" in spec:
            table[name]["prompt_inst"] = spec["prompt_inst"]

    app = types.SimpleNamespace(
        tool_call=types.SimpleNamespace(tools=table),
        settings=types.SimpleNamespace(tool_settings=tool_settings or {},
                                       prompts=prompts or {}),
    )
    selected = list(tools.keys()) if selected is None else selected
    work = Work.__new__(Work)
    work.app = app
    work.settings = app.settings
    work.cs = lambda key: {"tools": selected, "prompt": chat_prompt}.get(key, "")
    work.chat = types.SimpleNamespace(has_cap=lambda cap: has_image)
    return work


def tool(prompt, prompt_inst=None, multimodal=None, **settings):
    """One entry of the tool table, in the shape `tool_call.load_tools` builds:
    `settings` are the tool's own defaults (what `[token]` in PROMPT_INST is
    substituted from), `multimodal` is the REQUIRES_MULTIMODAL_IMAGE flag."""
    spec = {"settings": {"prompt": prompt, **settings},
            "requires_multimodal_image": bool(multimodal)}
    if prompt_inst is not None:
        spec["prompt_inst"] = prompt_inst
    return spec


print("=== 1. One tool: heading, text, instructions ===")
built = work({"alpha": tool("Alpha does things.", "Timeout is [timeout].", timeout=0)}).prompt()
check("t1-exact", built,
      TOOL_PROMPT + "## alpha\n\nAlpha does things.\nTimeout is 0.")
check("t1-heading-opens-a-line", built.split("\n").count("## alpha"), 1)
check("t1-inst-opens-a-line", built.split("\n").count("Timeout is 0."), 1)
check("t1-token-substituted", "[timeout]" in built, False)

print()
print("=== 2. PROMPT and PROMPT_INST do not run into each other ===")
glued = work({"alpha": tool("...hold paths.", "Timeout is set to 0.")}).prompt()
check("t2-not-glued", "paths.Timeout" in glued, False)
check("t2-one-break", "paths.\nTimeout is set to 0." in glued, True)
check("t2-not-a-paragraph-gap", "paths.\n\nTimeout" in glued, False)
check("t2-trailing-newline-in-prompt-changes-nothing",
      work({"alpha": tool("...hold paths.\n", "Timeout is set to 0.")}).prompt(), glued)
check("t2-prompt_inst-does-not-need-its-own-break",
      work({"alpha": tool("...hold paths.", "\nTimeout is set to 0.\n")}).prompt(), glued)

print()
print("=== 3. Two tools: the heading is never mid-line ===")
pair = work({"alpha": tool("Alpha does things."),
             "bravo": tool("Bravo does things.", "Timeout is set to 0.")}).prompt()
check("t3-exact", pair,
      TOOL_PROMPT + "## alpha\n\nAlpha does things.\n\n"
      "## bravo\n\nBravo does things.\nTimeout is set to 0.")
check("t3-no-heading-inside-a-line",
      [line for line in pair.split("\n") if "##" in line[1:]], [])
check("t3-one-blank-line-between-blocks", "things.\n\n## bravo" in pair, True)
check("t3-no-triple-break-anywhere", "\n\n\n" in pair, False)
check("t3-trailing-newline-in-a-prompt-changes-nothing",
      work({"alpha": tool("Alpha does things.\n\n"),
            "bravo": tool("Bravo does things.", "Timeout is set to 0.")}).prompt(), pair)

print()
print("=== 4. prompt_inst() on its own ===")
two = work({"alpha": tool("Text.", "First [a] second [b].", a=1, b="two")})
check("t4-substitutes-every-setting", two.prompt_inst("alpha"), "\nFirst 1 second two.")
check("t4-leading-break", two.prompt_inst("alpha").startswith("\n"), True)
none = work({"alpha": tool("Text.")})
check("t4-tool-without-prompt_inst", none.prompt_inst("alpha"), "")
blank = work({"alpha": tool("Text.", "\n\n")})
check("t4-blank-prompt_inst-is-empty", blank.prompt_inst("alpha"), "")

print()
print("=== 5. User settings win over the module, for both halves ===")
overridden = work({"alpha": tool("Module text.", "Module [timeout].", timeout=5)},
                  tool_settings={"alpha": {"prompt": {"value": "User text."},
                                           "timeout": {"value": 9}}})
check("t5-user-prompt-used", overridden.prompt(),
      TOOL_PROMPT + "## alpha\n\nUser text.\nModule 9.")
check("t5-partial-user-settings",
      work({"alpha": tool("Module text.", "Module [timeout].", timeout=5)},
           tool_settings={"alpha": {"timeout": {"value": 7}}}).prompt(),
      TOOL_PROMPT + "## alpha\n\nModule text.\nModule 7.")

print()
print("=== 6. Which tools are in it ===")
check("t6-unselected-tool-excluded",
      work({"alpha": tool("A."), "bravo": tool("B.")}, selected=["alpha"]).prompt(),
      TOOL_PROMPT + "## alpha\n\nA.")
check("t6-no-tools-no-tool_prompt",
      work({"alpha": tool("A.")}, selected=[]).prompt(), "")
mm = work({"alpha": tool("A.", multimodal=True)}, has_image=False)
check("t6-mm_tool_without_the_capability_excluded", mm.prompt(), "")
mm_ok = work({"alpha": tool("A.", multimodal=True)}, has_image=True)
check("t6-mm_tool_with_the_capability_included",
      mm_ok.prompt(), TOOL_PROMPT + "## alpha\n\nA.")

print()
print("=== 7. The chat prompt still wraps the tool prompts ===")
prompts = {"serious": {"text": {"value": "Be terse."}}}
check("t7-chat_prompt-prefix",
      work({"alpha": tool("A.")}, chat_prompt="serious", prompts=prompts).prompt(),
      "# INSTRUCTIONS\n\nBe terse.\n\n" + TOOL_PROMPT + "## alpha\n\nA.")
check("t7-unknown_chat_prompt_ignored",
      work({"alpha": tool("A.")}, chat_prompt="ghost", prompts=prompts).prompt(),
      TOOL_PROMPT + "## alpha\n\nA.")
check("t7-chat_prompt_with_no_tools",
      work({"alpha": tool("A.")}, selected=[], chat_prompt="serious",
           prompts=prompts).prompt(), "# INSTRUCTIONS\n\nBe terse.\n\n")

print()
print("=== 8. The real tool modules, assembled for real ===")
# Every PROMPT and PROMPT_INST in the tree, read out of the source: importing a
# tool module needs the app's dependencies, which the test python does not have
# (TRAPS #19), and the shapes checked here are all this needs. The mapping is
# asserted before it is trusted (TRAPS #13): a probe that found no tools would
# pass every check below vacuously.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
TOOLS_DIR = os.path.join(REPO_ROOT, "spit_app", "tools")
real, without_prompt = {}, []
for module_name in sorted(os.listdir(TOOLS_DIR)):
    if not module_name.endswith(".py"):
        continue
    with open(os.path.join(TOOLS_DIR, module_name)) as handle:
        source = ast.parse(handle.read())
    found = {}
    for node in source.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("PROMPT", "PROMPT_INST"):
                    found[target.id] = ast.literal_eval(node.value)
    if "PROMPT" not in found:
        without_prompt.append(module_name)
        continue
    real[module_name[:-3]] = tool(found["PROMPT"], found.get("PROMPT_INST"))

assembled = work(real).prompt()
check("t8-every_module_defines_a_prompt", without_prompt, [])
check("t8-tools_found", len(real) > 15, True)
check("t8-one_heading_per_tool", sum(1 for line in assembled.split("\n")
                                     if line.startswith("## ")), len(real))
check("t8-no_heading_mid_line", [line for line in assembled.split("\n")
                                 if "##" in line[1:]], [])
check("t8-no_blank_line_runs", "\n\n\n" in assembled, False)
glued = [name for name, spec in real.items() if spec.get("prompt_inst") and
         "\n" + spec["prompt_inst"].strip().split("\n")[0] not in assembled]
check("t8-no_instructions_glued_to_their_prompt", glued, [])

print()
print("==============================")
print(f"PASS: {pass_}  FAIL: {fail_}")
sys.exit(1 if fail_ else 0)
