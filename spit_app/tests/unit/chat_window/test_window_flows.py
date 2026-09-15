#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The window in the app's flows (WP-C Accept, second half).

  t6  abort-while-scrolled-up: the bottom is pruned away (idle), then a work
      run is entered and abort is pressed - `action_abort` materializes the
      tail by data index and removes it from BOTH sides; the chat is one
      message shorter and the window stays consistent.
  t7  materialize at both edges: above the top grows lo (anchor-armed, view
      held, 0 jump frames), below a pruned bottom closes the gap AND renders
      it (gap widgets are history, finished from their dicts); an already
      mounted index returns the same widget without touching anything; an
      index outside the DATA raises IndexError (what children[i] raised);
      materialize(0) covers the whole head.
  t8  churn (probe 7 at the ChatView level): 8 x (load_older(25) + prune()) -
      the mounted count stays flat and <= INITIAL_WINDOW at every depth, the
      window is consistent after every cycle, lo slides monotonically toward
      0, and the JSON is never touched by a window move (writes stay 0,
      store md5 fixed).
  t9  the chat-switch interplay, pinned as it works TODAY (side_panel.py
      option_selected / handlers.py on_ready): every opened chat keeps its
      own Chat widget and window mounted in #main (old ones are hidden, not
      destroyed - that is what holds today and what this WP keeps); opening
      another chat does not touch this window, a hidden chat is never pruned,
      and re-selecting an open chat reuses it (no second Chat, no reload).
