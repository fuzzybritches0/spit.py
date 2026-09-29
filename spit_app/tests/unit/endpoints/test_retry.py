#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t14 - P19/WP-2: the typed failures, the ONE retry loop, the awaited rollback
and the prompt-cache slot - driven over the canned server, whose POST recording
is the ONLY evidence that counts.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t14.
t1/t5/t8/t9 are in test_payload.py, t2/t3/t4 in test_stream_parse.py, t6/t7 in
test_requests.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py, t12
in test_system_note.py, t13 in test_note_chain.py.

WHAT IS PROVEN HERE AND WHERE
  * the CLASSIFIER (no server, no Work): every failure the endpoint can produce
    leaves as a typed `EndpointFailure` carrying `status_code` and `retryable` -
    deterministic 400, context-length 400, 429, 503, an in-stream `error`
    payload, and a refused socket - and each is the class its status says, with
    the deterministic ones `retryable = False`;
  * THE WIDTH OF THE LOOP, which is the whole design: a 400 costs **one**
    request (TRAPS #13: the control that a retry is not unconditional), a 503
    costs `retry_attempts` requests, `retry_attempts = 1` costs one, and a plain
    successful reply costs exactly ONE request through the work loop too - the
    check that catches a loop which re-asks after the reply landed (it did, once,
    during this package: three identical replies and three requests);
  * a transient that clears is not a failure: 503-then-200 costs two requests,
    delivers the reply, and reports nothing;
  * the rollback is complete before the next attempt: after an exhausted
    transient the messages list is back to its pre-send length - no assistant
    corpse, no half-built `tool_calls` - and the accepted cost (DECISIONS 84) is
    one UNDO entry per attempt, which is what "the same rollback as the user's
    own remove, awaited" buys;
  * the slot goes back on EVERY way out (the leak WP-2 exists for): a failed
    reply with `save_cache_prompt` leaves the slot marked free;
  * `slot == -1` (no free slot) sends NO request at all, and says so;
  * an ABORT during a retry sleep costs no further request, deletes nothing,
    and ends within about a tenth of a second - the human's own turn is the tail
    by then, so the cancel-and-delete branch would delete the user's message.
  * `retry_attempts`/`retry_delay` never reach the wire: the skip list holds
    them, and an off-list control leaks in the very same payload (t5's shape).

THE FIXTURES ARE LOADED, NOT GUESSED (TRAPS #13): the canned scenarios
`refuse-400` / `refuse-context` / `refuse-429` / `refuse-503` / `flaky-503` /
`stream-error` / `content` (see endpoint_harness.post_reply), the tail of the
chat is a USER message (so the reply's corpse and the human's own turn are
different dicts and the abort checks mean something), and the window stays
unknown - /props and /slots 404 on these paths - so the token-status hook is
silent (DECISIONS 80 b / 81 d) and every asserted body is note-free.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (CannedServer, DEAD_ADDRESS, NEW,  # noqa: E402
                              check, guarded, run_stream, saved_endpoint,
                              summary)
import endpoint_harness as harness  # noqa: E402

from counts_harness import StubEndpointApp, settle  # noqa: E402
# counts_harness put unit:chat_smoke on sys.path, which is how t13 imports the
# same two names (the smoke fixture, not a copy of it).
from smoke_scenario import CHAT_ID, fixture_settings  # noqa: E402

MODEL = "none"                     # fixture_settings()["model"]["value"]


# ------------------------------------------------------------------ the fixtures
def retry_content() -> dict:
    """A chat whose tail is the human's own turn: the reply a failed request
    leaves behind is then a DIFFERENT dict from the message an abort must not
    touch, which is what the abort checks below assert."""
    return {"ctime": "2026-01-01T00:00:00", "settings": fixture_settings(),
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "mm-user-first"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "mm-answer-one"}]},
                {"role": "user", "content": [{"type": "text", "text": "mm-turn-to-go"}]},
            ]}


