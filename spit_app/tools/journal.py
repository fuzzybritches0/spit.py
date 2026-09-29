# SPDX-License-Identifier: GPL-2.0
# P19/WP-3: the journal. The owner's second half of the failure-recovery brief -
# "a new tool the agent can use while still alive to keep records, which then
# becomes the recovery message in the new chat". It is an IN-PROCESS module tool
# with no `scripts/` script on purpose: a sandboxed script never sees the app's
# data dir (`bwrap_args()` binds `app_home/sandbox` over `/home/<user>` and
# `sandbox_tmp` over `/tmp`, tools/run/common.py), so a script tool could only
# write its records somewhere the recovery could not read them back. The shape
# is `set_chat_description`'s and `handoff`'s: `call(app, arguments, chat_id)`.
#
# Append-only, one file per chat, one timestamped entry per call, and the READ
# capped (DECISIONS 69 d's reasoning, the same one that caps a dead terminal's
# report at 50 lines): the tail of a journal is destined for a FRESH chat's
# context on the recovery path, which is exactly where the room is scarce, so
# `journal_max_chars` is a ceiling the tool applies rather than an error it
# raises. The journal is the IMPROVEMENT on a recovery message and never its
# only source (the P19 entry's alteration 3): a chat that never wrote one still
# gets an app-scaffolded brief, so nothing here may be load-bearing for the
# recovery to exist.
NAME = __file__.split("/")[-1][:-3]

MAX_CHARS = 4000               # the read cap's default, a setting (`journal_max_chars`)

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Append a timestamped entry to this chat's journal, or read it. "
            "With `entry` the entry is appended to the journal file and a short "
            "confirmation is returned; WITHOUT `entry` the journal is returned, "
            "newest last, capped at `journal_max_chars` characters from the "
            "end. The journal is yours to read and write while you work, and it "
            "is what a chat that inherits this one after an endpoint failure "
            "gets told about first, so write what the next agent needs, not "
            "what you already said in the chat."),
        "parameters": {
            "type": "object",
            "properties": {
                "entry": {
                    "type": "string",
                    "description": (
                        "The record to append. Leave it out to READ the "
                        "journal instead - `entry` writes and no `entry` reads, "
                        "one tool for both.")
                }
            },
            "required": []
        }
    }
}

PROMPT = (
    "Use the journal to keep the record a fresh agent would need to continue "
    "your work - your own crash-recovery note, written while you are still "
    "alive. Write it at the moments where losing the thread would cost the "
    "most: after every commit (what the commit was, its branch and sha), "
    "before a risky operation (what you are about to change and why), and "
    "IMMEDIATELY on a token-status warning or critical note, before you write "
    "a handoff. Keep each entry short and factual in the fields that record "
    "work: Branch / Scope / Done / Left / State hazards / Verify - plus "
    "anything you learned that is not in the repo. Append-only: an entry is "
    "never edited or deleted, so the journal also says when a plan changed. "
    "Call it WITHOUT `entry` to read what you have written; the read is capped "
    "at `journal_max_chars` characters counted from the END, because the "
    "journal is what a successor chat is told about first and the cap is what "
    "keeps that affordable. It is a record, not a checkpoint: nothing reads it "
    "back except a reader who asks, so it never changes what this chat does.")

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "journal_max_chars": { "value": MAX_CHARS, "stype": "uinteger", "empty": False,
                           "desc": "Journal read cap (characters, from the end)" }
}

OUTPUT_TYPE_HINT = "text"

import os
import re
import time
from spit_app.tool_call import load_user_settings


# One entry = a marker line, its body, and a blank line. The marker is its own
# full line and nothing else on the line, so a body line that happens to open
# with `[` - a markdown checkbox, a footnote, a bracketed tag - is body and
# never a second entry. Entries are MULTI-LINE on purpose: the fields the
# PROMPT asks for (Branch / Scope / Done / Left / …) are one entry, not five.
ENTRY_MARK = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]$", re.MULTILINE)


def journal_path(app, chat_id: str):
    # One file per chat, under the app's own data dir - the path a sandboxed
    # script cannot reach, which is the whole reason this tool is in-process.
    #
    # The id is WHITELISTED, not checked for `..`: it becomes a file name, and a
    # blacklist has to be right every time while the whitelist has to be right
    # once. A chat id in this app is `chat-<digits-and-dashes>`; anything else
    # - ``, `..`, `a/b`, `a\b`, an id that is not a string - is a name no chat of
    # this app has, and the answer is a refusal that writes nothing rather than
    # a file somewhere else.
    if not isinstance(chat_id, str) or not CHAT_ID_FORM.fullmatch(chat_id):
        return None
    return app.settings.path["data"] / "journal" / f"{chat_id}.txt"


CHAT_ID_FORM = re.compile(r"[A-Za-z0-9_-]+")


