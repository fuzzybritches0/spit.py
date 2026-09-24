#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t11 - the counts row on the chat-settings row (step 4), through the seams the
row is actually driven from. This is why the suite's gate takes **textual** as
well as httpx: `chat_settings` imports it, and the row only exists inside a
mounted widget tree.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t11.

ASSERT THE STRUCTURE, NOT THE SPELLING. The owner has an OPEN call on how this
row renders at 80 columns (the LIMIT filed in the step-4 block: at 80 columns
three compact Selects collapse to 3/3/4 with a zeroed chat and 1/1/1 with a
running chat's figures, and the relief is a rendering choice - k-abbreviation,
CSS leftover width + ellipsis, or a row of its own). So nothing here compares
the whole row string: what is pinned is that a None renders as a dash and the
string contains no "0 / 0", that a real zero renders as 0, the cache/probe
arithmetic, the child order, and the signal-0 ordering. A re-rendering must
still pass every check in this file; if one of them can't, it is pinning a
decision that is not ours and belongs out of the suite.

  StubEndpointApp (counts_harness.py) is NOT optional: unit:chat_smoke's stub
  answers endpoint_list() with {}, which is the GUARD path of refresh_usage()
  and can never start a probe - a suite built on it could not see a single
  probe behaviour.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (DEAD_ADDRESS, baseline_selfcheck, check,  # noqa: E402
                              guarded, summary)
import endpoint_harness as harness  # noqa: E402

from counts_harness import (FakeEndpoint, Reply, StubEndpointApp,  # noqa: E402
                            app_endpoint, fixture_chat, row_text, settle)

from spit_app.chat import chat_settings as cs_mod  # noqa: E402
from spit_app.chat import callback as callback_mod  # noqa: E402

PROBED = []                     # the model each probe was started with
REAL_GET_CONTEXT_SIZE = cs_mod.get_context_size


def install_counter(answers=None, slow=None):
    """Replace chat_settings.get_context_size with a probe that RECORDS the pair
    it was asked for. `answers` maps an endpoint url to the size to hand back
    (None = the server would not say); `slow` is the url that takes 0.5 s."""
    async def counting(endpoint, model=None):
        url = endpoint.get("endpoint_url", {}).get("value", "")
        if slow and url == slow:
            import asyncio
            await asyncio.sleep(0.5)
        PROBED.append(model)
        return (answers or {}).get(url, 8192)
    cs_mod.get_context_size = counting


async def t11_row_and_probes():
    if not baseline_selfcheck("t11"):
        return
    PROBED.clear()
    install_counter()
    app = StubEndpointApp(fixture_chat(), {"1": app_endpoint(DEAD_ADDRESS)})
    try:
        await _row_and_probe_checks(app)
    finally:
        cs_mod.get_context_size = REAL_GET_CONTEXT_SIZE


