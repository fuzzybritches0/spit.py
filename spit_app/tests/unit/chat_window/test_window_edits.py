#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The edits, the undo and the focus across the window edges (WP-E Accept).

The window is no longer the whole history, so the sites that change the DATA and
expect the widget tree to follow - `mount_message`, the three undo primitives and
the message-level removal - have to answer with the window's own vocabulary
(`widget`, `materialize`, `window_start`) instead of `children[...]`. Every claim
below was measured on the pre-WP-E tree with /tmp/wp-e-probe-*.py, and every row
re-measures the shape with the fix in place; every zero has a control (TRAPS #13).

  t21 `mount_message` at every index class. The insert-above-the-top branch was
      wrong in DIRECTION: an insert at any index <= lo shifts every MOUNTED
      widget's data index by +1, so the answer is `window_start += 1` (the mirror
      of the removal's -1), never a mount at the front - the front mount left a
      one-message HOLE even for the ADJACENT index. The bottom side grows the
      window instead of appending behind the wrong neighbour; `index == hi` used
      to work by luck and is now the ordinary case; the in-window branch is the
      neighbour mount, NOT a delegation. An index outside the DATA raises, as
      `children[i]` did.
  t22 the crash reachable with NO keypress: `check_action("add_message_next")`
      asked a WIDGET for the next message's role and raised IndexError out of the
      binding machinery with the bottom pruned - and `refresh_bindings` runs
      `check_action`. It answers from the data now, so the answer is the SAME
      with the neighbour mounted and pruned, in both directions of the answer
      (valid pair -> False, mismatched pair -> True).
  t23 `undo._insert` at every edge class, and through the REAL path
      (`append_undo` + `action_undo`/`action_redo`): the widget lands where the
      data says it is, the window stays consistent, `undo_index` moves, and the
      chat is WRITTEN - which it never was before, because the accessor raised
      first and `undo()` never reached `write_chat_history()`. Writes are a
      DELTA, never absolute (mounting writes; `update_selects` writes at mount).
  t24 `undo._remove` at every edge class: below the window lo slides -1 and no
      widget is touched; inside, the widget goes under its own lock; above,
      nothing moves at all. Before, `del self.messages[index]` ran FIRST and the
      accessor then raised, leaving the data shorter than the tree.
  t25 `undo._change`: the data write and the undo-entry overwrite are
      window-blind and stay; the widget half runs only when a widget exists, and
      an unmounted change does NOT drag the reader across the history.
  t26 the ONE focus rule both removal sites use: focus untouched when the
      vacated position is outside the mounted range (the old `or last_child()`
      dragged it to the window tail for a removal dozens of messages away), the
      neighbour that took the position when it is inside, the text area when the
      data is empty and the ChatView while the mode is on - and the two sites
      agree with each other.
  t27 `prune()` REFUSES while the view is in edit mode (the owner's ruling), with
      the mode-off control releasing the same grown window and the two runs
      landing on the SAME window once the edit is off - that equality is the
      accepted cost, stated as a measurement. The per-child pins of fact 5 stay.
  t28 the edit MODE is inherited AT MOUNT - by the target AND by the widgets in
      the gap a materialize mounts on the way - so `show_cots`/
      `reset_message_edit` need no replay code, and a child carrying per-widget
      edit state can never be evicted to be missed by them.
  t29 the undo primitives hold the page-op guard across their awaits and give
      back what they found: a page operation landing inside an undo is dropped,
      and the same call outside one is a page.

How this file drives the window, from WP-D's four lessons: the STATE is built
and then ASSERTED (a window that merely happens to be somewhere is not an edge
class); invariants are sampled at `rest()` because `window_consistent()` is a
QUIESCENCE invariant (231 false samples mid-batch, zero at rest); and fixtures
stay at 120-400 messages, because a far materialize mounts everything between
the window and the index - on a 1k fixture that is minutes per check (measured:
997 widgets, ~23.5 s headless).

And two lessons this file learned itself, both found by reds that blamed the
code and were really about the instrument (full write-ups at the rows): the
setup's `freeze_triggers` is part of the state a later row reads - a row that
exercises a TRIGGER path must thaw it and assert it live first, or the harness
freeze answers for the thing under test and a "dropped" green is about nothing
(t27-live, t29); and an undo "change" entry holds the PREVIOUS state, so a
setup that records the CURRENT dict asks `_change` to write the current state
over the current state - "no change" with nothing wrong (t25).
"""
import asyncio
from copy import deepcopy

from window_harness import (WindowApp, big_fixture, check, first_visible,
                            freeze_triggers, rest, settle, store_md5, summary,
                            thaw_triggers)

from spit_app.chat.textual_message import RemoveMessage  # noqa: E402

NEW_TOKEN = "mm-EDIT-NEW"


def new_message(role: str = "user") -> dict:
    """The message an edit inserts, with a token no fixture contains (#8)."""
    return {"role": role, "content": [{"type": "text", "text": f"{NEW_TOKEN} line"}]}


def rendered(widget, scontent: str = "content") -> str:
    """The Markdown sources a Message projects under one content key, joined.
    The same read `chat_smoke`'s `text_of` does, kept local so a rebuild claim is
    about rendered text and not about a widget count."""
    container = widget.cnt.get(scontent)
    if container is None:
        return ""
    return "|".join(" ".join(part.source for part in process.children
                             if hasattr(part, "source"))
                    for process in container.children)


async def open_view(app):
    """Mount the chat the way opening a chat does, and come to rest."""
    await app.chat.chat_view.load()
    return app.chat.chat_view


def insert_into_data(chat, index: int, role: str = "user") -> dict:
    """`mount_message`'s precondition: the dict is in the data FIRST.

    The window is deliberately left INCONSISTENT between this call and the
    `mount_message` that follows - that is the contract both callers have always
    had, and the reason the in-window branch cannot delegate to `materialize`
    (`widget(index)` in that interval is the neighbour, not the new message). No
    check here samples an invariant in that interval.
    """
    message = new_message(role)
    chat.messages.insert(index, message)
    return message


async def build_a_window_with_history_both_sides(view, pilot) -> tuple:
    """Release BOTH ends, so neither edge of the window is an end of the history.

    The order is the `build_an_edge` lesson: `prune()` releases the ends far from
    the VIEWPORT, so the reader has to be at the OTHER end while it runs. Park at
    the window top, prune (drops the tail); park at the window bottom, prune
    (drops the head). Frozen throughout - a setup `scroll_to` is a user scroll
    and would page and prune on its own account.
    """
    freeze_triggers(view)
    view.scroll_to(0, 0, animate=False)
    await settle(pilot)
    await view.prune()
    await settle(pilot)
    view.scroll_to(0, view.max_scroll_y, animate=False)
    await settle(pilot)
    await view.prune()
    await settle(pilot)
    lo, hi = view.window
    check("setup-history-above-the-window", lo > 0, True)
    check("setup-history-below-the-window", hi < len(view.messages), True)
    check("setup-came-to-rest", await rest(pilot, view), True)
    check("setup-consistent", view.window_consistent(), True)
    return view.window


def child_row(view, widget) -> int:
    children = list(view.children)
    return children.index(widget) if widget in children else -1


async def t21_mount_message_index_classes():
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        lo, hi = await build_a_window_with_history_both_sides(view, pilot)
        md5_before, writes_before = store_md5(app), len(app.writes)

        # --- index == hi: the case that used to work by LUCK (child_position ==
        # len(children), so the bare append happened to be the right neighbour).
        # Same answer now, for the ordinary reason.
        at_hi = insert_into_data(chat, hi)
        widget = await view.mount_message(hi)
        await settle(pilot)
        check("t21-at-hi-mounted", widget is view.widget(hi), True)
        check("t21-at-hi-projects-the-dict", widget.message is at_hi, True)
        check("t21-at-hi-lo-untouched", view.window_start, lo)
        check("t21-at-hi-hi-moved-by-one", view.window_hi, hi + 1)
        check("t21-at-hi-consistent", view.window_consistent(), True)

        # --- index > hi: the window closes the gap instead of appending behind
        # the wrong neighbour (measured pre-WP-E: append at the tail, IndexError
        # from the caller's require_widget, consistent=False).
        above_index = view.window_hi + 2
        above = insert_into_data(chat, above_index)
        widget = await view.mount_message(above_index)
        await settle(pilot)
        check("t21-above-mounted", widget is view.widget(above_index), True)
        check("t21-above-projects-the-dict", widget.message is above, True)
        check("t21-above-lo-untouched", view.window_start, lo)
        check("t21-above-gap-mounted",
              all(view.widget(i) is not None for i in range(lo, above_index + 1)), True)
        check("t21-above-consistent", view.window_consistent(), True)

        # --- index == lo - 1: ADJACENT below the top. THE measured hole: the
        # front mount left children[1] projecting lo+1 (one message missing) and
        # lo one below the widget it had just mounted.
        adjacent_index = view.window_start - 1
        old_lo = view.window_start
        old_tail_index = view.window_hi
        adjacent = insert_into_data(chat, adjacent_index)
        widget = await view.mount_message(adjacent_index)
        await settle(pilot)
        check("t21-adjacent-mounted", widget is view.widget(adjacent_index), True)
        check("t21-adjacent-projects-the-dict", widget.message is adjacent, True)
        check("t21-adjacent-lo-moved-down", view.window_start, old_lo - 1)
        check("t21-adjacent-front-is-the-new-widget", view.children[0] is widget, True)
        check("t21-adjacent-no-hole-behind-it",
              view.children[1].message is chat.messages[old_lo], True)
        check("t21-adjacent-tail-still-the-tail", view.window_hi, old_tail_index + 1)
        check("t21-adjacent-consistent", view.window_consistent(), True)

        # --- far below the top: the same answer at a distance, so the
        # compensation cannot be an accident of adjacency.
        far_lo, far_hi = view.window
        far = insert_into_data(chat, 3)
        widget = await view.mount_message(3)
        await settle(pilot)
        check("t21-far-mounted", widget is view.widget(3), True)
        check("t21-far-projects-the-dict", widget.message is far, True)
        check("t21-far-lo-is-the-index", view.window_start, 3)
        check("t21-far-hi-moved-by-one", view.window_hi, far_hi + 1)
        check("t21-far-mounted-everything-between",
              len(view.children), far_hi + 1 - 3)
        check("t21-far-old-lo-still-projected",
              view.widget(far_lo).message is chat.messages[far_lo], True)
        check("t21-far-consistent", view.window_consistent(), True)
        # A mount is a window move, not an edit: on its own it writes no JSON.
        check("t21-mount-wrote-no-json", len(app.writes), writes_before)
        check("t21-store-untouched", store_md5(app), md5_before)

        # --- in-window: the neighbour mount. Capturing the neighbour BEFORE the
        # insert is the only way to name it: between the insert and the mount the
        # mounted range is stale by design (that is the precondition), so
        # `widget(index)` in that interval answers with the neighbour.
        in_lo = view.window_start
        inner_index = in_lo + 4
        neighbour = view.widget(inner_index)      # the dict that shifts to +1
        inner = insert_into_data(chat, inner_index)
        widget = await view.mount_message(inner_index)
        await settle(pilot)
        check("t21-in-window-mounted", widget is view.widget(inner_index), True)
        check("t21-in-window-projects-the-dict", widget.message is inner, True)
        check("t21-in-window-is-not-the-neighbour", widget is not neighbour, True)
        check("t21-in-window-neighbour-shifted-right",
              view.widget(inner_index + 1) is neighbour, True)
        check("t21-in-window-lo-untouched", view.window_start, in_lo)
        check("t21-in-window-child-position", child_row(view, widget), 4)
        check("t21-in-window-consistent", view.window_consistent(), True)

        # --- outside the DATA: the exception `children[index]` used to raise.
        for bad in (-1, len(chat.messages)):
            try:
                await view.mount_message(bad)
                check(f"t21-out-of-data-{bad}", "no raise", "IndexError")
            except IndexError:
                check(f"t21-out-of-data-{bad}", "IndexError", "IndexError")
        check("t21-out-of-data-consistent", view.window_consistent(), True)


async def t22_check_action_answers_from_the_data():
    """The crash with no keypress, and the control that makes the answer real.

    `check_action` is what `refresh_bindings` runs, and it asked a WIDGET for a
    question about the history: with the bottom pruned and focus on the last
    mounted widget the whole binding pass raised. Stopping the crash is worth
    nothing if the answer quietly changed, so each row asks the same question
    twice - with the neighbour out of the window and with it mounted.
    """
    # big_fixture makes EVEN indexes user, and `maybe_add_message_next` on a user
    # message asks whether the next message is an assistant: an assistant next
    # door means nothing needs adding (False), anything else means it does (True).
    # A second `user` is the mismatch, and it stays renderable - a `tool` message
    # without a `name` key dies in `Process.tool_output_type_hint`, which would
    # make the control fail for a reason that has nothing to do with the answer.
    for label, next_role, want in (("matching-pair", "assistant", False),
                                   ("mismatched-pair", "user", True)):
        app = WindowApp(big_fixture(200))
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            chat = app.chat
            view = await open_view(app)
            await settle(pilot)
            await build_a_window_with_history_both_sides(view, pilot)
            focus_widget = view.last_child()
            index = chat.message_index(focus_widget.message)
            # THE INPUT MAPPING, asserted before the question: focus is the last
            # MOUNTED widget, its successor is NOT mounted, and its own role is
            # the user role the branch below depends on.
            check("t22-setup-focus-is-the-last-mounted", focus_widget is view.last_child(), True)
            check("t22-setup-successor-unmounted", view.widget(index + 1), None)
            check("t22-setup-focus-role-is-user", focus_widget.role, "user")
            chat.messages[index + 1]["role"] = next_role
            view.is_edit = True                          # the mode the binding needs
            await settle(pilot)
            answer_pruned = focus_widget.check_action("add_message_next", ())
            check(f"t22-{label}-answer-while-pruned", answer_pruned, want)
            await view.materialize(index + 1)            # only the window moves
            await settle(pilot)
            check(f"t22-{label}-control-neighbour-mounted",
                  view.widget(index + 1) is not None, True)
            check(f"t22-{label}-same-answer-when-mounted",
                  focus_widget.check_action("add_message_next", ()), answer_pruned)

    # And the binding pass itself, which is the crash a user would actually hit:
    # `refresh_bindings` runs on every worker-state change, with nobody touching
    # a key. Before WP-E this raised IndexError out of Textual's machinery.
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        focus_widget = view.last_child()
        focus_widget.focus(scroll_visible=False)
        await settle(pilot)
        view.is_edit = True
        await settle(pilot)
        check("t22-bottom-is-pruned", view.window_hi < len(chat.messages), True)
        check("t22-successor-is-out-of-window",
              view.widget(chat.message_index(focus_widget.message) + 1), None)
        try:
            app.refresh_bindings()
            check("t22-refresh_bindings-with-a-pruned-neighbour", "returned", "returned")
        except IndexError as exception:
            check("t22-refresh_bindings-with-a-pruned-neighbour",
                  f"IndexError: {exception}", "returned")
        # `add_message_prev`'s own check requires `message_index == 0`, so that
        # flow only ever runs with lo == 0 (in-window). Pinned so the claim
        # t21's in-window branch rests on cannot drift.
        check("t22-add-message-prev-blocked-away-from-0",
              focus_widget.check_action("add_message_prev", ()), False)


async def t23_undo_insert_at_the_edges():
    # The primitive, at each class of index the window can meet. Fixture 120 so
    # the far case mounts ~100 widgets instead of the ~900 a 1k fixture costs:
    # the claim is about the index arithmetic, and it is the same arithmetic.
    app = WindowApp(big_fixture(120))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)

        def index_classes(view):
            """Asked of the CURRENT window: every insert moves the bounds, so a
            captured index list would be about a window that no longer exists."""
            return (("below-the-window", view.window_start - 2, "lo-to-index"),
                    ("at-the-top", view.window_start, "lo-untouched"),
                    ("inside-the-window", view.window_start + 2, "lo-untouched"),
                    ("at-the-bottom", view.window_hi, "lo-untouched"),
                    ("above-the-bottom", view.window_hi + 3, "lo-untouched"))

        for label, index, lo_expectation in index_classes(view):
            len_before = len(chat.messages)
            lo_before, hi_before = view.window
            await chat.undo._insert(new_message(), index)
            await settle(pilot)
            check(f"t23-{label}-data-grew", len(chat.messages), len_before + 1)
            check(f"t23-{label}-widget-at-the-index", view.widget(index) is not None, True)
            check(f"t23-{label}-projects-the-new-dict",
                  rendered(view.widget(index)), f"{NEW_TOKEN} line")
            if lo_expectation == "lo-to-index":
                check(f"t23-{label}-lo-is-the-index", view.window_start, index)
            else:
                check(f"t23-{label}-lo-untouched", view.window_start, lo_before)
            check(f"t23-{label}-hi-moved-by-one", view.window_hi, hi_before + 1)
            check(f"t23-{label}-consistent", view.window_consistent(), True)
            check(f"t23-{label}-focus-landed-on-it",
                  view.focused_widget is view.widget(index), True)
            check(f"t23-{label}-the-view-can-see-it",
                  view.widget_index(first_visible(view)) <= index, True)

    # And through the REAL path. Undoing a "remove" entry IS an insert, so
    # `append_undo("remove", ...) + action_undo` is the user's own move, and the
    # promise this WP is about is that the change reaches the chat JSON: before,
    # the accessor raised inside the primitive and `undo()` never got to
    # `write_chat_history()`.
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        removed = dict(chat.messages[3])
        chat.undo.append_undo("remove", removed, 3)
        writes_before = len(app.writes)
        undo_index_before = chat.undo.undo_index
        len_before = len(chat.messages)
        check("t23-path-entry-is-a-remove", chat.undo.undo_list[-1][0], "remove")
        check("t23-path-target-is-unmounted", view.widget(3), None)
        await chat.chat_view.action_undo()
        await settle(pilot)
        check("t23-path-undo-data-grew", len(chat.messages), len_before + 1)
        check("t23-path-undo-widget-mounted", view.widget(3) is not None, True)
        check("t23-path-undo-restored-the-removed-dict",
              rendered(view.widget(3)), removed["content"][0]["text"])
        check("t23-path-undo-index-decremented", chat.undo.undo_index,
              undo_index_before - 1)
        check("t23-path-undo-wrote-the-chat", len(app.writes), writes_before + 1)
        check("t23-path-undo-consistent", view.window_consistent(), True)

        # Redo: the same entry replays as a REMOVE, again below the window.
        # The claim is NOT `widget(3) is None`: the message that FOLLOWED the
        # removed one took position 3, and it is inside the (grown) window, so
        # `widget(3)` legitimately answers with the successor. The redo of a
        # removal is the t24-inside shape: the right dict projects the slot,
        # one child less, and the widget that was there is the one that went.
        writes_before = len(app.writes)
        len_before = len(chat.messages)
        children_before = len(view.children)
        restored_widget = view.widget(3)
        await chat.chat_view.action_redo()
        await settle(pilot)
        check("t23-path-redo-data-shrank", len(chat.messages), len_before - 1)
        check("t23-path-redo-successor-projects-the-slot",
              view.widget(3).message is chat.messages[3], True)
        check("t23-path-redo-successor-is-a-different-widget",
              view.widget(3) is not restored_widget, True)
        check("t23-path-redo-one-child-less", len(view.children), children_before - 1)
        check("t23-path-redo-index-back", chat.undo.undo_index, undo_index_before)
        check("t23-path-redo-wrote-the-chat", len(app.writes), writes_before + 1)
        check("t23-path-redo-consistent", view.window_consistent(), True)


async def t24_undo_remove_at_the_edges():
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)

        # --- BELOW the window: lo slides -1, no widget is touched, and the
        # reader keeps both their position and their focus. (Pre-WP-E the `del`
        # ran first, the accessor then raised, and the chat came back with the
        # data shorter than the tree and nothing persisted.)
        focus_widget = view.children[1]
        focus_widget.focus(scroll_visible=False)
        await settle(pilot)
        lo, hi = view.window
        children_before, len_before = len(view.children), len(chat.messages)
        # THE READER IS TRACKED AS A WIDGET, not as an index: a removal BELOW
        # the window renumbers every mounted widget (lo 150 -> 149), so the
        # index of the first visible widget legitimately moves by one while the
        # reader has not moved at all. `first_visible` before and after, by
        # identity, is the question "did the view hold?" - the same reading the
        # WP-A frame instrument gives.
        reader_widget = first_visible(view)
        await chat.undo._remove(3)
        await settle(pilot)
        check("t24-below-data-shrank", len(chat.messages), len_before - 1)
        check("t24-below-lo-slid", view.window_start, lo - 1)
        check("t24-below-hi-slid-too", view.window_hi, hi - 1)
        check("t24-below-no-widget-lost", len(view.children), children_before)
        check("t24-below-consistent", view.window_consistent(), True)
        check("t24-below-view-held", first_visible(view) is reader_widget, True)
        check("t24-below-focus-untouched", view.focused_widget, focus_widget)

        # --- INSIDE the window: the widget goes, its successor takes the slot.
        lo, hi = view.window
        victim = view.require_widget(lo + 2)
        successor = view.require_widget(lo + 3)
        children_before, len_before = len(view.children), len(chat.messages)
        await chat.undo._remove(lo + 2)
        await settle(pilot)
        check("t24-inside-data-shrank", len(chat.messages), len_before - 1)
        check("t24-inside-widget-gone", victim not in list(view.children), True)
        check("t24-inside-lo-untouched", view.window_start, lo)
        check("t24-inside-successor-took-the-slot", view.widget(lo + 2), successor)
        check("t24-inside-one-child-less", len(view.children), children_before - 1)
        check("t24-inside-consistent", view.window_consistent(), True)

        # --- ABOVE the window: nothing is mounted there, so nothing moves.
        above_index = view.window_hi + 4
        lo, hi = view.window
        children_before, len_before = len(view.children), len(chat.messages)
        await chat.undo._remove(above_index)
        await settle(pilot)
        check("t24-above-data-shrank", len(chat.messages), len_before - 1)
        check("t24-above-lo-untouched", view.window_start, lo)
        check("t24-above-no-child-lost", len(view.children), children_before)
        check("t24-above-consistent", view.window_consistent(), True)

        # --- the last MOUNTED widget: the neighbour BEFORE it takes the cursor
        # (`widget(index)` is empty, so the rule falls back one).
        before_it = view.require_widget(view.window_hi - 2)
        tail = view.last_child()
        await chat.undo._remove(view.window_hi - 1)
        await settle(pilot)
        check("t24-tail-widget-gone", tail not in list(view.children), True)
        check("t24-tail-focus-on-the-predecessor", view.focused_widget, before_it)
        check("t24-tail-consistent", view.window_consistent(), True)

        # --- the window TOP widget: its predecessor is OUTSIDE the window, and
        # the old fallback `require_widget(index - 1)` raised IndexError here.
        # The answer is the widget that took the vacated slot.
        lo = view.window_start
        top = view.require_widget(lo)
        took_the_slot = view.require_widget(lo + 1)
        check("t24-top-setup-predecessor-unmounted", view.widget(lo - 1), None)
        await chat.undo._remove(lo)
        await settle(pilot)
        check("t24-top-widget-gone", top not in list(view.children), True)
        check("t24-top-focus-on-the-slot", view.focused_widget, took_the_slot)
        check("t24-top-consistent", view.window_consistent(), True)


async def t25_undo_change_is_data_first():
    """THE ENTRY MODEL, learned the hard way: a "change" entry holds the
    PREVIOUS state of the message, because `_change` WRITES the entry into the
    data and overwrites it with what it replaced. An entry built from the
    CURRENT dict therefore writes the current state over the current state -
    "no change" - and every text assertion about it reads the old value with
    nothing wrong. So the setup is: snapshot `old`, change the message (in
    place, so `child.message is messages[i]` never breaks between setup and
    undo), record `old`, undo, and assert the OLD text is back and the entry
    now holds the state the change wrote (the pairing that lets a REDO replay
    it). The realistic edit also repaints the widget - the mounted row does
    that in its setup, so the undo has a repaint to undo and the flip is
    observable rather than vacuous.
    """
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)

        # --- BELOW the window: the data and the undo entry are written, the
        # reader is NOT dragged to the change, and `undo()` reaches the write.
        old = deepcopy(chat.messages[3])
        chat.messages[3]["content"][0]["text"] = "mm-CHANGED"
        chat.undo.append_undo("change", old, 3)
        focus_widget = view.children[1]
        focus_widget.focus(scroll_visible=False)
        await settle(pilot)
        writes_before = len(app.writes)
        undo_index_before = chat.undo.undo_index
        reader_widget = first_visible(view)
        await chat.chat_view.action_undo()
        await settle(pilot)
        check("t25-unmounted-data-restored-to-the-entry",
              chat.messages[3]["content"][0]["text"], old["content"][0]["text"])
        check("t25-unmounted-wrote-the-chat", len(app.writes), writes_before + 1)
        check("t25-unmounted-index-decremented", chat.undo.undo_index,
              undo_index_before - 1)
        # The entry now holds the state the undo just REPLACED (the CHANGED
        # dict), so a redo re-applies the change rather than losing it (the
        # overwrite is the half that runs before any widget is asked about, and
        # it stays window-blind).
        check("t25-unmounted-entry-holds-the-state-the-change-wrote",
              chat.undo.undo_list[undo_index_before][1]["content"][0]["text"],
              "mm-CHANGED")
        check("t25-unmounted-focus-untouched", view.focused_widget, focus_widget)
        check("t25-unmounted-view-held", first_visible(view) is reader_widget, True)
        check("t25-unmounted-target-still-unmounted", view.widget(3), None)
        check("t25-unmounted-consistent", view.window_consistent(), True)

        # --- THE CONTROL, inside the window: the widget rebuilds and the
        # cursor goes to it, because the reader can see it. This is what makes
        # the row above a decision about UNMOUNTED widgets rather than a redraw
        # that quietly stopped happening.
        index = view.window_start + 2
        widget = view.require_widget(index)
        old = deepcopy(chat.messages[index])
        chat.messages[index]["content"][0]["text"] = "mm-CHANGED"
        await widget.reset()                    # the repaint the edit itself does
        await widget.finish()
        await settle(pilot)
        check("t25-mounted-setup-widget-shows-the-change",
              "mm-CHANGED" in rendered(widget), True)
        chat.undo.append_undo("change", old, index)
        await chat.chat_view.action_undo()
        await settle(pilot)
        check("t25-mounted-data-restored-to-the-entry",
              chat.messages[index]["content"][0]["text"], old["content"][0]["text"])
        check("t25-mounted-text-flipped", "mm-CHANGED" in rendered(widget), False)
        check("t25-mounted-old-text-rendered",
              old["content"][0]["text"] in rendered(widget), True)
        check("t25-mounted-focus-on-it", view.focused_widget, widget)
        check("t25-mounted-consistent", view.window_consistent(), True)