def read_journal(app, chat_id: str, max_chars: int) -> str:
    # The read half, on its own because WP-4's recovery brief appends the same
    # text and must apply the same cap for the same reason.
    file = journal_path(app, chat_id)
    if file is None or not file.exists():
        return ("No journal for this chat yet. `journal(entry=\"…\")` writes "
                "one; a fresh agent that inherits this chat gets the app's own "
                "recovery brief either way, so a journal is an improvement on "
                "that and not its source.")
    text = file.read_text(encoding="utf-8", errors="replace")
    entries = count_entries(text)
    cap = max_chars if isinstance(max_chars, int) and max_chars > 0 else MAX_CHARS
    if len(text) <= cap_of(max_chars):
        return (f"Journal of {chat_id}: {entries} entries, {len(text)} "
                f"characters, all of it (newest last):\n{text}")
    shown = cut_to_entries(text, cap_of(max_chars))
    return (f"Journal of {chat_id}: {entries} entries, {len(text)} characters, "
            f"SHOWING THE LAST {len(shown)} FROM THE END (the cap is "
            f"`journal_max_chars` = {cap_of(max_chars)}; what is cut is whole "
            f"entries and is still in the file):\n{shown}")


def cut_to_entries(text: str, cap: int) -> str:
    # The cut is made at an ENTRY boundary, not at character `cap`: half an
    # entry is worse than none, because a reader who was not here cannot tell
    # a truncated record from a complete one. Take the last `cap` characters,
    # then walk forward to the first marker in that window; if the window holds
    # no marker at all it is the tail of ONE entry, so start at that entry's own
    # marker and report it whole even when it is longer than the cap - the
    # newest record is the one a recovery must never be handed cut in half.
    shown = text[-cap:]
    match = ENTRY_MARK.search(shown)
    if match is not None:
        return shown[match.start():]
    starts = ENTRY_MARK.findall(text)
    if not starts:
        return shown
    last = 0
    for marker in ENTRY_MARK.finditer(text):
        last = marker.start()
    return text[last:]


def cap_of(max_chars) -> int:
    # The cap is a setting, so it can be anything a settings file holds: a
    # string, a float, 0 (which would show nothing), a negative. Anything that
    # is not a positive number of characters answers the module default - the
    # `retry_attempts` rule of 84 (a), and a blanked field (`value: None`) is
    # that case too, not a crash and not an uncapped read.
    # The setting is a `uinteger`, so an INT is the only answer: a float, a
    # string, a bool, None and a negative are all "not a number of characters"
    # and all get the default. Truncating a float here would be a policy nobody
    # asked for - 1.5 becoming 1 is a cap that reads almost nothing.
    if isinstance(max_chars, bool) or not isinstance(max_chars, int):
        return MAX_CHARS
    if max_chars <= 0:
        return MAX_CHARS
    return max_chars


def effective_cap(app) -> int:
    # The cap comes from THIS app's settings, not from the module's SETTINGS
    # dict. The house pattern is `load_user_settings(app, NAME, SETTINGS)`,
    # which COPIES the user's values INTO that dict - and the dict is module
    # state, shared by every chat in the process, so a value read back out of
    # it after some other chat's call is that chat's number (measured: a chat
    # whose cap was 300 left the next chat, which has no saved cap at all,
    # reading 300 too). Reading the setting where it lives, with the module
    # value as the fallback for a settings file written before this tool
    # existed, is one line more and makes the answer the app's own.
    saved = app.settings.tool_settings.get(NAME, {}) if hasattr(app, "settings") else {}
    field = saved.get("journal_max_chars") if isinstance(saved, dict) else None
    value = field.get("value") if isinstance(field, dict) else None
    if value is None:
        value = MAX_CHARS
    return cap_of(value)


def count_entries(text: str) -> int:
    # Counted from the text and not from a store: a hand-edited or copied file
    # still answers honestly, and this count is what the tool PRINTS, so a wrong
    # count is a wrong result and not a wrong log line.
    return len(ENTRY_MARK.findall(text))


def call(app, arguments: dict, chat_id: str) -> str|None:
    # A PLAIN `def`, not `async def`, and that is the DECISIONS 68 rule rather
    # than a style choice: `tool_call.ToolCall.call()` runs a plain function
    # through `asyncio.to_thread`, so the journal's disk I/O happens off the
    # event loop, while `async def` would run it ON the loop. What this tool
    # touches is the data dir and nothing else - no widget, no mount, no
    # worker - so there is no reason to pay for the loop's patience (the
    # `handoff`/`set_chat_description` pair is async precisely because it IS
    # widget work). A sync `call` is also what a suite can drive directly.
    load_user_settings(app, NAME, SETTINGS)
    file = journal_path(app, chat_id)
    if file is None:
        return ("ERROR: no journal for this chat - the chat id the call came "
                "with is not a name a file can take. Nothing was written.")
    max_chars = effective_cap(app)
    entry = arguments.get("entry")
    if entry is None or (isinstance(entry, str) and not entry.strip()):
        return read_journal(app, chat_id, max_chars)
    if not isinstance(entry, str):
        return ("ERROR: `entry` must be a string of text (or left out to read "
                "the journal). Nothing was written.")
    try:
        os.makedirs(file.parent, exist_ok=True)
        with open(file, "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n"
                         f"{entry.strip()}\n\n")
    except OSError as exception:
        return f"ERROR: could not write the journal: {exception}. Nothing was written."
    written = count_entries(file.read_text(encoding="utf-8", errors="replace"))
    return (f"Journal ok: entry {written} appended to `{file}`. It is the "
            f"record a successor chat is told about, so write the next agent's "
            f"answer, not this chat's note to yourself.")
