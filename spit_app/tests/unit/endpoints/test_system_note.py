#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t12 - the private key `system`: prepare_payload() unpacks each note onto the
wire as a `user` message right AFTER its carrier - or MERGES it into the
carrier's own content when the carrier's role is `user`.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t12.
t1/t5/t8/t9 are in test_payload.py, t2/t3/t4 in test_stream_parse.py, t6/t7 in
test_requests.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py;
harness names are imported, never redefined.

THE RULE THIS PINS (P13, owner ruling of 2026-09-25): a note - a
`{"hook": ..., "level": ..., "text": ...}` entry under the private key `system`
in a message dict - never reaches the wire as a `system` message (strict
templates raise_exception on a mid-conversation `system`), and never as a
SECOND consecutive `user` message (the alternation family - mistral-instruct,
gemma-it - raises on that instead). Hence: carrier `user` -> merge the text
into the wire copy's content; carrier `tool`/`assistant` -> append one
`{"role": "user", "content": text}` item after the carrier. The merge is
hazard 1's adjacency rule - do not "simplify" it into always-appending.

And nothing here moves the app's own data: the unpacking works on the deepcopy
only (the same argument t1 pins for `reasoning`), and `messages` keeps its
length and its order - that list is the index space the UI addresses. The
no-note differential against the pinned baseline `b799526` is the check that
makes this safe rather than plausible: the wire format did NOT move (TRAPS #14).

TRAPS #8 (`mm-*` tokens everywhere), #13 (a control beside every absence and
zero), #14 (the baseline differential, preceded by baseline_selfcheck), #15
(t12 is a new number), #18 (every group runs inside `guarded()`; the row a
runner reads is a floor).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (NEW, assistant, baseline_selfcheck, check,  # noqa: E402
                              dumps, guarded, md5, saved_endpoint, summary)
import endpoint_harness as harness  # noqa: E402

NOTE_A = {"hook": "mm-hook-one", "level": "mm-info", "text": "mm-note-alpha"}
NOTE_B = {"hook": "mm-hook-two", "level": "mm-warning", "text": "mm-note-bravo"}


def build(messages, prompt="", extra=None):
    """A NEW endpoint over `messages` - prepare_payload() only, no request."""
    return NEW(messages, saved_endpoint("http://mm-host/v1", **(extra or {})),
               "mm-model-1", {}, prompt, [], None)


def tool_reply(text="mm-tool-result", notes=None) -> dict:
    message = {"role": "tool", "tool_call_id": "call-mm-1", "content": text}
    if notes is not None:
        message["system"] = list(notes)
    return message


def user_message(content, notes=None) -> dict:
    message = {"role": "user", "content": content}
    if notes is not None:
        message["system"] = list(notes)
    return message


def t12_carrier_items():
    """(a) a note on a `tool` and one on an `assistant` carrier each become
    their own `user` item immediately after the carrier, and never a `system`
    item; the note item carries ONLY role+content (hook/level stay private)."""
    msgs = [
        user_message([{"type": "text", "text": "mm-user-one"}]),
        assistant("mm-answer", "mm-thoughts", tool_calls=harness.TOOL_CALL),
        tool_reply(notes=[NOTE_A]),
        dict(assistant("mm-final", "mm-thoughts-two"), system=[NOTE_B]),
    ]
    wire = build(msgs, prompt="mm-system-prompt").prepare_payload()["messages"]
    check("t12-role-sequence-note-after-tool-and-after-assistant",
          [m["role"] for m in wire],
          ["system", "user", "assistant", "tool", "user", "assistant", "user"])
    check("t12-tool-carrier-note-is-its-own-user-item", wire[4],
          {"role": "user", "content": "mm-note-alpha"})
    check("t12-assistant-carrier-note-is-its-own-user-item", wire[6],
          {"role": "user", "content": "mm-note-bravo"})
    check("t12-note-items-carry-role-and-content-only",
          [sorted(m) for m in (wire[4], wire[6])],
          [["content", "role"], ["content", "role"]])
    check("t12-hook-and-level-never-reach-the-wire",
          any(("hook" in m or "level" in m) for m in wire), False)
    check("t12-no-system-role-after-position-0",
          [m["role"] for m in wire[1:]].count("system"), 0)