class RetryApp(StubEndpointApp):
    """The two attributes a real `Work` asks the app for and the smoke stub does
    not carry: `slots` (ManageCache's bookkeeping) and `path` - the same shape
    t13's ChainApp adds."""

    def __init__(self, content: dict, endpoints: dict) -> None:
        super().__init__(content, endpoints)
        self.slots = {}
        self.path = "/tmp/mm-retry-not-used"


def retry_endpoint(server, scenario: str, attempts=None, delay=None, **extra) -> dict:
    """A saved endpoint aimed at one canned scenario, with the two WP-2 fields
    settable; `attempts=None` leaves the field ABSENT (the pre-P19 file on disk -
    every endpoint saved before this package), which must answer the default."""
    fields = {}
    if attempts is not None:
        fields["retry_attempts"] = {"value": attempts, "stype": "uinteger"}
    if delay is not None:
        fields["retry_delay"] = {"value": delay, "stype": "ufloat"}
    fields.update(extra)
    return saved_endpoint(f"{server.base}/{scenario}/v1", **fields)


def make_app(server, scenario: str, attempts=None, delay=None, **extra) -> RetryApp:
    return RetryApp(retry_content(),
                    {"1": retry_endpoint(server, scenario, attempts, delay, **extra)})


def attempts_of(server) -> int:
    """How many TIMES the work loop asked - as opposed to how many POSTs the
    endpoint sent. `stream()` probes `stream_options` and, on any 4xx, sends the
    request a SECOND time without it (t6's rule, and `prepare_payload` puts the
    flag back on every attempt), so one 4xx attempt is TWO POSTs. The second one
    is the only request that carries no flag, so counting the flagless requests
    counts attempts, whatever the probe costs. On a 5xx the probe never runs and
    the two numbers are equal - which is what makes the 503 group above the
    clean statement of the rule and this helper the honest one for the 4xx."""
    return sum(1 for body in server.bodies if "stream_options" not in body)


def completions(server) -> list:
    """The recorded POSTs that are REQUESTS FOR A REPLY. `save_cache_prompt`
    makes ManageCache POST `/<scenario>/slots/<n>?action=restore|save` to the
    same canned server, and those are not what "how many times did it ask the
    endpoint" means - counting them would make every retry count a lie."""
    return [line for line in server.posts() if "/chat/completions" in line]


def slots_of(app, endpoint_id: str = "1", model: str = MODEL) -> list:
    return app.slots.get(endpoint_id, {}).get(model, [])


class app_ctx:
    """`async with app_ctx(server, ...) as (chat_app, pilot)`."""

    def __init__(self, server, scenario="content", attempts=None, delay=None,
                 content=None, **extra) -> None:
        self.server, self.scenario = server, scenario
        self.attempts, self.delay, self.extra = attempts, delay, extra
        self.content = content
        self.app = None
        self.ctx = None

    async def __aenter__(self):
        endpoint = retry_endpoint(self.server, self.scenario, self.attempts,
                                  self.delay, **self.extra)
        self.app = RetryApp(retry_content() if self.content is None else self.content,
                            {"1": endpoint})
        self.ctx = self.app.run_test()
        pilot = await self.ctx.__aenter__()
        await settle(pilot)
        return self.app, pilot

    async def __aexit__(self, *exc):
        result = await self.ctx.__aexit__(*exc)
        self.app = None
        return result


async def send(app, pilot) -> object:
    """One real send: the real `Work`, the real `work_stream()`, and the real
    `_work` reference `action_abort` reads (chat_text_area.py sets it the same
    way before it runs the worker)."""
    from spit_app.chat.work import Work
    work = Work(app.chat)
    app.chat._work = work
    await work.work_stream()
    await settle(pilot)
    return work


