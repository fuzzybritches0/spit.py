#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t15 - THE HARVEST IS WIRED: what one real `Work.work_stream()` does to the
counts on the `Chat`, to the counts row, and to what the model is told on the
NEXT request. Driven over the canned server with a real headless `Chat` and a
real `Work`, exactly as `chat_text_area.py` builds and runs it.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t15.
t1/t5/t8/t9 are in test_payload.py, t2/t3/t4 in test_stream_parse.py, t6/t7 in
test_requests.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py, t12
in test_system_note.py, t13 in test_note_chain.py, t14 in test_retry.py.

WHY THIS FILE EXISTS - the regression it was written for. `Work.harvest_usage()`
was correct (t10, 19 checks) and the counts row was correct (t11, 43 checks), and
between `391bb3a` (P19/WP-2) and here the WHOLE SUITE STAYED GREEN AT 512 while
the chat showed `ctx 0 · gen 0 · cached 0` and the token-status notes never
spoke: WP-2 moved the request out of `work_stream()` into `stream_attempts()`
and left the call behind. Nothing could have reddened that. t10 calls the method
on a `SimpleNamespace`; t11 drives a `FakeEndpoint` through a hand-written
`Reply.one()` that COPIES the two statements instead of running the flow; t13
runs the real `work_stream()` against the `content` scenario, which carries no
usage chunk at all, and hand-sets the fill. A method and a widget can each be
right while the line that joins them is gone - so what is pinned here is the
JOIN: the real worker, the real endpoint, the real row, the real wire.

WHAT IS PROVEN AND WHERE
  * a reply that carries usage moves `chat.token_usage` to the server's own
    figures and the counts row shows them, with the control of the same worker
    on a reply that carries NONE (the zeros survive, so the greens are about the
    usage object and not about a chat that moves on any reply);
  * an error is not a counted reply, AT THE CALL SITE: the `usage-then-error`
    stream hands over its usage chunk and then dies, and the counts do not move
    - the check that reddens a harvest sitting in a `finally`, or before the
      `try`, or in the retry branch, which are the shapes a fix could plausibly
      take and must not (three attempts, three corpses, one report, no count);
  * a retry's success is counted and its failure is not (the `flaky-503-usage`
    scenario: a 503 that carries no usage object at all, then the `finishusage`
    reply - `generated` +7, `cached` the landed reply's 30, `context` its 48);
  * `context` is the latest call and `generated` accumulates, on the wired path
    and not only in the method: two requests, the second 100/20 against the
    first's 119000/1000, fill down and total up;
  * the model is told: the fill a reply earned is what the NEXT request's
    `info` note quotes, byte for byte - with the same chat's FIRST request, made
    while the fill was still 0, carrying none. This is the symptom the owner
    reported second, and it is the same single line: `used=0` is below every
    level, so no note is ever written and the chain that is entirely correct
    (t12, t13) never speaks.

THE FIXTURES ARE LOADED, NOT GUESSED (TRAPS #13). Every figure below comes from
the harness's own usage objects (`USAGE` 41/7/30, `BIG_USAGE` 119000/1000/90000,
`OTHER_USAGE` 100/20 with no details), the scenario that serves each is named at
the check, and the window is 200000 - percentage territory, no remaining-token
floor and no `small_window` note, so the only thing that can move a level is the
harvest. The mount's own context-size probe is awaited BEFORE the window is
written (the canned scenarios 404 both routes), so no late answer can clobber it
and the request path itself starts no probe.

TRAPS #8 (`mm-*` tokens), #13 (a control beside every absence), #15 (a new
number), #18 (groups inside `guarded()`, the row a runner reads is a floor),
#19 (needs the venv: a real Chat, a real Work, httpx).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from endpoint_harness import (BIG_USAGE, CannedServer, OTHER_USAGE, USAGE,  # noqa: E402
                              check, guarded, saved_endpoint, summary)
import endpoint_harness as harness  # noqa: E402

from counts_harness import StubEndpointApp, row_text, settle  # noqa: E402
from smoke_scenario import fixture_settings  # noqa: E402 (path via counts_harness)