def t12_note_order():
    """(b) two notes on one carrier keep their order."""
    msgs = [tool_reply(notes=[NOTE_A, NOTE_B]), tool_reply(notes=[NOTE_B, NOTE_A])]
    wire = build(msgs).prepare_payload()["messages"]
    check("t12-two-notes-on-a-carrier-keep-their-order",
          [m["content"] for m in wire[1:3]], ["mm-note-alpha", "mm-note-bravo"])
    check("t12-two-notes-reversed-on-the-other-carrier-stay-reversed",
          [m["content"] for m in wire[4:6]], ["mm-note-bravo", "mm-note-alpha"])
    check("t12-two-notes-grow-the-payload-by-two-per-carrier", len(wire), 6)


def t12_user_carrier_merges():
    """(c) hazard 1's rule: a note on a `user` carrier produces NO extra item -
    the count is what it was and the text is inside the carrier's content."""
    plain = build([user_message([{"type": "text", "text": "mm-user-carrier"}])]) \
        .prepare_payload()["messages"]
    merged = build([user_message([{"type": "text", "text": "mm-user-carrier"}],
                                 notes=[NOTE_A])]).prepare_payload()["messages"]
    check("t12-user-carrier-merges-no-second-user-message", len(merged), len(plain))
    check("t12-user-carrier-note-lands-in-the-carriers-own-content",
          merged[0]["content"],
          [{"type": "text", "text": "mm-user-carrier\n\nmm-note-alpha"}])
    both = build([user_message([{"type": "text", "text": "mm-user-carrier"}],
                               notes=[NOTE_A, NOTE_B])]).prepare_payload()["messages"]
    check("t12-two-merged-notes-keep-their-order-in-the-content",
          both[0]["content"][0]["text"],
          "mm-user-carrier\n\nmm-note-alpha\n\nmm-note-bravo")
    check("t12-a-merged-note-creates-no-consecutive-user-pair",
          any(a == "user" and b == "user"
              for a, b in zip([m["role"] for m in merged],
                              [m["role"] for m in merged][1:])), False)
    # THE CONTROL (TRAPS #13): the very same note on a `tool` carrier DOES grow
    # the count - without this row the equality above is about nothing.
    grown = build([tool_reply(notes=[NOTE_A])]).prepare_payload()["messages"]
    check("t12-CONTROL-tool-carrier-same-note-does-grow-the-count", len(grown), 2)


def t12_private_key():
    """(d) the private key `system` is nowhere on the wire - asserted on the
    key SET of every message, not on one key."""
    msgs = [
        user_message([{"type": "text", "text": "mm-user-one"}], notes=[NOTE_A]),
        tool_reply(notes=[NOTE_B]),
        dict(assistant("mm-answer", "mm-thoughts"), system=[NOTE_A]),
    ]
    wire = build(msgs, prompt="mm-prompt").prepare_payload()["messages"]
    check("t12-key-set-of-every-wire-message-has-no-private-system",
          [sorted(m) for m in wire],
          [["content", "role"],                              # the leading prompt
           ["content", "role"],                              # user carrier, merged
           ["content", "role", "tool_call_id"],               # tool carrier
           ["content", "role"],                              # its note
           ["content", "reasoning_content", "role"],          # assistant carrier
           ["content", "role"]])                              # its note


def t12_stored_dicts_untouched():
    """(e) the app-side dict keeps its `system` entry AND its own content
    byte-identical - the deepcopy argument, exactly as t1 pins it for
    `reasoning`."""
    carrier = user_message([{"type": "text", "text": "mm-user-carrier"}], notes=[NOTE_A])
    sidekick = tool_reply(notes=[NOTE_B])
    msgs = [carrier, sidekick]
    before = dumps(msgs)
    wire = build(msgs).prepare_payload()["messages"]
    check("t12-app-dict-keeps-its-system-note", carrier["system"], [NOTE_A])
    check("t12-app-dict-keeps-its-own-content-byte-identical",
          md5(dumps(carrier["content"])),
          md5(dumps([{"type": "text", "text": "mm-user-carrier"}])))
    check("t12-stored-messages-byte-identical-after-prepare", dumps(msgs), before)
    check("t12-messages-length-unchanged-by-the-unpacking", len(msgs), 2)
    check("t12-wire-copy-merged-while-the-app-copy-stays-separate",
          (wire[0]["content"][0]["text"], carrier["content"][0]["text"]),
          ("mm-user-carrier\n\nmm-note-alpha", "mm-user-carrier"))
    check("t12-tool-carrier-app-dict-keeps-its-note-too", sidekick["system"], [NOTE_B])