async def _row_and_probe_checks(app):
    async with app.run_test() as pilot:
        await settle(pilot)
        chat = app.chat
        settings = chat.chat_settings
        row = row_text(chat)

        # the row is THERE at mount - no reply was ever sent - and mounting it
        # did not shift the three Selects (children[1/3/5] is positional in this
        # file's own code; mount the Label earlier and chat_smoke dies inside its
        # own harness with `'Label' object has no attribute 'set_options'`).
        check("t11-the-row-exists-at-mount-with-no-reply-ever-sent",
              settings.usage_label is not None, True)
        check("t11-the-three-Selects-are-still-children-1-3-5",
              [settings.children[i].id for i in (1, 3, 5)],
              ["select-endpoint", "select-model", "select-model-settings"])
        check("t11-the-counts-Label-is-the-LAST-child",
              settings.children[-1] is settings.usage_label, True)
        check("t11-the-row-carries-something", len(row) > 0, True)

        # ONE probe per (endpoint, model) pair, however many refreshes fire.
        check("t11-mount-cost-exactly-one-probe", len(PROBED), 1)
        for _ in range(4):
            settings.refresh_usage()
            await settle(pilot, 3)
        check("t11-four-more-refreshes-cost-zero-probes", len(PROBED), 1)
        check("t11-none-is-CACHED-so-it-is-asked-once-not-every-reply", len(PROBED), 1)

        # a different model is a DIFFERENT pair -> exactly one new probe, and it
        # carried that model.
        model_select = settings.children[3]
        model_select.set_options((("mm-one-model", "mm-one-model"),))
        model_select.value = "mm-one-model"
        await settle(pilot)
        check("t11-a-different-model-is-a-different-pair", len(PROBED), 2)
        check("t11-each-probe-carried-its-own-model", PROBED, [None, "mm-one-model"])

        # a None renders as a dash, never as a number, and NEVER as "0 / 0" - and
        # an ASKED-AND-REFUSED pair is cached exactly like an answered one. The
        # refusing counter goes in BEFORE the app mounts: the cache is filled at
        # mount, so patching it after the mount would leave the mount's own
        # answer (8192, the default) on the row and measure nothing. PROBED is
        # cleared first so the arithmetic below is this pair's, not the whole
        # file's.
        PROBED.clear()
        install_counter(answers={DEAD_ADDRESS: None})
        dead = StubEndpointApp(fixture_chat(),
                               {"1": app_endpoint(DEAD_ADDRESS, context_size=0)})
        async with dead.run_test() as pilot:
            await settle(pilot)
            dead_row = row_text(dead.chat)
            check("t11-a-None-window-renders-as-a-dash", cs_mod.DASH in dead_row, True)
            check("t11-a-None-window-never-says-0-slash-0", "0 / 0" in dead_row, False)
            check("t11-an-asked-and-refused-pair-costs-exactly-one-probe",
                  len(PROBED), 1)
            for _ in range(3):
                dead.chat.chat_settings.refresh_usage()
                await settle(pilot, 3)
            check("t11-an-asked-and-refused-pair-is-cached-too", len(PROBED), 1)

        # a real 0 renders as 0 (and a real 0 is NOT the dash).
        check("t11-a-real-zero-renders-as-0", cs_mod.count_or_dash(0), "0")
        check("t11-a-None-renders-as-the-dash", cs_mod.count_or_dash(None), cs_mod.DASH)
        check("t11-a-real-number-renders-as-itself", cs_mod.count_or_dash(4311), "4311")

        # the endpoint's own override renders (step 3's field, honoured by step 1).
        # This one needs the REAL get_context_size: the override is a link IN that
        # chain (after /props and /slots), so a stub that replaces the whole chain
        # cannot show it. The addresses are the refused ones, so the two GETs fail
        # instantly on loopback and the number on the row can only be the override.
        cs_mod.get_context_size = REAL_GET_CONTEXT_SIZE
        override = StubEndpointApp(
            fixture_chat(),
            {"1": app_endpoint(DEAD_ADDRESS, context_size=131072),
             "2": app_endpoint("http://127.0.0.1:9/v2", context_size=65536)})
        async with override.run_test() as pilot:
            await settle(pilot)
            shown = row_text(override.chat)
            check("t11-the-endpoint-override-appears-on-the-row", "131072" in shown, True)
            endpoint_select = override.chat.chat_settings.children[1]
            endpoint_select.value = "2"
            await settle(pilot)
            shown = row_text(override.chat)
            check("t11-changing-endpoint-redraws-from-the-new-pair",
                  ("65536" in shown, "131072" in shown), (True, False))


