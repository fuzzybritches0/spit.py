#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t1, t5, t8, t9 - the OUTGOING request: what prepare_payload() builds, what
the skip list keeps out, what address the native routes hang off, and what
Authorization header goes with it.

Numbers are append-only across the whole suite (TRAPS #15): this file owns
t1 (payload), t5 (skip list), t8 (native_address), t9 (auth header). t2/t3/t4
are in test_stream_parse.py, t6/t7 in test_requests.py, t10 in
test_harvest_usage.py, t11 in test_counts_row.py.

TRAPS #8: every asserted string carries a distinctive `mm-*` token. TRAPS #13:
the skip-list check carries the control that makes it fail-able (a setting NOT
on the list DOES leak), and the t5/t9 comparisons against the OLD side are
preceded by `baseline_selfcheck()` so they can never compare the new code with
itself. TRAPS #15/#18: the old side is the pinned `b799526` file (see
endpoint_harness.py).

  t1  prepare_payload(): `stream_options` is EXACTLY {"include_usage": True};
      `stream` is True; the model, the system prompt and the reasoning-key
      rename still land; and the control that HEAD's payload had no
      stream_options at all.
  t5  the skip list: `context_size` NEVER appears - and a setting NOT on it,
      `n_ctx_control` 4242, DOES, in the same payload. The key SET is asserted,
      not the absence of one key. `temperature` is still forwarded and
      `parallel` is still skipped, exactly as the pinned file had them.
  t8  native_address(): strips a trailing /v1 once, leaves a URL without it
      alone, and equals work.py's blind [:-3] for every URL the app builds.
  t9  the auth header: key set -> `Bearer <key>`, key "" -> no header, key
      absent -> the same KeyError on both sides (HEAD's behaviour, unchanged).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import (CannedServer, NEW, baseline_endpoint,  # noqa: E402
                              baseline_selfcheck, check, guarded, md5,
                              saved_endpoint, summary, run_stream)
import endpoint_harness as harness  # noqa: E402


def build(address, extra=None, model_settings=None, prompt="", tools=None):
    """A NEW endpoint for prepare_payload() - no request is made."""
    return NEW([], saved_endpoint(address, **(extra or {})), "mm-model-1",
               model_settings or {}, prompt, tools or [], None)


def t1_prepare_payload():
    if not baseline_selfcheck("t1"):
        return
    endpoint = build("http://mm-host/v1", prompt="mm-system-prompt")
    payload = endpoint.prepare_payload()
    check("t1-stream_options-is-exactly-include-usage", payload.get("stream_options"),
          {"include_usage": True})
    check("t1-stream-is-true", payload.get("stream"), True)
    check("t1-model-lands", payload.get("model"), "mm-model-1")
    check("t1-system-prompt-lands", payload["messages"][0],
          {"role": "system", "content": "mm-system-prompt"})
    check("t1-key-set", sorted(payload.keys()),
          ["messages", "model", "stream", "stream_options", "timeout"])

    # the reasoning-key rename still lands: the message keeps its content, loses
    # "reasoning", gains the endpoint's configured key.
    messages = [{"role": "assistant", "content": [{"type": "text", "text": "mm-answer"}],
                 "reasoning": "mm-thoughts"}]
    endpoint = build("http://mm-host/v1",
                     extra={"reasoning_key": {"value": "mm_custom_reasoning", "stype": "string"}},
                     )
    endpoint.messages = messages
    payload = endpoint.prepare_payload()
    sent = payload["messages"][-1]
    check("t1-reasoning-renamed-to-the-endpoint-key", sent.get("mm_custom_reasoning"),
          "mm-thoughts")
    check("t1-plain-reasoning-key-not-sent", "reasoning" in sent, False)
    check("t1-messages-not-mutated-by-the-rename", messages[-1].get("reasoning"),
          "mm-thoughts")

    # the control (TRAPS #13): the pinned file sent no stream_options at all.
    old = baseline_endpoint()
    check("t1-CONTROL-old-had-no-stream_options", "stream_options" in old.prepare_payload(),
          False)
    check("t1-CONTROL-old-still-had-stream", old.prepare_payload().get("stream"), True)