# ----------------------------------------------------------- the endpoint classes
def t14_classes(server):
    """Every failure the endpoint can produce leaves as the typed failure its
    status says, and `run_stream()` never raises - the exception is a value."""
    # deterministic 400: the family that must NOT be retried.
    _ep, error = run_stream(NEW, f"{server.base}/refuse-400/v1")
    check("t14-400-is-a-DeterministicFailure", type(error).__name__,
          "DeterministicFailure")
    check("t14-400-is-an-EndpointFailure-carrying-400-and-not-retryable",
          (isinstance(error, harness.new_mod.EndpointFailure),
           error.status_code, error.retryable), (True, 400, False))
    check("t14-400-keeps-the-user-facing-wording-byte-exact", str(error),
          'Endpoint returned 400: {"error": {"message": "mm-bad-request-no-retry"}}')

    # the context-length 400: named, because on an endpoint that answers neither
    # /props nor /slots this refusal IS the first signal (the notes are silent).
    _ep, error = run_stream(NEW, f"{server.base}/refuse-context/v1")
    check("t14-context-400-is-a-ContextLengthExceeded", type(error).__name__,
          "ContextLengthExceeded")
    check("t14-context-400-is-deterministic-and-not-retryable",
          (isinstance(error, harness.new_mod.DeterministicFailure),
           error.retryable, error.status_code), (True, False, 400))

    # 429 and 5xx: transient, retryable.
    _ep, error = run_stream(NEW, f"{server.base}/refuse-429/v1")
    check("t14-429-is-a-TransientFailure-retryable",
          (type(error).__name__, error.retryable, error.status_code),
          ("TransientFailure", True, 429))
    _ep, error = run_stream(NEW, f"{server.base}/refuse-500/v1")
    check("t14-503-is-a-TransientFailure-retryable",
          (type(error).__name__, error.retryable, error.status_code),
          ("TransientFailure", True, 503))

    # the in-stream `error` payload: the request was accepted, so the status is
    # the payload's, and the attempt is worth repeating.
    endpoint, error = run_stream(NEW, f"{server.base}/stream-error/v1")
    check("t14-in-stream-error-is-a-StreamFailure-retryable",
          (type(error).__name__, error.retryable, error.status_code),
          ("StreamFailure", True, 500))
    check("t14-in-stream-error-keeps-the-user-facing-wording", str(error),
          "Endpoint raised Error: 500, Type: server_error, mm-mid-stream-death")
    check("t14-the-half-reply-a-dead-stream-leaves-stands-in-the-messages",
          endpoint.messages[-1]["content"][0]["text"], "mm-before-the-error-")

    # no answer at all: a ConnectionFailure, status_code None, and the httpx
    # error kept underneath so the user still reads what happened.
    _ep, error = run_stream(NEW, DEAD_ADDRESS)
    check("t14-refused-socket-is-a-ConnectionFailure-retryable",
          (type(error).__name__, error.retryable, error.status_code),
          ("ConnectionFailure", True, None))
    check("t14-a-ConnectionFailure-is-a-TransientFailure-with-the-httpx-error-kept",
          (isinstance(error, harness.new_mod.TransientFailure),
           type(error.__cause__).__name__), (True, "ConnectError"))

    # CONTROL (TRAPS #13): the classifier decides on the STATUS, not on a name -
    # a 418 and a 400 are the same shape, a 429 and a 500 are the same shape, and
    # none of that ever looked at a server.
    refused = harness.new_mod.refusal_failure
    check("t14-CONTROL-classified-by-status-not-by-name",
          [(type(refused(code, "x")).__name__, refused(code, "x").retryable)
           for code in (400, 404, 418, 422, 429, 500, 502, 503)],
          [("DeterministicFailure", False), ("DeterministicFailure", False),
           ("DeterministicFailure", False), ("DeterministicFailure", False),
           ("TransientFailure", True), ("TransientFailure", True),
           ("TransientFailure", True), ("TransientFailure", True)])
    check("t14-CONTROL-context-words-name-it-out-of-a-400-429-or-200-payload",
          [type(refused(400, "mm-context length exceeded")).__name__,
           type(refused(429, "reduce the length of the prompt")).__name__,
           type(harness.new_mod.stream_failure(400, "x", "too many tokens")).__name__],
          ["ContextLengthExceeded", "ContextLengthExceeded",
           "ContextLengthExceeded"])
    check("t14-CONTROL-the-defaults-of-a-failure-built-with-no-status",
          (harness.new_mod.EndpointFailure("x").status_code,
           harness.new_mod.EndpointFailure("x").retryable,
           harness.new_mod.TransientFailure("x").retryable),
          (None, False, True))