async def t11_no_bleeding():
    """A probe started for pair A must never draw A's number while pair B is
    selected. TWO arrangements, because there are two ways to lose and only one
    instrument can see the second:

      (1) B's pair is NOT cached, so the switch starts B's probe and the
          exclusive group replaces A's probe in flight - A's answer never even
          arrives. (Measured: with `group="context-size", exclusive=True` the
          sleeping probe is cancelled, so this arrangement alone proves
          NOTHING about where a completed answer is filed.)
      (2) B's pair IS pre-cached, so the switch starts no worker and A's probe
          runs to completion AFTER the switch. This is the arrangement that
          separates "stored under the pair it was asked for" from "stored under
          whatever is selected now" - filing it under the current pair paints
          A's number on B's row, which is exactly what (1) cannot show. Verified
          by substitution: filing under `self.context_key()` leaves every check
          of (1) green and reddens these."""
    slow_url = "http://127.0.0.1:9/slow/v1"
    fast_url = "http://127.0.0.1:9/fast/v1"
    PROBED.clear()
    install_counter(answers={slow_url: 111111, fast_url: 222222}, slow=slow_url)
    app = StubEndpointApp(fixture_chat(),
                          {"1": app_endpoint(slow_url), "2": app_endpoint(fast_url)})
    try:
        async with app.run_test() as pilot:
            await settle(pilot)
            settings = app.chat.chat_settings
            check("t11-slow-pair-probe-is-in-flight", len(PROBED), 0)
            # switch WHILE A's probe is still running: the exclusive group
            # replaces the probe in flight, and nothing A said can paint.
            settings.children[1].value = "2"
            await settle(pilot)
            shown = row_text(app.chat)
            check("t11-a-probe-started-for-A-never-draws-As-number-under-B",
                  "111111" in shown, False)
            await settle(pilot, 20)          # past the 0.5 s the slow probe wants
            check("t11-and-it-still-does-not-arrive-late-under-B",
                  "111111" in row_text(app.chat), False)
            check("t11-switch-to-an-uncached-B-draws-B-own-number",
                  "222222" in row_text(app.chat), True)

            # ARRANGEMENT (2): B's pair pre-cached, so switching starts NOTHING
            # and A's slow probe is free to finish after the switch.
            PROBED.clear()
            late = StubEndpointApp(fixture_chat(),
                                   {"1": app_endpoint(slow_url),
                                    "2": app_endpoint(fast_url)})
            async with late.run_test() as pilot:
                await settle(pilot)                   # A's slow probe in flight
                lsettings = late.chat.chat_settings
                lsettings.context_sizes[("2", None)] = 444444   # B already known
                lsettings.children[1].value = "2"
                await settle(pilot)
                check("t11-a-cached-pair-is-drawn-from-the-cache",
                      "444444" in row_text(late.chat), True)
                await settle(pilot, 20)               # A's probe has now FINISHED
                # the ONE probe so far is the mount's A probe: the switch to the
                # cached pair started none (and `PROBED` records COMPLETED probes,
                # so this also says A's answer arrived and where it went).
                check("t11-a-switch-to-a-cached-pair-starts-no-probe", PROBED, [None])
                check("t11-a-late-answer-does-not-paint-the-selected-row",
                      "111111" in row_text(late.chat), False)
                check("t11-a-late-answer-is-filed-under-the-pair-it-asked-about",
                      lsettings.context_sizes.get(("1", None)), 111111)
                lsettings.children[1].value = "1"
                await settle(pilot)
                check("t11-switch-back-to-A-draws-As-own-number",
                      "111111" in row_text(late.chat), True)
                check("t11-and-switching-back-to-A-costs-no-second-probe",
                      PROBED, [None])
    finally:
        cs_mod.get_context_size = REAL_GET_CONTEXT_SIZE