from spit_app.chat.token_status import TEXT_INFO  # noqa: E402
from spit_app.chat.work import Work  # noqa: E402

WINDOW = 200000                    # percentage territory: 50% = 100000
MARKERS = ("Token status:", "Token warning:", "Critical:",
           "This chat's context window is only")

# What each canned scenario's reply is worth, read off the harness object it is
# built from - never re-typed (a figure typed twice can disagree silently).
FINISH = {"context": USAGE["prompt_tokens"] + USAGE["completion_tokens"],
          "generated": USAGE["completion_tokens"],
          "cached": USAGE["prompt_tokens_details"]["cached_tokens"]}
BIG = {"context": BIG_USAGE["prompt_tokens"] + BIG_USAGE["completion_tokens"],
       "generated": BIG_USAGE["completion_tokens"],
       "cached": BIG_USAGE["prompt_tokens_details"]["cached_tokens"]}
OTHER = {"context": OTHER_USAGE["prompt_tokens"] + OTHER_USAGE["completion_tokens"],
         "cached": 0}               # OTHER_USAGE carries no details object


class HarvestApp(StubEndpointApp):
    """`slots` and `path`, the two attributes a real `Work` asks the app for and
    the smoke stub does not carry - the same shape t13's ChainApp and t14's
    RetryApp add (duplicated on purpose: a test file importing another test file
    couples two suites' fixtures through a module-level `SERVER`)."""

    def __init__(self, content: dict, endpoints: dict) -> None:
        super().__init__(content, endpoints)
        self.slots = {}
        self.path = "/tmp/mm-harvest-not-used"


def harvest_content() -> dict:
    """A chat whose tail is the human's own turn. NOT `fixture_chat()`: its tail
    is a `tool` result, and the point of this file is the ONE request a send
    makes - with a pending tool call the worker runs the tools first and the
    message count the checks read moves by something other than the reply."""
    return {"ctime": "2026-01-01T00:00:00", "settings": fixture_settings(),
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "mm-user-first"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "mm-answer-one"}]},
                {"role": "user", "content": [{"type": "text", "text": "mm-turn-to-go"}]},
            ]}


def asks(server) -> list:
    """The recorded POSTs that ask for a reply. ManageCache posts
    `/<scenario>/slots/<n>?action=…` to the same server when `save_cache_prompt`
    is on, and those are not requests to the endpoint (t14's helper of the same
    name is the precedent for filtering them out)."""
    return [line for line in server.posts() if "/chat/completions" in line]


def note_items(wire) -> list:
    return [m for m in wire if isinstance(m.get("content"), str)
            and any(marker in m["content"] for marker in MARKERS)]


def window_gets(server) -> list:
    return [g for g in server.gets()
            if ("/props" in g or "/slots" in g) and not g.endswith("/models")]


class app_ctx:
    """`async with app_ctx(server, scenario) as (chat_app, pilot)` - a fresh
    mounted chat aimed at one canned scenario, its window probe already answered
    and its window written by the test (200000, percentage territory).

    `attempts`/`delay` are the two P19 endpoint fields, settable so a failure
    group costs ONE attempt and a retry group costs no wall clock at all (the
    defaults are 3 and 1.0 s, and a suite that slept through them would be
    honest but slow); leaving `attempts` as None leaves the field ABSENT, the
    shape of every endpoint saved before P19."""

    def __init__(self, server, scenario: str, attempts: int = None,
                 delay=None) -> None:
        self.server, self.scenario = server, scenario
        self.attempts, self.delay = attempts, delay
        self.app = None
        self.ctx = None

    def _endpoint(self) -> dict:
        fields = {}
        if self.attempts is not None:
            fields["retry_attempts"] = {"value": self.attempts, "stype": "uinteger"}
        if self.delay is not None:
            fields["retry_delay"] = {"value": self.delay, "stype": "ufloat"}
        return saved_endpoint(f"{self.server.base}/{self.scenario}/v1", **fields)

    async def __aenter__(self):
        self.app = HarvestApp(harvest_content(), {"1": self._endpoint()})
        self.ctx = self.app.run_test()
        pilot = await self.ctx.__aenter__()
        await settle(pilot)
        settings = self.app.chat.chat_settings
        key = settings.context_key()
        for _ in range(100):                     # the mount's probe must have
            if key in settings.context_sizes:    # filed its answer first
                break
            await pilot.pause()
        settings.context_sizes[key] = WINDOW
        return self.app, pilot

    async def __aexit__(self, *exc):
        result = await self.ctx.__aexit__(*exc)
        self.app = None
        return result