def t5_skip_list():
    if not baseline_selfcheck("t5"):
        return
    extra = {"context_size": {"value": 8192, "stype": "uinteger"},
             "n_ctx_control": {"value": 4242, "stype": "uinteger"},
             "parallel": {"value": 0, "stype": "uinteger"}}
    model_settings = {"temperature": {"value": 0.7, "stype": "float"}}
    endpoint = build("http://mm-host/v1", extra=extra, model_settings=model_settings)
    payload = endpoint.prepare_payload()
    check("t5-context_size-never-forwarded", "context_size" in payload, False)
    check("t5-key-set-exactly", sorted(payload.keys()),
          ["messages", "model", "n_ctx_control", "stream", "stream_options",
           "temperature", "timeout"])
    # THE CONTROL (TRAPS #13): a setting that is NOT on the skip list leaks - in
    # the very same payload, through the same construct_payload() call. Without
    # this row "context_size is absent" would be about nothing.
    check("t5-CONTROL-off-list-setting-leaks-by-design", payload.get("n_ctx_control"), 4242)
    # temperature/parallel still behave exactly as HEAD had them.
    check("t5-temperature-still-forwarded", payload.get("temperature"), 0.7)
    check("t5-parallel-still-skipped", "parallel" in payload, False)
    check("t5-endpoint_url-still-skipped", "endpoint_url" in payload, False)
    check("t5-name-still-skipped", "name" in payload, False)

    # the pinned file: it had no skip-list entry, so context_size went out.
    # the same fixture through the pinned file: same saved endpoint, same
    # model_settings - the ONLY differences below are the two step-1 changes.
    old = harness.OLD_EP([], saved_endpoint("http://mm-host/v1", **extra),
                         "mm-model-1", model_settings, "", [], None)
    old_payload = old.prepare_payload()
    check("t5-CONTROL-old-forwarded-context_size", old_payload.get("context_size"), 8192)
    check("t5-CONTROL-old-skipped-parallel-too", "parallel" in old_payload, False)
    check("t5-CONTROL-old-off-list-setting-leaked-too", old_payload.get("n_ctx_control"), 4242)
    check("t5-the-only-payload-key-old-had-that-new-does-not",
          sorted(set(old_payload) - set(payload)), ["context_size"])
    check("t5-the-only-payload-key-new-has-that-old-did-not",
          sorted(set(payload) - set(old_payload)), ["stream_options"])

    # a DOTTED setting still reaches dot2obj, and context_size is not the only
    # entry on the list: save_cache_prompt stays out too.
    endpoint = build("http://mm-host/v1", extra={
        "save_cache_prompt": {"value": True, "stype": "boolean"},
        "cache-reuse.n": {"value": 5, "stype": "uinteger"}})
    payload = endpoint.prepare_payload()
    check("t5-save_cache_prompt-still-skipped", "save_cache_prompt" in payload, False)
    check("t5-dotted-setting-still-nested", payload.get("cache-reuse"), {"n": 5})


def t8_native_address():
    if not baseline_selfcheck("t8"):
        return
    check("t8-strips-a-trailing-v1", harness.new_mod.native_address(
        saved_endpoint("http://mm-host:8080/v1")), "http://mm-host:8080")
    check("t8-strips-it-ONCE", harness.new_mod.native_address(
        saved_endpoint("http://mm-host/v1/v1")), "http://mm-host/v1")
    check("t8-leaves-a-url-without-it-alone", harness.new_mod.native_address(
        saved_endpoint("http://mm-host:8080/api")), "http://mm-host:8080/api")
    check("t8-leaves-a-url-ending-in-v1-but-not-as-a-segment-alone",
          harness.new_mod.native_address(saved_endpoint("http://mm-host/v10")),
          "http://mm-host/v10")
    # equal to work.py's blind [:-3] for EVERY URL the app builds. The app
    # builds them in exactly two places (spit_app/llamacpp/server.py:60 for the
    # managed local server, manage/endpoint/endpoint.py NEW's default for a
    # saved one), plus the canned server below - all of them `<server>/v1`.
    app_built = ["http://127.0.0.1:8080/v1",       # NEW's default endpoint_url
                 "http://127.0.0.1:8081/v1",       # managed server, another port
                 "http://127.0.0.1:65000/v1",      # the range server.py picks
                 "https://mm.example.com/v1",      # a saved remote endpoint
                 ]
    for url in app_built:
        check(f"t8-equals-works-blind-slice[{url}]",
              harness.new_mod.native_address(saved_endpoint(url)), url[:-3])

    # DEVIATION D2 of step 1, pinned: for a URL the app does NOT build (no
    # trailing /v1) the two rules differ, and the new one is the one that does
    # not mangle the address.
    check("t8-D2-rule-differs-when-there-is-no-v1-and-new-is-the-safe-one",
          harness.new_mod.native_address(saved_endpoint("http://mm-host/api")),
          "http://mm-host/api")
    check("t8-D2-control-works-blind-slice-would-cut-it", "http://mm-host/api"[:-3],
          "http://mm-host/")
    check("t8-the-pinned-file-had-no-native_address-at-all",
          hasattr(harness.OLD, "native_address"), False)


