#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The window itself: open, slide, prune (WP-C Accept, first half).

  t1  open a 1k fixture -> exactly INITIAL_WINDOW mounted, window (950, 1000),
      open at the bottom, data complete, JSON untouched (load never writes),
      `view.messages is chat.messages` (the plan's standing hazard: nothing may
      window the DATA). t1b: the window has TEETH - a 120-message fixture also
      mounts only 50 (without windowing these counts are impossible; TRAPS #13
      applied to the checks themselves).
  t2  load_older(25) at a released bottom anchor: the view holds (frame spy:
      0 jump frames), lo -25, mounted +25, exactly one correction, JSON
      untouched, contiguity by dict identity. t2c is the control: the same
      operation with the anchor disarmed shows the defect (painted jump
      frames, scroll_y unmoved) - the t2 checks are only evidence because
      t2c proves they can fail.
  t3  prune evicting BELOW (user scrolled up): scroll_y, the view and the
      correction counter must not move AT ALL (rule 2 / anchored t14); the
      load_newer remount into the evicted gap holds the view (rule 3 / t15).
  t4  prune after opening at the bottom: evicts above back to the margin,
      scroll_y shifts by EXACTLY the evicted height (rule 1 / anchored t13),
      0 jump frames, and a second prune is a no-op (steady state reached; the
      mounted count returns to <= INITIAL_WINDOW - the window, not the data).
  t5  the fact-5 pins bound the eviction walks: an is_edit widget stops the
      above-walk (the one widget further up is still evicted - the pin bounds,
      it does not freeze the end); a focused widget below and the streaming
      tail while chat.is_working() block the below-walk, and the same prune
      without the pin evicts.