def t14_settings_are_not_on_the_wire():
    """The two new fields are client-side facts about the endpoint. A setting not
    on `construct_payload`'s skip list goes out to the server and the server
    refuses the payload - t5's `n_ctx_control` 4242 is the control shape, and it
    is in the SAME payload, so the two absences below cannot be vacuous."""
    endpoint = NEW([], saved_endpoint("http://mm-host/v1",
                                      retry_attempts={"value": 4, "stype": "uinteger"},
                                      retry_delay={"value": 0.25, "stype": "ufloat"},
                                      n_ctx_control={"value": 4242,
                                                     "stype": "uinteger"}),
                   "mm-model-1", {}, "", [], None)
    payload = endpoint.prepare_payload()
    check("t14-retry_attempts-never-forwarded", "retry_attempts" in payload, False)
    check("t14-retry_delay-never-forwarded", "retry_delay" in payload, False)
    check("t14-CONTROL-an-off-list-setting-leaks-in-the-same-payload",
          payload.get("n_ctx_control"), 4242)
    check("t14-the-reads-of-the-two-fields",
          (endpoint.attempts, endpoint.delay), (4, 0.25))

    # An endpoint SAVED BEFORE these fields existed - every endpoint saved so far:
    # the settings file is read verbatim and no migration was authorised, so the
    # defaults are the answer, not a KeyError.
    old_shape = NEW([], saved_endpoint("http://mm-host/v1", retry_attempts=None,
                                       retry_delay=None), "mm-model-1", {}, "", [], None)
    check("t14-absent-fields-answer-the-defaults",
          (old_shape.attempts, old_shape.delay), (3, 1.0))
    blanked_shape = NEW([], saved_endpoint(
        "http://mm-host/v1",
        retry_attempts={"value": None, "stype": "uinteger"},
        retry_delay={"value": None, "stype": "ufloat"}), "mm-model-1", {}, "", [], None)
    check("t14-a-blanked-field-answers-the-default-too",
          (blanked_shape.attempts, blanked_shape.delay), (3, 1.0))


# ---------------------------------------------------------------- the work loop
async def t14_deterministic_costs_one(server):
    """A 400 is ONE attempt - the control that a retry is not unconditional -
    and the report is the old one: app.exception, the corpse taken back, the
    model list refreshed.

    ONE ATTEMPT IS NOT ONE POST. `stream()` sends `stream_options` and, on any
    4xx, asks a SECOND time without it (t6's rule, unchanged by WP-2 and
    untouched by it), so every 4xx attempt is two POSTs on the wire. The count
    that says "the loop asked once" is therefore `attempts_of`, and the POST
    count is asserted next to it with the probe named, because a check that
    quietly expected 2 wherever the rule says 1 would pass on a loop that
    retried twice and never asked about the flag at all (TRAPS #13)."""
    async with app_ctx(server, "refuse-400", attempts=3, delay=0) as (app, pilot):
        before = len(app.chat.messages)
        server.reset()
        await send(app, pilot)
        check("t14-A-a-400-is-ONE-attempt", attempts_of(server), 1)
        check("t14-A-a-400-sends-two-POSTs-the-t6-flag-probe-not-a-retry",
              len(completions(server)), 2)
        check("t14-A-the-second-POST-is-the-probe-without-the-flag",
              ["stream_options" in body for body in server.bodies], [True, False])
        check("t14-A-a-deterministic-refusal-reports-at-once",
              type(app.exception).__name__, "DeterministicFailure")
        check("t14-A-no-corpse-is-left-in-the-messages",
              len(app.chat.messages), before)
        check("t14-A-the-human-turn-is-still-the-tail",
              app.chat.messages[-1]["content"][0]["text"], "mm-turn-to-go")

    # `retry_attempts = 1` is "no retry" for a TRANSIENT too: one attempt, and
    # the control beside it is the same scenario with 3.
    async with app_ctx(server, "refuse-429", attempts=1, delay=0) as (app, pilot):
        server.reset()
        await send(app, pilot)
        check("t14-A-attempts-1-means-NO-retry-even-for-a-transient",
              attempts_of(server), 1)

    # CONTROL (TRAPS #13): the same transient, attempts 3 - three asks, and no
    # corpse standing when they are all spent.
    async with app_ctx(server, "refuse-429", attempts=3, delay=0) as (app, pilot):
        server.reset()
        await send(app, pilot)
        check("t14-A-CONTROL-a-transient-with-attempts-3-is-3-asks",
              attempts_of(server), 3)
        check("t14-A-the-transient-control-leaves-no-corpse",
              len(app.chat.messages), 3)


