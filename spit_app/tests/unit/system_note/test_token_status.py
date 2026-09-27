#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""P13/WP-C - the token-status hook: the four levels, the rank machine, the four texts.

WHAT THIS PINS (and the contract it writes against, pinned by WP-B - do not
re-litigate it)
  `spit_app/chat/token_status.py` exposes `TokenStatus`, a hook: `name =
  "token_status"`, `notice(chat, messages, index)` returning `Note(level, text)`
  (the generator's OWN namedtuple, re-exported) or `None`. The generator stamps
  `hook`, enforces one note per hook per message forever, and catches nothing -
  so the hook must be TOTAL: no arithmetic on a `None` total, no KeyError on a
  chat with no counts. Unknown figure ⇒ silence, and that silence is also the
  door that keeps a request alive.

  The hook speaks ONLY at the tail (`index == len(messages) - 1`): a note is
  written once, at the tail, and from then on it is history (the prefix-cache
  argument of P13). Mid-conversation notes are the defect, not the feature.

THE TOTAL REACHES THE HOOK THROUGH `chat.context_window()` - the DECIDE the
entry asked for. The hook asks the chat for it with `getattr`, callable or not,
present or not: WP-D adds the accessor to `Chat`; `token_status.py` knows no
`Chat`, imports no Textual, and a chat that cannot answer has an unknown window
and is silent. The stub chats below hand over `messages`, `token_usage` and this
one method, and nothing else is ever asked (WP-B's one-attribute `MMChat` is
the precedent: a hook is handed only what it asks for).

THE LEVELS (owner ruling 2026-09-25: percentage OR remaining, whichever comes
first) and the ranks - `info` 1, `warning` 2, `critical` 3, `small_window`
orthogonal. The machine advances BY RANK, never by trigger order: the highest
level whose trigger holds is announced, and only if its rank is strictly above
every rank already announced. On a 32k window `warning` triggers at 39% and
`info` (50%) is shadowed forever - a design rule, pinned by t14.

THE HOOK'S MEMORY IS ITS OWN STANDING NOTES, not instance state: it scans the
message list for entries stamped `hook == "token_status"`. That is WP-B's own
principle - the note IS the record - pushed into the hook, and it is what makes
the three awkward walks behave: a RELOAD (fresh instance, old notes, counts
reset) never re-announces an announced rank; an ABORT (the tail's note removed
with the tail) re-arms the hook exactly as P13's consequence (3) promises; and a
verdict the generator DROPS because this hook already spoke on that message left
no record, so it is not lost - it rides the next message (t17).

THE TEXTS are model-facing text, i.e. CODE: byte-for-byte pins from the drafts
in `doc/TASKS-PLANNED.md` (wording delegated by the owner, ruling iii), at
fixtures where {used}/{total}/{remaining}/{pct} are all distinct, so a used-vs-
remaining swap cannot pass. The "do not call any more tools and do not start
new work after the handoff" half of `critical` is load-bearing (the owner
learned it the hard way); P14 (Go! 2026-09-26) replaced the fenced-block
clause with the `handoff` tool call and the fenced text became the fallback
for a chat without the tool - a text change plus this re-pin, the same
commit, the stop-clause byte-identical.

