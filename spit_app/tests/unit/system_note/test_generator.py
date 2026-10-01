#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""P13/WP-B - the system-note generator: the hook contract and its five invariants.

THE CONTRACT THIS PINS (decided and pinned by WP-B - do not re-litigate it)
  A hook is anything with `notice(chat, messages, index)`. It returns a
  `Note(level, text)` or `None`. `SystemNotes(chat).attach()` walks
  `chat.messages` by index, asks every hook in the module `HOOKS` list at every
  position, and writes what a hook says INTO the message dict at that index,
  under the private key `system`, as a `{"hook", "level", "text"}` entry.

  Why the return is a `Note` and not bare text: the stored entry needs a level,
  and WP-C's levels are state-machine output, not per-call arguments - a hook
  picks its level at the moment it speaks, so the level has to travel in the
  return value. `hook` is NOT part of the return value: it is provenance, the
  hook cannot lie about it, and the generator stamps it - the hook's `name` if
  it carries one, else its class name, so a name is never a second requirement
  on top of `notice()`. `None`, or a Note with empty text, is silence, and
  silence writes NOTHING - not an empty `system` key, not an empty list.

  Nothing is remembered on the generator: the note ITSELF is the record that
  this hook already spoke at this message, which is why (b) holds across
  instances and across a chat reload.

THE FIVE INVARIANTS, one group each
  (a) t2  asked at every position the walk visits,
  (b) t3  a hook speaks at most once per message, so N walks never duplicate,
  (c) t4  silence writes nothing,
  (d) t5  the messages LIST is untouched - object, length, identities, contents,
  (e) t6  a hook that raises is not swallowed.
  Plus t7 the stored shape (the pin `unit:endpoints` t12 reads the other way),
  t8 the return contract, t9 what the name is and what it keys.

THE OTHER SIDE OF THE CONTRACT
  `spit_app/tests/unit/endpoints/test_system_note.py` (t12, WP-A) pins what
  `prepare_payload()` does with these entries on the wire - `user` role, merged
  into a `user` carrier, never a second consecutive `user`, never a
  mid-conversation `system`, and neither the private key nor `hook`/`level`
  reaching it. That file is not imported here and must not be edited: the wire
  side is shipped and green, so this file matches IT. Importing `llamacpp`
  would drag httpx in, and t1 is the check that this file never does.