async def t26_the_focus_rule():
    """One rule, both sites, and the control for each of its branches.

    The rule: no widget left the tree → focus stays (nothing the reader can see
    changed); a widget left it → the neighbour that took the position, else the
    one before; the data empty → the text area, or the ChatView while the view is
    in edit mode.
    """
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        focus_widget = view.children[1]
        focus_widget.focus(scroll_visible=False)
        await settle(pilot)
        check("t26-setup-focus-is-child-1", child_row(view, focus_widget), 1)

        # far ABOVE the window - the streaming-error path's shape (`RemoveMessage
        # (len(messages) - 1)` after a pruned bottom). The old `or last_child()`
        # moved focus to the window tail here, about five messages away.
        view.post_message(RemoveMessage(len(chat.messages) - 1))
        await settle(pilot)
        check("t26-far-above-focus-untouched", view.focused_widget, focus_widget)
        check("t26-far-above-still-child-1", child_row(view, focus_widget), 1)
        check("t26-far-above-consistent", view.window_consistent(), True)

        # AT `index == window_hi`: asked as a bare `widget(index) or
        # widget(index - 1)` this answers "the last mounted widget" and drags the
        # cursor to the window tail all the same, which is why the rule asks
        # whether a WIDGET went before it asks who is next door.
        hi = view.window_hi
        check("t26-at-hi-neighbour-question-would-drag",
              view.widget(hi - 1) is view.last_child(), True)
        view.post_message(RemoveMessage(hi))
        await settle(pilot)
        check("t26-at-hi-focus-untouched", view.focused_widget, focus_widget)
        check("t26-at-hi-still-child-1", child_row(view, focus_widget), 1)
        check("t26-at-hi-consistent", view.window_consistent(), True)

        # BELOW the window: lo slides, focus stays.
        lo = view.window_start
        view.post_message(RemoveMessage(3))
        await settle(pilot)
        check("t26-below-lo-slid", view.window_start, lo - 1)
        check("t26-below-focus-untouched", view.focused_widget, focus_widget)
        check("t26-below-consistent", view.window_consistent(), True)

        # THE CONTROL: the same post one row from the cursor. A widget leaves the
        # tree, and the neighbour that took its position gets the focus.
        victim = view.children[1]
        successor = view.children[2]
        view.post_message(RemoveMessage(view.widget_index(victim)))
        await settle(pilot)
        check("t26-inside-widget-is-gone", victim not in list(view.children), True)
        check("t26-inside-focus-followed-the-slot", view.focused_widget, successor)
        check("t26-inside-consistent", view.window_consistent(), True)

    # The two sites AGREE: the same removal through `undo._remove` and through
    # `RemoveMessage` leaves the cursor on the same widget. (They used to answer
    # differently: one focused `widget(index)` then `require_widget(index - 1)`,
    # the other `widget(index)` then `last_child()`.)
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        await chat.undo._remove(view.window_start + 2)
        await settle(pilot)
        undo_focus = view.focused_widget
        check("t26-agree-undo-removal-focuses-the-slot",
              undo_focus is view.widget(view.window_start + 2), True)
        view.post_message(RemoveMessage(view.window_start + 2))
        await settle(pilot)
        check("t26-agree-post-removal-focuses-the-slot",
              view.focused_widget is view.widget(view.window_start + 2), True)
        check("t26-agree-the-widget-changed-between-the-two",
              view.focused_widget is not undo_focus, True)
        check("t26-agree-consistent", view.window_consistent(), True)

    # The empty data: the text area takes the cursor, except while the view is in
    # edit mode, where the ChatView does (the editor has nowhere to go).
    for label, edit_mode, want in (("edit-off", False, "ChatTextArea"),
                                   ("edit-on", True, "ChatView")):
        app = WindowApp(big_fixture(2))
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            chat = app.chat
            view = await open_view(app)
            await settle(pilot)
            freeze_triggers(view)
            view.is_edit = edit_mode
            await settle(pilot)
            view.post_message(RemoveMessage(1))
            await settle(pilot)
            check(f"t26-{label}-one-message-left", len(chat.messages), 1)
            view.post_message(RemoveMessage(0))
            await settle(pilot)
            check(f"t26-{label}-data-empty", len(chat.messages), 0)
            check(f"t26-{label}-tree-empty", len(view.children), 0)
            check(f"t26-{label}-focus-went-to", type(app.focused).__name__, want)
            check(f"t26-{label}-consistent", view.window_consistent(), True)


