# SPDX-License-Identifier: GPL-2.0
"""The token-status hook: what the model is told about how full its window is.

This is P13/WP-C's hook - the state machine and the four texts. It satisfies
the contract WP-B pinned in `system_note.py`: `notice(chat, messages, index)`
returns a `Note(level, text)` or `None`, it carries `name = "token_status"`
for the generator to stamp (the generator enforces one note per hook per
message - the second note on a message this hook already spoke on is DROPPED,
not stored), and NOTHING catches what a hook raises: WP-D calls `attach()`
immediately before `endpoint.stream()`, so a hook that throws takes the request
down. Hence the hook is TOTAL - every unknown figure answers silence, and the
silence is also the door that keeps a request alive (DECISIONS 80 b: the dash
is a dash on the counts row, and a guessed denominator is a lie about when the
chat dies).

WHAT IT READS, and the DECIDE of the entry (how the total reaches the hook):
`used = chat.token_usage["context"]` - the server's own `prompt_tokens +
completion_tokens` of the last call (DECISIONS 80 c) - and
`total = chat.context_window()`, asked with `getattr`, callable-or-not,
present-or-not. That accessor does not exist on `Chat` yet: it is WP-D's, and
this module does not build it and knows no `Chat` and no Textual. A duck-typed
ask is the narrowest thing that keeps the hook out of the UI's import graph
(WP-B's one-attribute `MMChat` is the precedent: a hook is handed only what it
asks for), and it makes "chat cannot answer" and "window unknown" the same
rule: silence. Absent attribute, non-callable attribute, `None`, zero, a
negative, a string, a float - all unknown. Counts likewise: no `token_usage`,
no `"context"` key, a non-integer value - all unknown. Integers only, because
the counts the server reports are integers; `True` is not one of them.

THE LEVELS (owner ruling 2026-09-25, percentage OR remaining, whichever comes
first) and their ranks - `info` 1, `warning` 2, `critical` 3, and
`small_window` orthogonal (a statement about the window's SIZE, not a level
of fill):

  small_window  total <= 32768, once, whatever the fill, first time known
  info          used >= 50% of total
  warning       used >= 80% of total  OR  remaining <= 20 000
  critical      used >= 90% of total  OR  remaining <= 10 000

so on a 32k window `warning` triggers at 39% and `critical` at 69%, and `info`
(50%) is shadowed forever - a design rule, not a wart, and the reason the
machine advances BY RANK and never by trigger order: the highest level whose
trigger holds is the verdict, and it is announced only if its rank is strictly
above every rank already announced. The four numbers the owner named
(`32768 / 0.5 / 20000 / 10000`) are module constants, plus the table's two
percentages; tuning is a one-line change and a re-pin of the texts that quote
them (settings are follow-up (c)).

THE HOOK'S MEMORY IS ITS OWN STANDING NOTES, not instance state: it scans the
message list for entries stamped `hook == "token_status"` (its name, resolved
the same way the generator resolves it). That is WP-B's own principle - the
note IS the record - pushed into the hook, and it is what makes the three
awkward walks behave without any per-chat bookkeeping:

  * RELOAD - fresh instance, notes persisted, counts reset (P13's first
    consequence): an announced rank is never announced twice;
  * ABORT - `action_abort` removes the tail and with it its note (P13's third
    consequence): the record is gone, so the hook re-arms and re-says;
  * DROP - the server's figure can move while the same message is still the
    tail; a verdict the generator drops left no record, so it is not lost, it
    rides the next message (to say something newer, speak on a newer message).

The hook keeps NO state of its own, so a shared instance across chats cannot
cross-contaminate them either: the memory travels with the messages.

IT SPEAKS ONLY AT THE TAIL (`index == len(messages) - 1`): a note is written
once, at the tail, at the moment it becomes true, and from then on it is
history - that is what keeps the prompt prefix cached (P13's rationale). Being
asked at every index is the generator's walk; answering anywhere but the tail
would put a note into the middle of a chat and is the defect, not the feature.

THE FOUR TEXTS are model-facing text, i.e. CODE: the drafts of
`doc/TASKS-PLANNED.md` (wording delegated by the owner, ruling iii), pinned
byte-for-byte by `spit_app/tests/unit/system_note/test_token_status.py` t16
and re-pinned when the owner revisits them. Ruling iv arrived with P14:
`critical` now sends the model to the `handoff` tool; the fenced block
survives in the text as the fallback for a chat that has not the tool
selected - the machine, the levels and the load-bearing stop-clause
unchanged. They give
the model the verdict and the action, never arithmetic - except the figures
themselves, and no clamping: if the server's `used` exceeds the window the
text says so (negative remaining and all), because the numbers are the
server's and a rounded-down last word is a lie about the same kind.

Import NOTHING of Textual or httpx (TRAPS #19): this module must stay
importable - and `unit:system_note` runnable - on the bare interpreter, and
t10 of that suite is the gate that says it is.
"""
from spit_app.chat.system_note import NOTE_KEY, Note, hook_name

# The owner's four numbers, plus the table's two percentages. `WARNING_REMAINING
# = 2 * CRITICAL_REMAINING` is the implementer's choice the entry states so it
# can be argued with; the owner's floor is the 10k one.
SMALL_WINDOW_TOTAL = 32768
INFO_PERCENT = 0.5
WARNING_PERCENT = 0.8
CRITICAL_PERCENT = 0.9
WARNING_REMAINING = 20000
CRITICAL_REMAINING = 10000