async def t11_signal_seam():
    """Signal 0 through the REAL ChatView seam moves the row, and a reply's
    numbers are on the row that produced them (the harvest-before-signal
    ordering step 4 measured), with the stale-by-one arrangement as its control.
    """
    app = StubEndpointApp(fixture_chat(), {"1": app_endpoint(DEAD_ADDRESS)})
    wired = callback_mod.CallbackMixIn.on_stream_callback

    async def unwired(self, message):
        if message.signal == 0:
            await self.message_finish(message.index)
        elif message.signal == 1:
            await self.message_start(message.index)
        elif message.signal == 2:
            await self.message_process(message.index)

    try:
        async with app.run_test() as pilot:
            await settle(pilot)
            chat = app.chat
            index = len(chat.chat_view.messages) - 1

            # CONTROL FIRST: with the seam unwired the row must NOT move (this is
            # what makes the next check evidence - a handler on ChatSettings, the
            # sibling of the ChatView, would sit dead and this whole group would
            # still print greens).
            callback_mod.CallbackMixIn.on_stream_callback = unwired
            chat.token_usage = {"context": 9999, "generated": 8888, "cached": 7777}
            chat.chat_view.callback(index, 0)
            await settle(pilot)
            check("t11-CONTROL-unwired-seam-leaves-the-row-stale",
                  ("9999" in row_text(chat)), False)

            # the wired seam (chat/callback.py, the signal-0 branch).
            callback_mod.CallbackMixIn.on_stream_callback = wired
            chat.chat_view.callback(index, 0)
            await settle(pilot)
            check("t11-signal-0-through-the-real-seam-moves-the-row",
                  ("9999" in row_text(chat), "8888" in row_text(chat)), (True, True))

            # and a reply's own numbers are on the row: the real stream/harvest
            # ordering, not a hand-set dict.
            chat.token_usage = {"context": 0, "generated": 0, "cached": 0}
            endpoint = FakeEndpoint(chat)
            reply = Reply(chat, endpoint)
            endpoint.script = [{"prompt_tokens": 4100, "completion_tokens": 211,
                                "prompt_tokens_details": {"cached_tokens": 3050}}]
            await reply.one()
            await settle(pilot)
            check("t11-a-replies-numbers-are-on-the-row-that-produced-them",
                  ("4311" in row_text(chat), "211" in row_text(chat),
                   "3050" in row_text(chat)), (True, True, True))
            endpoint.script = [{"prompt_tokens": 4200, "completion_tokens": 150}]
            await reply.one()
            await settle(pilot)
            check("t11-second-reply-is-not-one-reply-stale",
                  ("4350" in row_text(chat), "361" in row_text(chat)), (True, True))
            check("t11-cached-did-not-keep-the-previous-replys-figure",
                  "3050" in row_text(chat), False)

            # THE STALE-BY-ONE CONTROL: same objects, harvest DEFERRED past the
            # signal -> the instrument can see staleness, so the green above is
            # about the ordering and not about a row that cannot move.
            deferred = StubEndpointApp(fixture_chat(), {"1": app_endpoint(DEAD_ADDRESS)})
            async with deferred.run_test() as pilot2:
                await settle(pilot2)
                dchat = deferred.chat
                dchat.token_usage = {"context": 111, "generated": 22, "cached": 3}
                dendpoint = FakeEndpoint(dchat)
                dendpoint.defer = True
                dendpoint.script = [{"prompt_tokens": 700, "completion_tokens": 100}]
                dreply = Reply(dchat, dendpoint)
                await dreply.one()
                await settle(pilot2)
                check("t11-CONTROL-a-harvest-deferred-past-the-signal-is-seeable",
                      ("111" in row_text(dchat), "800" in row_text(dchat)),
                      (True, False))
    finally:
        callback_mod.CallbackMixIn.on_stream_callback = wired


def main():
    print("INPUT MAPPING (TRAPS #13): the row is read as TEXT off "
          "chat.chat_settings.usage_label.content; get_context_size is replaced by a "
          "recording stub (restored in a finally) so the probe arithmetic is "
          "observable; the seam is the real ChatView -> chat/callback.py signal-0 "
          "branch. STRUCTURE is asserted, never the row's exact spelling - the "
          "80-column rendering is the owner's open call.")
    guarded("t11-mount", lambda: run(t11_row_and_probes))
    guarded("t11-bleed", lambda: run(t11_no_bleeding))
    guarded("t11-seam", lambda: run(t11_signal_seam))
    summary()
    return 1 if harness.fail_ else 0


def run(coroutine_fn):
    import asyncio
    asyncio.run(coroutine_fn())


if __name__ == "__main__":
    sys.exit(main())