async def t14_transient_costs_attempts(server):
    """A 503 costs `retry_attempts` requests - and a 503 that clears is not a
    failure at all: two requests, the reply delivered, nothing reported."""
    for attempts in (1, 2, 3, 5):
        async with app_ctx(server, "refuse-500", attempts=attempts, delay=0) as (app, pilot):
            server.reset()
            await send(app, pilot)
            check(f"t14-B-a-503-costs-{attempts}-request(s)",
                  len(completions(server)), attempts)

    async with app_ctx(server, "flaky-503", attempts=3, delay=0) as (app, pilot):
        before = len(app.chat.messages)
        server.reset()
        await send(app, pilot)
        check("t14-B-a-503-that-clears-costs-two-requests",
              len(completions(server)), 2)
        check("t14-B-a-503-that-clears-delivers-the-reply",
              app.chat.messages[-1]["content"][0]["text"], "mm-alpha-one")
        check("t14-B-a-503-that-clears-reports-nothing",
              getattr(app, "exception", None), None)
        check("t14-B-a-retry-that-worked-leaves-one-message-behind",
              len(app.chat.messages), before + 1)

    # An endpoint saved without the fields asks THREE times (the default) - the
    # owner's "at least 3 times" on every endpoint that predates the setting.
    async with app_ctx(server, "refuse-500", delay=0) as (app, pilot):
        server.reset()
        await send(app, pilot)
        check("t14-B-no-retry_attempts-field-on-disk-defaults-to-three",
              len(completions(server)), 3)

    # the in-stream death is transient too: the whole attempt is repeated.
    async with app_ctx(server, "stream-error", attempts=2, delay=0) as (app, pilot):
        server.reset()
        await send(app, pilot)
        check("t14-B-an-in-stream-error-is-retried-to-the-limit",
              len(completions(server)), 2)
        check("t14-B-an-exhausted-in-stream-error-reports-the-StreamFailure",
              type(app.exception).__name__, "StreamFailure")


async def t14_one_reply_is_one_request(server):
    """THE control of the package (it caught a real bug in it): a reply that
    lands is ONE request and ONE message. A retry loop that falls through the
    success path asks three times and leaves three identical replies behind."""
    async with app_ctx(server, "content", attempts=3, delay=0) as (app, pilot):
        before = len(app.chat.messages)
        server.reset()
        await send(app, pilot)
        check("t14-C-a-successful-reply-is-ONE-request-through-the-loop",
              len(completions(server)), 1)
        check("t14-C-a-successful-reply-appends-ONE-message",
              len(app.chat.messages), before + 1)
        check("t14-C-a-successful-reply-reports-nothing",
              getattr(app, "exception", None), None)
        # The undo list holds the ONE `insert` of the reply signal 0 records - no
        # `remove` of anything, which is the difference between "one attempt, one
        # reply" and a loop that rolled something back on its way there. (Undo
        # entries are `[operation, message, index]` lists, undo.py:135.)
        check("t14-C-a-successful-reply-rolls-back-nothing",
              [entry[0] for entry in app.chat.undo.undo_list], ["insert"])