# The ranks, and the whole of the ordering: the machine advances strictly
# upward through these, and `small_window` is deliberately NOT in here (it is
# orthogonal - it never raises a rank and no rank shadows it).
RANKS = {"info": 1, "warning": 2, "critical": 3}

# The four texts (see the module docstring: code, pinned, not prose).
TEXT_SMALL_WINDOW = (
    "This chat's context window is only {total} tokens. That is small enough "
    "to run out during ordinary work, so work narrowly: read the range you "
    "need, not whole files; open few files at a time; do not repeat a read "
    "you already have; keep what you print short.")
TEXT_INFO = (
    "Token status: {used} of {total} used ({pct}%), {remaining} left (the "
    "server's figure at the end of the last reply \u2014 the newest tool "
    "results are not in it yet). Nothing urgent: spend what is left on the "
    "task, not on re-reading.")
TEXT_WARNING = (
    "Token warning: {used} of {total} used ({pct}%), {remaining} left. Start "
    "closing out: no new files unless the task cannot go on without them, "
    "targeted reads instead of whole files, and begin writing down what you "
    "have done and what is still left, while you still have room to say it "
    "properly. If a `journal` tool is available, write an entry now: it is "
    "what a chat that takes this work over is told about first.")
TEXT_CRITICAL = (
    "Critical: {used} of {total} used ({pct}%), {remaining} tokens left. "
    "Stop working now. Write a `journal` entry first if the journal tool is "
    "available, then hand the work off NOW: call the `handoff` tool with "
    "your handoff message - the task in one line, what you changed (paths), "
    "what is unfinished, the exact next step, and anything you learned that "
    "is not in the repo. If no handoff tool is available, write that "
    "message as a fenced block instead. Do not call any more tools and do "
    "not start new work after the handoff \u2014 the chat dies inside this "
    "reply.")

# Highest first: the first trigger that holds IS the verdict, and a verdict at
# or below the announced rank says nothing (an implementation that tested the
# levels in trigger order would announce `info` at 50% on a 32k window whose
# `warning` fired at 39%, and t14 reddens it). `floor` None is `info`: the
# 50% notice has no remaining-token floor of its own, and can have none -
# every remaining floor is at or above its fill by construction here.
LEVELS = (
    ("critical", CRITICAL_PERCENT, CRITICAL_REMAINING, TEXT_CRITICAL),
    ("warning", WARNING_PERCENT, WARNING_REMAINING, TEXT_WARNING),
    ("info", INFO_PERCENT, None, TEXT_INFO),
)


class TokenStatus:
    """The token-status hook. One instance is stateless as to WHICH chat: its
    memory is the notes standing in the messages it is handed (see the module
    docstring), so WP-D can build it per `Chat` or share it, and a reload or
    an abort needs no resync because the record was never anywhere else."""

    name = "token_status"

    def notice(self, chat, messages, index):
        """At the tail, the verdict; everywhere else, silence.

        The figures are read defensively (the hook runs immediately before
        `endpoint.stream()` and nothing catches exceptions on that path):
        unknown total or unknown used is silence, never arithmetic and never
        a raised key - and silence is what keeps the request alive.
        """
        if index != len(messages) - 1:
            return None                    # notes are written at the tail and
                                           # from then on they are history
        total = self.total(chat)
        used = self.used(chat)
        if total is None or used is None:
            return None                    # unknown figure => dash => silence
        said = self.spoken_levels(messages)
        if "small_window" not in said and total <= SMALL_WINDOW_TOTAL:
            # The one-shot notice about the window's SIZE: the first time the
            # fill is known at all, whatever it is - it wins this message, and
            # any pending fill-rank rides the next one (one note per message).
            return Note("small_window", TEXT_SMALL_WINDOW.format(total=total))
        announced = max((RANKS.get(level, 0) for level in said), default=0)
        for level, percent, floor, text in LEVELS:
            if used >= percent * total or (floor is not None
                                           and used >= total - floor):
                # The highest triggered level - and only news if it outranks
                # everything this hook already wrote. Never downgrades: the
                # fill is a moving number, the announce record is not.
                if RANKS[level] <= announced:
                    return None
                return Note(level, text.format(
                    used=used, total=total, remaining=total - used,
                    pct=round(100 * used / total)))
        return None

    @staticmethod
    def used(chat):
        """`chat.token_usage["context"]` or None - no KeyError on a chat with
        no counts, no arithmetic on junk (integers only: the server's counts
        are integers, and True is not one)."""
        counts = getattr(chat, "token_usage", None)
        if not isinstance(counts, dict):
            return None
        used = counts.get("context")
        if isinstance(used, bool) or not isinstance(used, int):
            return None
        return used

    @staticmethod
    def total(chat):
        """`chat.context_window()` or None - the accessor is WP-D's and may be
        absent (this module must not know `Chat`), present-but-junk (a setting
        with no answer is a dash), or answer None for "no endpoint reported a
        window". An unknown window is silence, not a guess."""
        accessor = getattr(chat, "context_window", None)
        if not callable(accessor):
            return None
        total = accessor()
        if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
            return None
        return total

    def spoken_levels(self, messages) -> set:
        """The levels this hook already announced: its own stamped entries in
        the standing notes, and nobody else's. An entry whose level the machine
        does not know carries no rank (counts as 0) but still stands as
        history - it is not this hook's business to re-grade old wordings."""
        name = hook_name(self)
        return {entry.get("level")
                for message in messages
                for entry in message.get(NOTE_KEY, ())
                if entry.get("hook") == name}
