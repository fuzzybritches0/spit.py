#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t2, t3, t4 - the parse: every stream shape, replayed through the NEW code
and through the PINNED pre-step-1 code, with the reconstruction compared
byte-for-byte.

Numbers are append-only across the whole suite (TRAPS #15): this file owns
t2 / t3 / t4; t1, t5, t8, t9 are in test_payload.py, t6 / t7 in
test_requests.py, t10 in test_harvest_usage.py, t11 in test_counts_row.py.

  t2  EVERY shape: content deltas; reasoning deltas; tool_calls split across
      chunks (id/type/name/arguments, the SECOND argument fragment arriving
      alone); the old `finish_reason` chunk carrying usage with `choices`
      NON-empty (llama.cpp before PR #15444); the final `"choices": []` chunk
      carrying usage (OpenAI, llama.cpp since #15444); usage arriving in a
      MIDDLE empty-choices chunk (read-anywhere - what "no version detection"
      buys); a stream with no usage at all; `data:` lines with no space; junk
      lines between chunks; and a stream that is only `data: [DONE]`.
      Each shape runs through BOTH sides and the whole `messages` list is
      compared byte-for-byte (TRAPS #18). For the shapes the pinned side cannot
      parse at all - it carries an empty-`choices` chunk, which is the bug step
      1 removed - the byte-for-byte pair is NEW-with-the-usage-chunk against
      NEW on the companion stream WITHOUT it, and against what the old side
      managed before it died: that says the usage chunk contributes nothing to
      the reply on either code, and it cannot be green by comparing the new
      code with itself.
  t3  an empty-`choices` chunk raises NOTHING (the latent IndexError step 1
      removed), writes nothing, and does not eat the rest of the reply - and the
      pinned OLD side raises IndexError on the same object and dies mid-stream
      with the reply truncated. That control is what makes t3 a check and not a
      wish (TRAPS #13).
  t4  `self.usage` is reset at the start of every stream() (a second stream that
      says nothing must not repeat the first reply's numbers), holds the WHOLE
      usage object when it arrives, is REPLACED by a second stream's usage and
      never merged with the first. Control: the pinned side has no `usage`
      attribute at all, so a green here is about step 1's code.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (CannedServer, NEW, SHAPES, USAGE, OTHER_USAGE,  # noqa: E402
                              baseline_endpoint, baseline_selfcheck, check,
                              describe_shapes, dumps, guarded,
                              messages_with_tail, raises, reply_of, run_stream,
                              saved_endpoint, summary)
import endpoint_harness as harness  # noqa: E402

# The shapes t2 replays. Companions are reached THROUGH the entry of the shape
# they belong to; "flagless" and "echo-auth" belong to t6 and t9.
PLAYED = ("content", "reasoning", "toolcalls", "finishusage", "emptyusage",
          "midusage", "otherusage", "nousage", "nospace", "junk", "done")


def stream_again(endpoint, base, shape):
    """Re-point ONE endpoint object at another canned route and stream again -
    the only way to watch `self.usage` across two streams of one object."""
    endpoint.endpoint = saved_endpoint(f"{base}/{shape}/v1")
    endpoint.api_endpoint = endpoint.endpoint["endpoint_url"]["value"] + "/chat/completions"
    loop = asyncio.new_event_loop()
    error = None
    try:
        loop.run_until_complete(endpoint.stream())
    except Exception as exception:  # noqa: BLE001 - DATA, see the harness
        error = exception
    finally:
        loop.close()
    return error


def t2_every_shape(server):
    if not baseline_selfcheck("t2"):
        return
    print(describe_shapes())
    for name in PLAYED:
        shape = SHAPES[name]
        server.reset()
        new_endpoint, new_error = run_stream(NEW, f"{server.base}/{name}/v1")
        new_reply = reply_of(new_endpoint)

        # (1) the shape means what the table says on the code under test - the
        # reconstruction carries the distinctive tokens and nothing else moved.
        check(f"t2-{name}-new-no-error", repr(new_error), "None")
        check(f"t2-{name}-new-reconstruction", dumps(new_reply), dumps(shape["expect"]))
        check(f"t2-{name}-usage", dumps(getattr(new_endpoint, "usage", "MISSING")),
              dumps(shape["usage"]))
        check(f"t2-{name}-request-line", server.posts(),
              [f"POST /{name}/v1/chat/completions"])

        server.reset()
        old_endpoint, old_error = run_stream(harness.OLD_EP, f"{server.base}/{name}/v1")
        if shape["old_parses"]:
            # (2) the pair, byte-for-byte: NEW against the pinned file.
            check(f"t2-{name}-old-no-error", repr(old_error), "None")
            check(f"t2-{name}-identical-to-old", dumps(old_endpoint.messages),
                  dumps(new_endpoint.messages))
        else:
            # (2) the pinned side dies exactly where step 1 says it died ...
            check(f"t2-{name}-CONTROL-old-raises-IndexError-on-this-shape",
                  type(old_error).__name__, "IndexError")
            # ... and what it had rebuilt when it died is the truncated reply:
            # this pair is about a real difference, not two runs of one code.
            check(f"t2-{name}-CONTROL-old-died-after-this-much-text",
                  old_endpoint.messages[-1]["content"][0]["text"], shape["old_partial"])
            check(f"t2-{name}-CONTROL-old-had-no-usage",
                  getattr(old_endpoint, "usage", "<no attribute>"), "<no attribute>")
            # (3) and the usage chunk moved NOTHING in the reconstruction.
            companion, companion_error = run_stream(
                NEW, f"{server.base}/{shape['companion']}/v1")
            check(f"t2-{name}-byte-identical-without-the-usage-chunk",
                  dumps(companion.messages), dumps(new_endpoint.messages))
            check(f"t2-{name}-companion-runs-on-the-old-side-too",
                  repr(companion_error), "None")

        print(f"        {name:<17} {shape['what']}\n"
              f"          new: text={new_reply.get('content')!r} "
              f"reasoning={new_reply.get('reasoning')!r} "
              f"tool_calls={new_reply.get('tool_calls')!r} "
              f"usage={getattr(new_endpoint, 'usage', 'MISSING')!r}\n"
              f"          old: parses={shape['old_parses']} "
              f"error={type(old_error).__name__} "
              f"usage={getattr(old_endpoint, 'usage', '<no attribute>')!r}")

    # The split tool call asserted piece by piece, not only as a whole: the
    # second argument fragment arrives ALONE and must land on the first call.
    tool_endpoint, _error = run_stream(NEW, f"{server.base}/toolcalls/v1")
    calls = tool_endpoint.messages[-1]["tool_calls"]
    check("t2-toolcalls-id", calls[0]["id"], "call-mm-1")
    check("t2-toolcalls-type", calls[0]["type"], "function")
    check("t2-toolcalls-name", calls[0]["function"]["name"], "mm_read")
    check("t2-toolcalls-arguments-from-both-fragments",
          calls[0]["function"]["arguments"], harness.TOOL_ARGS_1 + harness.TOOL_ARGS_2)
    check("t2-toolcalls-still-one-call", len(calls), 1)
    check("t2-toolcalls-no-text-invented",
          tool_endpoint.messages[-1]["content"][0]["text"], "")


def t3_empty_choices(server):
    if not baseline_selfcheck("t3"):
        return
    new = NEW(messages_with_tail(), saved_endpoint(harness.DEAD_ADDRESS),
              "mm-model-1", {}, "", [], None)
    old = baseline_endpoint()

    # the guard, on the code under test: nothing raises ...
    for label, chunk in (("empty-with-usage", {"choices": [], "usage": USAGE}),
                         ("empty-bare", {"choices": []}),
                         ("choices-key-missing", {})):
        check(f"t3-new-{label}-raises-nothing", raises(new.extract_fields, chunk), "None")
    # ... and nothing is written: an empty-choices chunk must not touch the reply.
    check("t3-new-empty-choices-wrote-nothing", dumps(new.messages[-1]),
          dumps({"role": "assistant", "reasoning": "",
                 "content": [{"type": "text", "text": ""}]}))

    # THE CONTROL that makes the greens above evidence: the pinned side raises
    # on the very same objects.
    check("t3-CONTROL-old-empty-with-usage-raises-IndexError",
          raises(old.extract_fields, {"choices": [], "usage": USAGE}), "IndexError")
    check("t3-CONTROL-old-empty-bare-raises-IndexError",
          raises(old.extract_fields, {"choices": []}), "IndexError")
    check("t3-CONTROL-old-missing-choices-key-raises-KeyError",
          raises(old.extract_fields, {}), "KeyError")

    # End to end over a real stream: the new reply is whole and carries the
    # usage; the old one dies with the chunk it could not read.
    whole, whole_error = run_stream(NEW, f"{server.base}/emptyusage/v1")
    truncated, truncated_error = run_stream(harness.OLD_EP, f"{server.base}/emptyusage/v1")
    check("t3-new-stream-over-an-empty-choices-chunk-delivers-the-reply",
          whole.messages[-1]["content"][0]["text"], "mm-openai-shape")
    check("t3-new-stream-no-error", repr(whole_error), "None")
    check("t3-new-stream-appended-exactly-the-one-assistant-reply",
          len(whole.messages), 2)
    check("t3-CONTROL-old-stream-dies-on-the-same-route",
          type(truncated_error).__name__, "IndexError")
    # what the old side LOST is not the text (this usage chunk is last) but the
    # usage and the whole finish path: stream() raises, so maybe_callback(0) and
    # work.py's harvest never run, and work_stream re-raises it out of the chat.
    check("t3-CONTROL-old-stream-died-before-the-finish-with-the-usage-unread",
          (truncated.messages[-1]["content"][0]["text"],
           getattr(truncated, "usage", "<no attribute>")),
          ("mm-openai-shape", "<no attribute>"))

    # and the chunk in the MIDDLE: reading the usage does not eat what follows.
    middle, middle_error = run_stream(NEW, f"{server.base}/midusage/v1")
    check("t3-new-stream-continues-past-a-middle-empty-choices-chunk",
          middle.messages[-1]["content"][0]["text"], "mm-leftmm-right")
    check("t3-new-middle-stream-no-error", repr(middle_error), "None")


def t4_usage_reset(server):
    if not baseline_selfcheck("t4"):
        return
    endpoint, error = run_stream(NEW, f"{server.base}/finishusage/v1")
    check("t4-first-stream-no-error", repr(error), "None")
    check("t4-holds-the-whole-usage-object", dumps(endpoint.usage), dumps(USAGE))
    check("t4-the-whole-object-includes-the-details-key",
          endpoint.usage["prompt_tokens_details"]["cached_tokens"], 30)

    check("t4-second-stream-no-error",
          repr(stream_again(endpoint, server.base, "nousage")), "None")
    check("t4-reset-at-the-start-of-every-stream", dumps(endpoint.usage), dumps(None))

    stream_again(endpoint, server.base, "finishusage")
    check("t4-captured-again-on-the-next-stream", dumps(endpoint.usage), dumps(USAGE))

    stream_again(endpoint, server.base, "otherusage")
    check("t4-a-second-usage-REPLACES-it-and-never-merges", dumps(endpoint.usage),
          dumps(OTHER_USAGE))

    # the control: the pinned side never had the attribute, so what is asserted
    # above cannot be an accident of the constructor.
    check("t4-CONTROL-old-side-had-no-usage-attribute",
          getattr(baseline_endpoint(), "usage", "<no attribute>"), "<no attribute>")

    # and the read happens BEFORE anything touches choices: a chunk that is both
    # a usage chunk and an empty-choices chunk is where that order is observable.
    middle, _error = run_stream(NEW, f"{server.base}/midusage/v1")
    check("t4-usage-read-from-a-middle-empty-choices-chunk", dumps(middle.usage),
          dumps(USAGE))
    check("t4-reading-it-did-not-eat-the-reply",
          middle.messages[-1]["content"][0]["text"], "mm-leftmm-right")


def main():
    print("INPUT MAPPING (TRAPS #13): every shape is POSTed to by the fixture's own "
          "endpoint_url; the shape name IS the first path segment, so the recorded "
          "request line proves which canned body each side was served.")
    server = CannedServer().start()
    try:
        print(f"canned server on {server.base}")
        guarded("t2", lambda: t2_every_shape(server))
        guarded("t3", lambda: t3_empty_choices(server))
        guarded("t4", lambda: t4_usage_reset(server))
    finally:
        server.stop()
    summary()
    return 1 if harness.fail_ else 0


if __name__ == "__main__":
    sys.exit(main())