async def t14_rollback_and_undo(server):
    """The awaited rollback is COMPLETE between attempts, and its accepted cost
    is one undo entry per attempt (DECISIONS 84): the alternative is a second
    rollback path that skips the undo record, which is what WP-2 removed."""
    async with app_ctx(server, "refuse-500", attempts=3, delay=0) as (app, pilot):
        before = len(app.chat.messages)
        server.reset()
        await send(app, pilot)
        check("t14-D-after-three-failed-attempts-no-corpse-stands",
              len(app.chat.messages), before)
        check("t14-D-the-tail-is-still-the-human-turn",
              app.chat.messages[-1]["content"][0]["text"], "mm-turn-to-go")
        # Attempts 1 and 2 roll back AWAITED (one `remove` undo entry each); the
        # third failure is the REPORT, whose RemoveMessage is POSTED and lands in
        # the same handler - three `remove` entries, and every one of them is an
        # assistant corpse. This is the accepted cost of having ONE rollback
        # instead of two (DECISIONS 84): undoing after three failed attempts
        # walks back three removals, and the alternative - a rollback that skips
        # the undo record - is the second path this package exists to remove.
        check("t14-D-one-undo-entry-per-rolled-back-attempt",
              [entry[0] for entry in app.chat.undo.undo_list],
              ["remove"] * 3)
        check("t14-D-every-undone-removal-is-an-assistant-corpse",
              [entry[1]["role"] for entry in app.chat.undo.undo_list],
              ["assistant"] * 3)


async def t14_the_slot(server):
    """The leak WP-2 exists for: `after_work()` on EVERY way out, and the
    no-free-slot answer where the question is actually asked."""
    # a FAILED reply with the cache on: the slot is back (the old code returned
    # before after_work() and the slot was lost for the rest of the run).
    async with app_ctx(server, "refuse-500", attempts=2, delay=0,
                       save_cache_prompt={"value": True, "stype": "boolean"},
                       parallel={"value": 1, "stype": "uinteger"}) as (app, pilot):
        server.reset()
        await send(app, pilot)
        check("t14-E-a-failed-reply-returns-the-slot",
              slots_of(app), [(CHAT_ID, False)])
        check("t14-E-the-slot-bookkeeping-is-what-the-next-chat-asks",
              len(completions(server)), 2)

    # and the slot is taken EXACTLY once per reply, not once per attempt: the
    # loop is around stream(), not around before_work().
    async with app_ctx(server, "refuse-500", attempts=3, delay=0,
                       save_cache_prompt={"value": True, "stype": "boolean"},
                       parallel={"value": 1, "stype": "uinteger"}) as (app, pilot):
        server.reset()
        await send(app, pilot)
        restores = [line for line in server.posts() if "action=restore" in line]
        saves = [line for line in server.posts() if "action=save" in line]
        check("t14-E-one-restore-per-reply-not-per-attempt", len(restores), 1)
        check("t14-E-one-save-per-reply-too", len(saves), 1)

    # NO FREE SLOT: the request never goes out, and the slot somebody else holds
    # is not marked idle by the -1 answer.
    async with app_ctx(server, "content", attempts=3, delay=0,
                       save_cache_prompt={"value": True, "stype": "boolean"},
                       parallel={"value": 1, "stype": "uinteger"}) as (app, pilot):
        app.slots["1"] = {MODEL: [("mm-other-chat", True)]}
        server.reset()
        await send(app, pilot)
        check("t14-E-no-free-slot-sends-NO-request", len(completions(server)), 0)
        check("t14-E-no-free-slot-says-so", str(getattr(app, "exception", "")),
              "No free slot for inference available! Please try again later!")
        check("t14-E-no-free-slot-does-not-touch-another-chats-slot",
              slots_of(app), [("mm-other-chat", True)])


