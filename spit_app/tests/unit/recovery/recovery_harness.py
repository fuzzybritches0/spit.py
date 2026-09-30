# SPDX-License-Identifier: GPL-2.0
"""Shared harness for unit:recovery (imported by test_*.py; the runner's glob
must not match this name - the `endpoint_harness.py` / `handoff_harness.py`
precedent).

WHAT THIS SUITE IS BUILT ON AND WHY IT IMPORTS `unit:handoff`
  P19/WP-4's whole mechanism is the handoff's: the continuation chat is opened
  through `create_and_submit` (WP-1 extracted it for exactly this), and what
  differs is WHO asks, what the first message says, and that the endpoint may be
  dead. So the harness does not rebuild `unit:handoff`'s world - it imports it:
  the real `Chat`, the real `SidePanel`, the real `Work`, the real `ToolCall`,
  the fixture shape, `mount_old`, `until`, `quiesce`, `new_id_from` and the
  counters. What it ADDS is the two things the recovery needs and a handoff
  never meets:

  * `RecoveryServer` - the canned server answering EVERY request for a reply
    with 503 while GET /models keeps answering the one model. That split IS the
    scenario of 84 b: the probe is answered, the request is not, so a recovery
    that probes and then submits is distinguishable from one that does neither.
  * `RecoveryApp` - the handoff's app with a `data` directory added. The journal
    lives at `settings.path["data"]/journal/` and HandoffApp has no `data` key;
    adding it here is what lets one case write a journal with the REAL
    `journal` tool and the next assert it inside the brief.

THE FAILURE IS DRIVEN THE HUMAN DRIVES IT
  `old.text_area.text = …` and `await old.text_area.action_submit()`: the real
  `Work`, the real retry loop, the real exhaustion, and then the real
  `report_failure`. Nothing calls `recover()` directly, so a recovery that only
  works when it is handed a convenient object is not what is being tested.

THE FIXTURES ARE THE RECOVERY'S OWN
  `./fixtures/recovery-data` - generated, removed after the run,
  `KEEP_FIXTURES=1` keeps - holding `chats/` (the real chat files the tool
  writes), `custom_tools/` and `data/journal/`. Nothing lives outside `./fixtures/`.
"""
import json
import os
import shutil
import sys
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 4))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
HANDOFF = os.path.join(REPO, "spit_app", "tests", "unit", "handoff")
if HANDOFF not in sys.path:
    sys.path.insert(0, HANDOFF)

import handoff_harness as H     # noqa: E402  (the module, for the redirect below)
from handoff_harness import (APP_SIZE, MODEL, OLD_ID, CannedServer,  # noqa: E402
                             HandoffApp, check, guarded, mount_old,
                             new_id_from, old_chat_content, quiesce, summary,
                             until)
from spit_app.tool_call import load_module_from_path  # noqa: E402

FIXTURES = Path(_HERE) / "fixtures"
DATA = FIXTURES / "recovery-data"

# Reusing `unit:handoff`'s app means inheriting the fixture home it reads out of
# its OWN module globals: `StubSettings.__init__` builds `path` from `DATA`, and
# `HandoffApp.__init__` builds the settings before any subclass can touch them
# (`ToolCall.__init__` already wants `path["custom_tools"]` to exist). So the
# globals are pointed at THIS suite's generated directory, which is the one lever
# that works before the app is built - and without it `unit:recovery` would
# either write into another suite's fixtures or not start at all.
H.FIXTURES = FIXTURES
H.DATA = DATA

# The transcript the brief is supposed to quote, and the two strings the checks
# look for. The second assistant turn is LONGER than the brief's per-message cap
# on purpose: the truncation marker is an assertion and the cut needs a control,
# which is the first turns appearing whole in the same brief.
FIRST_TEXT = "mm-recovery-first-question"
SECOND_TEXT = "mm-recovery-second-answer"
TURN_TEXT = "mm-recovery-turn-to-go"
LONG_TAIL = "mm-recovery-tail-that-must-be-cut"
JOURNAL_MARK = "mm-recovery-journal-entry"
JOURNAL_LEFT = "mm-recovery-journal-left-the-work"

