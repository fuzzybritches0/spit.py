# SPDX-License-Identifier: GPL-2.0
"""System notes: what the model is told about its own situation.

A NOTE is one thing the model is told on top of its own conversation - "you are
at 80% of your window, start closing out" - and the constraint that shapes the
whole of P13 is that it may NOT become an item of `chat.messages`: that list is
the index space the UI addresses (the sliding window projects it by dict
identity, `StreamCallback`/`RemoveMessage` carry those indexes, `Undo` stores
them, a mid-stream `ToolCall` holds a `message_index` into it). So a note is
written INTO the message dict it follows, under the private key `system`, as a
`{"hook", "level", "text"}` entry, and `endpoints/llamacpp.py:prepare_payload`
unpacks each entry onto the wire right after its carrier - as a `user` message,
merged into the carrier's own content when the carrier is itself `user` (the
owner's ruling of 2026-09-25, P13 hazard 1; WP-A shipped it and
`unit:endpoints` `test_system_note.py` t12 pins it). This module only writes the
notes; the unpacking, the token-status hook (WP-C) and the wiring into
`Chat`/`Work` (WP-D) are elsewhere, and nothing here imports them.

THE HOOK CONTRACT
  A hook is anything with `notice(chat, messages, index)`. It returns a
  `Note(level, text)` or `None`.

  The level travels in the return value and not on the hook because WP-C's
  levels are state-machine output - a hook decides its level at the moment it
  speaks, and the stored entry needs it. `hook` is NOT in the return value: who
  spoke is provenance, a hook must not be able to say it was somebody else, and
  the generator stamps it - the hook's `name` if it carries one, else its class
  name, so `notice()` stays the only requirement on a hook. Anything else a
  hook returns is refused with its name in the message: bare text in particular
  would silently drop the level the stored entry needs.

THE FIVE INVARIANTS, pinned by `spit_app/tests/unit/system_note/`
  (a) every hook is asked at every index the walk visits (t2);
  (b) a hook speaks at most once per message, so N walks never duplicate a note
      (t3) - the standing note IS the record that this hook already spoke there,
      which is why nothing is remembered on the generator and why the rule also
      holds across a chat reload (notes persist with the chat, the token counts
      do not);
  (c) `None`, or a Note with empty text, writes NOTHING - not an empty
      `system` key, not an empty list under it (t4);
  (d) the messages LIST is untouched: same object, same length, same dicts in
      the same order, nothing but the private key added (t5);
  (e) a hook that raises is not swallowed - no `except` anywhere near the call,
      and no rollback of what was already written (t6): the failure belongs to
      the request, and a note that stands was true when it was written.

Import NOTHING of Textual or httpx (TRAPS #19): `spit_app/chat/` is a namespace
package, so this module is importable - and this suite runnable - on the bare
interpreter, and `unit:system_note` gates that on every run.
"""
from collections import namedtuple

# The private key a note list lives under in a message dict. The sender strips
# it (prepare_payload pops it from the deepcopy); nothing else reads it, and no
# UI renders it - `Message` renders reasoning/content/tool_calls only.
NOTE_KEY = "system"

Note = namedtuple("Note", ["level", "text"])

# The hooks every chat asks. A module list, not per-chat state: a hook is
# stateless about WHO it speaks to (the chat it is handed changes per request),
# and its own memory is its business. WP-C appends the token-status hook here.
HOOKS = []


def hook_name(hook) -> str:
    # Who wrote a note. Explicit `name` first, so two instances of one class
    # can be told apart; the class name otherwise, so a name is never a second
    # requirement on top of `notice()` and a hook cannot be anonymous.
    return getattr(hook, "name", "") or type(hook).__name__


class SystemNotes:
    """Writes what the hooks say into the message dicts, and nothing else."""

    def __init__(self, chat) -> None:
        self.chat = chat

    def attach(self) -> None:
        """Ask every hook at every position the walk visits; write what answers.

        Reads HOOKS here rather than in __init__: the wiring (WP-D) builds this
        per chat, and a hook registered once at import time must reach chats
        that already exist.
        """
        messages = self.chat.messages
        for index in range(len(messages)):
            for hook in HOOKS:
                self.write(messages, index, hook)

    def write(self, messages, index, hook) -> None:
        """One hook, one message. Silence writes nothing; a note is appended at
        most once per hook per message; a raising hook propagates."""
        note = hook.notice(self.chat, messages, index)
        if note is None:
            return
        name = hook_name(hook)
        if not isinstance(note, Note):
            raise TypeError(f"system-note hook {name} returned {type(note).__name__}"
                            f", expected a Note(level, text) or None")
        if not note.text:
            return
        message = messages[index]
        if self.already_spoken(message, name):
            return
        message.setdefault(NOTE_KEY, []).append(
            {"hook": name, "level": note.level, "text": note.text})

    def already_spoken(self, message, name) -> bool:
        # The standing note is the record: this is (b) - idempotence over the
        # same walk, across instances, and across a reload of the chat. A note
        # is never edited or upgraded in place; a hook that has outgrown its own
        # earlier note says so on the next message.
        return any(entry.get("hook") == name
                   for entry in message.get(NOTE_KEY, []))
