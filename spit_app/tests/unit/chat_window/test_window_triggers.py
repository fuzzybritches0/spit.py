#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The scroll triggers (WP-D Accept): the view asks for history, the window answers.

  t10 the headline: a continuous wheel-UP through a 1k fixture pages history in AND
      prunes the bottom - `lo` slides up, `hi` slides down, the mounted count is
      FLAT at every depth, and every settle paints zero jump frames. Its control
      freezes the triggers and the same 200 notches move nothing at all: without it
      the flat count would be an accident of the fixture (TRAPS #13).
  t11 the debounce: thirty scroll events, ONE prune. The number of SCROLLS is what
      prunes, never the number of notches - and frozen, nothing prunes.
  t12 the second half of the plan - after every LOAD, not only after a settled
      scroll. An UNBROKEN burst never settles (the timer is re-armed by every
      notch), so once the reader is deep in the history it is the prune behind the
      page operation that holds the bound; the control takes the prune alone away
      and the count climbs past INITIAL_WINDOW, which is the claim in one number.
  t13 the way back down reloads symmetrically: flat while both sides have history,
      one constant at the tail, and the reader arrives AT the tail.
  t14 the release semantics interact (WP-D's one deliberate touch on follow-bottom,
      measured three ways): a page below that will NOT reach the tail releases the
      anchor and HOLDS the view; a page that DOES reach the tail is the tail, keeps
      the anchor and pulls; an already-released anchor is not released again.
  t15 the starvation this design exists to close: parked at the window bottom with
      history unmounted below, the settle pages that history back in WITHOUT
      dragging the reader. The control is the defect itself - prune alone, no edge
      re-check, leaves the reader starved - so t15's zero is read against it.
  t16 the true ends stop cleanly, and the control is the same call taken at the
      other window edge with history there: it IS a page, so the zero is an end and
      not a miss.
  t17 the freezes: is_edit (the same direct call, before and after), a working chat
      (triggers silent AND the tail still stuck to the bottom, then the same call
      once the chat is idle), and a page operation in flight.
  t18 the guard extension: materialize() holds the page-op guard across its mount
      batch, gives it back, drops a trigger that arrives while it is held, and
      RESTORES a guard it found held instead of clearing it.
  t19 the anti-oscillation invariant: TRIGGER < PRUNE, and a view parked at either
      window edge (and at the true top) is a FIXED POINT - the same window, mounted
      count, scroll_y and correction count, settle after settle. A chase is the
      failure mode of the whole design.

Three rules about how a trigger is driven here, all learned from the probes
(/tmp/wp-d2-probe-*.py), and each one is a place an earlier draft of this file was
wrong rather than a style preference:

* A trigger is driven by a WHEEL (`window_harness.wheel_event`, a real
  MouseScrollUp/Down forwarded by the screen), because a scroll is what drives it.
* A STATE is asked for directly: `anchor()` arms follow-bottom and lands at the
  window bottom; `scroll_to` is the user path that RELEASES it; `_scroll_settled()`
  and `_load_at_edge()` are the two callbacks themselves, called once. `settle()`
  only ever waits for a timer that something has already armed.
* A snapshot is taken AFTER any armed settle has run, and an edge is BUILT (scroll
  to the edge, prune, then release the freeze) rather than assumed from wherever a
  previous scroll left the view - "mid-window" measured 21 rows of history on a
  side against a 17-row trigger is not an edge, it is a side with enough history.
"""
import asyncio

# window_harness FIRST: it puts the repo root (and chat_smoke's stub) on sys.path,
# which is how the other two files in this suite import the app at all.
from window_harness import (BIG_N, FakeWork, FrameSpy, WindowApp, big_fixture,
                            CallCount, check, first_visible, freeze_settle,
                            freeze_triggers, rest, settle, thaw_settle,
                            thaw_triggers, wheel_event, wheel_scroll, summary)

# A message of this fixture renders 7 rows at (80,24) under the app's stylesheet and
# the viewport is 17 rows, so a settled mid-history window is 11-15 children and the
# tail window is 8 (/tmp/wp-d2-probe-suite-numbers.py). The page boundary lands on a
# different message each time, which is the +-2 the flatness checks allow.
FLAT_SPAN = 4


async def open_view(app):
    """Mount the chat the way opening a chat does, and come to rest."""
    await app.chat.chat_view.load()
    return app.chat.chat_view


async def top_index(view):
    """The MESSAGE at the top of the viewport - the only position measure that
    survives a sliding window. `scroll_y` is WINDOW-relative and the window moves
    under it (measured: scroll_y 352 against 308 rows of content above the
    viewport), so every "did the reader move" check in this file is an index."""
    return view.widget_index(first_visible(view))


async def build_an_edge(view, pilot, up=True):
    """Put the reader AT a window edge with history UNMOUNTED on that side.

    The order is the whole point, and getting it backwards is a bug this file had:
    `prune()` releases the ends that are far from the VIEWPORT, so the reader has to
    be at the OTHER end while it runs. Park at the opposite end, prune (that is
    what unmounts the history on the side we are about to go to), then move to the
    edge and release the freeze. Frozen throughout, because `scroll_to` is a user
    scroll and would arm the very settle these checks are meant to measure; the
    thing that happens after the thaw is then the trigger's, and only the trigger's.
    """
    freeze_triggers(view)
    view.scroll_to(0, view.max_scroll_y if up else 0, animate=False)
    await settle(pilot)
    await view.prune()
    await settle(pilot)
    view.scroll_to(0, 0 if up else view.max_scroll_y, animate=False)
    await settle(pilot)
    thaw_triggers(view)
    # Assert the state that was asked for: a downstream zero is only evidence about
    # an END if the setup really parked the reader at an edge with history there.
    label = "top" if up else "bottom"
    at_edge = round(view.scroll_y) == (0 if up else round(view.max_scroll_y))
    history = view.window_start if up else len(view.messages) - view.window_hi
    check(f"edge-{label}-is-at-the-edge", at_edge, True)
    check(f"edge-{label}-has-history-unmounted-beyond", history > 0, True)
    return view.window

async def walk_into_the_sliding_region(app, pilot, view, max_bursts=16):
    """Get the window sliding the way a reader does it, then let it come to rest.

    This exists because of where `load()` starts: it mounts INITIAL_WINDOW at the
    tail, a notch is 2 rows, and the fixture's messages are 7 rows tall, so the
    first ~170 notches are travel INSIDE those 50 messages and say nothing about the
    bound. The walk is therefore driven until the STATE the burst needs - with a
    ceiling - and not for a fixed number of notches. Measured, burst by burst
    (/tmp/wp-d3-probe-setup.py): the first settle already takes the mounted count
    from 50 to 13 and the second releases the tail, while `lo` only passes below the
    range `load()` mounted at burst 11 (950 -> 939). The earlier draft of this
    helper walked 8 bursts and asserted `window_start < 940`, which is precisely the
    one depth where the state is nearly right and the assertion is not (it reads 953
    there), so the burst ran from a state its own setup had just called wrong.

    Live, not frozen - a reader reaches the sliding region by scrolling, and what the
    scrolling does is exactly what is under test.
    """
    below_the_open_window = BIG_N - view.INITIAL_WINDOW
    for _ in range(max_bursts):
        if (view.window_start < below_the_open_window and view.window_hi < BIG_N
                and len(view.children) <= 20):
            break
        await wheel_scroll(app, pilot, view, 20, up=True)
        await settle(pilot)
    check("setup-window-is-past-what-load-mounted",
          view.window_start < below_the_open_window, True)
    check("setup-window-has-released-the-tail", view.window_hi < BIG_N, True)
    check("setup-window-is-at-a-settled-size", len(view.children) <= 20, True)
    check("setup-came-to-rest", await rest(pilot, view), True)



async def t10_up_walk_pages_and_prunes():
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        lo0, hi0 = view.window
        top0 = await top_index(view)
        mounted, jumps = [], []
        for burst in range(10):
            await wheel_scroll(app, pilot, view, 20, up=True)
            tracked = first_visible(view)
            row = tracked.region.y
            spy = FrameSpy(app, tracked).install()
            await settle(pilot)
            spy.remove()
            if spy.bad_frames(row):
                jumps.append((burst, spy.bad_frames(row)))
            mounted.append(len(view.children))
            # At rest, because `window_consistent()` is an invariant of QUIESCENCE
            # (both window moves write `window_start` after their batch, so sampling
            # one mid-batch reads False with nothing wrong). See `rest()`.
            check(f"t10-burst-{burst}-came-to-rest", await rest(pilot, view), True)
            check(f"t10-burst-{burst}-consistent", view.window_consistent(), True)
        check("t10-reader-travelled-up", top0 - await top_index(view) > 30, True)
        check("t10-lo-slid-up", view.window_start < lo0, True)
        check("t10-bottom-was-pruned", view.window_hi < hi0, True)
        # Flatness is measured over the walk, not over its first sample: sample 0 is
        # the state load() left behind (INITIAL_WINDOW mounted, the reader inside it,
        # nothing asked for yet) and the walk's first settle is what brings it down
        # to the viewport-sized window. Counting that first sample as a violation
        # would make the headline number a claim about 50 vs 13 rather than about
        # depth - and the number that matters is that deep in a 1k history the window
        # is STILL 13, which is t10-mounted-settled-size-below.
        check("t10-mounted-flat-through-the-walk",
              max(mounted[1:]) - min(mounted[1:]) <= FLAT_SPAN, True)
        check("t10-never-mounted-more-than-load-does",
              max(mounted) <= view.INITIAL_WINDOW, True)
        check("t10-mounted-settled-size-below", mounted[-1] <= 20, True)
        check("t10-zero-jump-frames", jumps, [])
        # The control: the SAME 200 notches with the triggers frozen. The reader
        # still scrolls to the top of what is mounted (a wheel is a wheel), but no
        # page comes in and no bottom is released.
        lo_c, hi_c, mounted_c = view.window_start, view.window_hi, len(view.children)
        freeze_triggers(view)
        await wheel_scroll(app, pilot, view, 200, up=True)
        await settle(pilot)
        check("t10-control-frozen-no-page-in", view.window_start, lo_c)
        check("t10-control-frozen-no-prune", view.window_hi, hi_c)
        check("t10-control-frozen-mounted-unchanged", len(view.children), mounted_c)


async def t11_debounce_one_settle_per_scroll():
    """Thirty scroll events re-arm ONE timer, and the burst settles once.

    Two claims, because they fail differently. The MECHANISM is that every scroll
    re-arms the same single timer (`arms == watches`, and nothing armed afterwards):
    that is what a debounce is, and it is timing-free. The COUNT is a ratio, not a
    constant - prunes follow scrolls, never notches.

    The count cannot be a constant on this design, and pretending otherwise is the
    machine-dependent assertion `unit:terminal` already got burned by. The settle is
    a wall-clock `SCROLL_SETTLE_DELAY` of 0.15 s; a notch costs a frame plus the
    message pump, measured 66 ms here. Thirty notches of pure travel (this state:
    freshly open, the reader inside what `load()` mounted, nothing to page) therefore
    re-arm the timer faster than it expires and settle exactly ONCE - but 30 notches
    taken deep in a sliding window, where each notch can carry a mount batch of its
    own, settled 3 times in one measurement. A per-notch prune would be 30 either
    way, and that is the failure this check exists to catch.
    """
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        # The debounce is measured on the SETTLE, not on prune(): a page operation
        # prunes too (t12), so counting prunes would charge the page operations to
        # the debounce and make the ratio meaningless.
        settles = CallCount(view, "_scroll_settled").install()
        watches = CallCount(view, "watch_scroll_y").install()
        arms = CallCount(view, "_arm_scroll_settle").install()
        await wheel_scroll(app, pilot, view, 30, up=True)
        await settle(pilot)
        check("t11-thirty-notches-were-thirty-scroll-events", watches.count, 30)
        check("t11-every-scroll-re-armed-the-one-timer", arms.count, watches.count)
        check("t11-thirty-notches-settled-once", settles.count, 1)
        check("t11-the-burst-settled-a-twentieth-of-its-notches",
              settles.count * 20 <= watches.count, True)
        await settle(pilot)
        check("t11-a-quiet-view-does-not-settle-again", settles.count, 1)
        check("t11-no-timer-left-armed-when-quiet", view._settle_timer, None)
        watches.remove()
        settles.remove()
        arms.remove()

        # ...and a second SCROLL gets its own settle: the one above is a debounce,
        # not a one-shot that stopped working.
        settles2 = CallCount(view, "_scroll_settled").install()
        await wheel_scroll(app, pilot, view, 4, up=False)
        await settle(pilot)
        check("t11-a-second-scroll-settles-too", settles2.count > 0, True)
        settles2.remove()

        settles3 = CallCount(view, "_scroll_settled").install()
        prunes3 = CallCount(view, "prune").install()
        freeze_triggers(view)
        await wheel_scroll(app, pilot, view, 40, up=True)
        await settle(pilot)
        check("t11-control-frozen-never-settles", settles3.count, 0)
        check("t11-control-frozen-never-prunes", prunes3.count, 0)
        settles3.remove()
        prunes3.remove()


async def t12_prune_after_every_load():
    """The half the debounce cannot do: the prune BEHIND EVERY LOAD.

    Both arms walk to the same sliding state, then run the same 200-notch burst with
    the settle taken away (`freeze_settle`), so no scroll can prune at all and the
    ONLY prune left in the system is the one each page operation runs. Arm one is
    the shipped code: the count stays bounded and flat. The control changes exactly
    one thing - `prune()` does nothing - and the same triggers, paging exactly as
    before, let the count climb past what `load()` would ever mount.

    Why the settle has to be removed rather than dodged: the burst is frame-based
    and the settle is a wall-clock 0.15 s timer, and a notch plus a pause costs
    66-71 ms on this box. A 200-notch burst is therefore ~14 s of wall clock and the
    timer expires inside it - measured 17 settles during one such burst, and 3
    during a 30-notch burst taken where every notch mounts. "A scroll that never
    stops" is not a thing the harness can produce by not waiting, so the burst is
    made unbroken by construction and the claim stops depending on the machine.
    """
    async def burst(app, pilot, view, notches=200):
        """The mounted count every 20 notches, with no settle asked for in between."""
        series = []
        for notch in range(notches):
            app.screen._forward_event(wheel_event(view, up=True))
            await pilot.pause()
            if notch % 20 == 19:
                series.append(len(view.children))
        return series

    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        await walk_into_the_sliding_region(app, pilot, view)
        settles = CallCount(view, "_scroll_settled").install()
        lo0 = view.window_start
        freeze_settle(view)
        series = await burst(app, pilot, view)
        settles_during_the_burst = settles.count
        settles.remove()
        # The premise of the whole check, asserted rather than assumed: no settle
        # ran, so nothing below is credited to a settled scroll.
        check("t12-the-burst-really-never-settled", settles_during_the_burst, 0)
        check("t12-the-burst-paged-history-in", view.window_start < lo0, True)
        check("t12-sliding-count-stays-bounded", max(series) <= 20, True)
        check("t12-sliding-count-flat", max(series) - min(series) <= FLAT_SPAN, True)
        check("t12-never-mounted-more-than-load-does",
              max(series) <= view.INITIAL_WINDOW, True)
        check("t12-consistent", view.window_consistent(), True)

    app2 = WindowApp(big_fixture(BIG_N))
    async with app2.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view2 = await open_view(app2)
        await settle(pilot)
        await walk_into_the_sliding_region(app2, pilot, view2)

        async def no_prune():
            return None

        lo0 = view2.window_start
        view2.prune = no_prune
        freeze_settle(view2)
        series2 = await burst(app2, pilot, view2)
        check("t12-control-the-burst-still-paged-in", view2.window_start < lo0, True)
        check("t12-control-count-grows-past-the-initial-window",
              max(series2) > view2.INITIAL_WINDOW, True)
        check("t12-control-count-grows-with-the-burst",
              series2[-1] > series2[0] + FLAT_SPAN, True)


async def t13_down_walk_reloads_to_the_tail():
    """The way back down, driven until it ARRIVES.

    The burst count is a ceiling, not the experiment: how many 20-notch bursts the
    return costs depends on how deep the up-walk got and on how many settles land
    inside the bursts (a settle is wall-clock, a notch is a frame - see the harness's
    `freeze_settle`), and a fixed count of 12 turns "does the reader get home" into a
    race with the machine. Measured on this box, the walk down from the state a
    160-notch up-walk leaves - window (955, 966), 11 mounted - reaches the tail at
    burst 7 or 8 and then sits at 8 mounted; the same walk under load does not reach
    it inside 12 at all, which is how this check once killed the whole suite file on
    a `max()` of an empty list. What is claimed is: flat while both sides have
    history, one constant at the tail ONCE the page that arrived there has been
    pruned (the arrival sample is spent, as t19 spends the settle that hands a parked
    view its last page), and the reader ends AT the tail.
    """
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        await wheel_scroll(app, pilot, view, 160, up=True)
        check("t13-up-walk-came-to-rest", await rest(pilot, view), True)
        lo_after_up = view.window_start
        check("t13-setup-bottom-was-evicted", view.window_hi < BIG_N, True)
        mid, at_tail, never_rest = [], [], 0
        for burst in range(30):
            await wheel_scroll(app, pilot, view, 20, up=False)
            if not await rest(pilot, view):
                never_rest += 1
            (at_tail if view.window_hi == BIG_N else mid).append(len(view.children))
            if len(at_tail) >= 5:
                break
        # Every invariant in this file is taken at rest, because `window_consistent()`
        # is documented as an invariant of QUIESCENCE: both window moves update
        # `window_start` after their batch, so a sample inside one reads False with
        # nothing wrong. Measured: 231 such samples over four racing walks, zero once
        # the sample waits for rest.
        check("t13-every-burst-came-to-rest", never_rest, 0)
        check("t13-came-back-down", view.window_start > lo_after_up, True)
        check("t13-reached-the-tail", view.window_hi, BIG_N)
        check("t13-tail-widget-mounted", view.widget(BIG_N - 1) is not None, True)
        check("t13-reader-is-at-the-tail", round(view.scroll_y),
              round(view.max_scroll_y))
        check("t13-flat-while-both-sides-had-history",
              len(mid) >= 3 and max(mid) - min(mid) <= FLAT_SPAN, True)
        # At the tail there is nothing below to keep, so the settled window is a
        # DIFFERENT constant - asserted as its own, never averaged with the walk.
        # The FIRST tail sample is spent and not counted, exactly as t19 spends the
        # settle that hands a parked view its last page: a burst arrives at the tail
        # WITH that page mounted, and it is the next event that prunes the tail down
        # to its constant. Measured over three whole walks: the arrival sample reads
        # 12 mounted and the three following samples 8; five more settles leave the
        # settled tail exactly as it is, (992, 1000) with 8 mounted
        # (/tmp/wp-d3-probe-t13tail.py). Counting the arrival sample in the constant
        # asks a burst to have pruned a page its own settle never saw, and read red
        # once in a handful of runs on that - a race with the machine, not a state.
        check("t13-at-the-tail-five-samples", len(at_tail) >= 5, True)
        check("t13-at-the-tail-one-constant",
              len(set(at_tail[1:5])) if len(at_tail) >= 5 else 0, 1)
        check("t13-at-the-tail-still-bounded",
              max(at_tail) <= view.INITIAL_WINDOW if at_tail else False, True)
        check("t13-consistent", view.window_consistent(), True)


async def t14_follow_bottom_release():
    """The three cases of the one deliberate touch on follow-bottom.

    The state is asked for directly: `anchor()` is Textual's own arming primitive
    and it lands the view at the window bottom - which is precisely the state
    `_check_anchor` re-arms into (widget.py:823): the anchor armed, `max_scroll_y`
    reached, and `max_scroll_y` being the WINDOW's bottom, not the chat's. The
    triggers are frozen for the whole check because what is under test is
    `load_newer`; a trigger paging on its own account would only make the numbers
    mean less.
    """
    for label, count, want in (("short-page", 10, "hold"),
                               ("tail-page", 60, "pull")):
        app = WindowApp(big_fixture(400))
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            view = await open_view(app)
            await settle(pilot)
            freeze_triggers(view)
            view.scroll_to(0, 0, animate=False)      # release, then prune the tail
            await settle(pilot)
            await view.prune()
            await settle(pilot)
            view.anchor()                            # armed, AT the window bottom
            await settle(pilot)
            releases = CallCount(view, "release_anchor").install()
            armed = view._anchored and not view._anchor_released
            history_below = len(view.messages) - view.window_hi
            before = round(view.scroll_y)
            await view.load_newer(count)
            await settle(pilot)
            after = round(view.scroll_y)
            check(f"t14-{label}-setup-anchor-armed", armed, True)
            if want == "hold":
                # the page stops short of the tail: history is still unmounted below
                check(f"t14-{label}-setup-page-short-of-the-tail",
                      view.window_hi + count <= len(view.messages), True)
                check(f"t14-{label}-view-held", after, before)
                check(f"t14-{label}-anchor-released", view._anchor_released, True)
                check(f"t14-{label}-exactly-one-release", releases.count, 1)
            else:
                check(f"t14-{label}-reached-the-tail", view.window_hi,
                      len(view.messages))
                check(f"t14-{label}-pulled-to-the-tail", after,
                      round(view.max_scroll_y))
                check(f"t14-{label}-follow-bottom-kept", view._anchor_released, False)
                check(f"t14-{label}-no-release-call", releases.count, 0)
            check(f"t14-{label}-consistent", view.window_consistent(), True)
            check(f"t14-{label}-setup-had-history-below", history_below > 10, True)
            releases.remove()

    # The third case: an anchor already released is never released a second time.
    app3 = WindowApp(big_fixture(400))
    async with app3.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view3 = await open_view(app3)
        await settle(pilot)
        freeze_triggers(view3)
        view3.scroll_to(0, 0, animate=False)         # the user path releases it
        await settle(pilot)
        check("t14-already-released-setup", view3._anchor_released, True)
        releases3 = CallCount(view3, "release_anchor").install()
        await view3.load_newer(5)
        await settle(pilot)
        check("t14-already-released-no-extra-release", releases3.count, 0)
        releases3.remove()


async def t15_parked_at_the_window_bottom_not_starved():
    """The reader at the window bottom, history unmounted below.

    Two measured facts built into this check: a wheel notch AT a scroll limit does
    not move scroll_y and so fires no watcher at all, which is why the settle is the
    only thing that can reach this state; and being at the window bottom says
    nothing about the tail, because `max_scroll_y` is the window's.
    """
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        window0 = await build_an_edge(view, pilot, up=False)
        hi0, top0 = view.window_hi, await top_index(view)
        check("t15-setup-history-below-unmounted", window0[1] < BIG_N, True)
        check("t15-setup-at-the-window-bottom", round(view.scroll_y),
              round(view.max_scroll_y))
        await view._scroll_settled()                 # ONE settle
        await settle(pilot)
        check("t15-settle-paged-history-back-in", view.window_hi > hi0, True)
        check("t15-the-reader-did-not-move", await top_index(view), top0)
        check("t15-consistent", view.window_consistent(), True)

    # The control IS the defect: prune alone - a settle that does not re-check the
    # edge, which is the shape this design had before the starvation was measured -
    # leaves the reader exactly where they were with the history still unmounted.
    app2 = WindowApp(big_fixture(BIG_N))
    async with app2.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view2 = await open_view(app2)
        await settle(pilot)
        await build_an_edge(view2, pilot, up=False)
        hi_c, top_c = view2.window_hi, await top_index(view2)
        await view2.prune()                          # prune, no edge re-check
        await settle(pilot)
        check("t15-control-prune-alone-leaves-it-starved", view2.window_hi, hi_c)
        check("t15-control-history-still-unmounted",
              len(view2.messages) - view2.window_hi > 0, True)
        check("t15-control-reader-untouched", await top_index(view2), top_c)


async def t16_true_ends_stop_cleanly():
    app = WindowApp(big_fixture(120))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        await view.materialize(0)                    # the whole history mounted
        await settle(pilot)
        freeze_triggers(view)                        # a true end, not a moving one
        view.scroll_to(0, 0, animate=False)          # ...and the reader at message 0
        await settle(pilot)
        thaw_triggers(view)
        older = CallCount(view, "load_older").install()
        newer = CallCount(view, "load_newer").install()
        await wheel_scroll(app, pilot, view, 40, up=True)
        await view._scroll_settled()
        await settle(pilot)
        check("t16-at-message-0-no-older-page", older.count, 0)
        check("t16-at-message-0-lo-still-0", view.window_start, 0)
        check("t16-at-message-0-consistent", view.window_consistent(), True)

        # Down to the tail the way a reader with the End key does it: to the bottom
        # of the window, again and again, the window sliding under each press.
        for _ in range(40):
            freeze_triggers(view)
            view.scroll_end(animate=False)
            await settle(pilot)
            thaw_triggers(view)
            await view._scroll_settled()
            await settle(pilot)
            if view.window_hi == len(view.messages):
                break
        check("t16-setup-reached-the-tail", view.window_hi, len(view.messages))
        newer.calls.clear()
        older.calls.clear()
        for _ in range(5):
            await wheel_scroll(app, pilot, view, 10, up=False)
            await view._scroll_settled()
            await settle(pilot)
        check("t16-at-the-tail-no-newer-page", newer.count, 0)
        check("t16-at-the-tail-window-intact", view.window_hi, len(view.messages))

        # The control that makes both zeros an END and not a miss: the SAME call on
        # the SAME widget at the OTHER edge, where history exists, is a page.
        await build_an_edge(view, pilot, up=True)
        await view._load_at_edge()
        await settle(pilot)
        check("t16-control-at-the-other-edge-it-is-a-page", older.count, 1)
        check("t16-control-consistent", view.window_consistent(), True)
        older.remove()
        newer.remove()


async def t17_the_freezes():
    # is_edit: the SAME direct call, before the freeze and after it, with nothing
    # else changed - the zero is the freeze and not an edge with nothing to do.
    app = WindowApp(big_fixture(400))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        await build_an_edge(view, pilot, up=True)
        older = CallCount(view, "load_older").install()
        prunes = CallCount(view, "prune").install()
        check("t17-edit-setup-the-edge-is-live", view._page_edge(), "older")
        view.action_edit_on()
        await settle(pilot)
        window_edit = view.window
        await view._load_at_edge()
        await view._scroll_settled()
        await settle(pilot)
        check("t17-is_edit-drops-the-page-op", older.count, 0)
        check("t17-is_edit-drops-the-prune", prunes.count, 0)
        check("t17-is_edit-window-untouched", view.window, window_edit)
        older.calls.clear()
        prunes.calls.clear()
        await view.action_edit_off()
        await settle(pilot)
        await view._load_at_edge()
        await settle(pilot)
        check("t17-edit-off-the-same-call-pages-in", older.count, 1)
        check("t17-edit-off-consistent", view.window_consistent(), True)
        older.remove()
        prunes.remove()

    # A working chat: the triggers are silent AND the tail is still stuck to the
    # bottom - the two halves of the streaming requirement, on a view nobody
    # scrolled. Then the same call once the chat is idle, which is a page.
    app2 = WindowApp(big_fixture(120))
    async with app2.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        chat = app2.chat
        view2 = await open_view(app2)
        await settle(pilot)
        work = FakeWork()
        work.is_running = True
        chat.work = work
        chat._work = work
        prunes2 = CallCount(view2, "prune").install()
        older2 = CallCount(view2, "load_older").install()
        chat.messages.append({"role": "assistant", "reasoning": "",
                              "content": [{"type": "text", "text": "mm-stream-1"}]})
        view2.callback(len(chat.messages) - 1, 1)
        await settle(pilot)
        check("t17-stream-start-tail-at-the-bottom", round(view2.scroll_y),
              round(view2.max_scroll_y))
        chat.messages[-1]["content"][0]["text"] += " streamed words " * 40
        view2.callback(len(chat.messages) - 1, 2)
        await settle(pilot)
        view2.callback(len(chat.messages) - 1, 0)
        await settle(pilot)
        check("t17-stream-end-tail-still-at-the-bottom", round(view2.scroll_y),
              round(view2.max_scroll_y))
        # with the chat working, an edge is built and the same call does nothing...
        await build_an_edge(view2, pilot, up=True)
        window_working = view2.window
        older2.calls.clear()
        prunes2.calls.clear()
        await view2._load_at_edge()
        await view2._scroll_settled()
        await settle(pilot)
        check("t17-streaming-no-page-in", older2.count, 0)
        check("t17-streaming-no-prune", prunes2.count, 0)
        check("t17-streaming-window-untouched", view2.window, window_working)
        check("t17-streaming-consistent", view2.window_consistent(), True)
        work.is_running = False
        # ...and once it is idle, the same call from the same edge is a page: the
        # freeze was the working chat, not a widget that stopped working.
        await build_an_edge(view2, pilot, up=True)
        await view2._load_at_edge()
        await settle(pilot)
        check("t17-idle-again-the-same-call-pages", older2.count, 1)
        check("t17-idle-again-consistent", view2.window_consistent(), True)
        prunes2.remove()
        older2.remove()

    # A page operation in flight drops the trigger outright.
    app3 = WindowApp(big_fixture(400))
    async with app3.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view3 = await open_view(app3)
        await settle(pilot)
        await build_an_edge(view3, pilot, up=True)
        check("t17-guard-setup-the-edge-is-live", view3._page_edge(), "older")
        older3 = CallCount(view3, "load_older").install()
        newer3 = CallCount(view3, "load_newer").install()
        window_before = view3.window
        view3._window_page_op = True                 # a page op is in flight
        await view3._load_at_edge()
        await view3._scroll_settled()
        await settle(pilot)
        check("t17-page-op-in-flight-drops-the-trigger",
              older3.count + newer3.count, 0)
        check("t17-page-op-in-flight-window-untouched", view3.window, window_before)
        older3.remove()
        newer3.remove()


async def t18_the_guard_is_saved_not_cleared():
    """WP-D's guard extension: materialize() holds the page-op guard across its own
    mount batch, and a caller that already holds it must not have it dropped
    underneath it."""
    app = WindowApp(big_fixture(400))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        check("t18-load-returns-the-guard-free", view._window_page_op, False)
        seen = []
        real_grow_up = type(view)._grow_up

        async def spy_grow_up(self, count, render=True):
            seen.append(self._window_page_op)
            return await real_grow_up(self, count, render)

        view._grow_up = spy_grow_up.__get__(view)
        await view.materialize(view.window_start - 5)
        await settle(pilot)
        check("t18-materialize-holds-the-guard-during-the-batch", seen, [True])
        check("t18-materialize-gives-it-back", view._window_page_op, False)
        # A trigger that arrives while the guard is held is dropped: the guard is
        # exactly what the trigger asks, so hold it and ask.
        older = CallCount(view, "load_older").install()
        view._window_page_op = True
        await view._load_at_edge()
        view._window_page_op = False
        check("t18-trigger-dropped-while-the-guard-is-held", older.count, 0)
        older.remove()
        # And RESTORE, never clear. With the guard held by someone else, materialize
        # must still do its own work AND leave the flag held - if it cleared it, the
        # trigger it was holding off would get through while its caller still
        # believes it owns the window.
        view._window_page_op = True
        lo_before = view.window_start
        await view.materialize(lo_before - 5)
        await settle(pilot)
        check("t18-materialize-worked-while-the-guard-was-held",
              view.window_start, lo_before - 5)
        check("t18-materialize-restores-a-guard-it-found-held",
              view._window_page_op, True)
        view._window_page_op = False
        check("t18-consistent", view.window_consistent(), True)


async def t19_parked_is_a_fixed_point():
    """The anti-oscillation invariant, at the edges where a chase would live.

    `TRIGGER_MARGIN_FACTOR` is strictly below `PRUNE_MARGIN_FACTOR`, so a settled
    prune always leaves more history mounted on a side than a trigger asks for: a
    page-in and a prune cannot chase each other across frames. The consequence a
    user would feel is the check: a view parked at a window edge does not move,
    settle after settle, and its correction counter stops growing. The first settle
    is spent and not counted - a reader AT an edge is exactly where the design
    brings a page in, and that page is the last one.
    """
    parked = (("window-top", True), ("window-bottom", False))
    for label, up in parked:
        app = WindowApp(big_fixture(BIG_N))
        async with app.run_test(size=(80, 24)) as pilot:
            await settle(pilot)
            view = await open_view(app)
            await settle(pilot)
            check(f"t19-{label}-trigger-asks-less-than-prune-keeps",
                  view.TRIGGER_MARGIN_FACTOR < view.PRUNE_MARGIN_FACTOR, True)
            window_at_edge = await build_an_edge(view, pilot, up=up)
            await view._scroll_settled()             # the page the edge asks for
            await settle(pilot)
            check(f"t19-{label}-first-settle-is-not-a-no-op",
                  view.window != window_at_edge, True)
            arrived = (view.window, len(view.children), round(view.scroll_y),
                       view.corrections)
            for round_number in range(4):
                await view._scroll_settled()
                await settle(pilot)
                check(f"t19-{label}-settle-{round_number}-fixed-point",
                      (view.window, len(view.children), round(view.scroll_y),
                       view.corrections), arrived)
            check(f"t19-{label}-consistent", view.window_consistent(), True)

    # The true top: nothing above to page, everything below to prune - the other
    # place a chase could hide.
    app3 = WindowApp(big_fixture(120))
    async with app3.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view3 = await open_view(app3)
        await settle(pilot)
        await view3.materialize(0)
        await settle(pilot)
        freeze_triggers(view3)
        view3.scroll_to(0, 0, animate=False)
        await settle(pilot)
        thaw_triggers(view3)
        await view3._scroll_settled()
        await settle(pilot)
        arrived = (view3.window, len(view3.children), round(view3.scroll_y),
                   view3.corrections)
        for round_number in range(4):
            await view3._scroll_settled()
            await settle(pilot)
            check(f"t19-true-top-settle-{round_number}-fixed-point",
                  (view3.window, len(view3.children), round(view3.scroll_y),
                   view3.corrections), arrived)
        check("t19-true-top-lo-still-0", view3.window_start, 0)
        check("t19-true-top-consistent", view3.window_consistent(), True)


async def t20_prune_holds_the_guard_too():
    """WP-D's second guard hole, found by t13 and fixed in `prune()` itself.

    WP-C could let `prune()` merely ASK about `_window_page_op`: nothing else was
    ever moving the window at the same moment. WP-D is the first code that runs the
    two concurrently - the settled scroll is a `set_timer` callback and the page
    operation is a `call_after_refresh` callback, i.e. two asyncio tasks, and
    prune's removal batch is nothing but await points. The damage is not cosmetic:
    `_grow_up` ASSIGNS lo absolutely (`window_start = lo - count`, from the value it
    read) while prune ADDS to it (`window_start += len(evict_above)`), so a
    page-above landing between the last `child.remove()` and that addition leaves the
    eviction count added to the wrong base. The mounted range then keeps a HOLE in
    the middle of the history, and every accessor reads it wrong from then on.
    Forced at that point against the pre-fix tree, 2 of 3 runs ended inconsistent
    (/tmp/wp-d3-probe-interleave4.py, /tmp/wp-d3-probe-fix.py).

    The interleave is asked for from INSIDE prune's body, which is the hazard point,
    and the page operation is the real `load_older` answering to the real guard -
    nothing of the shipped code is patched, only observed (t18's spy shape). The
    state it observes is the reader parked in the MIDDLE of the mounted range, which
    is the only state where prune has an above-side walk at all (its two setup checks
    say so) and therefore the only one where the lo base this bug corrupts is ever
    written.
    """
    app = WindowApp(big_fixture(BIG_N))
    async with app.run_test(size=(80, 24)) as pilot:
        await settle(pilot)
        view = await open_view(app)
        await settle(pilot)
        freeze_triggers(view)                    # the scroll below is setup, not input
        # Park the reader IN THE MIDDLE of what load() mounted: 23 widgets above the
        # viewport and 24 below, so prune has a walk on BOTH sides. This state is
        # asked for rather than assumed, and the reason is a bug this check had:
        # `scroll_to(0, 0)` puts the reader at the window TOP, where the above-side
        # walk is empty by construction (measured, both states settled before the
        # walk: at scroll_y=0 above=0/evict_above=0, below=48/evict_below=43, so lo
        # cannot move and 50 children drop to 7; parked mid-mount at max/2,
        # above=23/evict_above=18 and below=24/evict_below=19, lo 950 -> 968 and 50
        # drop to 13, consistent). A `window_start > lo_before` check taken in the
        # first state is not evidence about prune's work at all - lo has no way to
        # move - and the hazard point would have had no above-side removals to
        # interleave with. Same lesson as `build_an_edge`: build the state, then
        # assert it.
        view.scroll_to(0, view.max_scroll_y // 2, animate=False)
        await rest(pilot, view)
        above_viewport = [c for c in view.children
                          if c.region.bottom <= view.content_region.y]
        below_viewport = [c for c in view.children
                          if c.region.y >= view.content_region.bottom]
        check("t20-setup-has-mounted-history-above-the-viewport",
              len(above_viewport) > 0, True)
        check("t20-setup-has-mounted-history-below-the-viewport",
              len(below_viewport) > 0, True)
        thaw_triggers(view)
        lo_before = view.window_start

        paged = []
        real_grow_up = type(view)._grow_up

        async def spy_grow_up(self, count, render=True):
            paged.append(count)
            return await real_grow_up(self, count, render)

        view._grow_up = spy_grow_up.__get__(view)
        hazard = []
        real_release = type(view)._release_outside_the_margin

        async def spy_release(self):
            # About to remove children with lo still unmoved: ask for the page a
            # wheel-up's callback could ask for at this exact moment.
            await view.load_older(20)
            hazard.append((self._window_page_op, view.window_start, list(paged)))
            return await real_release(self)

        view._release_outside_the_margin = spy_release.__get__(view)
        await view.prune()
        check("t20-the-hazard-point-was-reached", len(hazard), 1)
        check("t20-guard-held-during-the-removal-batch", hazard[0][0], True)
        check("t20-page-above-asked-for-inside-it-was-dropped", hazard[0][2], [])
        check("t20-and-it-mounted-nothing", view.window_start < lo_before, False)
        check("t20-prune-still-did-its-work", view.window_start > lo_before, True)
        check("t20-prune-gives-the-guard-back", view._window_page_op, False)
        view._release_outside_the_margin = real_release

        # The control: the same call, from the same widget, is a page - the drop
        # above was the guard and not a window with nothing above it.
        await view.load_older(20)
        check("t20-control-the-same-call-outside-a-prune-pages", len(paged), 1)
        check("t20-consistent", view.window_consistent(), True)


async def main():
    print("=== the scroll triggers: page in, prune back, stop at the ends ===")
    await t10_up_walk_pages_and_prunes()
    await t11_debounce_one_settle_per_scroll()
    await t12_prune_after_every_load()
    await t13_down_walk_reloads_to_the_tail()
    await t14_follow_bottom_release()
    await t15_parked_at_the_window_bottom_not_starved()
    await t16_true_ends_stop_cleanly()
    await t17_the_freezes()
    await t18_the_guard_is_saved_not_cleared()
    await t19_parked_is_a_fixed_point()
    await t20_prune_holds_the_guard_too()
    summary()


if __name__ == "__main__":
    asyncio.run(main())