# `spit_app/tools`, the directory the app loads its tools from - the same path
# `unit:journal`'s harness resolves (`journal_harness.py:52`).
TOOLS_DIR = Path(_HERE).resolve().parents[2] / "tools"
journal = load_module_from_path("tools.journal", TOOLS_DIR / "journal.py")


def recovery_chat_content(recovered_from: str = None) -> dict:
    """The handoff fixture's settings (endpoint "7" = the canned server, model,
    tools) with a transcript of two completed turns, so the tail the human
    submits next is a NEW user turn and the brief has something to quote."""
    content = old_chat_content()
    content["messages"] = [
        {"role": "user", "content": [{"type": "text", "text": FIRST_TEXT}]},
        {"role": "assistant", "reasoning": "",
         "content": [{"type": "text",
                      "text": f"{SECOND_TEXT} " + ("filler " * 200) + LONG_TAIL}]},
    ]
    if recovered_from is not None:
        content["settings"]["recovered_from"] = {
            "value": recovered_from, "stype": "string", "desc": "Recovered from"}
    return content


def make_data(recovered_from: str = None) -> None:
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    (DATA / "chats").mkdir(parents=True)
    (DATA / "custom_tools").mkdir()
    (DATA / "data").mkdir()
    (DATA / "chats" / f"{OLD_ID}.json").write_text(
        json.dumps(recovery_chat_content(recovered_from), indent=4))


def teardown() -> None:
    if not os.environ.get("KEEP_FIXTURES"):
        shutil.rmtree(FIXTURES, ignore_errors=True)


def chat_names() -> list:
    return sorted(p.name[:-5] for p in (DATA / "chats").iterdir())


def other_chat(names: list) -> str:
    """The one chat that is not the fixture's. `assert`-shaped on purpose: a
    case that finds two of them has a runaway recovery, and the name of the
    list is the evidence."""
    others = [name for name in names if name != OLD_ID]
    return others[0] if len(others) == 1 else f"EXPECTED-ONE-NEW-GOT-{others}"


def read_chat(chat_id: str) -> dict:
    return json.loads((DATA / "chats" / f"{chat_id}.json").read_text())


def first_message(chat_id: str) -> str:
    messages = read_chat(chat_id)["messages"]
    if not messages:
        return ""
    return messages[0]["content"][0]["text"]


def last_message(chat_id: str) -> dict:
    """The LAST message of a chat's file - which is where a notice has to be for
    the human to read it after a reload."""
    messages = read_chat(chat_id)["messages"]
    return messages[-1] if messages else {}


def message_text(message: dict) -> str:
    content = message.get("content")
    if not isinstance(content, list) or not content:
        return ""
    return str(content[0].get("text") or "")


def write_journal(app, entry: str, chat_id: str = OLD_ID) -> str:
    """A journal written through the REAL tool - `call(app, arguments, chat_id)`,
    the function the agent's tool call reaches - so the brief is asserted against
    the format the writer writes and not against a copy of it. `app.settings`
    carries `path["data"]` (RecoveryApp) and an empty `tool_settings`, which is
    the cap's default case."""
    return journal.call(app, {"entry": entry}, chat_id)


class RecoveryServer(CannedServer):
    """The canned server with the split that makes WP-4 testable.

    POSTs asking for a reply get 503 - a `TransientFailure`, which is the class
    WP-2 sends to recovery - while `/models` keeps answering, which is what
    makes the probe answer and the brief get submitted. `refuses_replies =
    False` hands the same server back to a case that needs a working endpoint;
    `server.stop()` is how a case makes the probe itself fail (84 b's DRAFT
    branch), and a stopped server records nothing more, which is what the
    draft case asserts on.
    """

    def __init__(self) -> None:
        super().__init__()
        self.refuses_replies = True

    def _reply(self, body: dict) -> tuple:
        if self.refuses_replies:
            return (503, b"mm-recovery-unavailable", "text/plain")
        return super()._reply(body)


