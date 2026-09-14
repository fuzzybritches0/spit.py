#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The SLIDING window: eviction at BOTH ends of the pinned scroll.

Rebuilt from /tmp/anchor-probe/probe7.py - the measurements the plan's model
rules 1-3 rest on (30 messages x 3 rows, 10-row viewport, scrolled to y=30,
pinned; frame spy on App._display throughout):

  t13 EVICT ABOVE (user scrolled down): the same event as a mount above with
      the sign flipped - the view is held (anchor row unchanged, zero jump
      frames) and scroll_y shifts by EXACTLY the evicted height (30->18 for
      4 x 3 = 12 rows).
  t14 EVICT BELOW (user scrolled up, nothing intersecting or above the
      viewport removed): pure arithmetic - scroll_y, the view AND the
      correction counter must not move AT ALL (scroll_y <= new_total -
      viewport_h holds by construction while the margin below is kept).
  t15 REMOUNT into an evicted gap below (the load_newer case): pin holds,
      same frame.
  t16 CHURN: 20 mount-older/prune-both-ends cycles under the clamp-zone
      invariant (>= viewport + MARGIN rows kept on each side) - mounted
      widget count stays FLAT (bounded by viewport + margin, measured worst
      13 at viewport 10 / margin 20, never by history), anchor held in every
      cycle, no frame ever shows the wrong anchor row.

A message widget is a disposable projection of its dict, so eviction is
child.remove() and remount is the normal mount path plus the anchor - this is
the container-level proof of that, before any ChatView uses it.
"""
import asyncio

from anchored_app import (APP_SIZE, MSG_H, VIEW_H, AnchoredScroll, FrameSpy,
                          ScrollApp, check, make_msg, settle, setup, summary)


async def eviction_and_churn():
    app = ScrollApp(AnchoredScroll)
    async with app.run_test(size=APP_SIZE) as pilot:
        c, _ = await setup(app, pilot, n=30, scroll_y=30)
        c.pin()
        anchor = next(ch for ch in c.children if ch.region.bottom > c.region.y)
        spy = FrameSpy(app, anchor).install()
        before = (round(c.scroll_y), anchor.region.y)  # (30, 0)

        # t13. evict the 4 children strictly ABOVE the viewport (12 rows).
        top = [ch for ch in c.children if ch.region.bottom <= c.region.y][:4]
        async with c.batch():
            for ch in top:
                await ch.remove()
        await settle(pilot)
        check("t13-scroll-shifts-by-exactly-the-evicted-height",
              round(c.scroll_y), before[0] - 4 * MSG_H)
        check("t13-view-held", anchor.region.y, before[1])
        check("t13-zero-jump-frames", spy.bad_frames(before[1]), [])

        # t14. evict BELOW the viewport (after mounting a bottom page): the
        # view, scroll_y AND the correction counter must not move at all.
        await c.mount(*[make_msg(f"BOTTOM-{i}") for i in range(10)])
        await settle(pilot)
        corrections_before = c.corrections
        spy.clear()
        below = [ch for ch in c.children if ch.region.y >= c.region.y + VIEW_H]
        async with c.batch():
            for ch in below:
                await ch.remove()
        await settle(pilot)
        check("t14-evict-below-scroll-y-untouched", round(c.scroll_y), 18)
        check("t14-evict-below-view-held", anchor.region.y, before[1])
        check("t14-evict-below-zero-corrections", c.corrections,
              corrections_before)
        check("t14-evict-below-zero-jump-frames", spy.bad_frames(before[1]), [])

        # t15. remount into the gap below (the load_newer path): pin holds.
        spy.clear()
        await c.mount(make_msg("LATE", 5))
        await settle(pilot)
        check("t15-remount-below-view-held", anchor.region.y, before[1])
        check("t15-remount-below-zero-jump-frames", spy.bad_frames(before[1]), [])

        # t16. churn: 20 x (mount 4 rows above + prune BOTH ends back to the
        # margin). The margin invariant (>= viewport + 2*VIEW_H rows each
        # side) is what keeps the correction out of the clamp zone - pruning
        # through it is the hazard probe 7 found, so the cycle respects it by
        # construction, exactly as the probe ran it.
        MARGIN = 2 * VIEW_H
        worst_mounted, jumps, series = 0, [], []
        for i in range(20):
            spy.clear()
            async with c.batch():
                await c.mount(make_msg(f"OLDER-{i}", 4), before=0)
                above = [ch for ch in c.children
                         if ch.region.bottom <= c.region.y]
                while sum(ch.region.height for ch in above) - 4 > MARGIN:
                    gone = above.pop(0)
                    await gone.remove()
                below = [ch for ch in c.children
                         if ch.region.y >= c.region.y + VIEW_H]
                while sum(ch.region.height for ch in below) - VIEW_H > MARGIN:
                    gone = below.pop()
                    await gone.remove()
            await settle(pilot)
            worst_mounted = max(worst_mounted, len(c.children))
            if anchor.region.y != before[1]:
                jumps.append((i, anchor.region.y))
            series.append(len(c.children))
            check(f"t16-cycle-{i}-no-jump-frames", spy.bad_frames(before[1]), [])
        check("t16-anchor-held-every-cycle", jumps, [])
        check("t16-mounted-count-bounded-flat-in-history", worst_mounted <= 13,
              True)
        check("t16-mounted-flat-over-cycles", series[-1] <= series[2] + 1, True)
        check("t16-anchor-still-mounted", anchor in c.children, True)
        print(f"    (churn mounted series c0,c2,c19 = {[series[0], series[2], series[-1]]}, "
              f"worst={worst_mounted}, corrections={c.corrections})")
        spy.remove()


async def main():
    print("=== sliding-window eviction (probe7.py rebuilt) ===")
    await eviction_and_churn()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