async def one_send(app, pilot):
    """One send exactly as the UI does it: a NEW `Work` (a `Work` is built per
    send, DECISIONS 80 c) running the real `work_stream()`."""
    work = Work(app.chat)
    app.chat._work = work
    await work.work_stream()
    await settle(pilot)
    return work


async def t15_a_reply_moves_the_counts(server):
    """The join itself: the worker's success path feeds `chat.token_usage`, and
    the signal-0 redraw that closes the reply therefore shows THIS reply's
    figures. With the call gone every one of these is red and the suite is
    otherwise silent - which is precisely the hole t10 and t11 could not see."""
    async with app_ctx(server, "finishusage") as (app, pilot):
        chat = app.chat
        check("t15-a-fresh-chat-starts-at-three-zeros",
              chat.token_usage, {"context": 0, "generated": 0, "cached": 0})
        check("t15-the-setup-row-reads-the-zeros",
              ("0" in row_text(chat), "ctx 0" in row_text(chat)), (True, True))

        server.reset()
        work = await one_send(app, pilot)
        # The endpoint kept what the server said. Stated FIRST because it is the
        # half that never broke: when the counts below read 0 the fault is the
        # line between this and `chat.token_usage`, not the parse (t2/t3/t4).
        check("t15-the-endpoint-held-the-usage-object", work.endpoint.usage, USAGE)
        check("t15-the-landed-reply-moved-context", chat.token_usage["context"],
              FINISH["context"])
        check("t15-the-landed-reply-moved-generated", chat.token_usage["generated"],
              FINISH["generated"])
        check("t15-the-landed-reply-moved-cached", chat.token_usage["cached"],
              FINISH["cached"])
        check("t15-the-row-shows-this-replies-own-figures",
              (str(FINISH["context"]) in row_text(chat),
               str(FINISH["generated"]) in row_text(chat),
               str(FINISH["cached"]) in row_text(chat)), (True, True, True))
        check("t15-one-send-is-one-request", len(asks(server)), 1)
        check("t15-the-reply-landed-as-one-message", len(chat.messages), 4)
        check("t15-the-harvest-wrote-nothing-into-the-messages",
              sorted(chat.messages[-1]), ["content", "reasoning", "role"])

        # CONTROL (TRAPS #13): the same worker, the same chat, a reply that says
        # nothing about tokens - the figures SURVIVE, they do not zero and they do
        # not double (DECISIONS 80 c's silence rule, on the wired path). Without
        # this the greens above could be "any send writes these numbers".
        server.reset()
        chat.chat_settings.context_sizes[chat.chat_settings.context_key()] = WINDOW
        app.endpoints["1"]["endpoint_url"]["value"] = f"{server.base}/nousage/v1"
        await one_send(app, pilot)
        check("t15-CONTROL-a-reply-with-no-usage-leaves-the-counts-alone",
              chat.token_usage, {"context": FINISH["context"],
                                 "generated": FINISH["generated"],
                                 "cached": FINISH["cached"]})
        check("t15-CONTROL-that-reply-did-land", len(chat.messages), 5)


