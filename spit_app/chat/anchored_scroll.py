# SPDX-License-Identifier: GPL-2.0
"""Top-anchored scroll container: the solved half of on-demand message loading.

A plain ``VerticalScroll`` keeps its ``scroll_y`` when children are mounted
above the viewport, so the visible content jumps down (reproduced as a check:
``spit_app/tests/unit/anchored/test_oneshot.py`` t1). This subclass holds its
VISUAL position across layout changes at either end - mounts, evictions, and
late growth of content above - with zero intermediate jump frames. Design,
mechanism and measurements: ``doc/TASKS-PLANNED.md`` P8,
``doc/UI-ONDEMAND-LOADING.md``.

The mechanism (textual 8.2.8, file:line from the venv) is Textual's own
bottom anchor, pointed at an arbitrary child:

- Layout runs *inside* compositing: ``Compositor._arrange_root`` calls
  ``widget.arrange()``, which calls the public hook ``process_layout
  (placements)`` (``_arrange.py:96``) BEFORE the compositor translates
  placements by ``-widget.scroll_offset`` (``_compositor.py:631``). A
  ``scroll_y`` written inside ``process_layout`` therefore lands in the same
  drawn frame - the correction is never one frame late.
- The write uses ``set_reactive`` exactly as the built-in bottom anchor does
  (``_compositor.py:609-619``). It deliberately does NOT go through
  ``scroll_to``/``scroll_relative``: every user-scroll path funnels through
  ``Widget._scroll_to``, which calls ``release_anchor()`` (``widget.py:2750``)
  - a correction must not release ChatView's follow-bottom anchor, and this
  one does not.
- Pure scrolling reuses the cached arrangement (``widget.py:1347``), so
  ``process_layout`` does NOT run when only the scroll position changes: the
  pin never fights the user, and user scrolls re-baseline it instead.

Two modes share one anchor slot - the first child at least partly visible at
the viewport top:

- ``arm_top_anchor()`` - one-shot: the NEXT layout pass compensates by the
  anchor's content-space delta (direction-agnostic: positive for mounts
  above, negative for evictions above - probe 7 measured both), then disarms.
- ``pin()`` / ``unpin()`` - persistent: every layout pass compensates, and
  every landed scroll re-baselines the anchor (``watch_scroll_y`` ->
  ``call_after_refresh``), so content that grows ABOVE the viewport later
  (an image or LaTeX landing after the mount) is compensated too while user
  scrolling simply wins.

If the anchor widget disappears while armed or pinned, the compensation is
SKIPPED, never applied against a phantom: the one-shot disarms, the pin
re-baselines onto the new first visible child after the frame.
"""
from textual.containers import VerticalScroll
from textual.widget import Widget


class AnchoredScroll(VerticalScroll):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._anchor_widget: Widget | None = None
        self._anchor_content_y: int = 0   # one-shot baseline: anchor's content-space y
        self._anchor_offset: int = 0      # pin baseline: anchor's rows below the viewport top
        self._anchor_active: bool = False
        self._pinned: bool = False
        # Test instrument: how many scroll_y corrections the widget has applied.
        self.corrections: int = 0

    # ------------------------------------------------------------------ modes

    def arm_top_anchor(self) -> None:
        """Remember the current visual position; the next layout pass restores it.

        A no-op while pinned: the persistent pin already compensates every
        pass, so arming on top of it would ask for the same correction twice.
        """
        if self._pinned:
            return
        anchor = self._first_visible_child()
        if anchor is None:
            return
        self._anchor_widget = anchor
        self._anchor_content_y = round(self.scroll_y + anchor.region.y - self.region.y)
        self._anchor_active = True

    def pin(self) -> None:
        """Hold the visual position across EVERY layout pass until unpinned."""
        self._anchor_active = False  # the pin subsumes a one-shot arm
        self._pinned = True
        self._rebaseline()

    def unpin(self) -> None:
        self._pinned = False
        self._anchor_widget = None

    @property
    def is_pinned(self) -> bool:
        return self._pinned

    # ------------------------------------------------------------- the anchor

    def _first_visible_child(self) -> Widget | None:
        return next((c for c in self.children if c.region.bottom > self.region.y), None)

    def _rebaseline(self) -> None:
        """Re-point the pin at what is actually on screen now."""
        anchor = self._first_visible_child()
        self._anchor_widget = anchor
        self._anchor_offset = round(anchor.region.y - self.region.y) if anchor else 0

    def _set_scroll_y_in_layout(self, value: float) -> None:
        # The bottom-anchor write of Compositor._arrange_root, mirrored: this
        # lands in the frame being composed, and it never releases the
        # built-in bottom anchor (no _scroll_to, no message posted).
        self.set_reactive(Widget.scroll_y, value)
        self.set_reactive(Widget.scroll_target_y, value)
        if self.show_vertical_scrollbar:
            self.vertical_scrollbar._reactive_position = value
        self.corrections += 1

    # ------------------------------------------------------------- the hook

    def process_layout(self, placements):
        if self._anchor_active:
            self._apply_one_shot(placements)
        elif self._pinned:
            self._apply_pin(placements)
        return placements

    def _apply_one_shot(self, placements) -> None:
        # The arm is consumed by exactly one layout pass whatever it finds -
        # an anchor removed in the meantime disarms without any compensation.
        anchor = self._anchor_widget
        content_y = self._anchor_content_y
        self._anchor_active = False
        self._anchor_widget = None
        self._anchor_content_y = 0
        if anchor is None:
            return
        for placement in placements:
            if placement.widget is anchor:
                delta = placement.region.y - content_y
                if delta:
                    self._set_scroll_y_in_layout(self.scroll_y + delta)
                break

    def _apply_pin(self, placements) -> None:
        anchor = self._anchor_widget
        if anchor is None:
            return
        scroll_y = round(self.scroll_y)
        for placement in placements:
            if placement.widget is anchor:
                desired = placement.region.y - self._anchor_offset
                if desired != scroll_y:
                    self._set_scroll_y_in_layout(desired)
                return
        # The pinned anchor is gone: skip the correction (no phantom), then
        # re-baseline onto the new first visible child. Children regions are
        # stale inside a layout pass and fresh after it, hence after_refresh.
        self.call_after_refresh(self._rebaseline)

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        # Every scroll - the user's OR our own correction - re-baselines the
        # pin once the frame has landed: the invariant is "what is on screen
        # now stays on screen", relative to where the scroll actually ended.
        if self._pinned and round(old_value) != round(new_value):
            self.call_after_refresh(self._rebaseline)