"""
import asyncio

from window_harness import (BIG_N, FakeWork, FrameSpy, WindowApp, big_fixture,
                            check, first_visible, settle, store_md5, summary)


async def t1_open():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        # baseline AFTER mount: ChatSettings.update_selects writes the chat on
        # mount (pre-existing behaviour, nothing to do with the window - it is
        # the reason the write count is measured as a DELTA, never absolute).
        md5_before, writes_before = store_md5(app), len(app.writes)
        await chat.chat_view.load()
        await settle(pilot)
        check("t1-mounted-is-the-initial-window", len(view.children), view.INITIAL_WINDOW)
        check("t1-window", view.window, (BIG_N - view.INITIAL_WINDOW, BIG_N))
        check("t1-open-at-bottom", round(view.scroll_y), round(view.max_scroll_y))
        check("t1-data-complete", len(chat.messages), BIG_N)
        check("t1-data-list-identity", view.messages is chat.messages, True)
        check("t1-window-consistent", view.window_consistent(), True)
        check("t1-first-child-projects-lo",
              view.children[0].message is chat.messages[950], True)
        check("t1-last-child-projects-tail",
              view.last_child().message is chat.messages[999], True)
        check("t1-load-writes-no-json", len(app.writes), writes_before)
        check("t1-store-untouched", store_md5(app), md5_before)
    app2 = WindowApp(big_fixture(120))
    async with app2.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        await app2.chat.chat_view.load()
        await settle(pilot)
        check("t1b-teeth-120-mounts-only-50", len(app2.chat.chat_view.children), 50)
        check("t1b-teeth-120-lo", app2.chat.chat_view.window_start, 70)


async def t2_load_older():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        md5_before, writes_before = store_md5(app), len(app.writes)
        # the state a page-load above really happens in: the user scrolled,
        # which released the follow-bottom anchor (scroll_to funnels through
        # the user path - the anchored_app setup precedent).
        view.scroll_to(0, round(view.max_scroll_y / 2), animate=False)
        await settle(pilot)
        anchor = first_visible(view)
        row = anchor.region.y
        spy = FrameSpy(app, anchor).install()
        corrections_before = view.corrections
        await view.load_older(25)
        await settle(pilot)
        check("t2-lo-moved-by-25", view.window_start, BIG_N - 50 - 25)
        check("t2-window", view.window, (925, 1000))
        check("t2-mounted-plus-25", len(view.children), 75)
        check("t2-anchor-held", anchor.region.y, row)
        check("t2-zero-jump-frames", spy.bad_frames(row), [])
        check("t2-one-correction", view.corrections, corrections_before + 1)
        check("t2-window-consistent", view.window_consistent(), True)
        check("t2-front-projects-the-new-lo",
              view.children[0].message is chat.messages[925], True)
        check("t2-json-untouched", store_md5(app), md5_before)
        check("t2-no-writes", len(app.writes), writes_before)
        spy.remove()


async def t2c_control_no_anchor():
    """TRAPS #13: falsify the instrument before believing it. Same fixture,
    same operation, one-shot anchor disarmed -> the plain-VerticalScroll
    defect: painted jump frames and scroll_y unmoved by the mounted height."""
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = app.chat.chat_view
        await view.load()
        await settle(pilot)
        view.scroll_to(0, round(view.max_scroll_y / 2), animate=False)
        await settle(pilot)
        anchor = first_visible(view)
        row = anchor.region.y
        scroll_before = round(view.scroll_y)
        spy = FrameSpy(app, anchor).install()
        view.arm_top_anchor = lambda: None  # disarm the compensation
        await view.load_older(25)
        await settle(pilot)
        spy.remove()
        check("t2c-control-scroll-y-unmoved", round(view.scroll_y), scroll_before)
        check("t2c-control-anchor-pushed-down", anchor.region.y > row, True)
        check("t2c-control-painted-frames-show-the-jump", spy.bad_frames(row) != [], True)


async def t3_prune_below_and_load_newer():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        view.scroll_to(0, 0, animate=False)  # top of the WINDOW; bottom far below
        await settle(pilot)
        visible = first_visible(view)
        row = visible.region.y
        scroll_before = round(view.scroll_y)
        corrections_before = view.corrections
        mounted_before = len(view.children)
        spy = FrameSpy(app, visible).install()
        await view.prune()
        await settle(pilot)
        check("t3-below-was-evicted", len(view.children) < mounted_before, True)
        check("t3-window-hi-shrank", view.window_hi < BIG_N, True)
        check("t3-window-still-at-lo", view.window_start, BIG_N - 50)
        check("t3-evict-below-scroll-y-untouched", round(view.scroll_y), scroll_before)
        check("t3-evict-below-zero-corrections", view.corrections, corrections_before)
        check("t3-evict-below-view-held", spy.bad_frames(row), [])
        check("t3-consistent", view.window_consistent(), True)
        hi_before = view.window_hi
        spy.clear()
        await view.load_newer(25)
        await settle(pilot)
        check("t3-load-newer-mounted-25", view.window_hi, hi_before + 25)
        check("t3-remount-below-view-held", spy.bad_frames(row), [])
        check("t3-remount-consistent", view.window_consistent(), True)
        check("t3-remount-front-unchanged",
              view.children[0].message is chat.messages[view.window_start], True)
        spy.remove()


async def t4_prune_above_at_bottom():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        scroll_before = round(view.scroll_y)
        lo_before = view.window_start
        old_children = list(view.children)
        heights = {id(c): c.region.height for c in old_children}
        visible = first_visible(view)
        row = visible.region.y
        spy = FrameSpy(app, visible).install()
        await view.prune()
        await settle(pilot)
        # the evicted set is a prefix of the OLD child list; its size is the
        # lo shift (rule 1). At the BOTTOM the follow-bottom anchor keeps the
        # view pinned to the tail through the eviction, so the view holds
        # (zero jump frames - the check that matters here, the same anchor
        # win probe 7 measured) and scroll_y sits exactly one evicted-height
        # lower, clamped at the new max:
        #   scroll_after == min(scroll_before - evicted, new_max).
        n_evicted = view.window_start - lo_before
        check("t4-above-was-evicted", n_evicted > 0, True)
        check("t4-bottom-intact", view.window_hi, BIG_N)
        check("t4-scroll-pinned-to-the-tail", round(view.scroll_y), round(view.max_scroll_y))
        expected_scroll = min(scroll_before - sum(heights[id(c)] for c in old_children[:n_evicted]),
                              round(view.max_scroll_y))
        check("t4-scroll-shifted-by-evicted-height-clamped-at-max",
              round(view.scroll_y), expected_scroll)
        check("t4-zero-jump-frames", spy.bad_frames(row), [])
        check("t4-mounted-back-under-window-size",
              len(view.children) <= view.INITIAL_WINDOW, True)
        check("t4-consistent", view.window_consistent(), True)
        mounted_steady = len(view.children)
        spy.clear()
        await view.prune()
        await settle(pilot)
        check("t4-second-prune-is-steady", len(view.children), mounted_steady)
        check("t4-second-prune-no-frames-moved", spy.bad_frames(row), [])
        spy.remove()


async def t5_pins():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app.chat
        view = chat.chat_view
        await view.load()
        await settle(pilot)
        # is_edit pin at the TOP: scroll to the bottom of a fresh window so
        # messages 950/951 are far above the viewport; pin 951; the above-walk
        # evicts 950 and STOPS at 951.
        edit_pin = view.widget(951)
        edit_pin.is_edit = 1
        await view.prune()
        await settle(pilot)
        check("t5-unpinned-above-evicted", view.widget(950), None)
        check("t5-is_edit-pin-survives", view.widget(951) is edit_pin, True)
        check("t5-lo-stopped-at-the-pin", view.window_start, 951)
        check("t5-consistent-after-pinned-prune", view.window_consistent(), True)
        # streaming tail pin at the BOTTOM: scroll to the window top, arm a
        # working chat, prune: the below-walk breaks on the pinned tail at
        # once - nothing below goes.
        view.scroll_to(0, 0, animate=False)
        await settle(pilot)
        work = FakeWork()
        work.is_running = True
        chat.work = work
        chat._work = work
        mounted_before = len(view.children)
        await view.prune()
        await settle(pilot)
        check("t5-tail-pin-blocks-below", len(view.children), mounted_before)
        # the same prune with the pin released evicts the bottom back to the
        # margin.
        work.is_running = False
        await view.prune()
        await settle(pilot)
        check("t5-no-pin-below-evicts", len(view.children) < mounted_before, True)
        check("t5-consistent", view.window_consistent(), True)
        # focus pin: focus the LAST mounted widget (below the viewport at
        # scroll 0), unevictable while it holds focus.
        tail_widget = view.last_child()
        tail_widget.focus(scroll_visible=False)
        await settle(pilot)
        mounted_before = len(view.children)
        await view.prune()
        await settle(pilot)
        check("t5-focus-pin-blocks-below", len(view.children), mounted_before)
        check("t5-focused-widget-still-mounted", view.last_child() is tail_widget, True)


async def main():
    print("=== the window: open, slide, prune ===")
    await t1_open()
    await t2_load_older()
    await t2c_control_no_anchor()
    await t3_prune_below_and_load_newer()
    await t4_prune_above_at_bottom()
    await t5_pins()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