async def t15_an_error_is_not_counted(server):
    """A stream that reports its usage and THEN dies leaves the counts exactly
    where they were. This is the shape of the fix that must not be: a harvest in
    a `finally`, or ahead of the `try`, passes every other check in this file and
    reddens this one, because the corpse handed over a usage chunk and the reply
    was never got."""
    # THREE attempts and NO delay - the count matters, not the clock. An
    # in-stream error is a `StreamFailure`, i.e. transient, so the loop asks
    # three times (t14 pins that rule); here it says the SAME corpse was handed
    # over THREE TIMES, its usage chunk with it, and the chat was not told a
    # single one of them. `can_recover(app)` is False for this stub (its
    # `StubSettings` carries no `path`), so the report is the modal path:
    # `app.exception`, as t14 records.
    async with app_ctx(server, "usage-then-error", attempts=3, delay=0) as (app, pilot):
        chat = app.chat
        before = dict(chat.token_usage)
        server.reset()
        work = await one_send(app, pilot)
        check("t15-the-dead-streams-did-carry-their-usage", work.endpoint.usage, BIG_USAGE)
        check("t15-a-transient-in-stream-death-was-asked-three-times",
              len(asks(server)), 3)
        check("t15-and-it-was-reported-as-the-in-stream-failure-it-is",
              type(getattr(app, "exception", None)).__name__, "StreamFailure")
        check("t15-a-dead-reply-moves-no-count", chat.token_usage, before)
        check("t15-a-dead-reply-leaves-no-corpse-behind", len(chat.messages), 3)
        check("t15-the-row-still-reads-the-zeros", "ctx 0" in row_text(chat), True)
        # CONTROL (TRAPS #13): the scenario is not a stream that never said
        # anything - the same server answers `finishusage` for the same chat and
        # the SAME code moves the counts. Without this, "nothing moved" could be
        # about a chat whose harvest is dead rather than about the error path.
        app.endpoints["1"]["endpoint_url"]["value"] = f"{server.base}/finishusage/v1"
        await one_send(app, pilot)
        check("t15-CONTROL-the-same-worker-harvests-the-next-LANDING",
              chat.token_usage["context"], FINISH["context"])


async def t15_a_retry_harvests_once(server):
    """Two requests, one reply: the harvest runs when a reply LANDS, so the
    retry's success adds the completion ONCE. `flaky-503-usage` refuses the first
    POST with a 503, then answers the second with `finishusage`'s reply. The
    counts therefore move by THAT reply and by nothing the dead attempt left
    behind: `stream()` resets `self.usage` at its own start, so the 503 carries
    no usage object and the harvest of a landed reply is the only figure that
    reaches the chat - `generated` +7, `cached` the landed reply's 30, `context`
    its 48. t14 pins the REQUEST counts of this scenario; what nothing pinned
    was what a successful retry LEAVES BEHIND."""
    async with app_ctx(server, "flaky-503-usage", attempts=2, delay=0) as (app, pilot):
        chat = app.chat
        chat.token_usage = {"context": 1000, "generated": 500, "cached": 20}
        server.reset()
        await one_send(app, pilot)
        check("t15-a-retry-that-landed-asked-twice", len(asks(server)), 2)
        check("t15-a-landed-retry-added-its-completion-ONCE",
              chat.token_usage,
              {"context": FINISH["context"],
               "generated": 500 + FINISH["generated"],
               "cached": FINISH["cached"]})
        check("t15-and-it-left-one-reply-not-two", len(chat.messages), 4)


async def t15_the_latest_and_the_total(server):
    """DECISIONS 80 c's two rules on the wired path: `context` is the LATEST call
    (it goes DOWN on a smaller reply, it never sums - the next prompt already
    contains the previous answer), `generated` is the one number that adds up,
    and `cached` is this read's figure or 0 - not the previous call's 90000."""
    async with app_ctx(server, "bigusage") as (app, pilot):
        chat = app.chat
        server.reset()
        await one_send(app, pilot)
        check("t15-a-big-reply-set-the-fill-to-its-own-figure",
              chat.token_usage["context"], BIG["context"])
        check("t15-a-big-reply-added-its-own-completion",
              chat.token_usage["generated"], BIG["generated"])
        check("t15-a-big-reply-set-cached-from-its-own-details",
              chat.token_usage["cached"], BIG["cached"])

        # the second request is SMALLER (the harness's OTHER_USAGE, 100/20, and
        # NO details object): the fill falls, the total grows, cached drops to 0.
        app.endpoints["1"]["endpoint_url"]["value"] = f"{server.base}/otherusage/v1"
        server.reset()
        await one_send(app, pilot)
        check("t15-the-next-fill-is-the-smaller-calls-figure",
              chat.token_usage["context"], OTHER["context"])
        check("t15-context-never-sums-it-went-DOWN",
              chat.token_usage["context"] < BIG["context"], True)
        check("t15-generated-did-add-the-two-completions",
              chat.token_usage["generated"], BIG["generated"] + 20)
        check("t15-cached-is-this-reads-figure-or-zero", chat.token_usage["cached"], 0)