NUMBERS are append-only WITHIN THIS FILE (TRAPS #15): t10-t18 belong to WP-C.
t1-t9 are WP-B's `test_generator.py` - which must stay green alongside this
file, every run: a red there means the contract was bent to the hook. The
`unit:endpoints` sequence is separate again (t12 is WP-A's, t13 is WP-D's).

TRAPS #13: every silence here has the control that makes the same hook speak.
TRAPS #19 (inherited from WP-B's runner, inverted): this file and its module
run on the BARE python3; t10 is the gate, and a Textual or httpx import in
`token_status.py` reddens it loudly. TRAPS #18: every group runs inside
`guarded()`; read the whole output, not just the row.
"""
import json
import os
import sys

# repo root is four levels up: system_note/ <- unit/ <- tests/ <- spit_app/
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 4))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from spit_app.chat import system_note as note_mod  # noqa: E402  (the contract)
from spit_app.chat import token_status as ts       # noqa: E402  (the code under test)

NOTE_KEY = note_mod.NOTE_KEY

# What the app needs at runtime (requirements.txt) and this module must never
# pull in - the same list as WP-B's t1, which gates the same way.
APP_DEPENDENCIES = ("textual", "httpx", "libtmux")

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def guarded(group, fn):
    """Run one check group: a crash is ONE red, never a dead file whose row is
    whatever happened to be counted before it died (the WP-B runner reads the
    sum, and the outer runner reads only `tail -n 1` - TRAPS #18)."""
    try:
        fn()
    except Exception as exception:  # noqa: BLE001 - that is the whole point
        import traceback
        traceback.print_exc()
        check(f"{group}-did-not-crash", f"{type(exception).__name__}: {exception}",
              "None")


def dumps(obj) -> str:
    """Byte-for-byte comparison form: sorted keys, so dict order cannot lie."""
    return json.dumps(obj, sort_keys=True)


# --------------------------------------------------------------- the fixtures
# The hook is handed a chat; the hook asks three things of it and nothing else:
# `messages`, `token_usage["context"]` (the server's own figure, DECISIONS 80 c)
# and `context_window()`. Plain objects, no Textual, no endpoint, no network.
TOTAL_64K = 65536
TOTAL_128K = 131072
TOTAL_200K = 200000


class StubChat:
    """The chat as far as this hook is concerned. `context_window()` is exactly
    the accessor WP-D will add to `Chat`; here it answers what the test says,
    including None - the dash, the unknown window, the silence."""

    def __init__(self, total=TOTAL_128K, used=0, messages=None):
        self.messages = ([{"role": "user", "content": "mm-user-one"}]
                         if messages is None else list(messages))
        self.token_usage = {"context": used, "generated": 0, "cached": 0}
        self._total = total

    def context_window(self):
        return self._total


class WindowlessChat:
    """A chat whose class has no `context_window` at all - the state before
    WP-D, or a chat object some other code path hands over. `getattr` must find
    nothing: an absent accessor is silence, not an AttributeError."""

    def __init__(self, used=120000):
        self.messages = [{"role": "user", "content": "mm-user-one"}]
        self.token_usage = {"context": used}


def attach(chat, hook):
    """One request in WP-D's shape: `SystemNotes(chat).attach()` immediately
    before `endpoint.stream()` - through the REAL generator, so the once-per-
    message rule, the stamping and the drop are the shipped ones, not a stub."""
    saved = note_mod.HOOKS
    note_mod.HOOKS = [hook]
    try:
        note_mod.SystemNotes(chat).attach()
    finally:
        note_mod.HOOKS = saved


def reply(chat, role="assistant"):
    """A reply landed or a tool ran: a NEW message stands at the tail, which is
    the only place a newer claim from one voice can go."""
    chat.messages.append({"role": role, "content": f"mm-msg-{len(chat.messages)}"})


def spoken(chat) -> list:
    """The announce record: every level this hook ever wrote, in message order."""
    return [entry["level"] for message in chat.messages
            for entry in message.get(NOTE_KEY, [])
            if entry.get("hook") == "token_status"]


def without_system(chat) -> str:
    """Everything the hook has no business touching, byte for byte."""
    return dumps([{k: v for k, v in message.items() if k != NOTE_KEY}
                  for message in chat.messages])


def walk(chat, hook, steps, group):
    """The shape of a working chat: attach (the request), then a new message
    arrives, then attach again - with the server's figure set before each
    attach. Every step compares the WHOLE announce record, so an extra note
    anywhere is a red, not just a missing one."""
    for step, (used, expected) in enumerate(steps):
        if step:
            reply(chat)
        chat.token_usage = {"context": used}
        attach(chat, hook)
        check(f"{group}-at-used-{used}", spoken(chat), list(expected))


# ------------------------------------------------------------------------- t10
def t10_the_gate_and_the_shape():
    """TRAPS #19 inherited: the hook must stay importable on the bare
    interpreter, and the gate is the same probe WP-B's t1 runs - measured on
    the repository's own file, with the control that the probe sees a module
    that IS loaded. The rest of the group is what the contract and the entry
    require the hook to LOOK like: the name the generator will stamp, the
    generator's own Note (the generator isinstance-checks it - a homegrown
    namedtuple of the same shape would raise TypeError at the request), and
    the owner's four numbers plus the table's two percentages as module
    constants, so tuning is the one-line change the entry promises."""
    check("t10-imported-the-repositories-own-hook",
          os.path.realpath(ts.__file__),
          os.path.realpath(os.path.join(REPO, "spit_app", "chat",
                                        "token_status.py")))
    offenders = sorted({name.split(".")[0] for name in sys.modules
                        if name.split(".")[0] in APP_DEPENDENCIES})
    check("t10-importing-it-loaded-no-app-dependency", offenders, [])
    check("t10-importing-it-pulled-nothing-but-its-own-namespace",
          sorted(name for name in sys.modules if name.startswith("spit_app.")),
          ["spit_app.chat", "spit_app.chat.system_note",
           "spit_app.chat.token_status"])
    # THE CONTROL (TRAPS #13): the same expression over a module that IS loaded.
    check("t10-CONTROL-the-same-probe-sees-a-module-that-is-loaded",
          sorted({name.split(".")[0] for name in sys.modules
                  if name.split(".")[0] == "json"}), ["json"])
    hook = ts.TokenStatus()
    check("t10-the-hook-carries-the-name-the-generator-stamps",
          hook.name, "token_status")
    check("t10-the-hook-has-notice", callable(getattr(hook, "notice", None)), True)
    check("t10-the-Note-it-returns-is-the-generators-own", ts.Note, note_mod.Note)
    check("t10-the-owners-four-numbers-are-module-constants",
          (ts.SMALL_WINDOW_TOTAL, ts.INFO_PERCENT,
           ts.WARNING_REMAINING, ts.CRITICAL_REMAINING),
          (32768, 0.5, 20000, 10000))
    check("t10-the-tables-two-percentages-are-module-constants",
          (ts.WARNING_PERCENT, ts.CRITICAL_PERCENT), (0.8, 0.9))
    check("t10-the-three-ranked-levels", ts.RANKS,
          {"info": 1, "warning": 2, "critical": 3})
    check("t10-small_window-is-not-a-rank", "small_window" in ts.RANKS, False)


# ------------------------------------------------------------------------- t11
def t11_silence_one_token_below_the_first_trigger():
    """Silent below every trigger - and the boundary itself is the control: one
    token more and the SAME chat speaks. 65 536 is exactly 50% of 131 072."""
    chat = StubChat(total=TOTAL_128K, used=65535)
    hook = ts.TokenStatus()
    before = dumps(chat.messages)
    attach(chat, hook)
    check("t11-one-token-below-info-writes-nothing", dumps(chat.messages), before)
    chat.token_usage = {"context": 65536}
    attach(chat, hook)
    check("t11-CONTROL-one-token-later-the-same-chat-speaks-info",
          spoken(chat), ["info"])


def t11_silence_at_zero_usage():
    """A chat that knows its window but has sent nothing: silence, with the
    same chat as the control."""
    chat = StubChat(total=TOTAL_128K, used=0)
    hook = ts.TokenStatus()
    attach(chat, hook)
    check("t11-zero-usage-writes-nothing", spoken(chat), [])
    chat.token_usage = {"context": 65536}
    attach(chat, hook)
    check("t11-CONTROL-the-same-chat-above-half-speaks", spoken(chat), ["info"])


def t11_silence_when_the_counts_are_not_there():
    """`attach()` runs immediately before `endpoint.stream()` and nothing
    catches what a hook raises, so a chat with no counts must be silence, not a
    KeyError or a TypeError - this is the door that keeps a request alive."""
    hook = ts.TokenStatus()
    chat = StubChat(total=TOTAL_128K, used=120000)   # would be critical with counts
    del chat.token_usage
    raised = None
    try:
        attach(chat, hook)
    except Exception as exception:  # noqa: BLE001
        raised = f"{type(exception).__name__}: {exception}"
    check("t11-no-token_usage-attribute-raises-nothing", raised, None)
    check("t11-no-token_usage-attribute-writes-nothing",
          dumps(chat.messages), dumps([{"role": "user", "content": "mm-user-one"}]))
    chat.token_usage = {"context": 65536}
    attach(chat, hook)
    check("t11-CONTROL-the-same-chat-with-counts-speaks", spoken(chat), ["info"])

    no_context = StubChat(total=TOTAL_128K)
    no_context.token_usage = {"generated": 7, "cached": 1}   # no "context" key
    attach(no_context, hook)
    check("t11-no-context-key-writes-nothing", spoken(no_context), [])
    no_context.token_usage["context"] = 65536
    attach(no_context, hook)
    check("t11-CONTROL-the-same-chat-with-the-key-speaks", spoken(no_context),
          ["info"])


def t11_silence_when_the_window_is_unknown():
    """Unknown total ⇒ silence (DECISIONS 80 b: the dash is a dash on the
    counts row, and a guessed denominator is a lie about when the chat dies) -
    even at a fill that would be `critical` under any real total."""
    chat = StubChat(total=None, used=120000)
    hook = ts.TokenStatus()
    attach(chat, hook)
    check("t11-an-unknown-window-writes-nothing", spoken(chat), [])
    chat._total = TOTAL_128K
    attach(chat, hook)
    check("t11-CONTROL-the-same-usage-under-a-known-window-is-critical",
          spoken(chat), ["critical"])


def t11_silence_when_the_chat_has_no_accessor():
    """The accessor does not exist until WP-D adds it, and a chat that answers
    no `context_window` at all is an ordinary input, not a crash: the hook asks
    with getattr and accepts the silence it gets."""
    hook = ts.TokenStatus()
    chat = WindowlessChat(used=120000)
    raised = None
    try:
        attach(chat, hook)
    except Exception as exception:  # noqa: BLE001
        raised = f"{type(exception).__name__}: {exception}"
    check("t11-a-chat-without-context_window-raises-nothing", raised, None)
    check("t11-a-chat-without-context_window-writes-nothing",
          [NOTE_KEY in message for message in chat.messages], [False])
    control = StubChat(total=TOTAL_128K, used=120000)
    attach(control, hook)
    check("t11-CONTROL-the-same-usage-on-a-chat-that-answers-speaks",
          spoken(control), ["critical"])


def t11_the_hook_speaks_only_at_the_tail():
    """The generator asks at EVERY index; a note must land at the tail and
    nowhere else - a note written into the middle of a chat rewrites the cached
    prompt prefix and is the defect P13 exists to avoid. The fixture is full
    enough for `critical`, so a hook that talked at every position could not
    hide from this."""
    chat = StubChat(total=TOTAL_128K, used=130000, messages=[
        {"role": "user", "content": "mm-user-one"},
        {"role": "assistant", "content": "mm-answer-one"},
        {"role": "tool", "tool_call_id": "mm-call-1", "content": "mm-tool-result"},
    ])
    attach(chat, ts.TokenStatus())
    check("t11-only-the-tail-carries-a-note",
          [NOTE_KEY in message for message in chat.messages],
          [False, False, True])
    check("t11-CONTROL-and-the-tail-really-got-it", spoken(chat), ["critical"])


def t11_an_empty_transcript_silences_the_hook():
    """No messages means no tail, and `notice()` must be total for that too -
    the generator never asks index 0 of an empty list, so this is the direct
    call (a control on the same hook and fixture with a tail stands right after
    it, t11-the-hook-speaks-only-at-the-tail)."""
    chat = StubChat(total=TOTAL_128K, used=130000, messages=[])
    check("t11-no-message-no-note", ts.TokenStatus().notice(chat, chat.messages, 0),
          None)


# ------------------------------------------------------------------------- t12
def t12_the_machine_advances_by_rank_and_each_level_fires_once():
    """On a 128k window the three levels come in rank order, each exactly once,
    with nothing in between: between the triggers, and after the fill DROPS
    back down, no new note appears (never downgrade - the fill is a moving
    number, the announce record is not)."""
    chat = StubChat(total=TOTAL_128K, used=0)
    hook = ts.TokenStatus()
    walk(chat, hook, [
        (0, []),                                        # known, but nothing holds
        (65536, ["info"]),                              # exactly 50%
        (70000, ["info"]),                              # between: nothing new
        (105000, ["info", "warning"]),                  # 80% wins first (floor 111072)
        (78000, ["info", "warning"]),                   # fill drops: NO downgrade note
        (118000, ["info", "warning", "critical"]),      # 90% wins first
        (130000, ["info", "warning", "critical"]),      # above it again: still one
    ], "t12")
    check("t12-each-level-was-written-at-its-own-message",
          [(index, entry["level"]) for index, message in enumerate(chat.messages)
           for entry in message.get(NOTE_KEY, [])],
          [(1, "info"), (3, "warning"), (5, "critical")])
    check("t12-three-notes-and-the-private-key-appears-on-them-alone",
          [sorted(message) for message in chat.messages],
          [["content", "role"], ["content", "role", NOTE_KEY],
           ["content", "role"], ["content", "role", NOTE_KEY],
           ["content", "role"], ["content", "role", NOTE_KEY],
           ["content", "role"]])
    standing = dumps(chat.messages[1][NOTE_KEY])
    before = dumps(chat.messages)
    attach(chat, hook)
    attach(chat, hook)
    check("t12-two-more-walks-changed-not-a-byte", dumps(chat.messages), before)
    check("t12-the-info-note-was-never-upgraded-in-place",
          dumps(chat.messages[1][NOTE_KEY]), standing)


# ------------------------------------------------------------------------- t13
def t13_the_warning_floor_beats_the_percentage_on_64k():
    """The owner's ruling measured: on 65 536 the 20 000-remaining floor holds
    at 45 536 used (69%), long before the 80% (52 428.8) a percentage-only
    machine would have waited for - and NOT one token earlier (45 535: the
    floor is `remaining <= 20000`, inclusive)."""
    walk(StubChat(total=TOTAL_64K), ts.TokenStatus(), [
        (32768, ["info"]),
        (45535, ["info"]),                       # one token short of the floor
        (45536, ["info", "warning"]),            # remaining exactly 20000
    ], "t13-warning-64k")


def t13_the_critical_floor_beats_the_percentage_on_64k():
    """Same at `critical`: the 10 000 floor holds at 55 536 used (85%), before
    the 90% (58 982.4); 55 535 still says nothing new."""
    walk(StubChat(total=TOTAL_64K), ts.TokenStatus(), [
        (32768, ["info"]),
        (45536, ["info", "warning"]),
        (55535, ["info", "warning"]),
        (55536, ["info", "warning", "critical"]),   # remaining exactly 10000
    ], "t13-critical-64k")


def t13_the_percentages_govern_on_128k():
    """The other half of the ruling: on 131 072 the percentages come FIRST -
    warning at 104 858 (remaining 26 214, the floor never had a chance),
    critical at 117 965 (remaining 13 107). Both boundaries are one-token."""
    walk(StubChat(total=TOTAL_128K), ts.TokenStatus(), [
        (65536, ["info"]),
        (104857, ["info"]),                          # one token short of 80%
        (104858, ["info", "warning"]),               # 80%, remaining still 26214
        (117964, ["info", "warning"]),               # one token short of 90%
        (117965, ["info", "warning", "critical"]),   # 90%, remaining 13107
    ], "t13-percent-128k")


def t13_the_percentages_govern_on_200k():
    """On 200 000 the same, at the rounder numbers: 80% = 160 000 fires where
    the floor (180 000) is still 40 000 tokens away."""
    walk(StubChat(total=TOTAL_200K), ts.TokenStatus(), [
        (100000, ["info"]),
        (159999, ["info"]),
        (160000, ["info", "warning"]),
    ], "t13-percent-200k")


# ------------------------------------------------------------------------- t14
def t14_the_32k_announce_order_is_warning_critical_info_never():
    """The consequence the entry orders pinned: on 32 768 the floors make
    `warning` trigger at 39% and `critical` at 69%, so the first note the model
    ever sees is `small_window` (its first moment: the fill is known), then
    `warning`, then `critical` - and `info`, whose 50% sits ABOVE the warning
    trigger, is shadowed forever. That is the machine advancing by rank, not by
    trigger order; an implementation that announced whatever threshold was
    crossed would emit `info` at 50% here, and this walk reddens it."""
    chat = StubChat(total=32768)
    walk(chat, ts.TokenStatus(), [
        (100, ["small_window"]),                           # fill known for the first time
        (12768, ["small_window", "warning"]),              # remaining 20000, at 39%
        (16384, ["small_window", "warning"]),              # 50%: info NEVER fires
        (22768, ["small_window", "warning", "critical"]),  # remaining 10000, at 69%
        (32000, ["small_window", "warning", "critical"]),
    ], "t14-order-32k")
    check("t14-info-is-never-emitted-on-a-32k-window", "info" in spoken(chat), False)


def t14_the_highest_triggered_level_is_announced_from_nothing():
    """From zero announced ranks, the level announced is the HIGHEST whose
    trigger holds, not the lowest: a chat that starts life already at exactly
    10 000 remaining hears `critical` first and only. One token more remaining
    and it is not critical - the level below speaks (that is the OR, measured
    at the exact edge)."""
    chat = StubChat(total=TOTAL_64K, used=55536)   # remaining exactly 10000
    attach(chat, ts.TokenStatus())
    check("t14-at-the-critical-floor-the-first-note-is-critical",
          spoken(chat), ["critical"])
    not_quite = StubChat(total=TOTAL_64K, used=55535)
    attach(not_quite, ts.TokenStatus())
    check("t14-one-token-above-the-floor-the-level-below-speaks",
          spoken(not_quite), ["warning"])


# ------------------------------------------------------------------------- t15
def t15_small_window_fires_once_whatever_the_fill_is():
    """`small_window` is a statement about the window's SIZE, not about the
    fill: it fires the first time the fill is known at all - at 0 used, at 3% -
    and after that never again, however many walks and messages follow. THE
    CONTROL is one token of window larger: 32 769 is not a small window, it
    says nothing at 0, and it CAN still speak (at a level) once there is a
    fill to speak about - so the silence at 32 769 is the size rule, not a
    dead hook."""
    chat = StubChat(total=32768, used=0)
    hook = ts.TokenStatus()
    attach(chat, hook)
    check("t15-small_window-fires_at_zero_fill", spoken(chat), ["small_window"])
    attach(chat, hook)
    check("t15-small_window-does-not-repeat-on-the-same-tail",
          spoken(chat), ["small_window"])
    reply(chat)
    chat.token_usage = {"context": 1000}
    attach(chat, hook)
    reply(chat)
    chat.token_usage = {"context": 2000}
    attach(chat, hook)
    check("t15-small_window-never-returns",
          spoken(chat).count("small_window"), 1)
    check("t15-and-still-the-only-note-in-the-chat", spoken(chat), ["small_window"])

    big = StubChat(total=32769, used=0)
    attach(big, hook)
    check("t15-one-token-more-is-not-a-small-window", spoken(big), [])
    big.token_usage = {"context": 20000}      # 61%: the warning floor holds
    reply(big)
    attach(big, hook)
    check("t15-CONTROL-that-chat-speaks-but-never-of-size", spoken(big), ["warning"])


def t15_small_window_wins_its_message_and_the_level_follows():
    """One note per hook per message: when the first known fill ALREADY holds a
    level (20 000 used on 32 768 is past the 20 000-remaining floor), the
    one-shot size notice wins its message - and the rank is PENDING, not lost:
    the very next message carries `warning`. A machine that marked the level
    announced without announcing it would go silent here forever."""
    chat = StubChat(total=32768, used=20000)
    hook = ts.TokenStatus()
    attach(chat, hook)
    check("t15-size-claims-wins-the-message-it-earned",
          spoken(chat), ["small_window"])
    reply(chat)
    attach(chat, hook)
    check("t15-the-pending-rank-rode-the-next-message",
          spoken(chat), ["small_window", "warning"])


# ------------------------------------------------------------------------- t16
# The four expected strings are the drafts of `doc/TASKS-PLANNED.md` (owner ruling iii:
# wording delegated to the implementer, pinned here word-for-word, re-pinned
# when the owner revisits it; the P14 re-pin of the `critical` clause is
# applied below). Written here with
# their numbers substituted, next to each fixture, so the pin is the literal
# the model reads and not a re-derivation of the template.


def t16_the_four_texts_pinned_byte_for_byte():
    """Model-facing text is code. Every fixture is chosen so {used}, {total},
    {remaining} and {pct} are all distinct - a used-vs-remaining swap, a lost
    `{pct}` or a wrong substitution cannot pass - and each level is met by a
    fresh chat whose first note it is, so the level is the verdict rather than
    leftover state. The entry's load-bearing half of `critical` - do not call
    any more tools, do not start new work after the handoff - is inside its
    byte-for-byte pin below, and an em-dash here is a byte like every other."""
    for label, used, total, expected in (
        #    used      total     used%  remaining   all four figures distinct
        ("info", 111200, TOTAL_200K,
         "Token status: 111200 of 200000 used (56%), 88800 left (the server's "
         "figure at the end of the last reply \u2014 the newest tool results are "
         "not in it yet). Nothing urgent: spend what is left on the task, not on "
         "re-reading."),
        ("warning", 160100, TOTAL_200K,
         "Token warning: 160100 of 200000 used (80%), 39900 left. Start closing "
         "out: no new files unless the task cannot go on without them, targeted "
         "reads instead of whole files, and begin writing down what you have "
         "done and what is still left, while you still have room to say it "
         "properly."),
        ("critical", 180300, TOTAL_200K,
         "Critical: 180300 of 200000 used (90%), 19700 tokens left. Stop working "
         "now. Hand the work off NOW: call the `handoff` tool with your handoff "
         "message - the task in one line, what you changed (paths), what is "
         "unfinished, the exact next step, and anything you learned that is not "
         "in the repo. If no handoff tool is available, write that message as a "
         "fenced block instead. Do not call any more tools and do not start new "
         "work after the handoff \u2014 the chat dies inside this reply."),
        ("small_window", 0, 32768,
         "This chat's context window is only 32768 tokens. That is small enough "
         "to run out during ordinary work, so work narrowly: read the range you "
         "need, not whole files; open few files at a time; do not repeat a read "
         "you already have; keep what you print short."),
    ):
        chat = StubChat(total=total, used=used)
        attach(chat, ts.TokenStatus())
        entries = chat.messages[-1].get(NOTE_KEY, [])
        check(f"t16-{label}-is-the-level", [e["level"] for e in entries], [label])
        entry = entries[0] if entries else {}
        check(f"t16-{label}-carries-the-stamp-of-its-hook", entry.get("hook"),
              "token_status")
        check(f"t16-{label}-text-byte-for-byte", entry.get("text"), expected)


def t16_an_overrun_is_reported_as_the_arithmetic_says():
    """`used > total` is not a crash and not a clamp: the numbers are the
    server's, the text carries them, remaining goes negative and says the
    truth (`-700`), the percentage passes 100. Pinned so a later `max(0, ...)`
    cannot quietly round a dying chat's last words."""
    chat = StubChat(total=100000, used=100700)
    attach(chat, ts.TokenStatus())
    check("t16-the-overrun-text", chat.messages[-1][NOTE_KEY][0]["text"],
          "Critical: 100700 of 100000 used (101%), -700 tokens left. Stop "
          "working now. Hand the work off NOW: call the `handoff` tool with "
          "your handoff message - the task in one line, what you changed "
          "(paths), what is unfinished, the exact next step, and anything you "
          "learned that is not in the repo. If no handoff tool is available, "
          "write that message as a fenced block instead. Do not call any more "
          "tools and do not start new work after the handoff \u2014 the chat "
          "dies inside this reply.")


# ------------------------------------------------------------------------- t17
def t17_a_dropped_verdict_rides_the_next_message():
    """WP-B's drop rule met by the state machine: the server's figure can move
    while the same message is still the tail (WP-D attaches per request, and
    one message can carry more than one request's silence). A `critical`
    verdict handed to a message this hook already spoke on is DROPPED by the
    generator - not stored, not an upgrade - and because the hook's memory is
    the standing notes and nothing else, the verdict is not lost: the next
    message carries it. The standing note itself never changes: a written note
    is history (WP-B's t3), and here it is the hook's own memory of 50%."""
    chat = StubChat(total=TOTAL_128K, used=65536)
    hook = ts.TokenStatus()
    attach(chat, hook)
    standing = dumps(chat.messages[0][NOTE_KEY])
    check("t17-the-first-note-is-info", spoken(chat), ["info"])
    chat.token_usage = {"context": 118000}    # the figure moves under the tail
    attach(chat, hook)
    check("t17-the-standing-note-is-not-upgraded-in-place",
          dumps(chat.messages[0][NOTE_KEY]), standing)
    check("t17-the-later-verdict-was-dropped-not-stored",
          len(chat.messages[0][NOTE_KEY]), 1)
    reply(chat)
    attach(chat, hook)
    check("t17-CONTROL-the-dropped-verdict-spoke-on-the-newer-message",
          spoken(chat), ["info", "critical"])


def t17_the_messages_list_survives_the_hook():
    """WP-B's invariant (d) re-proven with THIS hook installed (it is WP-D's
    hook, and a note of its own must keep the same premise true): the messages
    LIST is untouched - same object, same identities, nothing but the private
    key added, no note ever became a message."""
    chat = StubChat(total=TOTAL_128K, used=130000, messages=[
        {"role": "user", "content": "mm-user-one"},
        {"role": "assistant", "content": "mm-answer-one"},
        {"role": "tool", "tool_call_id": "mm-call-1", "content": "mm-result"},
    ])
    hook = ts.TokenStatus()
    the_list = chat.messages
    ids = [id(message) for message in chat.messages]
    others = without_system(chat)
    attach(chat, hook)
    attach(chat, hook)
    check("t17-chat.messages-is-still-the-same-list-object",
          chat.messages is the_list, True)
    check("t17-every-message-kept-its-identity-and-its-place",
          [id(message) for message in chat.messages], ids)
    check("t17-nothing-but-the-private-key-appears-on-a-message",
          [sorted(message) for message in chat.messages],
          [["content", "role"], ["content", "role"],
           ["content", "role", NOTE_KEY, "tool_call_id"]])
    check("t17-every-other-key-is-byte-identical", without_system(chat), others)
    check("t17-CONTROL-and-one-note-really-was-written",
          sum(len(m.get(NOTE_KEY, [])) for m in chat.messages), 1)
    check("t17-no-note-ever-became-a-list-item",
          any("hook" in message for message in chat.messages), False)


# ------------------------------------------------------------------------- t18
def t18_rubbish_counts_are_silence_never_an_exception():
    """TOTALITY, hard inputs: nothing between `attach()` and `endpoint.stream()`
    catches a hook, so a value that is not a token count - None, prose, a list,
    a float, a bool - must answer silence, not an exception and not arithmetic
    on junk. One control for the family, at the end: the same chat with an
    integer figure speaks."""
    hook = ts.TokenStatus()
    for label, usage in (("none", None),
                         ("string", "mm-many"),
                         ("list", [65536, 0]),
                         ("float-context", {"context": 120000.5})):
        chat = StubChat(total=TOTAL_128K, used=120000)
        chat.token_usage = usage
        raised = None
        try:
            attach(chat, hook)
        except Exception as exception:  # noqa: BLE001
            raised = f"{type(exception).__name__}: {exception}"
        check(f"t18-counts-{label}-raises-nothing", raised, None)
        check(f"t18-counts-{label}-writes-nothing", spoken(chat), [])
    control = StubChat(total=TOTAL_128K, used=120000)
    attach(control, hook)
    check("t18-CONTROL-the-same-chat-with-an-integer-speaks",
          spoken(control), ["critical"])


def t18_rubbish_windows_are_silence_never_an_exception():
    """The same for the other figure, through the accessor: None answers, zero
    and a negative answer, a string answers, a float answers (the counts are
    integers; a float denominator is not the figure DECISIONS 80 measured), and
    an attribute in the accessor's place that is not callable answers. Every
    one of them keeps the request alive; the control at the end proves the
    fixture can speak."""
    hook = ts.TokenStatus()
    # `True` is a real case, not a jest: accepted as an int it is a window of
    # ONE token, and a chat at 120 000 used would instantly read `critical`
    # against it - the kind of lie about the window the guard exists for.
    for label, value in (("none", None),
                         ("zero", 0),
                         ("negative", -4096),
                         ("string", "mm-128k"),
                         ("float", 131072.0),
                         ("bool", True)):
        chat = StubChat(total=TOTAL_128K, used=120000)
        chat._total = value
        raised = None
        try:
            attach(chat, hook)
        except Exception as exception:  # noqa: BLE001
            raised = f"{type(exception).__name__}: {exception}"
        check(f"t18-window-{label}-raises-nothing", raised, None)
        check(f"t18-window-{label}-writes-nothing", spoken(chat), [])
    not_callable = StubChat(total=TOTAL_128K, used=120000)
    not_callable.context_window = "mm-not-a-method"
    raised = None
    try:
        attach(not_callable, hook)
    except Exception as exception:  # noqa: BLE001
        raised = f"{type(exception).__name__}: {exception}"
    check("t18-window-accessor-not-callable-raises-nothing", raised, None)
    check("t18-window-accessor-not-callable-writes-nothing",
          spoken(not_callable), [])
    control = StubChat(total=TOTAL_128K, used=120000)
    attach(control, hook)
    check("t18-CONTROL-the-same-chat-with-a-number-speaks",
          spoken(control), ["critical"])


def t18_only_its_own_notes_are_the_hooks_memory():
    """The rank scan is keyed on the hook's OWN stamped name: another hook's
    `critical` is not this hook's memory and does not shadow anything (and the
    foreign entry is left byte-identical). THE CONTROL is the other side of
    the same key: this hook's own older note - even an unknown level word -
    stands, and its rank (or lack of one) is what the machine counts."""
    chat = StubChat(total=TOTAL_128K, used=65536)
    foreign_entry = {"hook": "mm-other-hook", "level": "critical",
                     "text": "mm-not-my-memory"}
    chat.messages[0][NOTE_KEY] = [dict(foreign_entry)]
    attach(chat, ts.TokenStatus())
    check("t18-another-hooks-note-is-not-my-announced-rank",
          spoken(chat), ["info"])
    # The foreign entry stands byte-identical as the FIRST entry of the list -
    # two hooks, one message, two voices (WP-B's t3) - and it did not stop
    # this hook from adding its own.
    check("t18-the-foreign-entry-was-left-alone",
          chat.messages[0][NOTE_KEY][0], foreign_entry)
    check("t18-CONTROL-both-voices-stand-on-the-one-message",
          [entry["hook"] for entry in chat.messages[0][NOTE_KEY]],
          ["mm-other-hook", "token_status"])

    mine = StubChat(total=TOTAL_128K, used=65536)
    mine.messages[0][NOTE_KEY] = [{"hook": "token_status", "level": "critical",
                                   "text": "mm-already-said"}]
    before = dumps(mine.messages)
    attach(mine, ts.TokenStatus())
    check("t18-CONTROL-my-own-critical-note-shadows-the-50-percent",
          dumps(mine.messages), before)


def t18_an_unrecognised_own_level_shadows_nothing():
    """A standing note whose level the machine does not know counts as rank 0,
    not as a rank that swallows the future: a reloaded chat carrying an old
    note of the hook's own from some earlier wording still gets `info` at 50%
    on the message after it. (The note stands on message 0 and `info` must go
    to a NEWER message - WP-B's once-per-message rule - so this is the reload
    shape: old note, new traffic.) The old entry stands untouched either way
    (WP-B's t3: written notes are history)."""
    chat = StubChat(total=TOTAL_128K, used=0)
    old = [{"hook": "token_status", "level": "mm-older-wording",
            "text": "mm-from-a-previous-draft"}]
    chat.messages[0][NOTE_KEY] = list(old)
    reply(chat)
    chat.token_usage = {"context": 65536}
    attach(chat, ts.TokenStatus())
    check("t18-an-unknown-level-carries-no-rank",
          spoken(chat), ["mm-older-wording", "info"])
    check("t18-CONTROL-the-unknown-note-itself-was-not-touched",
          dumps(chat.messages[0][NOTE_KEY]), dumps(old))


def main():
    print("INPUT MAPPING (TRAPS #13): code under test = the repository's own")
    print("  spit_app/chat/token_status.py (realpath asserted in t10), driven")
    print("  THROUGH the real generator (note_mod.SystemNotes) against plain")
    print("  stub chats carrying messages, token_usage and context_window() -")
    print("  no Textual, no endpoint, no network, no venv. Fixtures: the levels")
    print("  table of doc/TASKS-PLANNED.md (owner ruling ii) at 32k/64k/128k/200k.")
    guarded("t10-gate-and-shape", t10_the_gate_and_the_shape)
    guarded("t11-silence-below", t11_silence_one_token_below_the_first_trigger)
    guarded("t11-silence-zero", t11_silence_at_zero_usage)
    guarded("t11-silence-no-counts", t11_silence_when_the_counts_are_not_there)
    guarded("t11-silence-no-window", t11_silence_when_the_window_is_unknown)
    guarded("t11-silence-no-accessor", t11_silence_when_the_chat_has_no_accessor)
    guarded("t11-tail-only", t11_the_hook_speaks_only_at_the_tail)
    guarded("t11-empty-chat", t11_an_empty_transcript_silences_the_hook)
    guarded("t12-rank-machine", t12_the_machine_advances_by_rank_and_each_level_fires_once)
    guarded("t13-warning-floor-64k", t13_the_warning_floor_beats_the_percentage_on_64k)
    guarded("t13-critical-floor-64k", t13_the_critical_floor_beats_the_percentage_on_64k)
    guarded("t13-percent-128k", t13_the_percentages_govern_on_128k)
    guarded("t13-percent-200k", t13_the_percentages_govern_on_200k)
    guarded("t14-order-32k", t14_the_32k_announce_order_is_warning_critical_info_never)
    guarded("t14-highest-first", t14_the_highest_triggered_level_is_announced_from_nothing)
    guarded("t15-small-window", t15_small_window_fires_once_whatever_the_fill_is)
    guarded("t15-small-pending", t15_small_window_wins_its_message_and_the_level_follows)
    guarded("t16-texts", t16_the_four_texts_pinned_byte_for_byte)
    guarded("t16-overrun", t16_an_overrun_is_reported_as_the_arithmetic_says)
    guarded("t17-dropped-verdict", t17_a_dropped_verdict_rides_the_next_message)
    guarded("t17-list-survives", t17_the_messages_list_survives_the_hook)
    guarded("t18-rubbish-counts", t18_rubbish_counts_are_silence_never_an_exception)
    guarded("t18-rubbish-windows", t18_rubbish_windows_are_silence_never_an_exception)
    guarded("t18-own-memory", t18_only_its_own_notes_are_the_hooks_memory)
    guarded("t18-unknown-level", t18_an_unrecognised_own_level_shadows_nothing)
    print()
    print("==============================")
    print(f"PASS: {pass_}  FAIL: {fail_}")
    return 1 if fail_ else 0


if __name__ == "__main__":
    sys.exit(main())