class RecoveryApp(HandoffApp):
    """The handoff app + the data dir the journal lives in + the two retry
    fields set for a fast suite (1 attempt and no delay by default: this suite
    is about what happens AFTER the retries, and the retry counts themselves are
    `unit:endpoints` t14's)."""

    def __init__(self, server: RecoveryServer, attempts: int = 1,
                 delay: float = 0) -> None:
        super().__init__(server)
        self.settings.path["data"] = DATA
        endpoint = self.settings.endpoints["7"]
        endpoint["retry_attempts"] = {"value": attempts, "stype": "uinteger"}
        endpoint["retry_delay"] = {"value": delay, "stype": "ufloat"}


async def run_case(fn, attempts: int = 1, delay: float = 0,
                   recovered_from: str = None) -> None:
    """One fresh fixture dir, one fresh server, one fresh app - the shape of
    `handoff_harness.run_case` with the two switches this suite needs (a chat
    that is ITSELF a recovery, and the retry numbers). The finally-quiesce runs
    even when the case failed, for the reason that file states: a case that
    dies mid-stream must not have its own error replaced by a teardown race."""
    make_data(recovered_from)
    server = RecoveryServer().start()
    try:
        app = RecoveryApp(server, attempts=attempts, delay=delay)
        async with app.run_test(size=APP_SIZE) as pilot:
            await pilot.pause()
            try:
                await fn(app, pilot, server)
            finally:
                try:
                    await quiesce(pilot, app)
                except Exception:    # noqa: BLE001 - never mask the case's error
                    pass
    finally:
        server.stop()
        teardown()


async def fail_a_turn(app, pilot, text: str = TURN_TEXT):
    """Mount the old chat the way the sidebar does and send a turn into the
    server that will refuse it. Answers the old chat; the caller waits for
    whatever the failure is supposed to have produced."""
    old = await mount_old(app, pilot)
    old.text_area.text = text
    await old.text_area.action_submit()
    await pilot.pause()
    return old


async def recovery_appeared(pilot, timeout: float = 20.0) -> bool:
    """Wait for the recovery's chat file to exist - the event every assertion
    below it is about. `until` polls against pilot pauses, so this waits for
    the app's state and not for the clock."""
    return await until(pilot, lambda: len(chat_names()) > 1, timeout)


async def recovery_reported(pilot, timeout: float = 20.0) -> bool:
    """Wait for the LAST act of a successful recovery: the notice in the dead
    chat. The new chat's FILE is its FIRST act, so every assertion about the
    brief, the settings or the text area that reads the world the moment the
    file appears is reading a recovery that has not finished - a red on a busy
    machine, which is not a finding. The depth-cap case writes this notice too,
    so one wait serves every group."""
    return await until(pilot, lambda: "Recovery:" in
                       message_text(last_message(OLD_ID)), timeout)


def settings_of(chat_id: str) -> dict:
    return read_chat(chat_id)["settings"]


def settings_diff(old: dict, new: dict) -> list:
    """The keys the two chats' settings disagree on - the shape of the answer
    the entry demands: ONLY `desc` and `recovered_from` may differ, and the
    check is a set of key names, so an inherited entry whose VALUE drifted is
    named instead of the whole dict being dumped."""
    keys = set()
    for key in set(old) | set(new):
        if old.get(key) != new.get(key):
            keys.add(key)
    return sorted(keys)


def posted_briefs(server, marker: str = OLD_ID) -> list:
    """The recorded POST bodies that carry the recovery brief. The brief quotes
    the dead chat's id and no other message of either chat does, so the marker
    is the brief and not a coincidence - and the same marker on a stopped
    server is the absence a draft case asserts."""
    return server.bodies_with(marker)
