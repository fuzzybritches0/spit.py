#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""One-shot top anchor (arm_top_anchor + the next layout pass).

Rebuilt from /tmp/anchor-probe/probe.py (P8 measurements, 20 messages x 3 rows
in a 10-row viewport, scrolled to y=15, a 4-row message mounted at index 0):

  t1  plain VerticalScroll - the CONTROL: the defect is real and EVERY painted
      frame shows the jump (scroll_y stays 15, the anchor child is pushed 4
      rows down, and it persists until the user scrolls). Without this control
      the green checks below would only prove that nothing moved.
  t2  AnchoredScroll, mount 1 above: scroll_y 15->19, anchor stays at the
      viewport top, 0 jump frames, 1 correction.
  t3  AnchoredScroll, batch() mount 3 above: same, 15->27, 0 jump frames.
  t4  with Textual's bottom anchor also armed (the ChatView.__init__ state):
      the correction lands, 0 jump frames - proof the set_reactive write did
      NOT leave the bottom anchor fighting for the frame.
  t5  after a correction: a manual scroll is exact, and follow-bottom armed
      afterwards still sticks to the bottom on append.
  t6  disarm-if-anchor-gone: an armed one-shot whose anchor is removed is
      skipped (no phantom compensation) and disarms; t6b arming with no
      children arms nothing.
"""
import asyncio

from anchored_app import (APP_SIZE, AnchoredScroll, FrameSpy, MSG_H, OLD_H,
                          SCROLL_Y, ScrollApp, VerticalScroll, check, make_msg,
                          settle, setup, summary)


async def t1_plain_defect():
    app = ScrollApp(VerticalScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        spy = FrameSpy(app, anchor).install()
        await c.mount(make_msg("OLDER-1", OLD_H), before=0)
        await settle(pilot)
        spy.remove()
        check("t1-control-scroll-y-stays", round(c.scroll_y), SCROLL_Y)
        check("t1-control-anchor-pushed-down", anchor.region.y, OLD_H)
        check("t1-control-painted-frames-show-the-jump",
              spy.bad_frames(0) != [], True)


async def t2_mount_one_above():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        spy = FrameSpy(app, anchor).install()
        c.arm_top_anchor()
        await c.mount(make_msg("OLDER-1", OLD_H), before=0)
        await settle(pilot)
        spy.remove()
        check("t2-view-held", anchor.region.y, 0)
        check("t2-scroll-compensated-exactly", round(c.scroll_y), SCROLL_Y + OLD_H)
        check("t2-zero-jump-frames", spy.bad_frames(0), [])
        check("t2-one-correction", c.corrections, 1)


async def t3_batched_mount_above():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        spy = FrameSpy(app, anchor).install()
        c.arm_top_anchor()
        async with c.batch():
            for i in range(3):
                await c.mount(make_msg(f"OLDER-{i}", OLD_H), before=0)
        await settle(pilot)
        spy.remove()
        check("t3-view-held", anchor.region.y, 0)
        check("t3-scroll-compensated-exactly", round(c.scroll_y), SCROLL_Y + 3 * OLD_H)
        check("t3-zero-jump-frames", spy.bad_frames(0), [])


async def t4_bottom_anchor_coexistence():
    app = ScrollApp(AnchoredScroll, bottom_anchor=True)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)  # the setup scroll released the
        # bottom anchor exactly the way any user scroll does - what is left to
        # prove is that the correction lands while Textual's anchored rewrite
        # runs AFTER process_layout in the same compositor pass: a competing
        # bottom anchor would show up as frames at the wrong row.
        spy = FrameSpy(app, anchor).install()
        c.arm_top_anchor()
        await c.mount(make_msg("OLDER-1", OLD_H), before=0)
        await settle(pilot)
        spy.remove()
        check("t4-view-held", anchor.region.y, 0)
        check("t4-scroll-compensated", round(c.scroll_y), SCROLL_Y + OLD_H)
        check("t4-zero-jump-frames", spy.bad_frames(0), [])


async def t5_after_the_correction():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        c.arm_top_anchor()
        await c.mount(make_msg("OLDER-1", OLD_H), before=0)
        await settle(pilot)
        c.scroll_relative(0, 2, animate=False)
        await settle(pilot)
        check("t5-manual-scroll-still-exact", round(c.scroll_y), SCROLL_Y + OLD_H + 2)
        c.anchor()  # follow bottom, like ChatView does for streaming
        await c.mount(make_msg("NEWEST", MSG_H))
        await settle(pilot)
        check("t5-follow-bottom-still-sticks", round(c.scroll_y), round(c.max_scroll_y))


async def t6_anchor_gone_while_armed():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        c.arm_top_anchor()
        await anchor.remove()  # the anchor widget is gone at the next pass
        await settle(pilot)
        check("t6-no-phantom-correction", c.corrections, 0)
        # The arm is disarmed, not kept alive for some later pass: this next
        # mount above moves the view exactly like the plain control (t1).
        await c.mount(make_msg("OLDER-1", OLD_H), before=0)
        await settle(pilot)
        check("t6-arm-disarmed-not-held-for-later", round(c.scroll_y), SCROLL_Y)
        check("t6-still-zero-corrections", c.corrections, 0)


async def t6b_arm_with_no_children():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c = app.container
        await pilot.pause()
        c.arm_top_anchor()  # nothing visible to anchor on: arms nothing
        await c.mount(*[make_msg(f"MSG-{i}") for i in range(10)])
        await settle(pilot)
        check("t6b-empty-container-no-correction", c.corrections, 0)


async def main():
    print("=== one-shot top anchor (probe.py rebuilt) ===")
    await t1_plain_defect()
    await t2_mount_one_above()
    await t3_batched_mount_above()
    await t4_bottom_anchor_coexistence()
    await t5_after_the_correction()
    await t6_anchor_gone_while_armed()
    await t6b_arm_with_no_children()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