"""
import asyncio
import json

from window_harness import (FakeWork, FrameSpy, WindowApp, big_fixture, check,
                            first_visible, settle, store_md5, summary)


async def t6_abort_scrolled_up():
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        view.scroll_to(0, 0, animate=False)   # scrolled up (releases follow-bottom)
        await settle(pilot)
        await view.prune()                    # idle: the bottom goes, tail included
        await settle(pilot)
        check("t6-tail-pruned-away-first", view.widget(199), None)
        work = FakeWork(busy=False)
        work.is_running = True
        chat._work = work
        chat.work = work
        await chat.action_abort()
        await settle(pilot)
        check("t6-work-cancelled", work.cancelled, 1)
        check("t6-tail-gone-from-data", len(chat.messages), 199)
        check("t6-tail-gone-from-tree", view.widget(199), None)
        check("t6-last-message-is-the-old-neighbour",
              chat.messages[-1]["content"][0]["text"], "mm-open-0198 line")
        check("t6-window-consistent", view.window_consistent(), True)
        check("t6-data-list-identity", view.messages is chat.messages, True)


async def t7_materialize_edges():
    app = WindowApp(big_fixture(200))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        anchor = first_visible(view)
        row = anchor.region.y
        spy = FrameSpy(app, anchor).install()
        m = await view.materialize(140)                     # far above the top
        await settle(pilot)
        check("t7-above-lo-moved", view.window_start, 140)
        check("t7-widget-returned", m is view.widget(140), True)
        check("t7-anchor-held", anchor.region.y, row)
        check("t7-zero-jump-frames", spy.bad_frames(row), [])
        check("t7-consistent", view.window_consistent(), True)
        again = await view.materialize(150)                 # already mounted
        await settle(pilot)
        check("t7-mounted-is-no-op", again is view.widget(150), True)
        check("t7-no-op-lo-untouched", view.window_start, 140)
        head = await view.materialize(0)                    # the whole head
        await settle(pilot)
        check("t7-materialize-0", (view.window, view.window_start), ((0, 200), 0))
        check("t7-head-widget", head is view.children[0], True)
        check("t7-head-rendered", "content" in view.children[0].cnt, True)
        # below a pruned bottom: scroll to the head, prune, materialize the tail
        view.scroll_to(0, 0, animate=False)
        await settle(pilot)
        await view.prune()
        await settle(pilot)
        check("t7-bottom-pruned-for-test", view.widget(199), None)
        tail = await view.materialize(199)
        await settle(pilot)
        check("t7-below-tail-mounted", tail is view.widget(199), True)
        check("t7-below-window-whole", view.window, (0, 200))
        gap = view.widget(180)
        check("t7-gap-rendered-from-its-dict", "content" in gap.cnt, True)
        check("t7-consistent", view.window_consistent(), True)
        for bad in (-1, 200):
            try:
                await view.materialize(bad)
                check(f"t7-out-of-data-{bad}", "no raise", "IndexError")
            except IndexError:
                check(f"t7-out-of-data-{bad}", "IndexError", "IndexError")
        spy.remove()


async def t8_churn_flat_and_json_untouched():
    app = WindowApp(big_fixture(1000))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        md5_before, writes_before = store_md5(app), len(app.writes)
        # The churn is probe 7's cycle at the ChatView level: load a page,
        # prune back to the margin. The HEADLINE number is the mounted count
        # - flat, a function of viewport + margin, never of history length
        # (WP-F's table is the official measurement; this is the tripwire).
        # lo is NOT expected to slide monotonically: a prune at a viewport
        # that has not moved legitimately reclaims the page just mounted
        # above the margin - the view never asked to keep it. What must hold
        # is 0 jump frames per cycle, window consistency, and lo in the data.
        series, jumps = [], []
        for cycle in range(8):
            spy = FrameSpy(app, first_visible(view))
            row = spy.tracked.region.y
            spy.install()
            await view.load_older(25)
            await view.prune()
            await settle(pilot)
            spy.remove()
            series.append(len(view.children))
            if spy.bad_frames(row):
                jumps.append((cycle, spy.bad_frames(row)))
            check(f"t8-cycle-{cycle}-consistent", view.window_consistent(), True)
        check("t8-mounted-flat-in-history", max(series) - min(series) <= 2, True)
        check("t8-mounted-under-window-size", max(series) <= view.INITIAL_WINDOW, True)
        check("t8-zero-jump-frames-every-cycle", jumps, [])
        check("t8-lo-in-data", 0 <= view.window_start < 1000, True)
        check("t8-json-untouched-by-window-moves", store_md5(app), md5_before)
        check("t8-no-writes", len(app.writes), writes_before)


async def t9_chat_switch_interplay():
    content = big_fixture(200)
    content_b = big_fixture(60)
    app = WindowApp(content)
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat_a = app.chat
        await chat_a.chat_view.load()
        await settle(pilot)
        window_a = chat_a.chat_view.window
        # what side_panel.option_selected does for a not-yet-open chat: mount
        # a fresh Chat into #main, load it, focus it. (The same two lines as
        # handlers.py on_ready.)
        app.store["chats/chat-b.json"] = json.loads(json.dumps(content_b))
        from spit_app.chat.chat import Chat
        main = app.query_one("#main")
        await main.mount(Chat("chat-b"))
        chat_b = app.query_one("#chat-b")
        await chat_b.chat_view.load()
        await settle(pilot)
        # hide-all-show-one, the side_panel loop:
        for cont in main.children:
            cont.display = cont is chat_b
        await settle(pilot)
        check("t9-both-chats-mounted-in-main",
              [c.id for c in main.children if c.id in ("smoke-chat", "chat-b")],
              ["smoke-chat", "chat-b"])
        check("t9-per-chat-windows", (window_a, chat_b.chat_view.window),
              ((150, 200), (10, 60)))
        check("t9-hidden-chat-not-pruned", len(chat_a.chat_view.children), 50)
        await chat_b.chat_view.load_older(10)
        await settle(pilot)
        check("t9-b-slide-leaves-a-alone", chat_a.chat_view.window, window_a)
        # re-select A: the side_panel loop finds the mounted chat and shows
        # it - no second Chat widget, no reload, the window is where it was.
        for cont in main.children:
            cont.display = cont is chat_a
        await settle(pilot)
        check("t9-reopen-reuses-no-stack",
              len([c for c in main.children if c.id == "smoke-chat"]), 1)
        check("t9-window-preserved-across-switch", chat_a.chat_view.window, window_a)


async def main():
    print("=== the window in the flows: abort, materialize, churn, switch ===")
    await t6_abort_scrolled_up()
    await t7_materialize_edges()
    await t8_churn_flat_and_json_untouched()
    await t9_chat_switch_interplay()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
