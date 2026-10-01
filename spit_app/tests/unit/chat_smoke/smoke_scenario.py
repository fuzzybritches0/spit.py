# SPDX-License-Identifier: GPL-2.0
"""The WP-B differential smoke: ONE scripted walk over a real Chat, dumped
canonically, run against two trees - the pre-refactor tip and the refactor.

It began (WP-B, 2026-09) as a differential proof in the sense of TRAPS
#14/#18: a green suite cannot see a refactor that quietly addressed a different
widget, so the proof is a byte-for-byte dump of a scripted walk, taken against
an older tree. That purpose outlived the refactor and the sliding window that
followed it and their revert (DECISIONS 89): `golden.txt` is the OLD tree's
output - generated from `f201700`, before any of it - and it is what proved the
revert restored the old behaviour rather than a new one.

Version-agnostic on purpose. It drives the PUBLIC app surface (load, focus,
edit_on/off, the message-level add/remove actions, the stream callbacks, the
undo/redo actions, abort) and dumps plain data, so it can drive a tree that
looks nothing like this one. The invariants of THIS tree live in
test_chat_smoke.py, which imports this file - and so do the fixture chat and the
stub app that `unit:endpoints`, `unit:handoff` and `unit:recovery` import.

Run it directly to print or regenerate the canonical dump:

    python3 smoke_scenario.py                        # the tree this file is in
    python3 smoke_scenario.py --tree /tmp/spit-base  # another tree
    python3 smoke_scenario.py --out golden.txt
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Markdown, TextArea

APP_SIZE = (80, 24)
CHAT_ID = "smoke-chat"


# ----------------------------------------------------------------- the fixture
# Generated, never committed (TRAPS #10): a fixture chat holding the shapes
# the coupling surface actually touches - plain user/assistant turns,
# reasoning (the show_cots path), tool_calls plus a tool result (the
# message-level add/remove paths), and text content that renders into Process
# widgets so the widget tree under each Message is part of the dump.

def fixture_settings() -> dict:
    return {
        "endpoint": {"value": "1"},
        "model": {"value": "none"},
        "model_settings": {"value": None},
        "tools": {"value": []},
        "prompt": {"value": None},
    }


def fixture_chat() -> dict:
    return {
        "ctime": "2026-01-01T00:00:00",
        "settings": fixture_settings(),
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "one"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "two"}],
             "reasoning": "thinking"},
            {"role": "user", "content": [{"type": "text", "text": "three"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "four"}],
             "tool_calls": [{"id": "call-1", "type": "function",
                             "function": {"name": "read_files", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call-1", "name": "read_files",
             "content": [{"type": "text", "text": "tool output"}]},
        ],
    }


# ------------------------------------------------------------------ stub app
# The three things Chat asks an app for and nothing else (the unit:terminal /
# unit:sandbox stub_app.py precedent). Deliberately NOT SpitApp: the real app
# starts the llama.cpp server, reads the user's own settings and chats, and
# loads the whole tool tree - none of it under test, all of it machine-
# dependent output. `read_json` hands out a fresh deep copy so the fixture
# literal cannot be mutated between the two runs.

class StubSettings:
    def __init__(self) -> None:
        self.active_chat = None
        self.tool_settings = {}
        self.models = {}
        self.prompts = {}
        self.llamacpp = {}
        self.endpoints = {}
        self.downloads = {}

    def save(self) -> None:
        pass


class FakeSidePanel(Widget):
    """ChatView.ensure_is_highlighted() queries `#side-panel` and highlights
    this chat in it; that is all this stands in for (no OptionList)."""

    def get_option_index(self, chat_id: str) -> int:
        return 0


class FakeWork:
    """What Chat.action_abort() pokes: `busy` picks the branch, `cancel()` is
    the observable effect, `is_running` keeps is_working() answering."""

    def __init__(self, busy: bool = False) -> None:
        self.busy = busy
        # P19/WP-2: `action_abort` reads `busy or retrying`, so the stub that
        # stands in for `Work` here must carry the attribute or every abort step
        # of the golden run raises AttributeError.
        self.retrying = False
        self.is_running = False
        self.exit_after_busy = False
        self.cancelled = 0

    def cancel(self) -> None:
        self.cancelled += 1


class StubToolCall:
    """Process.tool_output_type_hint() reads app.tool_call.tools[name] for a
    tool result's OUTPUT_TYPE_HINT; the real tool tree is not under test."""

    def __init__(self) -> None:
        self.tools = {"read_files": {"output_type_hint": "text"}}