async def t15_the_model_is_told(server):
    """THE SECOND SYMPTOM, and the same single line. The fill a reply earned is
    the figure the NEXT request's note quotes: `BIG_USAGE` is 60% of the window,
    so the second request must carry exactly one `info` note and it must say the
    harvested number, byte for byte. The chat's FIRST request is the control -
    asked while the fill was still 0, it carries nothing, so the note below is
    about a figure that arrived and not about a chain that always speaks."""
    async with app_ctx(server, "bigusage") as (app, pilot):
        chat = app.chat
        server.reset()
        await one_send(app, pilot)
        check("t15-CONTROL-the-first-request-carries-no-note",
              len(note_items(server.bodies[-1]["messages"])), 0)
        check("t15-the-first-request-did-land", len(asks(server)), 1)
        server.reset()
        await one_send(app, pilot)
        wire = server.bodies[-1]["messages"]
        expected = TEXT_INFO.format(used=BIG["context"], total=WINDOW,
                                    remaining=WINDOW - BIG["context"],
                                    pct=round(100 * BIG["context"] / WINDOW))
        check("t15-the-next-request-carries-exactly-one-note", len(note_items(wire)), 1)
        check("t15-the-note-quotes-the-figure-the-reply-earned",
              (wire[-1] if wire else None), {"role": "user", "content": expected})
        check("t15-that-note-costs-no-extra-request", len(asks(server)), 1)
        check("t15-that-note-started-no-window-probe", window_gets(server), [])


SERVER = None


def main():
    print("INPUT MAPPING (TRAPS #13): a real headless `Chat` on the stub app "
          "(+ slots/path) and a real `Work.work_stream()`, POSTing to the canned "
          "server. Scenarios and what each reply is worth: `finishusage` = "
          f"USAGE 41+7 with cached 30 -> ctx {FINISH['context']} · gen "
          f"{FINISH['generated']} · cached {FINISH['cached']}; `nousage` = a text "
          "reply, no usage chunk -> the counts unmoved; `usage-then-error` = the "
          "usage chunk THEN an error payload -> nothing moves; `flaky-503-usage` = "
          "503 then the `finishusage` reply -> two requests, ONE harvest, "
          "`generated` +7 and not +14; `bigusage` = "
          f"BIG_USAGE 119000+1000 cached 90000 -> {BIG['context']} of a "
          f"{WINDOW} window = 60% -> the `info` note on the NEXT request; "
          f"`otherusage` = 100+20, no details -> the fill FALLS to "
          f"{OTHER['context']}, `generated` still adds, cached drops to 0. The "
          "window is written after the mount's own probe answered, so the "
          "denominator is known and no floor or small-window note is involved.")
    global SERVER
    SERVER = CannedServer().start()
    try:
        guarded("t15-counts", lambda: run(t15_a_reply_moves_the_counts, SERVER))
        guarded("t15-error", lambda: run(t15_an_error_is_not_counted, SERVER))
        guarded("t15-retry", lambda: run(t15_a_retry_harvests_once, SERVER))
        guarded("t15-latest", lambda: run(t15_the_latest_and_the_total, SERVER))
        guarded("t15-notes", lambda: run(t15_the_model_is_told, SERVER))
    finally:
        SERVER.stop()
    summary()
    return 1 if harness.fail_ else 0


def run(coroutine_fn, server):
    import asyncio
    asyncio.run(coroutine_fn(server))


if __name__ == "__main__":
    sys.exit(main())