async def t27_prune_refuses_while_editing():
    """The owner's ruling (2026-09-19): `prune()` itself returns while `is_edit`
    is set. The mode is per-VIEW, the fact-5 pins are per-CHILD; both stay.

    The two runs of the same walk - mode off, mode on - must land on the SAME
    window once the edit is off. That equality IS the accepted cost, stated as a
    measurement instead of as a promise: what an edit defers is the release, not
    the release's size.
    """
    released = {}
    for label, edit_mode in (("mode-off", False), ("mode-on", True)):
        app = WindowApp(big_fixture(400))
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            chat = app.chat
            view = await open_view(app)
            await settle(pilot)
            await build_a_window_with_history_both_sides(view, pilot)
            # Grow the window on purpose. Without this, a refusal and an empty
            # walk are the same observable state and the zero proves nothing.
            await view.materialize(view.window_start - 12)
            await settle(pilot)
            grown = (view.window, len(view.children))
            check(f"t27-{label}-window-was-grown", grown[1] > 10, True)
            view.is_edit = edit_mode
            await settle(pilot)
            await view.prune()
            await settle(pilot)
            during = (view.window, len(view.children))
            if edit_mode:
                check("t27-mode-on-held-everything", during, grown)
            else:
                check("t27-mode-off-released-something", during[1] < grown[1], True)
            # The cost, paid: the first prune after edit_off.
            view.is_edit = False
            await view.prune()
            await settle(pilot)
            released[label] = (view.window, len(view.children))
            if edit_mode:
                check("t27-mode-on-released-nothing-early", during, grown)
            check(f"t27-{label}-consistent", view.window_consistent(), True)
    check("t27-edit-off-releases-exactly-what-mode-off-did",
          released["mode-on"], released["mode-off"])

    # The refusal belongs to the view, not to a frozen trigger: with the trigger
    # paths LIVE, the settle holds while the mode is on and releases after
    # edit_off. This is the ruling in the app rather than in a direct call.
    app = WindowApp(big_fixture(400))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        # THE STATE THAT MAKES THE ZEROS MEANINGFUL, asserted before the
        # experiment. The setup froze the triggers (its `scroll_to`s are setup,
        # not input) - leaving that freeze in place made EVERY row below vacuous
        # in both directions: `_scroll_settled` returns at its first line for a
        # reason that has nothing to do with the mode (the held row was green
        # because of the harness, and the release row could never happen). The
        # harness's own recipe is "setup frozen, experiment live"
        # (`thaw_triggers`): drop the freeze, assert the triggers are LIVE, and
        # the only thing that can freeze them from here is the ruling itself.
        # (/tmp/wp-e-probe-t27live-t29.py: with the freeze left on, the settle
        # changed nothing after edit_off; thawed, it released 19 -> 8, exactly
        # the direct-call control's number.)
        thaw_triggers(view)
        check("t27-live-triggers-live-after-thaw", view._triggers_frozen(), False)
        await view.materialize(view.window_start - 12)
        await settle(pilot)
        grown = len(view.children)
        check("t27-live-window-was-grown", grown > 10, True)
        view.action_edit_on()                # the real action: the mode + show_cots
        await settle(pilot)
        check("t27-live-edit_on-freezes-the-triggers", view._triggers_frozen(), True)
        await view._scroll_settled()
        await settle(pilot)
        check("t27-live-settle-held-while-editing", len(view.children), grown)
        check("t27-live-consistent-while-editing", view.window_consistent(), True)
        # Baseline while STILL HELD: the release below may come from this
        # test's own `_scroll_settled()` call or from a live settle the mode-off
        # layout change arms by itself - both are the app's own path, and the
        # claim is about the mode, not about which call did it.
        held_lo = view.window_start
        await view.action_edit_off()
        await settle(pilot)
        await rest(pilot, view)               # absorb any settle in flight
        check("t27-live-edit_off-thaws-the-triggers", view._triggers_frozen(), False)
        await view._scroll_settled()
        await settle(pilot)
        await rest(pilot, view)
        # The release is measured by LO, not by the child count: a settled
        # `_scroll_settled` is prune PLUS the edge re-check (WP-D's starvation
        # fix), and the reader parked at the window bottom gets a page back in
        # below - measured 11 released above and 5 paged below, so the CHILD
        # COUNT can read anything while the window demonstrably moved. lo
        # moving up IS the release.
        check("t27-live-settle-released-after-edit_off",
              view.window_start > held_lo, True)
        check("t27-live-consistent", view.window_consistent(), True)

    # And the per-CHILD pins are untouched by the ruling (t5 walks them for the
    # window core; this is the one the mode-off walk depends on): a child
    # carrying per-widget edit state survives a prune with the MODE off, while
    # the rest of the grown window is released around it.
    app = WindowApp(big_fixture(400))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        await view.materialize(view.window_start - 12)
        await settle(pilot)
        grown = len(view.children)
        # PINNED DEEPER THAN THE FIRST EVICTABLE ROW, and that is the whole
        # point of the row: a pin at children[0] bounds the ABOVE-walk at once
        # (the entry measures exactly this: one `is_edit` widget → 19→19) and
        # the released-the-rest half was then asserting a zero the PIN caused.
        # Pinning children[3] asks the real question - WP-C t5's wording: THE
        # PIN BOUNDS, IT DOES NOT FREEZE THE END.
        first_three = list(view.children)[0:3]
        pinned = view.children[3]            # outside the margin, and in edit
        pinned.is_edit = 1                   # exactly what a Process edit sets
        await view.prune()
        await settle(pilot)
        children_after = list(view.children)
        check("t27-pin-released-the-rest",
              all(c not in children_after for c in first_three), True)
        check("t27-pin-child-survived", pinned in children_after, True)
        check("t27-pin-stopped-at-the-pin", children_after[0] is pinned, True)
        check("t27-pin-consistent", view.window_consistent(), True)