def t9_auth_header(server):
    if not baseline_selfcheck("t9"):
        return
    address = f"{server.base}/echo-auth/v1"
    for label, key, want in (("set", "mm-sekret-1", "Bearer mm-sekret-1"),
                             ("empty", "", "<no-header>")):
        extra = {"key": {"value": key, "stype": "string"}}
        server.reset()
        new_endpoint, new_error = run_stream(NEW, address, extra=extra)
        check(f"t9-key-{label}-no-error", repr(new_error), "None")
        check(f"t9-key-{label}-header-sent-as-bearer",
              new_endpoint.messages[-1]["content"][0]["text"], want)
        check(f"t9-key-{label}-exactly-one-request-recorded", server.posts(),
              [f"POST /echo-auth/v1/chat/completions"])
        server.reset()
        old_endpoint, old_error = run_stream(harness.OLD_EP, address, extra=extra)
        check(f"t9-key-{label}-same-answer-from-the-pinned-side",
              old_endpoint.messages[-1]["content"][0]["text"], want)
        check(f"t9-key-{label}-pinned-side-one-request-too", len(server.posts()), 1)

    # the auth_headers() the new code extracted (D3) is the rule stream() used;
    # the absent key is HEAD's KeyError on BOTH sides - stream() indexes it.
    server.reset()
    new_error = run_stream(NEW, address, extra={"key": None})[1]
    old_error = run_stream(harness.OLD_EP, address, extra={"key": None})[1]
    check("t9-key-absent-raises-KeyError-new", type(new_error).__name__, "KeyError")
    check("t9-key-absent-raises-KeyError-old", type(old_error).__name__, "KeyError")
    check("t9-key-absent-same-exception-on-both-sides",
          type(new_error).__name__, type(old_error).__name__)
    check("t9-key-absent-no-request-was-made", len(server.posts()), 0)

    # get_context_size()/get_models() take the header from auth_headers(), which
    # tolerates an absent key - that is get_models' HEAD rule, unchanged.
    check("t9-auth_headers-key-set", harness.new_mod.auth_headers(
        saved_endpoint("http://mm-host/v1", key={"value": "mm-sekret-2", "stype": "string"})),
        {"Authorization": "Bearer mm-sekret-2"})
    check("t9-auth_headers-key-empty", harness.new_mod.auth_headers(
        saved_endpoint("http://mm-host/v1")), {})
    check("t9-auth_headers-key-absent-does-not-raise",
          harness.new_mod.auth_headers({"endpoint_url": {"value": "http://mm-host/v1"}}), {})


def main():
    print(describe())
    server = CannedServer().start()
    try:
        print(f"canned server on {server.base}")
        guarded("t1", t1_prepare_payload)
        guarded("t5", t5_skip_list)
        guarded("t8", t8_native_address)
        guarded("t9", lambda: t9_auth_header(server))
    finally:
        server.stop()
    summary()
    return 1 if harness.fail_ else 0


def describe() -> str:
    return ("INPUT MAPPING (TRAPS #13): t1/t5/t8 are pure request-building, no "
            "socket; t9 streams from POST <base>/echo-auth/v1, which replies "
            "with the Authorization header it was sent.\n"
            "OLD side: " + f"git show {harness.BASELINE_SHA}:{harness.BASELINE_FILE} "
            f"(md5 {md5(harness.OLD_SRC)}, expected {harness.BASELINE_MD5})")


if __name__ == "__main__":
    sys.exit(main())
