#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Persistent pin (pin / unpin) - the mode an on-demand ChatView grows into.

Rebuilt from /tmp/anchor-probe/probe6.py: a pin keeps "what is on screen stays
on screen" across EVERY layout pass and re-baselines on every landed scroll,
so user scrolling wins while late content changes are compensated. The
measurements reproduced here (probe 6's table): user scroll 21 respected;
mount above 21->25 no shift; late growth above 25->29 no shift; unpin and the
defect returns; 2 corrections total; 0 jump frames throughout.

  t7  pin sets the flag; a user scroll is respected (re-baseline, not a fight)
      and costs no correction.
  t8  mount an older message above: same-frame correction, 0 jump frames.
  t9  a message ABOVE the viewport grows LATER (the image/LaTeX landing case):
      view must not move; the correction lands, 0 jump frames.
  t11 total corrections for t8+t9 is exactly 2 (the pin is not twitching).
  t10 unpin: the same growth DOES move the view - proves it is the pin that
      holds it, the control without which t8/t9 prove nothing.
  t12 the pinned anchor widget is REMOVED: no phantom correction, and the pin
      re-baselines onto the new first visible child - growth above is held
      around the new anchor from then on.
"""
import asyncio

from anchored_app import (APP_SIZE, AnchoredScroll, FrameSpy, OLD_H, SCROLL_Y,
                          ScrollApp, check, make_msg, settle, setup, summary)


async def pin_lifecycle():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, _ = await setup(app, pilot)
        c.pin()
        check("t7-pin-flag", c.is_pinned, True)

        # a. user scroll: the anchor re-baselines, the view follows the intent
        c.scroll_to(0, 21, animate=False)
        await settle(pilot)
        check("t7-user-scroll-respected", round(c.scroll_y), 21)
        check("t7-user-scroll-costs-no-correction", c.corrections, 0)

        anchor = c.children[7]  # the child at content y=21, top of the viewport
        spy = FrameSpy(app, anchor).install()
        before = anchor.region.y

        # b. mount an older message above: no visible shift, zero jump frames
        await c.mount(make_msg("OLDER", OLD_H), before=0)
        await settle(pilot)
        check("t8-view-held", anchor.region.y, before)
        check("t8-scroll-compensated", round(c.scroll_y), 25)
        check("t8-zero-jump-frames", spy.bad_frames(before), [])

        # c. a message ABOVE the viewport grows later: no shift
        above = c.children[2]  # well above the viewport (scroll_y is 25)
        above.styles.height = 7
        above.refresh(layout=True)
        await settle(pilot)
        check("t9-late-growth-above-held", anchor.region.y, before)
        check("t9-scroll-compensated", round(c.scroll_y), 29)
        check("t9-zero-jump-frames", spy.bad_frames(before), [])

        check("t11-exactly-two-corrections", c.corrections, 2)

        # d. unpin: the defect returns - the pin was what held the view
        c.unpin()
        check("t10-unpin-clears-flag", c.is_pinned, False)
        above2 = c.children[1]
        above2.styles.height = 10
        above2.refresh(layout=True)
        await settle(pilot)
        check("t10-after-unpin-growth-moves-the-view",
              anchor.region.y != before, True)
        spy.remove()


async def pin_anchor_gone():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, anchor = await setup(app, pilot)
        c.pin()

        # the pinned anchor itself is removed: the correction against a
        # phantom is skipped...
        await anchor.remove()
        await settle(pilot)
        check("t12-anchor-removal-not-compensated", c.corrections, 0)

        # ...and the pin re-baselines onto the new first visible child: growth
        # above the viewport is held around THAT child from then on. (If the
        # pin had stayed armed on the dead widget, this growth would move the
        # view - the t10 control shows what an unheld view does.)
        new_anchor = next(ch for ch in c.children
                          if ch.region.bottom > c.region.y)
        row = new_anchor.region.y
        spy = FrameSpy(app, new_anchor).install()
        above = c.children[0]
        above.styles.height = 7
        above.refresh(layout=True)
        await settle(pilot)
        check("t12-rebaselined-pin-holds-the-view", new_anchor.region.y, row)
        check("t12-one-correction-around-new-anchor", c.corrections, 1)
        check("t12-zero-jump-frames", spy.bad_frames(row), [])
        spy.remove()


async def main():
    print("=== persistent pin (probe6.py rebuilt) ===")
    await pin_lifecycle()
    await pin_anchor_gone()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