async def t28_the_mode_is_inherited_at_mount():
    """No replay code, because a materialized widget reads the mode AT MOUNT -
    the target AND the gap widgets mounted on the way there. (The earlier probe
    of this sampled a gap that landed on a user message, so the gap row here is
    the point of the check.)"""
    def with_reasoning(n=200):
        fixture = big_fixture(n)
        for index, message in enumerate(fixture["messages"]):
            if message["role"] == "assistant":
                message["reasoning"] = f"mm-cot-{index:04d}"
        return fixture

    for label, edit_mode, want in (("mode-off", False, False), ("mode-on", True, True)):
        app = WindowApp(with_reasoning())
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            chat = app.chat
            view = await open_view(app)
            await settle(pilot)
            await build_a_window_with_history_both_sides(view, pilot)
            # An index BELOW the window whose dict carries reasoning, far enough
            # below the top that the mount has to walk a gap over it - and a
            # second reasoning-bearing index inside that gap.
            target = next(i for i in range(view.window_start - 4, -1, -1)
                          if "reasoning" in chat.messages[i])
            gap = next(i for i in range(target + 1, view.window_start)
                       if "reasoning" in chat.messages[i])
            check("t28-setup-target-unmounted", view.widget(target), None)
            check("t28-setup-gap-unmounted", view.widget(gap), None)
            check("t28-setup-target-is-an-assistant-turn",
                  chat.messages[target]["role"], "assistant")
            view.is_edit = edit_mode
            await view.materialize(target)
            await settle(pilot)
            check(f"t28-{label}-target-inherited-the-mode",
                  view.widget(target).cnt["reasoning"].display, want)
            check(f"t28-{label}-gap-inherited-the-mode",
                  view.widget(gap).cnt["reasoning"].display, want)
            check(f"t28-{label}-consistent", view.window_consistent(), True)

    # A widget mounted BEFORE the mode came on flips with it: that is what
    # `show_cots`'s window-only loop is for, and why nothing has to be replayed.
    app = WindowApp(with_reasoning())
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        index = next(i for i in range(view.window_start, view.window_hi)
                     if "reasoning" in chat.messages[i])
        widget = await view.materialize(index)      # mounted with the mode OFF
        await settle(pilot)
        check("t28-roundtrip-mounted-with-the-mode-off",
              widget.cnt["reasoning"].display, False)
        view.action_edit_on()
        await settle(pilot)
        check("t28-roundtrip-edit_on-showed-it", widget.cnt["reasoning"].display, True)
        await view.action_edit_off()
        await settle(pilot)
        check("t28-roundtrip-edit_off-hid-it", widget.cnt["reasoning"].display, False)
        check("t28-roundtrip-consistent", view.window_consistent(), True)

    # The soundness half of `reset_message_edit`'s window-only loop: per-widget
    # edit state can never be out there unmounted and missed by it, because the
    # pin refuses to evict it.
    app = WindowApp(with_reasoning())
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)
        edited = view.children[0]
        edited.is_edit = 1
        await view.materialize(view.window_start - 6)
        await settle(pilot)
        grown = len(view.children)
        await view.prune()                        # the MODE is off: the walk runs
        await settle(pilot)
        check("t28-edit-pin-pruned-the-rest", len(view.children) < grown, True)
        check("t28-edit-pin-held-the-edited-child", edited in list(view.children), True)
        check("t28-edit-pin-consistent", view.window_consistent(), True)