class SmokeApp(App[None]):
    def __init__(self, content: dict) -> None:
        super().__init__()
        self.settings = StubSettings()
        self.tool_call = StubToolCall()
        self.store = {f"chats/{CHAT_ID}.json": content}
        self.writes = []
        self.chat = None

    # --- the app surface Chat / ChatView / Message actually use
    def read_json(self, key: str):
        return json.loads(json.dumps(self.store[key]))

    def write_json(self, key: str, content) -> bool:
        self.store[key] = json.loads(json.dumps(content))
        self.writes.append(key)
        return True

    def endpoint_list_tuple(self) -> tuple:
        return (("None", "1"),)

    def endpoint_list(self) -> dict:
        return {}

    def get_endpoint(self, endpoint_id: str) -> dict:
        return {}

    # --- composition: the real Chat inside an app shell
    def compose(self) -> ComposeResult:
        with Horizontal(id="app"):
            yield FakeSidePanel(id="side-panel")
            yield Vertical(id="main")

    async def on_mount(self) -> None:
        from spit_app.chat.chat import Chat
        await self.query_one("#main").mount(Chat(CHAT_ID))
        self.chat = self.query_one(f"#{CHAT_ID}")


# ------------------------------------------------------------------ the dump
# Canonical and machine-independent: app-level data only - no widget reprs, no
# paths, no timings. `focused` names the focused widget by what a user could
# tell apart; the per-child lines carry the widget tree's shape under each
# Message, which is what an index-accessor bug would move.

def name_of(app) -> str:
    from spit_app.chat.chat_view import ChatView
    from spit_app.chat.message.message import Message
    widget = app.focused
    if widget is None:
        return "none"
    if isinstance(widget, TextArea):
        return "text-area"
    if isinstance(widget, Message):
        children = list(widget.chat_view.children)
        return f"message[{children.index(widget) if widget in children else -1}]"
    if isinstance(widget, ChatView):
        return "chat-view"
    return type(widget).__name__


def text_of(message, scontent: str) -> str:
    """The rendered text of one Message under one content key, in mount order:
    the Part (Markdown) sources, process by process. This is the projection an
    index-accessor bug would move - data identical, widgets swapped."""
    out = []
    container = message.cnt.get(scontent)
    if container is not None:
        for process in container.children:
            out.append(" ".join(part.source for part in process.children
                                if isinstance(part, Markdown)))
    return "|".join(out)


def facts(app, chat) -> dict:
    view = chat.chat_view
    children = list(view.children)
    per_child = []
    for child in children:
        per_child.append({
            "role": child.role,
            "cnt": sorted(child.cnt.keys()),
            "cots": ("reasoning" in child.cnt and child.cnt["reasoning"].display),
            "is_edit": child.is_edit,
            "is_removing": child.is_removing,
            "has_focus": child.has_focus,
            "text": text_of(child, "content"),
            "reasoning_text": text_of(child, "reasoning"),
            "tool_calls_text": text_of(child, "tool_calls"),
        })
    return {
        "children": len(children),
        "roles": [c.role for c in children],
        "messages": len(chat.messages),
        "messages_md5": hashlib.md5(
            json.dumps(chat.messages, sort_keys=True).encode()).hexdigest(),
        "data_list_identity": view.messages is chat.messages,
        "per_child": per_child,
        "view_is_edit": view.is_edit,
        "view_is_removing": view.is_removing,
        "focused": name_of(app),
        "focused_message": (children.index(view.focused_message)
                            if view.focused_message in children else -1),
        "undo_index": chat.undo.undo_index,
        "undo_list": [[entry[0], entry[2] if len(entry) > 2 else None]
                      for entry in chat.undo.undo_list],
        "writes": len(app.writes),
        "store_md5": hashlib.md5(json.dumps(app.store, sort_keys=True).encode()).hexdigest(),
        "scroll_y": round(view.scroll_y, 2),
        "text_area_text": chat.text_area.text,
        "text_area_was_focused": chat.text_area.was_focused,
        "work_cancelled": getattr(getattr(chat, "_work", None), "cancelled", None),
        "exit_after_busy": getattr(getattr(chat, "_work", None), "exit_after_busy", None),
    }


# ---------------------------------------------------------------- the script
async def settle(pilot, passes: int = 4) -> None:
    for _ in range(passes):
        await pilot.pause()


async def step_load(app, chat, pilot):
    await chat.chat_view.load()


async def step_focus_view(app, chat, pilot):
    # the user path back to the message list: focus leaves the text area and
    # ChatView.on_focus -> enter() -> focus_this() picks the last message
    # (Textual auto-focuses the ChatView at mount, so focus it away first)
    chat.text_area.focus()
    await settle(pilot, 2)
    chat.chat_view.focus()


async def step_edit_on(app, chat, pilot):
    chat.chat_view.action_edit_on()


async def step_edit_off(app, chat, pilot):
    await chat.chat_view.action_edit_off()


async def step_focus_next(app, chat, pilot):
    chat.chat_view.action_next_message()
    chat.chat_view.action_next_message()


async def step_focus_prev(app, chat, pilot):
    chat.chat_view.action_previous_message()


async def step_add_message_next(app, chat, pilot):
    # focus an assistant turn and grow a reply after it: mount at index+1
    chat.chat_view.action_previous_message()
    await settle(pilot, 2)
    await chat.chat_view.focused_message.action_add_message_next()


async def step_add_message_prev(app, chat, pilot):
    await chat.chat_view.children[0].action_add_message_prev()


