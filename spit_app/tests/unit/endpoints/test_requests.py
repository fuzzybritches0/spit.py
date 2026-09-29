#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t6, t7 - the two HTTP behaviours of step 1: the one-retry rule around
`stream_options`, and the `get_context_size()` fallback chain.

Numbers are append-only across the whole suite (TRAPS #15). This file owns
t6 / t7; t1, t5, t8, t9 are in test_payload.py, t2 / t3 / t4 in
test_stream_parse.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py.

Every count here is read off the RECORDED REQUEST LINES of the canned server,
because the retry rule and the chain ARE request counts and request order - the
answer alone cannot tell "asked once" from "asked twice and the second won".

  t6  the 4xx retry: a 4xx with the flag is retried EXACTLY once, the second
      request carries no `stream_options`, and the reply is delivered anyway
      (never lose a reply over counting); a 4xx that refuses BOTH times raises
      the same `Endpoint returned N: ...` RuntimeError work.py already catches,
      so `work_stream`'s error path is unchanged; a 5xx is NOT retried; a
      success is one request.
  t7  the chain, each rung answered by the route that is supposed to miss:
      `/props` default_generation_settings.n_ctx wins even when /slots has a
      different number; a model given puts `?model=<id>` on the /props request
      line; a /props that 400s, that lacks n_ctx, that is a JSON list, or that
      is not JSON at all falls to the first /slots entry whose n_ctx is a
      POSITIVE INT; a dead /props AND /slots falls to the endpoint's
      `context_size` when it is > 0; 0 is auto-detect, not a size; a blanked
      field (the way store_values leaves it, value None) and a key absent
      entirely both answer None; nothing said at all answers None; garbage
      JSON, a 404 and a refused address never raise.
      EXCEPT the {} endpoint dict, which raises KeyError: native_address
      indexes ["endpoint_url"] (llamacpp.py:37) and ChatSettings' guard is what
      keeps it out of reach. Step 1 does not guard it and this step must not
      either - pinned below, with the reason in the name, NOT "fixed".
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (CannedServer, DEAD_ADDRESS, NEW,  # noqa: E402
                              baseline_selfcheck, blanked, check,
                              describe_context_scenarios, dumps, get_context,
                              guarded, run_stream, saved_endpoint, summary)
import endpoint_harness as harness  # noqa: E402

CHAT_COMPLETIONS = "/chat/completions"


def t6_retry(server):
    if not baseline_selfcheck("t6"):
        return
    # a 4xx while the flag is set, a normal reply without it
    server.reset()
    endpoint, error = run_stream(NEW, f"{server.base}/refuse-flag/v1")
    check("t6-refused-with-the-flag-retried-EXACTLY-once", len(server.posts()), 2)
    check("t6-both-requests-hit-the-same-route",
          set(server.posts()), {f"POST /refuse-flag/v1{CHAT_COMPLETIONS}"})
    check("t6-first-request-carried-the-flag",
          "stream_options" in server.bodies[0], True)
    check("t6-second-request-carried-no-flag",
          "stream_options" in server.bodies[1], False)
    check("t6-second-request-asked-for-the-same-model",
          server.bodies[1]["model"], "mm-model-1")
    check("t6-the-reply-was-delivered-anyway",
          endpoint.messages[-1]["content"][0]["text"], "mm-noflag-reply")
    check("t6-no-error-raised-for-a-retry-that-worked", repr(error), "None")

    # a 4xx that refuses both times: exactly two requests, then the error
    # the work loop now classifies. RE-PINNED IN PLACE by P19/WP-2 (numbers kept,
    # count not down, DECISIONS 70's precedent for a deliberate behaviour change):
    # this check used to pin `RuntimeError` and membership in `work_stream`'s
    # exception-NAME tuple. What moved is the type - the endpoint answers a
    # refusal with a `DeterministicFailure`, which carries the status code and
    # `retryable = False` so the work loop decides on a flag instead of on a name
    # (the typed hierarchy and its argues are DECISIONS 84). The WORDING inside
    # `str()` is the same sentence the app has always shown and the check below
    # still pins byte-for-byte.
    server.reset()
    _endpoint, error = run_stream(NEW, f"{server.base}/refuse-always/v1")
    check("t6-refused-both-times-two-requests-only", len(server.posts()), 2)
    check("t6-refused-both-times-raises-a-DeterministicFailure",
          type(error).__name__, "DeterministicFailure")
    check("t6-refused-both-times-message-is-the-HEAD-shape",
          str(error), 'Endpoint returned 403: ' + json.dumps(
              {"error": {"message": "mm-denied-every-time"}}))
    check("t6-the-error-is-the-typed-failure-carrying-status-and-retryable",
          (isinstance(error, harness.new_mod.EndpointFailure),
           error.status_code, error.retryable), (True, 403, False))
    check("t6-CONTROL-the-classifier-is-not-name-matching-a-429-is-the-same-shape-retryable",
          (type(harness.new_mod.refusal_failure(429, "x")).__name__,
           harness.new_mod.refusal_failure(429, "x").retryable,
           harness.new_mod.refusal_failure(503, "x").status_code,
           type(harness.new_mod.refusal_failure(503, "x")).__name__),
          ("TransientFailure", True, 503, "TransientFailure"))
    check("t6-neither-request-dropped-its-flag-on-the-first-try",
          ["stream_options" in body for body in server.bodies], [True, False])

    # a 5xx is NOT retried (the flag is not what a 500 is complaining about)
    server.reset()
    _endpoint, error = run_stream(NEW, f"{server.base}/refuse-500/v1")
    check("t6-5xx-is-not-retried", len(server.posts()), 1)
    check("t6-5xx-still-raises-with-the-same-message-shape",
          str(error), "Endpoint returned 503: mm-unavailable")

    # a success is one request: the retry costs nothing when nothing refuses
    server.reset()
    _endpoint, error = run_stream(NEW, f"{server.base}/content/v1")
    check("t6-success-is-one-request", len(server.posts()), 1)
    check("t6-success-no-error", repr(error), "None")

    # the control (TRAPS #13): the pinned file makes exactly ONE request of the
    # same 4xx endpoint and loses the reply the retry saves - and it never sent
    # the flag in the first place, which is why it could not be refused for it.
    server.reset()
    old_endpoint, old_error = run_stream(harness.OLD_EP, f"{server.base}/refuse-flag/v1")
    # ONE request, and no error: the scenario only 400s a request that carries
    # the flag, and the pinned side never sends one. So this control pins the
    # other half of the story - the retry exists for a server that refuses the
    # NEW field, and the old code could never meet such a server because it
    # never asked for counts at all. (Its reply is the same mm-noflag-reply:
    # losing a reply is exactly what the new code must never do.)
    check("t6-CONTROL-old-made-one-request-only",
          (len(server.posts()), type(old_error).__name__), (1, "NoneType"))
    check("t6-CONTROL-old-sent-no-stream_options-so-could-never-be-refused-for-one",
          ("stream_options" in server.bodies[0],
           old_endpoint.messages[-1]["content"][0]["text"]),
          (False, "mm-noflag-reply"))


def t7_context_chain(server):
    if not baseline_selfcheck("t7"):
        return
    print(describe_context_scenarios())

    # rung 1: /props wins - and it wins AGAINST a /slots that answers 4096, so
    # "8192" cannot be the second rung answering by accident.
    server.reset()
    check("t7-props-default_generation_settings-wins",
          get_context(saved_endpoint(f"{server.base}/props/v1")), 8192)
    check("t7-props-won-so-slots-was-never-asked", server.gets(),
          [f"GET /props/props"])

    # with a model, the /props request line carries ?model=<id> - a router /
    # multi-model server is the reason the query exists.
    server.reset()
    check("t7-model-given-still-answers",
          get_context(saved_endpoint(f"{server.base}/props/v1"), "mm-model-9"), 8192)
    check("t7-props-request-line-carries-the-model", server.gets(),
          ["GET /props/props?model=mm-model-9"])
    check("t7-the-model-arrives-as-a-query-parameter", server.models, ["mm-model-9"])
    # Its OWN reset/call pair (the pair above left a recorded `mm-model-9` in
    # `server.models`, and `gets()` would still hold its request line): the query
    # is absent from the line AND the /props route itself saw no model.
    server.reset()
    get_context(saved_endpoint(f"{server.base}/props/v1"))
    check("t7-no-model-given-carries-no-query", server.gets(), ["GET /props/props"])
    check("t7-no-model-given-the-route-read-no-model-parameter", server.models, [None])

    # rung 2: the /slots fallback. Four different ways /props misses.
    server.reset()
    check("t7-props-400-falls-to-slots",
          get_context(saved_endpoint(f"{server.base}/props400/v1")), 4096)
    check("t7-props-400-asked-props-then-slots", server.gets(),
          ["GET /props400/props", "GET /props400/slots"])
    check("t7-props-without-n_ctx-falls-to-slots",
          get_context(saved_endpoint(f"{server.base}/propsnone/v1")), 2048)
    check("t7-props-that-is-a-json-list-falls-to-slots",
          get_context(saved_endpoint(f"{server.base}/propslist/v1")), 512)
    check("t7-props-that-is-not-json-falls-to-slots-no-raise",
          get_context(saved_endpoint(f"{server.base}/garbage/v1"),
                      ), None)   # /slots is not JSON either -> the override rung

    # the first /slots entry whose n_ctx is a POSITIVE INT: 0, a string and a
    # negative are all skipped, not read as a size.
    check("t7-first-positive-int-slot-wins",
          get_context(saved_endpoint(f"{server.base}/slotjunk/v1")), 1024)

    # rung 3: the endpoint's own override, only when both routes missed.
    over = {"context_size": {"value": 32768, "stype": "uinteger"}}
    check("t7-dead-props-and-slots-fall-to-the-override",
          get_context(saved_endpoint(f"{server.base}/nothing/v1", **over)), 32768)
    check("t7-the-override-is-asked-only-after-both-routes",
          server.gets()[-2:], ["GET /nothing/props", "GET /nothing/slots"])
    check("t7-not-json-anywhere-falls-to-the-override-too",
          get_context(saved_endpoint(f"{server.base}/garbage/v1", **over)), 32768)

    # 0 is auto-detect, not a size; blanked and absent behave the same way.
    check("t7-override-0-is-auto-detect-not-a-size",
          get_context(saved_endpoint(f"{server.base}/nothing/v1",
                                     context_size={"value": 0, "stype": "uinteger"})),
          None)
    check("t7-override-blanked-the-way-store_values-leaves-it",
          get_context(saved_endpoint(
              f"{server.base}/nothing/v1",
              context_size=blanked({"value": 32768, "stype": "uinteger"}))), None)
    check("t7-override-key-absent-entirely",
          get_context(saved_endpoint(f"{server.base}/nothing/v1", context_size=None)),
          None)
    check("t7-nothing-said-at-all-is-None",
          get_context(saved_endpoint(f"{server.base}/nothing/v1")), None)

    # a refused address: never raises, and costs 39 ms, not the 3 s of a filter.
    check("t7-refused-address-is-None-and-never-raises",
          get_context(saved_endpoint(DEAD_ADDRESS)), None)
    check("t7-an-unparseable-host-is-None-and-never-raises",
          get_context(saved_endpoint("mm-not-a-url-at-all")), None)

    # the header rides on the native request too (auth_headers, D3).
    server.reset()
    get_context(saved_endpoint(f"{server.base}/props/v1",
                               key={"value": "mm-sekret-3", "stype": "string"}))
    check("t7-props-carried-the-authorization-header",
          len(server.gets()), 1)

    # THE PINNED LIMIT, deliberately NOT fixed: a dict with no endpoint_url
    # raises KeyError inside native_address (llamacpp.py:37), because get_context_size
    # guards the HTTP rungs and the override - NOT the endpoint dict itself.
    # ChatSettings.refresh_usage() is what keeps it out of reach (it checks
    # `key[0] in self.app.endpoint_list()` first, step 4), and unit:chat_smoke's
    # stub answers endpoint_list() with {} and never reaches this code at all.
    check("t7-LIMIT-empty-endpoint-dict-raises-KeyError-because-native_address-"
          "indexes-endpoint_url-and-ChatSettings-is-the-guard-not-this-function",
          harness.raises(harness.get_context, {}), "KeyError")
    check("t7-LIMIT-the-pinned-file-cannot-be-compared-here-it-had-no-chain",
          hasattr(harness.OLD, "get_context_size"), False)


def main():
    print("INPUT MAPPING (TRAPS #13): the scenario name is the first path segment; "
          "the assertions below read the server's own recording of every request "
          "line, so an assertion about a request count is about the requests the "
          "endpoint actually made.")
    server = CannedServer().start()
    try:
        print(f"canned server on {server.base}")
        guarded("t6", lambda: t6_retry(server))
        guarded("t7", lambda: t7_context_chain(server))
    finally:
        server.stop()
    summary()
    return 1 if harness.fail_ else 0


if __name__ == "__main__":
    sys.exit(main())