async def t14_abort_during_a_retry(server):
    """An abort during the sleep: no further request, nothing deleted, over in
    about a tenth of a second - `retrying` is what makes `action_abort` take the
    flag path instead of deleting `messages[-1]`, which by then is the human's."""
    async with app_ctx(server, "refuse-500", attempts=3, delay=5.0) as (app, pilot):
        from spit_app.chat.work import Work
        work = Work(app.chat)
        app.chat._work = work
        before = len(app.chat.messages)
        server.reset()
        running = asyncio.ensure_future(work.work_stream())
        for _ in range(200):                      # until the FIRST failure sleeps
            if work.retrying or running.done():
                break
            await asyncio.sleep(0.01)
        check("t14-F-the-abort-happened-during-a-retry-sleep", work.retrying, True)
        started = time.monotonic()
        await app.chat.action_abort()
        await running
        await settle(pilot)
        elapsed = time.monotonic() - started

        check("t14-F-an-abort-costs-NO-further-request", len(completions(server)), 1)
        check("t14-F-the-abort-ends-the-sleep-within-a-slice", elapsed < 1.0, True)
        check("t14-F-an-abort-deletes-NOTHING", len(app.chat.messages), before)
        check("t14-F-the-human-turn-is-still-there",
              app.chat.messages[-1]["content"][0]["text"], "mm-turn-to-go")
        check("t14-F-the-flag-path-was-taken", work.exit_after_busy, True)
        check("t14-F-the-flag-is-let-go-again", work.retrying, False)
        check("t14-F-an-abort-is-silent", getattr(app, "exception", None), None)


async def t14_stale_signal(server):
    """The handler guard, pinned on its own: a `StreamCallback` whose index is no
    longer a message does NOTHING, and one whose index IS a message still mounts
    it (the control without which the guard would pass on a handler that answers
    nothing at all). This is the hole the delete-by-data-index sites open:
    `action_abort` removes the tail without waiting for the queue, so the signals
    a stream posted before it died are delivered after the dict is gone - and
    `message_start` mounting a vanished index is an IndexError inside a Textual
    message handler, which is the app dying, not a reply failing."""
    from spit_app.chat.textual_message import StreamCallback
    async with app_ctx(server, "content") as (app, pilot):
        view = app.chat.chat_view
        before = len(app.chat.messages)
        children_before = len(view.children)
        stale = len(app.chat.messages)              # one PAST the end
        await view.on_stream_callback(StreamCallback(stale, 1))
        await settle(pilot)
        check("t14-G-a-stale-signal-mounts-nothing",
              len(view.children), children_before)
        check("t14-G-a-stale-signal-changes-no-data",
              len(app.chat.messages), before)
        await view.on_stream_callback(StreamCallback(stale, 0))
        await settle(pilot)
        check("t14-G-a-stale-finish-signal-writes-no-data-and-no-undo",
              (len(app.chat.messages), len(app.chat.undo.undo_list)), (before, 0))

        # CONTROL: the same handler, a LIVE index - its widget appears. Without
        # this row every absence above is just a handler that does nothing.
        app.chat.messages.append({"role": "assistant", "reasoning": "",
                                  "content": [{"type": "text", "text": "mm-live"}]})
        live = len(app.chat.messages) - 1
        check("t14-G-CONTROL-the-live-index-has-no-widget-before-the-signal",
              view.widget(live), None)
        await view.on_stream_callback(StreamCallback(live, 1))
        await settle(pilot)
        check("t14-CONTROL-a-live-signal-still-mounts-its-message",
              view.widget(live) is not None, True)


def main():
    server = CannedServer().start()
    try:
        guarded("t14-classes", lambda: t14_classes(server))
        guarded("t14-settings", lambda: t14_settings_are_not_on_the_wire())
        guarded("t14-deterministic", lambda: run(t14_deterministic_costs_one, server))
        guarded("t14-attempts", lambda: run(t14_transient_costs_attempts, server))
        guarded("t14-one-request", lambda: run(t14_one_reply_is_one_request, server))
        guarded("t14-rollback", lambda: run(t14_rollback_and_undo, server))
        guarded("t14-slot", lambda: run(t14_the_slot, server))
        guarded("t14-abort", lambda: run(t14_abort_during_a_retry, server))
        guarded("t14-stale-signal", lambda: run(t14_stale_signal, server))
    finally:
        server.stop()
    summary()
    return 1 if harness.fail_ else 0


def run(coroutine_fn, server):
    asyncio.run(coroutine_fn(server))


if __name__ == "__main__":
    sys.exit(main())