NUMBERS are append-only WITHIN THIS SUITE (TRAPS #15): t1-t9 belong to this
file. `unit:endpoints` keeps its own sequence - t12 is WP-A's, t13 is WP-D's -
and the two never share a name or a meaning.

TRAPS #13: every absence here has the control that makes it speak - the empty
`HOOKS`, the empty chat, the silence, the unchanged list, the refused return.
TRAPS #19 (inverted): the runner runs this file on the BARE python3 with no venv
preamble, and t1 asserts that stays possible; an `import textual` added to the
module later reddens HERE instead of quietly making the suite venv-bound.
TRAPS #18: every group runs inside `guarded()` and the row the runner reads is
the sum of the groups that ran - read the whole output, not just the row.
"""
import contextlib
import json
import os
import sys
import traceback

# repo root is four levels up: system_note/ <- unit/ <- tests/ <- spit_app/
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 4))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from spit_app.chat import system_note as note_mod  # noqa: E402  (the code under test)

Note = note_mod.Note
SystemNotes = note_mod.SystemNotes

# What the app needs at runtime (requirements.txt) and this module must never
# pull in - and the namespace packages that `import spit_app.chat.system_note`
# legitimately creates on its own.
APP_DEPENDENCIES = ("textual", "httpx", "libtmux")
NAMESPACE_PARENTS = ["spit_app.chat", "spit_app.chat.system_note"]

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
    whatever happened to be counted before it died (TESTING.md: the row is a
    floor, and the outer runner reads only `tail -n 1`)."""
    try:
        fn()
    except Exception as exception:  # noqa: BLE001 - that is the whole point
        traceback.print_exc()
        check(f"{group}-did-not-crash", f"{type(exception).__name__}: {exception}",
              "None")


def dumps(obj) -> str:
    """Byte-for-byte comparison form: sorted keys, so dict order cannot lie."""
    return json.dumps(obj, sort_keys=True)


def raises(expected, fn) -> bool:
    """Did the call fail with exactly this exception type? The wrong exception
    is a red, not an accident - t8 and t6 both ask."""
    try:
        fn()
    except expected:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


# --------------------------------------------------------------- the fixtures
# Plain dicts in a one-attribute chat: no Textual, no endpoint, no network. The
# roles are the ones the walk really meets - the `tool_calls` carrier included -
# so "every position" is not measured across four identical dicts, and so a
# note written at the wrong index cannot pass.
TOOL_CALLS = [{"id": "call-mm-1", "type": "function",
               "function": {"name": "mm-tool", "arguments": "{}"}}]
ROLES = ["user", "assistant", "tool", "user"]
KEY_SETS = [["content", "role"],                       # user
            ["content", "reasoning", "role", "tool_calls"],  # assistant
            ["content", "role", "tool_call_id"],       # tool
            ["content", "role"]]                       # user


class MMChat:
    """The chat as far as the generator is concerned: `messages`, and nothing
    else is ever asked of it - which is what lets this suite run bare."""

    def __init__(self, messages):
        self.messages = messages


def fixture() -> MMChat:
    return MMChat([
        {"role": "user", "content": [{"type": "text", "text": "mm-user-one"}]},
        {"role": "assistant", "content": "mm-ask", "reasoning": "mm-thoughts",
         "tool_calls": TOOL_CALLS},
        {"role": "tool", "tool_call_id": "call-mm-1", "content": "mm-tool-result"},
        {"role": "user", "content": [{"type": "text", "text": "mm-user-two"}]},
    ])


def noted_chat(hook_name, level="mm-warning", text="mm-note-from-the-past") -> MMChat:
    """A chat as a RELOAD hands it over: a note already written into the tail
    message, because write_chat_history() persists notes with the chat (P13's
    first consequence - and the counts, which are NOT persisted, re-arm)."""
    chat = fixture()
    chat.messages[3]["system"] = [{"hook": hook_name, "level": level, "text": text}]
    return chat


class Call:
    def __init__(self, chat, messages, index):
        self.chat = chat
        self.messages = messages
        self.index = index


class SilentHook:
    """Asks to be asked and says nothing. Has no `name`, so t9's fallback."""

    def __init__(self, level="mm-info", text=None):
        self.calls = []
        self.level = level
        self.text = text

    def notice(self, chat, messages, index):
        self.calls.append(Call(chat, messages, index))
        return None

    @property
    def indexes(self):
        return [call.index for call in self.calls]


class SpeakingHook(SilentHook):
    """Speaks whenever it is asked, with whatever level/text it holds NOW -
    which is what makes the once-per-message rule measurable rather than a
    side effect of a hook that runs dry."""

    def notice(self, chat, messages, index):
        self.calls.append(Call(chat, messages, index))
        return Note(level=self.level, text=self.text)


class TailHook(SpeakingHook):
    """Speaks at the last position only: the shape WP-C's token-status hook has
    (a note is written once, at the tail, and from then on it is history)."""

    def notice(self, chat, messages, index):
        self.calls.append(Call(chat, messages, index))
        if index != len(messages) - 1:
            return None
        return Note(level=self.level, text=self.text)


class NamedHook(TailHook):
    """A hook that names itself, so the stamp is not the class name, and that
    speaks at the tail - the shape WP-C's token-status hook has."""

    def __init__(self, name, level="mm-info", text="mm-note"):
        super().__init__(level=level, text=text)
        self.name = name


class EverywhereHook(NamedHook):
    """Named, and speaks at EVERY position it is asked - the shape that makes
    "one note per message" measurable on all four messages at once."""

    def notice(self, chat, messages, index):
        self.calls.append(Call(chat, messages, index))
        return Note(level=self.level, text=self.text)


class RaisingHook(SilentHook):
    """Raises where it is told to, and is silent everywhere before that."""

    def __init__(self, raises_at=None):
        super().__init__()
        self.raises_at = raises_at
        self.raised = 0

    def notice(self, chat, messages, index):
        self.calls.append(Call(chat, messages, index))
        if self.raises_at is None or index == self.raises_at:
            self.raised += 1
            raise ValueError("mm-hook-said-no")
        return None


@contextlib.contextmanager
def hooks(*new_hooks):
    """Install hooks in the module list for one test and restore it after. The
    list is looked up when attach() runs, not when SystemNotes is built - and
    the tests build their SystemNotes BEFORE entering this, so late wiring
    (WP-D's) is what t2 measures."""
    saved = note_mod.HOOKS
    note_mod.HOOKS = list(new_hooks)
    try:
        yield
    finally:
        note_mod.HOOKS = saved


def notes(chat) -> list:
    """What was written, per message: [ [entry, ...], ... ]."""
    return [list(message.get("system", [])) for message in chat.messages]


def without_system(chat) -> str:
    """Everything the generator has no business touching, byte for byte."""
    return dumps([{k: v for k, v in message.items() if k != "system"}
                  for message in chat.messages])


# ------------------------------------------------------------------------- t1
def t1_the_bare_interpreter_gate():
    """TRAPS #19 inverted: the module under test imports NOTHING of the app's
    runtime, so this suite needs no venv - and that absence IS the gate. A
    `textual`/`httpx`/`libtmux` import added to `system_note.py` later reddens
    HERE, loudly, instead of the suite quietly becoming venv-bound and reading
    `PASS: 0 FAIL: 1` on the bare interpreter (which means "measured nothing").
    INPUT MAPPING (TRAPS #13): the module measured is the repository's own file,
    named by realpath; `sys.modules` is read by the SAME expression for the
    control as for the absence, so the control proves the probe sees a module
    that IS loaded."""
    check("t1-imported-the-repositories-own-module",
          os.path.realpath(note_mod.__file__),
          os.path.realpath(os.path.join(REPO, "spit_app", "chat",
                                        "system_note.py")))
    offenders = sorted({name.split(".")[0] for name in sys.modules
                        if name.split(".")[0] in APP_DEPENDENCIES})
    check("t1-importing-it-loaded-no-app-dependency", offenders, [])
    check("t1-importing-it-pulled-nothing-but-its-own-namespace-parents",
          sorted(name for name in sys.modules if name.startswith("spit_app.")),
          NAMESPACE_PARENTS)
    # THE CONTROL (TRAPS #13): the same expression over a module that IS loaded.
    # Without it, a probe that always answered "nothing" would pass both rows.
    check("t1-CONTROL-the-same-probe-sees-a-module-that-is-loaded",
          sorted({name.split(".")[0] for name in sys.modules
                  if name.split(".")[0] == "json"}),
          ["json"])
    check("t1-the-hook-list-is-a-list", isinstance(note_mod.HOOKS, list), True)
    check("t1-the-note-carries-a-level-and-a-text", Note._fields, ("level", "text"))
    check("t1-system-notes-takes-a-chat-and-attaches",
          [name for name in ("__init__", "attach")
           if callable(getattr(SystemNotes, name, None))], ["__init__", "attach"])


# ------------------------------------------------------------------------- t2
def t2_the_walk_asks_at_every_position():
    """Invariant (a). The walk visits every index of chat.messages, in order,
    and asks every hook there; the hook is handed the chat, the real messages
    list (not a copy) and the index it is asked about. The generator is built
    while HOOKS is still EMPTY: the list is read by attach(), which is how WP-D
    will be able to wire a hook in after the Chat exists."""
    chat = fixture()
    asked = SilentHook()
    second = NamedHook("mm-second-hook", text="mm-second-speaks")
    attach = SystemNotes(chat)
    with hooks(asked, second):
        attach.attach()
    check("t2-asked-at-every-index-in-order", asked.indexes, [0, 1, 2, 3])
    check("t2-every-hook-is-asked-at-every-index", second.indexes, [0, 1, 2, 3])
    check("t2-the-walk-visits-every-role-including-a-tool_calls-carrier",
          [chat.messages[i]["role"] for i in asked.indexes], ROLES)
    check("t2-the-chat-handed-over-is-that-chat",
          all(call.chat is chat for call in asked.calls), True)
    check("t2-the-messages-handed-over-are-the-chats-own-list-not-a-copy",
          all(call.messages is chat.messages for call in asked.calls), True)
    check("t2-the-index-points-at-the-message-asked-about",
          all(call.messages[call.index] is chat.messages[call.index]
              for call in asked.calls), True)
    check("t2-HOOKS-is-read-by-attach-not-by-the-constructor",
          len(second.calls) > 0, True)


def t2_a_speaking_hook_reaches_every_message():
    """(a) is about being ASKED; a hook that answers everywhere proves the walk
    also reaches the WRITE at every position, and that a note lands in the
    message asked about rather than always at the tail."""
    chat = fixture()
    with hooks(SpeakingHook(level="mm-info", text="mm-note-everywhere")):
        SystemNotes(chat).attach()
    check("t2-a-speaking-hook-notes-every-message-visited",
          [len(per_message) for per_message in notes(chat)], [1, 1, 1, 1])
    check("t2-every-message-got-the-note-of-the-message-asked-about",
          [per_message[0]["text"] for per_message in notes(chat)],
          ["mm-note-everywhere"] * 4)


def t2_nothing_installed_says_nothing():
    """The state WP-B ships: nothing in HOOKS (the token-status hook is WP-C,
    the wiring into Chat/Work is WP-D). This is also the CONTROL for everything
    after it - a generator that wrote notes out of nothing would pass every
    other group."""
    chat = fixture()
    before = dumps(chat.messages)
    with hooks():
        SystemNotes(chat).attach()
    check("t2-no-hooks-installed-writes-nothing-at-all", dumps(chat.messages), before)
    # THE CONTROL (TRAPS #13): one hook, the same fixture, and the note appears.
    with hooks(NamedHook("mm-one-note", text="mm-just-one")):
        SystemNotes(chat).attach()
    check("t2-CONTROL-one-hook-installed-writes-it",
          [len(per_message) for per_message in notes(chat)], [0, 0, 0, 1])


def t2_an_empty_chat_visits_nothing():
    """Zero notes on zero messages is a fact about an empty chat, not about a
    walk that never runs. THE CONTROL is the same fixture with one message."""
    empty = MMChat([])
    asked = NamedHook("mm-empty-walk", text="mm-never")
    attach = SystemNotes(empty)
    with hooks(asked):
        attach.attach()
    check("t2-an-empty-chat-asks-nothing", asked.calls, [])
    check("t2-an-empty-chat-is-still-empty", empty.messages, [])
    # THE CONTROL (TRAPS #13): the hook and the walk are fine; the chat was empty.
    one = MMChat([{"role": "user", "content": [{"type": "text", "text": "mm-only"}]}])
    control = NamedHook("mm-one-walk", text="mm-speaks")
    with hooks(control):
        SystemNotes(one).attach()
    check("t2-CONTROL-one-message-is-asked-and-noted",
          [control.indexes, notes(one)],
          [[0], [[{"hook": "mm-one-walk", "level": "mm-info",
                   "text": "mm-speaks"}]]])


# ------------------------------------------------------------------------- t3
def t3_a_hook_speaks_once_per_message():
    """Invariant (b), the check that keeps N requests quiet: attach() over the
    same walk is idempotent, because the note itself is the record that this
    hook already spoke at this message. Nothing is remembered on the generator,
    so it holds across instances - a new SystemNotes per request is WP-D's
    shape, and a new one here is the same thing."""
    chat = fixture()
    speaker = EverywhereHook("mm-token-status", level="mm-info", text="mm-half-full")
    attach = SystemNotes(chat)
    with hooks(speaker):
        attach.attach()
        after_one = dumps(chat.messages)
        SystemNotes(chat).attach()      # a second request, a new instance
        attach.attach()                 # and a third, the same instance
    check("t3-three-walks-still-one-note-per-message",
          [len(per_message) for per_message in notes(chat)], [1, 1, 1, 1])
    check("t3-the-third-walk-changed-not-a-byte", dumps(chat.messages), after_one)
    check("t3-idempotence-is-in-the-writing-not-in-skipping-the-asking",
          len(speaker.calls), 12)


def t3_a_written_note_is_history():
    """A note that stands is never rewritten: it was true when it was written,
    and the prompt prefix behind it is cached. So a hook that has since changed
    its level adds NOTHING where it already spoke - and THE CONTROL is the
    message that arrived after it, which does get the new level."""
    chat = fixture()
    speaker = NamedHook("mm-token-status", level="mm-warning", text="mm-warning-text")
    with hooks(speaker):
        SystemNotes(chat).attach()
        standing = notes(chat)[3][0]
        speaker.level = "mm-critical"
        speaker.text = "mm-critical-text"
        SystemNotes(chat).attach()
        chat.messages.append({"role": "assistant", "content": "mm-answer-two"})
        SystemNotes(chat).attach()
    check("t3-the-standing-note-keeps-its-level-and-its-text",
          notes(chat)[3][0], standing)
    check("t3-the-standing-note-is-not-upgraded-in-place",
          [len(per_message) for per_message in notes(chat)], [0, 0, 0, 1, 1])
    # THE CONTROL (TRAPS #13): the same hook DOES speak - on the message that
    # had no note yet. Without this row the two above could read "hook dead".
    check("t3-CONTROL-the-new-message-gets-the-new-level", notes(chat)[4],
          [{"hook": "mm-token-status", "level": "mm-critical",
            "text": "mm-critical-text"}])


def t3_a_note_from_a_reloaded_chat_is_left_alone():
    """The reload case: notes persist with the chat while the token counts do
    not, so a re-arming hook meets a history that already carries its own voice.
    That note stays byte-identical and no second one is added - even when the
    hook now speaks a HIGHER level, which is exactly what a chat reloaded near
    the end of its window will try to do."""
    chat = noted_chat("mm-token-status")
    before = dumps(chat.messages)
    speaker = NamedHook("mm-token-status", level="mm-critical", text="mm-newer-claim")
    with hooks(speaker):
        SystemNotes(chat).attach()
    check("t3-a-reloaded-note-is-not-duplicated-or-upgraded",
          dumps(chat.messages), before)
    # THE CONTROL: a message that arrives after the reload IS noted by the same
    # hook at the same moment it stops being written on the old one.
    chat.messages.append({"role": "tool", "tool_call_id": "call-mm-1",
                          "content": "mm-tool-result-two"})
    with hooks(speaker):
        SystemNotes(chat).attach()
    check("t3-CONTROL-the-fresh-message-is-noted", notes(chat)[4],
          [{"hook": "mm-token-status", "level": "mm-critical",
            "text": "mm-newer-claim"}])
    check("t3-CONTROL-the-reloaded-note-is-still-the-one-from-before",
          dumps(chat.messages[3]["system"]),
          dumps(noted_chat("mm-token-status").messages[3]["system"]))


def t3_two_hooks_are_two_voices():
    """At most once per message is per HOOK: two voices on one message are two
    entries, in HOOKS order - the order WP-A's t12 keeps onto the wire."""
    chat = fixture()
    first = SpeakingHook(level="mm-info", text="mm-note-one")
    first.name = "mm-first"
    second = SpeakingHook(level="mm-warning", text="mm-note-two")
    second.name = "mm-second"
    with hooks(first, second):
        SystemNotes(chat).attach()
        SystemNotes(chat).attach()
    check("t3-two-hooks-one-message-two-entries-in-HOOKS-order", notes(chat)[0],
          [{"hook": "mm-first", "level": "mm-info", "text": "mm-note-one"},
           {"hook": "mm-second", "level": "mm-warning", "text": "mm-note-two"}])
    check("t3-three-walks-two-hooks-still-two-entries",
          [len(per_message) for per_message in notes(chat)], [2, 2, 2, 2])


# ------------------------------------------------------------------------- t4
def t4_silence_writes_nothing():
    """Invariant (c): `None`, and a Note whose text is empty, write NOTHING at
    all. Asserted on the KEY SET of every message: an empty `system` key - or
    an empty list under it - is a nothing that shows up in every saved chat
    forever and reaches prepare_payload() as an empty unpack."""
    for label, hook in (("none", SilentHook()),
                        ("empty-string", SpeakingHook(text="")),
                        ("none-text", SpeakingHook(text=None))):
        chat = fixture()
        before = dumps(chat.messages)
        with hooks(hook):
            SystemNotes(chat).attach()
        check(f"t4-{label}-adds-no-key-to-any-message",
              [sorted(message) for message in chat.messages], KEY_SETS)
        check(f"t4-{label}-leaves-every-message-byte-identical",
              dumps(chat.messages), before)
        # THE CONTROL (TRAPS #13): the absence is that hook's silence, not a
        # walk that skipped the messages or a generator that cannot write.
        with hooks(NamedHook("mm-control", text="mm-speaks")):
            SystemNotes(chat).attach()
        check(f"t4-CONTROL-the-same-chat-with-a-speaking-hook-is-noted",
              [len(per_message) for per_message in notes(chat)], [0, 0, 0, 1])
    # A silent hook is still ASKED everywhere: silence is the answer, not the
    # absence of the question - invariant (a) survives silence.
    asked = SilentHook()
    with hooks(asked):
        SystemNotes(fixture()).attach()
    check("t4-a-silent-hook-was-still-asked-at-every-index", asked.indexes,
          [0, 1, 2, 3])


def t4_empty_means_empty_not_whitespace():
    """The emptiness test is `not text`, not a strip: dropping " " would be the
    generator editorialising over a hook's words. Pinned so a later
    `text.strip()` cannot pass quietly."""
    chat = fixture()
    with hooks(SpeakingHook(level="mm-info", text=" ")):
        SystemNotes(chat).attach()
    check("t4-a-blank-text-is-a-note-not-silence", notes(chat)[3],
          [{"hook": "SpeakingHook", "level": "mm-info", "text": " "}])


def t4_silence_never_removes_a_note():
    """Silence is writing nothing, not un-writing: a hook that says nothing on a
    later walk leaves every standing note exactly as it is."""
    chat = noted_chat("mm-token-status")
    before = dumps(chat.messages)
    with hooks(SilentHook()):
        SystemNotes(chat).attach()
    check("t4-silence-leaves-a-standing-note-in-place", dumps(chat.messages), before)
    # THE CONTROL: the same chat and walk DO grow when a new voice speaks.
    with hooks(NamedHook("mm-other-voice", text="mm-second-voice")):
        SystemNotes(chat).attach()
    check("t4-CONTROL-a-new-voice-still-writes",
          [entry["hook"] for entry in notes(chat)[3]],
          ["mm-token-status", "mm-other-voice"])


# ------------------------------------------------------------------------- t5
def t5_the_messages_list_is_untouched():
    """Invariant (d), the constraint that shapes all of P13 and the premise of
    WP-A: a note never becomes a message. `chat.messages` is the index space the
    whole UI addresses - the widget tree projects it one child per message, by
    dict identity - `children[i].message is messages[i]` - and
    `StreamCallback`/`RemoveMessage` carry those same indexes, `Undo` stores
    them, and a mid-stream `ToolCall` holds a
    `message_index` into it. So: same list object, same length, same message
    identities in the same order, nothing but `system` added to any of them."""
    chat = fixture()
    the_list = chat.messages
    ids = [id(message) for message in chat.messages]
    roles = [message["role"] for message in chat.messages]
    others = without_system(chat)
    speaker = SpeakingHook(text="mm-into-the-dict")
    speaker.name = "mm-speaker"
    with hooks(speaker):
        SystemNotes(chat).attach()
        SystemNotes(chat).attach()
    check("t5-chat.messages-is-still-the-same-list-object",
          chat.messages is the_list, True)
    check("t5-the-length-is-unchanged", len(chat.messages), len(ids))
    check("t5-every-message-keeps-its-identity-and-its-place",
          [id(message) for message in chat.messages], ids)
    check("t5-no-message-was-inserted-or-removed-in-any-role",
          [message["role"] for message in chat.messages], roles)
    check("t5-nothing-but-the-private-key-appears-on-a-message",
          [sorted(message) for message in chat.messages],
          [sorted(keys + ["system"]) for keys in KEY_SETS])
    check("t5-every-other-key-is-byte-identical", without_system(chat), others)
    # THE CONTROLS (TRAPS #13): the invariance is not vacuous - the notes really
    # are in those same dicts, and no note became a message of its own.
    check("t5-CONTROL-the-notes-are-inside-the-dicts",
          sum(len(per_message) for per_message in notes(chat)), 4)
    check("t5-CONTROL-no-note-ever-became-a-list-item",
          any("hook" in message for message in chat.messages), False)


def t5_a_note_lands_in_the_dict_and_nowhere_else():
    """Where a note goes: into the dict at the index the hook was asked about.
    Checked against a fixture whose four messages differ, so a note written at
    the wrong position cannot pass."""
    chat = fixture()
    with hooks(NamedHook("mm-tail-only", level="mm-critical", text="mm-tail-note")):
        SystemNotes(chat).attach()
    check("t5-the-note-sits-in-the-message-the-hook-was-asked-about", notes(chat),
          [[], [], [], [{"hook": "mm-tail-only", "level": "mm-critical",
                         "text": "mm-tail-note"}]])
    check("t5-CONTROL-the-other-three-dicts-got-no-key-at-all",
          ["system" in message for message in chat.messages],
          [False, False, False, True])


# ------------------------------------------------------------------------- t6
def t6_a_raising_hook_is_not_swallowed():
    """Invariant (e): a broken hook must not survive by silently doing nothing -
    the posture of the `{}`-endpoint KeyError pinned in DECISIONS 80 b. The
    exception reaches the caller with its type and its message intact: no
    `except`, no retry, and no note made out of the failure."""
    chat = fixture()
    before = dumps(chat.messages)
    witness = SilentHook()
    boom = RaisingHook()
    with hooks(witness, boom):          # the witness is asked first, at index 0
        try:
            SystemNotes(chat).attach()
            raised = None
        except Exception as exception:  # noqa: BLE001 - the point of the group
            raised = exception
    check("t6-the-exception-reaches-the-caller", type(raised).__name__, "ValueError")
    check("t6-the-message-is-not-wrapped-or-replaced", str(raised), "mm-hook-said-no")
    check("t6-a-raise-writes-no-note-of-its-own", dumps(chat.messages), before)
    check("t6-the-walk-stops-at-the-raise-it-does-not-carry-on",
          (witness.indexes, boom.raised), ([0], 1))
    # THE CONTROL (TRAPS #13): the same fixture and the same walk complete and
    # write when the hook does not raise - so the reds above are the raise.
    with hooks(NamedHook("mm-calm", text="mm-calm-note")):
        SystemNotes(chat).attach()
    check("t6-CONTROL-without-the-raise-the-walk-completes-and-writes",
          [len(per_message) for per_message in notes(chat)], [0, 0, 0, 1])


def t6_notes_written_before_a_raise_stay_written():
    """No rollback, stated rather than discovered later: a note written earlier
    in the walk was already true, and the failure belongs to the request, not to
    the note. What stands, stands; what was not reached, is not written."""
    chat = fixture()
    flaky = RaisingHook(raises_at=2)
    speaker = SpeakingHook(text="mm-written-first")
    speaker.name = "mm-speaker"
    with hooks(flaky, speaker):
        try:
            SystemNotes(chat).attach()
        except ValueError:
            pass
    check("t6-the-notes-written-before-the-raise-stand",
          [len(per_message) for per_message in notes(chat)], [1, 1, 0, 0])
    check("t6-and-the-walk-reached-the-raise-and-died-there", flaky.indexes,
          [0, 1, 2])


# ------------------------------------------------------------------------- t7
def t7_the_stored_shape():
    """The entry `unit:endpoints` t12 reads from the wire side: a dict with
    exactly `hook`, `level`, `text`, in a list under the private key `system`.
    A `Note` is a namedtuple and a namedtuple would persist as a JSON LIST, so
    the stored entry has to be a real DICT or write_chat_history() writes
    something prepare_payload() cannot read - that is what the type check is
    for, and it is not pedantry."""
    chat = fixture()
    with hooks(NamedHook("mm-token-status", level="mm-warning",
                         text="mm-close-out")):
        SystemNotes(chat).attach()
    check("t7-the-private-key-is-system", "system" in chat.messages[3], True)
    check("t7-the-notes-of-one-message-are-a-list",
          type(chat.messages[3]["system"]).__name__, "list")
    entry = chat.messages[3]["system"][0]
    check("t7-an-entry-has-exactly-hook-level-text", sorted(entry),
          ["hook", "level", "text"])
    check("t7-an-entry-is-a-dict-not-a-namedtuple", type(entry), dict)
    check("t7-the-three-fields-carry-the-hooks-own-words",
          (entry["hook"], entry["level"], entry["text"]),
          ("mm-token-status", "mm-warning", "mm-close-out"))
    check("t7-the-note-rides-with-the-message-it-follows",
          chat.messages[3]["role"], "user")
    check("t7-the-entry-survives-a-chat-save-and-reload-byte-identical",
          dumps(json.loads(dumps(chat.messages[3]))["system"]),
          dumps([{"hook": "mm-token-status", "level": "mm-warning",
                  "text": "mm-close-out"}]))
    # THE CONTROL (TRAPS #13): the shape comes from the hook, not from a
    # constant - a different hook with different words gets its own entry.
    with hooks(NamedHook("mm-other", level="mm-info", text="mm-other-words")):
        SystemNotes(chat).attach()
    check("t7-CONTROL-a-different-hook-gets-its-own-entry",
          chat.messages[3]["system"][1],
          {"hook": "mm-other", "level": "mm-info", "text": "mm-other-words"})
    # And the same dict in an assistant carrier, the other role WP-A unpicks:
    assistant = MMChat([{"role": "assistant", "content": "mm-answer",
                         "reasoning": "mm-thoughts"}])
    with hooks(NamedHook("mm-token-status", level="mm-info", text="mm-on-assistant")):
        SystemNotes(assistant).attach()
    check("t7-the-same-entry-in-an-assistant-carrier",
          assistant.messages[0]["system"],
          [{"hook": "mm-token-status", "level": "mm-info",
            "text": "mm-on-assistant"}])


# ------------------------------------------------------------------------- t8
def t8_the_return_contract():
    """What `notice()` may return: `None` or a `Note`. Anything else is a
    contract violation and says so, naming the hook - bare text in particular
    would silently lose the level the stored entry needs, and a dict or a tuple
    would be a second contract nobody pinned. Refusing loudly is the same
    posture as t6."""
    for label, value in (("bare-text", "mm-just-text"),
                         ("bare-tuple", ("mm-info", "mm-just-text")),
                         ("a-dict", {"level": "mm-info", "text": "mm-just-text"}),
                         ("a-number", 1)):
        chat = fixture()
        offender = NamedHook("mm-broken-hook")
        offender.notice = lambda chat_, messages_, index_, value=value: value
        with hooks(offender):
            check(f"t8-{label}-is-refused",
                  raises(TypeError, SystemNotes(chat).attach), True)
        check(f"t8-{label}-wrote-nothing",
              any("system" in message for message in chat.messages), False)
        # THE CONTROL (TRAPS #13): the SAME level and text inside a Note are
        # written, so every red above is about the shape and not the words.
        control = fixture()
        with hooks(EverywhereHook("mm-good-hook", level="mm-info",
                                  text="mm-just-text")):
            SystemNotes(control).attach()
        check(f"t8-CONTROL-the-same-words-in-a-Note-are-written",
              control.messages[0]["system"],
              [{"hook": "mm-good-hook", "level": "mm-info", "text": "mm-just-text"}])


def t8_the_refusal_names_the_hook():
    """The refusal has to say WHICH hook broke, on a module-level HOOKS list
    that every chat shares: "TypeError: not a Note" would send the next agent
    reading the wrong file."""
    offender = NamedHook("mm-broken-hook")
    offender.notice = lambda chat_, messages_, index_: "mm-just-text"
    message = ""
    with hooks(offender):
        try:
            SystemNotes(fixture()).attach()
        except TypeError as exception:
            message = str(exception)
    check("t8-the-refusal-names-the-hook", "mm-broken-hook" in message, True)
    check("t8-the-refusal-says-what-it-expected", "Note" in message, True)
    # THE CONTROL: a named hook that returns a Note raises nothing.
    with hooks(NamedHook("mm-calm", text="mm-fine")):
        check("t8-CONTROL-a-conforming-hook-raises-nothing",
              raises(TypeError, SystemNotes(fixture()).attach), False)


def t8_the_note_record_itself():
    """The record's shape is part of the contract WP-C writes against: two
    fields, level first, and both ways of writing it mean the same note. The
    arity checks are why a hook cannot return a bare string by accident -
    `Note("mm-text")` is already a TypeError."""
    positional = Note("mm-info", "mm-text")
    keyword = Note(level="mm-info", text="mm-text")
    check("t8-a-note-is-level-then-text", (positional.level, positional.text),
          ("mm-info", "mm-text"))
    check("t8-positional-and-keyword-are-the-same-note", positional, keyword)
    check("t8-one-field-is-not-a-note", raises(TypeError, lambda: Note("mm-info")),
          True)
    check("t8-three-fields-are-not-a-note",
          raises(TypeError, lambda: Note("mm-info", "mm-text", "mm-extra")), True)


# ------------------------------------------------------------------------- t9
def t9_the_name_is_the_provenance_and_the_key():
    """The hook's name is stamped by the generator - a hook cannot lie about who
    spoke - and it is what "already spoke here" is matched on. A hook with a
    `name` is named by it (so a hook can be renamed, or two instances of one
    class told apart); a hook without one is named by its class, because the
    contract asks only for `notice()` and a name must never become a second
    requirement. An empty `name` is not a name."""
    by_class = SpeakingHook(text="mm-by-class")
    chat = fixture()
    with hooks(by_class):
        SystemNotes(chat).attach()
    check("t9-no-name-attribute-falls-back-to-the-class-name",
          chat.messages[0]["system"][0]["hook"], "SpeakingHook")

    named = EverywhereHook("mm-token-status", text="mm-named")
    chat2 = fixture()
    with hooks(named):
        SystemNotes(chat2).attach()
    check("t9-a-name-attribute-beats-the-class-name",
          chat2.messages[0]["system"][0]["hook"], "mm-token-status")
    check("t9-CONTROL-the-class-name-was-different",
          type(named).__name__ != "mm-token-status", True)

    blank = EverywhereHook("", text="mm-blank-name")
    chat3 = fixture()
    with hooks(blank):
        SystemNotes(chat3).attach()
    check("t9-an-empty-name-is-no-name-and-the-class-stands",
          chat3.messages[0]["system"][0]["hook"], "EverywhereHook")

    # Two hooks, one name: they ARE one voice, and the first in HOOKS order owns
    # the note. The consequence of the name being the key, stated here so nobody
    # files it as a bug - and the reason WP-C gives its hook a name.
    twin_one = SpeakingHook(level="mm-info", text="mm-twin-one")
    twin_two = SpeakingHook(level="mm-warning", text="mm-twin-two")
    chat4 = fixture()
    with hooks(twin_one, twin_two):
        SystemNotes(chat4).attach()
    check("t9-two-hooks-one-name-are-one-voice-and-the-first-wins",
          notes(chat4)[0], [{"hook": "SpeakingHook", "level": "mm-info",
                             "text": "mm-twin-one"}])
    # THE CONTROL: rename the second and the same walk writes two voices.
    twin_two.name = "mm-twin-two"
    chat5 = fixture()
    with hooks(twin_one, twin_two):
        SystemNotes(chat5).attach()
    check("t9-CONTROL-two-names-are-two-voices",
          [entry["hook"] for entry in notes(chat5)[0]],
          ["SpeakingHook", "mm-twin-two"])


def main():
    print("INPUT MAPPING (TRAPS #13): code under test = the repository's own")
    print("  spit_app/chat/system_note.py (its realpath and the absence of every")
    print("  app dependency are both asserted in t1); fixtures = plain dicts in a")
    print("  one-attribute chat - no Textual, no endpoint, no network, no venv.")
    guarded("t1-import-gate", t1_the_bare_interpreter_gate)
    guarded("t2-the-walk", t2_the_walk_asks_at_every_position)
    guarded("t2-speaking-hook", t2_a_speaking_hook_reaches_every_message)
    guarded("t2-nothing-installed", t2_nothing_installed_says_nothing)
    guarded("t2-empty-chat", t2_an_empty_chat_visits_nothing)
    guarded("t3-once-per-message", t3_a_hook_speaks_once_per_message)
    guarded("t3-note-is-history", t3_a_written_note_is_history)
    guarded("t3-reloaded-note", t3_a_note_from_a_reloaded_chat_is_left_alone)
    guarded("t3-two-hooks", t3_two_hooks_are_two_voices)
    guarded("t4-silence", t4_silence_writes_nothing)
    guarded("t4-blank-text", t4_empty_means_empty_not_whitespace)
    guarded("t4-silence-removes-nothing", t4_silence_never_removes_a_note)
    guarded("t5-list-untouched", t5_the_messages_list_is_untouched)
    guarded("t5-where-a-note-goes", t5_a_note_lands_in_the_dict_and_nowhere_else)
    guarded("t6-raise-not-swallowed", t6_a_raising_hook_is_not_swallowed)
    guarded("t6-no-rollback", t6_notes_written_before_a_raise_stay_written)
    guarded("t7-stored-shape", t7_the_stored_shape)
    guarded("t8-return-contract", t8_the_return_contract)
    guarded("t8-refusal-message", t8_the_refusal_names_the_hook)
    guarded("t8-note-record", t8_the_note_record_itself)
    guarded("t9-the-name", t9_the_name_is_the_provenance_and_the_key)
    print()
    print("==============================")
    print(f"PASS: {pass_}  FAIL: {fail_}")
    return 1 if fail_ else 0


if __name__ == "__main__":
    sys.exit(main())