def t12_merge_cells():
    """(f) the merge lands on a list content WITH a text part, on a list
    content WITHOUT one (multimodal), and on a plain string - plus the None /
    missing / empty cells that must end as `text`, never `"None"`."""
    def merged(content):
        return build([user_message(content, notes=[NOTE_A])]) \
            .prepare_payload()["messages"][0]["content"]

    check("t12-merge-cell-list-with-a-text-part",
          merged([{"type": "text", "text": "mm-here"}]),
          [{"type": "text", "text": "mm-here\n\nmm-note-alpha"}])
    check("t12-merge-cell-image-only-list-appends-a-text-part",
          merged([{"type": "image_url", "image_url": {"url": "mm-url-one"}}]),
          [{"type": "image_url", "image_url": {"url": "mm-url-one"}},
           {"type": "text", "text": "mm-note-alpha"}])
    check("t12-merge-cell-plain-string-content", merged("mm-plain"),
          "mm-plain\n\nmm-note-alpha")
    check("t12-merge-cell-none-content-becomes-text-not-None",
          merged(None), "mm-note-alpha")
    no_content = {"role": "user", "system": [NOTE_A]}
    check("t12-merge-cell-missing-content-becomes-text",
          build([no_content]).prepare_payload()["messages"][0]["content"],
          "mm-note-alpha")
    check("t12-merge-cell-empty-string-content-no-leading-separator",
          merged(""), "mm-note-alpha")
    check("t12-merge-cell-empty-text-part-no-leading-separator",
          merged([{"type": "text", "text": ""}]),
          [{"type": "text", "text": "mm-note-alpha"}])
    check("t12-merge-lands-on-the-LAST-text-part",
          merged([{"type": "text", "text": "mm-first"},
                  {"type": "text", "text": "mm-second"}]),
          [{"type": "text", "text": "mm-first"},
           {"type": "text", "text": "mm-second\n\nmm-note-alpha"}])


def t12_baseline_differential():
    """(g) THE PROOF (TRAPS #14): messages with NO notes produce a payload
    byte-identical to the pinned baseline `b799526` apart from `stream_options`
    - the wire format did not move, so no live endpoint sees a format change
    from this commit."""
    print("INPUT MAPPING (TRAPS #13): the same no-note fixture through")
    print("  NEW  = working-tree endpoints/llamacpp.py, and")
    print("  OLD  = " + f"git show {harness.BASELINE_SHA}:{harness.BASELINE_FILE} "
          f"(md5 {md5(harness.OLD_SRC)}, expected {harness.BASELINE_MD5}).")
    print("  endpoint fixture = saved_endpoint MINUS `context_size`: its skip-list")
    print("  entry is P12's own change, pinned in t5 - here the ONLY expected")
    print("  difference is stream_options (added by P12 step 1, absent from OLD).")
    if not baseline_selfcheck("t12"):
        return
    fixture = [
        user_message([{"type": "text", "text": "mm-user-one"}]),
        assistant("mm-answer", "mm-thoughts", tool_calls=harness.TOOL_CALL),
        tool_reply(),
        assistant("mm-final", "mm-thoughts-two"),
    ]
    old = harness.OLD_EP([dict(m) for m in fixture],
                         saved_endpoint("http://mm-host/v1", context_size=None),
                         "mm-model-1", {}, "mm-system-prompt", [], None)
    new = NEW([dict(m) for m in fixture],
              saved_endpoint("http://mm-host/v1", context_size=None),
              "mm-model-1", {}, "mm-system-prompt", [], None)
    old_payload = old.prepare_payload()
    new_payload = new.prepare_payload()
    check("t12-no-note-added-key-vs-baseline-is-stream_options-only",
          sorted(set(new_payload) - set(old_payload)), ["stream_options"])
    check("t12-no-note-stream_options-is-exactly-include-usage",
          new_payload["stream_options"], {"include_usage": True})
    check("t12-no-note-payload-byte-identical-to-pinned-baseline-except-stream-options",
          dumps({k: v for k, v in new_payload.items() if k != "stream_options"}),
          dumps(old_payload))
    # THE CONTROL (TRAPS #13/#14): the SAME fixture with ONE note does NOT match
    # the baseline - without this the byte-identity could pass on a code path
    # that never reads the notes at all.
    noted = [dict(m) for m in fixture]
    noted[2]["system"] = [NOTE_A]
    noted_payload = NEW(noted, saved_endpoint("http://mm-host/v1", context_size=None),
                        "mm-model-1", {}, "mm-system-prompt", [], None).prepare_payload()
    check("t12-CONTROL-one-note-moves-the-payload-off-the-baseline",
          dumps({k: v for k, v in noted_payload.items() if k != "stream_options"})
          == dumps(old_payload), False)