async def t29_the_undo_primitives_hold_the_guard():
    """A page operation landing inside an undo's awaits is DROPPED, and the same
    call outside one is a page.

    WP-D fixed the same interleave between a settled prune and a page operation,
    and the reason was arithmetic rather than tidiness: `_grow_up` assigns lo
    ABSOLUTELY while prune ADDS to it. An undo primitive writes lo too (-1 for a
    removal below the window, +1 for an insert there) and awaits across child
    removals and mount batches, so it holds the guard the same way - and gives
    back what it found.
    """
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = await open_view(app)
        await settle(pilot)
        await build_a_window_with_history_both_sides(view, pilot)

        # The reader is parked at the WINDOW BOTTOM after the setup, so the page
        # the trigger would ask for is the one BELOW: spy `_grow_down`, and ask
        # for the guard's answer on both sides of the block.
        seen = []
        real_grow_down = type(view)._grow_down

        async def spy_grow_down(self, count, render=True):
            seen.append(self._window_page_op)
            return await real_grow_down(self, count, render)

        view._grow_down = spy_grow_down.__get__(view)
        await chat.undo._insert(new_message(), view.window_hi + 2)
        await settle(pilot)
        check("t29-insert-held-the-guard-over-its-batch", seen, [True])
        check("t29-insert-gave-it-back", view._window_page_op, False)
        view._grow_down = real_grow_down

        # A trigger that arrives while the guard is held is dropped, and the SAME
        # call outside the block is a page: the zero is the guard, not a window
        # with nothing left to mount.
        paged = []
        real_grow_down = type(view)._grow_down

        async def spy_page(self, count, render=True):
            paged.append(count)
            return await real_grow_down(self, count, render)

        view._grow_down = spy_page.__get__(view)
        # THE INSTRUMENT FIRST (this is what the red was): the setup froze the
        # triggers, and `_load_at_edge` asks `_triggers_frozen` FIRST - so with
        # the harness freeze still in place BOTH sides of the comparison were
        # dropped by the harness, the green "dropped" was about nothing and the
        # control could never page (/tmp/wp-e-probe-t27live-t29.py: frozen=True
        # every moment, paged stayed []). Setup frozen, experiment live: thaw,
        # assert the state is live, and the ONLY thing that can drop the page
        # inside the block is the guard.
        thaw_triggers(view)
        check("t29-triggers-live-after-thaw", view._triggers_frozen(), False)
        check("t29-the-edge-is-live", view._page_edge(), "newer")
        async with view.page_operations_held():
            check("t29-held-block-freezes-the-triggers",
                  view._triggers_frozen(), True)
            await view._load_at_edge()
            check("t29-guard-held-dropped-the-page", paged, [])
        await view._load_at_edge()
        await settle(pilot)
        check("t29-control-the-same-call-outside-is-a-page", len(paged), 1)
        check("t29-consistent", view.window_consistent(), True)

        # RESTORED, not cleared: hold the guard as a caller would and the
        # primitive must leave it held when it finishes.
        view._window_page_op = True
        await chat.undo._remove(view.window_start + 1)
        await settle(pilot)
        check("t29-removal-restored-a-guard-it-found-held", view._window_page_op, True)
        view._window_page_op = False
        check("t29-removal-worked-under-a-callers-guard", view.window_consistent(), True)
        view._grow_down = real_grow_down


async def main():
    print("=== the edits, the undo and the focus across the window edges ===")
    await t21_mount_message_index_classes()
    await t22_check_action_answers_from_the_data()
    await t23_undo_insert_at_the_edges()
    await t24_undo_remove_at_the_edges()
    await t25_undo_change_is_data_first()
    await t26_the_focus_rule()
    await t27_prune_refuses_while_editing()
    await t28_the_mode_is_inherited_at_mount()
    await t29_the_undo_primitives_hold_the_guard()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