async def step_stream_start(app, chat, pilot):
    chat.messages.append({"role": "assistant", "reasoning": "",
                          "content": [{"type": "text", "text": ""}]})
    chat.chat_view.callback(len(chat.messages) - 1, 1)


async def step_stream_process(app, chat, pilot):
    chat.messages[-1]["content"][0]["text"] += "streamed"
    chat.messages[-1]["reasoning"] += "musing"
    chat.chat_view.callback(len(chat.messages) - 1, 2)


async def step_stream_finish(app, chat, pilot):
    chat.chat_view.callback(len(chat.messages) - 1, 0)


async def step_undo(app, chat, pilot):
    await chat.chat_view.action_undo()


async def step_redo(app, chat, pilot):
    await chat.chat_view.action_redo()


async def step_remove_tool(app, chat, pilot):
    chat.chat_view.children[-1].action_remove()


async def step_remove_first(app, chat, pilot):
    chat.chat_view.children[0].action_remove()


async def step_undo_remove(app, chat, pilot):
    await chat.chat_view.action_undo()


async def step_undo_remove_first(app, chat, pilot):
    await chat.chat_view.action_undo()


async def step_focus_after_abort(app, chat, pilot):
    # NOT an undo: action_abort removes the tail without recording an undo
    # entry (a wart of the pre-window code, filed not fixed), so an undo here
    # would replay the entry before it - out of range. This step pins the
    # state abort leaves behind, and keeps focus moving afterwards.
    chat.chat_view.action_next_message()
    await settle(pilot, 2)
    chat.chat_view.action_previous_message()


async def step_abort_busy(app, chat, pilot):
    chat._work = FakeWork(busy=True)
    chat.work = chat._work
    await chat.action_abort()


async def step_abort(app, chat, pilot):
    chat._work.busy = False
    await chat.action_abort()


async def step_add(app, chat, pilot):
    await chat.chat_view.action_add()


STEPS_POPULATED = [
    ("01-load", step_load),
    ("02-focus-view", step_focus_view),
    ("03-edit-on", step_edit_on),
    ("04-focus-next", step_focus_next),
    ("05-focus-prev", step_focus_prev),
    ("06-add-message-next", step_add_message_next),
    ("07-add-message-prev", step_add_message_prev),
    ("08-stream-start", step_stream_start),
    ("09-stream-process", step_stream_process),
    ("10-stream-finish", step_stream_finish),
    ("11-undo-insert", step_undo),
    ("12-redo-insert", step_redo),
    ("13-remove-tool", step_remove_tool),
    ("14-undo-remove", step_undo_remove),
    ("15-remove-first", step_remove_first),
    ("16-undo-remove-first", step_undo_remove_first),
    ("17-abort-busy", step_abort_busy),
    ("18-abort", step_abort),
    ("19-focus-after-abort", step_focus_after_abort),
    ("20-edit-off", step_edit_off),
]

# action_add is only reachable when the chat has no messages (its check_action
# says so), so it gets its own headed run on an empty fixture.
STEPS_EMPTY = [
    ("E1-load-empty", step_load),
    ("E2-edit-on-empty", step_edit_on),
    ("E3-add", step_add),
    ("E4-undo-add", step_undo),
    ("E5-redo-add", step_redo),
    ("E6-edit-off-empty", step_edit_off),
]


async def run_scenario(on_step) -> None:
    for steps, content in ((STEPS_POPULATED, fixture_chat()),
                           (STEPS_EMPTY, {"ctime": "2026-01-01T00:00:00",
                                          "settings": fixture_settings(),
                                          "messages": []})):
        app = SmokeApp(content)
        async with app.run_test(size=APP_SIZE) as pilot:
            await settle(pilot)
            chat = app.chat
            for name, step in steps:
                await step(app, chat, pilot)
                await settle(pilot)
                on_step(name, app, chat)


# ---------------------------------------------------------------------- main
def dump(steps: list) -> str:
    lines = []
    for name, fact in steps:
        lines.append(f"=== STEP {name}")
        for key in sorted(fact.keys()):
            value = fact[key]
            if key == "per_child":
                for index, child in enumerate(value):
                    lines.append(f"  child[{index}] " + " ".join(
                        f"{k}={child[k]}" for k in sorted(child.keys())))
            elif isinstance(value, (list, dict)):
                lines.append(f"  {key}={json.dumps(value, sort_keys=True)}")
            else:
                lines.append(f"  {key}={value}")
    return "\n".join(lines) + "\n"


async def collect() -> list:
    steps = []

    def on_step(name, app, chat):
        steps.append((name, facts(app, chat)))

    await run_scenario(on_step)
    return steps


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", default=os.path.abspath(os.path.join(here, *[".."] * 4)),
                        help="spit.py tree whose spit_app/chat code is driven")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    sys.path.insert(0, os.path.abspath(args.tree))
    text = dump(asyncio.run(collect()))
    if args.out:
        with open(args.out, "w") as file:
            file.write(text)
        print(f"wrote {args.out} ({len(text.splitlines())} lines, "
              f"md5 {hashlib.md5(text.encode()).hexdigest()})")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