def t12_reasoning_rename_coexists():
    """(h) notes coexist with the `reasoning` -> endpoint-key rename."""
    carrier = dict(assistant("mm-answer", "mm-thoughts"), system=[NOTE_A])
    msgs = [user_message([{"type": "text", "text": "mm-user-one"}]), carrier]
    wire = build(msgs, extra={"reasoning_key":
                              {"value": "mm_custom_reasoning", "stype": "string"}}) \
        .prepare_payload()["messages"]
    check("t12-reasoning-renamed-on-a-noted-carrier",
          wire[1]["mm_custom_reasoning"], "mm-thoughts")
    check("t12-note-still-appended-next-to-the-rename", wire[2],
          {"role": "user", "content": "mm-note-alpha"})
    check("t12-app-carrier-keeps-reasoning-AND-note",
          (carrier["reasoning"], carrier["system"]), ("mm-thoughts", [NOTE_A]))


def t12_leading_prompt():
    """(i) the leading system prompt is still payload["messages"][0] - with
    notes in play and unchanged when there is no prompt."""
    msgs = [tool_reply(notes=[NOTE_A])]
    wire = build(msgs, prompt="mm-system-prompt").prepare_payload()["messages"]
    check("t12-leading-system-prompt-still-index-0", wire[0],
          {"role": "system", "content": "mm-system-prompt"})
    no_prompt = build(msgs).prepare_payload()["messages"]
    check("t12-no-prompt-wire-starts-with-the-first-carrier",
          (no_prompt[0]["role"], no_prompt[0]["content"]),
          ("tool", "mm-tool-result"))


def t12_tool_call_adjacency():
    """(j) no `tool` message is ever separated from the `assistant` whose
    `tool_calls` it answers, and a note on an assistant CARRYING `tool_calls`
    still lands after the whole assistant message. Hazard 2 says the generator
    will never put a note there (it notes only the last message, and a pending
    tool run is not noted); the shape is pinned anyway."""
    run = [
        user_message([{"type": "text", "text": "mm-user-one"}]),
        assistant("mm-ask", "mm-think", tool_calls=harness.TOOL_CALL),
        tool_reply("mm-tool-result-one"),
        {"role": "tool", "tool_call_id": "call-mm-1", "content": "mm-tool-result-two"},
        dict(assistant("mm-final"), system=[NOTE_A]),
    ]
    wire = build(run).prepare_payload()["messages"]
    check("t12-note-never-separates-a-tool-run-from-its-assistant",
          [m["role"] for m in wire],
          ["user", "assistant", "tool", "tool", "assistant", "user"])
    check("t12-tool-replies-still-follow-the-tool_calls-carrier-in-order",
          [m.get("content") for m in wire[2:4]],
          ["mm-tool-result-one", "mm-tool-result-two"])
    carrying = dict(assistant("mm-ask", "mm-think", tool_calls=harness.TOOL_CALL),
                    system=[NOTE_A])
    wire2 = build([carrying]).prepare_payload()["messages"]
    check("t12-note-on-a-tool_calls-assistant-lands-after-the-whole-message",
          (wire2[0]["role"], wire2[1]),
          ("assistant", {"role": "user", "content": "mm-note-alpha"}))
    check("t12-tool_calls-carrier-still-carries-its-tool_calls",
          wire2[0]["tool_calls"], harness.TOOL_CALL)


def main():
    print(describe())
    guarded("t12-carrier-items", t12_carrier_items)
    guarded("t12-note-order", t12_note_order)
    guarded("t12-user-carrier-merges", t12_user_carrier_merges)
    guarded("t12-private-key", t12_private_key)
    guarded("t12-stored-dicts", t12_stored_dicts_untouched)
    guarded("t12-merge-cells", t12_merge_cells)
    guarded("t12-baseline", t12_baseline_differential)
    guarded("t12-reasoning", t12_reasoning_rename_coexists)
    guarded("t12-leading-prompt", t12_leading_prompt)
    guarded("t12-tool-adjacency", t12_tool_call_adjacency)
    summary()
    return 1 if harness.fail_ else 0


def describe() -> str:
    return ("INPUT MAPPING (TRAPS #13): pure request-building, no socket. Notes are "
            "`{\"hook\": ..., \"level\": ..., \"text\": ...}` entries under the private "
            "key `system` of a message dict; the carrier roles exercised are user, "
            "tool and assistant (with and without tool_calls). The differential (g) "
            "prints its own OLD/NEW mapping where it runs.")


if __name__ == "__main__":
    sys.exit(main())
