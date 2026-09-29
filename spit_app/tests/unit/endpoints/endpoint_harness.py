# SPDX-License-Identifier: GPL-2.0
"""Shared harness for unit:endpoints (imported by the test_*.py files; the
runner's glob deliberately does not match this name - the `stub_app.py` /
`window_harness.py` precedent: a harness file inside the `test_*.py` glob
becomes a suite file, and the runner would report its own import as a check file.

This is the FIFTH dependency-listed suite (TRAPS #19): `endpoints/llamacpp.py`
imports **httpx**, which the bare system python3 does not have, and the counts
row (t11) drives `chat_settings`, which pulls **Textual**. run_tests.sh probes
`import httpx, textual` and reports FAIL with the remedy when either is missing
- never a silent zero.

WHAT IS NOT HERE
  No live model, no port but 127.0.0.1, no fixture outside this directory, no
  tool import, no user data directory. Everything the endpoint talks to is the
  canned `http.server` below, bound to port 0 so it can never collide with a
  real llama.cpp endpoint, served from a daemon thread and shut down in the
  `finally` of the file that started it.

THE CANNED SERVER
  Scenario-by-path routing, one scenario per first path segment, the way
  /tmp/p12_check.py (the step-1 probe) built it - that probe works, so its
  routing is reused rather than reinvented. The endpoint fixture's
  `endpoint_url` is `<base>/<scenario>/v1` because the native routes hang off
  the URL MINUS the trailing /v1 (`native_address`, llamacpp.py:33-40), so the
  same scenario answers `POST /<scenario>/v1/chat/completions`,
  `GET /<scenario>/props` and `GET /<scenario>/slots`.

  Every request is recorded as its REQUEST LINE ("GET /props/props?model=x")
  and POST bodies are recorded too: `?model=<id>` is a behaviour and the retry
  checks COUNT requests, so those assertions read the recording, not the answer.

THE PINNED BASELINE (TRAPS #13 - the reason this file exists)
  The differential's OLD side is
  `git show b799526:spit_app/endpoints/llamacpp.py` - `b799526` is `a173854^`,
  the entry move, so it holds the file exactly as step 1 found it (and it is
  byte-identical to `main`'s bf55d39). It is exec'd into a module of its own
  from the git object: no temp file, so nothing can be silently overwritten
  between runs.

  WHY PIN BY SHA. The step-1 probe derived its OLD side from `git show HEAD:...`
  and rewrote /tmp/p12_old_llamacpp.py on every run - correct while step 1 was
  uncommitted, a lie after it was: re-run, it printed PASS: 47 FAIL: 3, the
  three reds being exactly the checks that ask the old side to be OLD, while
  its two "identical-to-old" reconstruction pairs stayed green VACUOUSLY,
  comparing the new code with itself, and printed the tidy row a lying probe
  always prints. So EVERY comparison against the old side in this suite is
  preceded by `baseline_selfcheck()`, which proves the old side is old (no
  stream_options, no get_context_size / native_address / auth_headers,
  `extract_fields` raises IndexError on "choices": [], bytes different from the
  current file). A differential that cannot fail is not evidence.

  And a differential half that CRASHES hides every red after it (DECISIONS 70),
  so nothing calls the old code except through `run_stream()` (an exception
  becomes a returned value) or `raises()` (an exception becomes its type name),
  and every group runs inside `guarded()`: a crash costs ONE red and the rest
  of the file still runs and still reports its own totals.
"""
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import threading
import traceback
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, *[".."] * 4))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from spit_app.endpoints import llamacpp as new_mod  # noqa: E402  (the code under test)

NEW = new_mod.LlamaCppEndpoint

# The address of a port that REFUSES. Measured 39 ms for the whole chain on this
# box, so the None-path checks cost nothing; a filtered address would cost 3 s
# each (both httpx timeouts are 3 s, llamacpp.py:44 and :57).
DEAD_ADDRESS = "http://127.0.0.1:9/v1"

# ----------------------------------------------------------------- the counters
pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def guarded(group: str, fn) -> None:
    """Run one check group. A crash is ONE red and a traceback on the terminal -
    never a file that dies mid-run and reports the counts of the checks that
    happened to come first (TESTING.md: the outer runner reads `tail -n 1`)."""
    try:
        fn()
    except Exception as exception:  # noqa: BLE001 - that is the whole point
        traceback.print_exc()
        check(f"{group}-did-not-crash", f"{type(exception).__name__}: {exception}", "None")


def summary() -> None:
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def dumps(obj) -> str:
    """Byte-for-byte comparison form: sorted keys, so dict order cannot lie."""
    return json.dumps(obj, sort_keys=True)


def raises(fn, *args, **kwargs) -> str:
    """The NAME of the exception `fn` raises, or "None". Every control that asks
    the old code to be broken reads this instead of letting it raise."""
    try:
        fn(*args, **kwargs)
    except BaseException as exception:  # noqa: BLE001 - the name is the answer
        return type(exception).__name__
    return "None"


# ------------------------------------------------------------- pinned OLD side
BASELINE_SHA = "b799526"           # = a173854^ : the entry move, pre-step-1 file
STEP1_SHA = "a173854"              # step 1, the commit that changed that file
MAIN_SHA = "bf55d39"               # main's copy: verified byte-identical
BASELINE_FILE = "spit_app/endpoints/llamacpp.py"
BASELINE_MD5 = "38858cde93e6066ce24e39a908cd0a6a"    # `git show b799526:...`


def git(*args) -> str:
    result = subprocess.run(["git", "-C", REPO, *args],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def _load_baseline():
    """The pinned file's source, exec'd into a module of its own (the
    p12_check.py way, minus the temp file that made that probe lie)."""
    src = git("show", f"{BASELINE_SHA}:{BASELINE_FILE}")
    module = types.ModuleType("p12_old_pre_step1")
    module.__file__ = f"{BASELINE_SHA}:{BASELINE_FILE}"
    sys.modules["p12_old_pre_step1"] = module
    exec(compile(src, module.__file__, "exec"), module.__dict__)
    return module, src


try:
    OLD, OLD_SRC = _load_baseline()
    OLD_EP = OLD.LlamaCppEndpoint          # the pre-step-1 class, for run_stream
    OLD_LOAD_ERROR = None
except Exception as exception:  # noqa: BLE001
    OLD, OLD_SRC, OLD_EP = None, "", None
    OLD_LOAD_ERROR = f"{type(exception).__name__}: {exception}"


def current_source() -> str:
    with open(os.path.join(REPO, BASELINE_FILE)) as file:
        return file.read()


def baseline_selfcheck(group: str) -> bool:
    """Prove the OLD side IS old before any "identical to old" row is believed.
    Every check carries the name of the group that depends on it, so a file
    whose baseline is broken reports its own reds instead of tidy greens."""
    if OLD is None:
        check(f"{group}-baseline-loads-from-{BASELINE_SHA}", OLD_LOAD_ERROR, "None")
        return False
    check(f"{group}-baseline-bytes-are-the-pinned-sha", md5(OLD_SRC), BASELINE_MD5)
    check(f"{group}-baseline-is-the-parent-of-step-1",
          git("rev-parse", "--short", f"{STEP1_SHA}^").strip(), BASELINE_SHA)
    check(f"{group}-baseline-is-byte-identical-to-main",
          md5(git("show", f"{MAIN_SHA}:{BASELINE_FILE}")), BASELINE_MD5)
    check(f"{group}-baseline-is-not-the-current-file",
          md5(OLD_SRC) == md5(current_source()), False)
    check(f"{group}-baseline-source-has-no-stream_options",
          "stream_options" in OLD_SRC, False)
    check(f"{group}-baseline-has-no-get_context_size", hasattr(OLD, "get_context_size"), False)
    check(f"{group}-baseline-has-no-native_address", hasattr(OLD, "native_address"), False)
    check(f"{group}-baseline-has-no-auth_headers", hasattr(OLD, "auth_headers"), False)
    check(f"{group}-baseline-extract_fields-raises-IndexError",
          raises(baseline_endpoint().extract_fields, {"choices": []}), "IndexError")
    return True


# ------------------------------------------------------------- endpoint fixture
def saved_endpoint(address: str, **extra) -> dict:
    """A SAVED endpoint, every field `{"value": ..., "stype": ...}`:
    construct_payload indexes settings[setting]["value"] and ["stype"]
    (llamacpp.py:147-163) and auth_headers indexes ["key"]["value"] (:27-31), so
    the raw `NEW` dict of manage/endpoint/endpoint.py raises KeyError for every
    setting that carries no default (step 3's probe note). `timeout` is NON-ZERO
    on purpose: 0 becomes `timeout=None` (llamacpp.py:136-138) and a hung
    request would then hang the suite.

    Pass `field=None` to remove a field entirely (the absent-key case), or a
    `{"value": ..., "stype": ...}` dict to add or replace one.
    """
    endpoint = {
        "name": {"value": "mm-one-endpoint", "stype": "string"},
        "endpoint_url": {"value": address, "stype": "string"},
        "key": {"value": "", "stype": "string"},
        "timeout": {"value": 5, "stype": "uinteger"},
        "reasoning_key": {"value": "reasoning_content", "stype": "string"},
        "context_size": {"value": 0, "stype": "uinteger"},
    }
    for field, entry in extra.items():
        if entry is None:
            endpoint.pop(field, None)
        else:
            endpoint[field] = entry
    return endpoint


def baseline_endpoint():
    """An OLD `LlamaCppEndpoint` on the same fixture shape, for the checks that
    call the pinned code directly (`extract_fields`). Built against a refused
    address: nothing it does can reach a live socket."""
    return OLD.LlamaCppEndpoint(messages_fixture(), saved_endpoint(DEAD_ADDRESS),
                                "mm-model-1", {}, "", [], None)


def blanked(entry: dict) -> dict:
    """The shape `store_values` leaves behind when a field is emptied: the key
    stays, `value` becomes None."""
    return {**entry, "value": None}


def messages_fixture() -> list:
    """The conversation handed to `LlamaCppEndpoint(messages, ...)`: one user
    turn, and NO assistant tail - stream() appends that itself, so a fixture
    that already carried one would make every reply-check off by a message."""
    return [{"role": "user", "content": [{"type": "text", "text": "mm-user-one"}]}]


def messages_with_tail() -> list:
    """The same conversation AFTER stream() appended the assistant message -
    the shape `extract_fields()` writes into, for the checks that call it
    directly instead of running a stream."""
    return messages_fixture() + [assistant()]


# --------------------------------------------------------------- stream runner
def run_stream(cls, address: str, extra: dict = None, model_settings: dict = None,
               prompt: str = "", tools: list = None, messages: list = None):
    """Build `cls` (NEW or the pinned OLD) and run one stream() on its OWN
    asyncio loop - httpx.AsyncClient binds to the loop it ran on, so one loop
    per case and `close()` in the `finally` (the p12_check.py way), with
    `shutdown_asyncgens()` BEFORE the close: `stream()` breaks out of
    `response.aiter_lines()` at `data: [DONE]`, and closing the loop with that
    async generator still alive prints `Task was destroyed but it is pending!`
    and a RuntimeWarning about `Response.aiter_text`'s `aclose` on stderr for
    every case that ends on the terminator - 958 bytes of it from this suite
    alone (measured), where every other suite in the repo writes nothing.

    Returns (endpoint, error) and NEVER raises: a differential half that dies
    mid-stream is DATA (DECISIONS 70), not a suite failure.
    """
    loop = asyncio.new_event_loop()
    endpoint = None
    error = None
    try:
        endpoint = cls(messages_fixture() if messages is None else messages,
                       saved_endpoint(address, **(extra or {})),
                       "mm-model-1", model_settings or {}, prompt, tools or [], None)
        loop.run_until_complete(endpoint.stream())
    except Exception as exception:  # noqa: BLE001 - see the docstring
        error = exception
    finally:
        try:                            # let httpx's async generators finish
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:               # noqa: BLE001 - the loop is going anyway
            pass
        loop.close()
    return endpoint, error


def reply_of(endpoint) -> dict:
    """The assistant message a stream produced, or the fact that there was none."""
    if endpoint is None:
        return {"__no_endpoint__": True}
    return endpoint.messages[-1]


def run_coro(coroutine):
    """One asyncio loop per case, closed in the `finally` (see run_stream)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:               # noqa: BLE001 - the loop is going anyway
            pass
        loop.close()


def get_context(endpoint: dict, model: str = None):
    """get_context_size() on its own loop (never the caller's: see run_stream)."""
    return run_coro(new_mod.get_context_size(endpoint, model))


# ------------------------------------------------------------ the canned bodies
USAGE = {"prompt_tokens": 41, "completion_tokens": 7, "total_tokens": 48,
         "prompt_tokens_details": {"cached_tokens": 30}}
OTHER_USAGE = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}


def chunk(text=None, reasoning=None, tool=None, finish=False, usage=None,
          choices=True) -> dict:
    delta = {}
    if text is not None:
        delta["content"] = text
    if reasoning is not None:
        delta["reasoning_content"] = reasoning
    if tool is not None:
        delta["tool_calls"] = tool
    choice = {"delta": delta}
    if finish:
        choice["finish_reason"] = "stop"
    body = {"choices": [choice] if choices else []}
    if usage:
        body["usage"] = usage
    return body


def sse(*chunks) -> bytes:
    """`data: {json}\n\n` per chunk, then `data: [DONE]\n\n`."""
    return ("".join("data: " + json.dumps(one) + "\n\n" for one in chunks)
            + "data: [DONE]\n\n").encode()


def sse_raw(*lines) -> bytes:
    """Hand-built lines, for the shapes whose SPELLING is the point."""
    return "".join(lines).encode()


def assistant(text: str = "", reasoning: str = "", tool_calls: list = None) -> dict:
    message = {"role": "assistant", "reasoning": reasoning,
               "content": [{"type": "text", "text": text}]}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return message


# One tool call's arguments, split into the two fragments the canned stream
# sends: the first arrives with id/type/name, the SECOND arrives alone.
TOOL_ARGS_1 = '{"path'
TOOL_ARGS_2 = '": "mm-file-one"}'
TOOL_CALL = [{"id": "call-mm-1", "type": "function",
              "function": {"name": "mm_read",
                           "arguments": TOOL_ARGS_1 + TOOL_ARGS_2}}]

# name -> the shape table. `body` is what the canned server writes for
# POST /<name>/v1/chat/completions; `expect` the assistant message it must
# reconstruct; `old_parses` whether the PINNED side can parse the shape at all
# (it cannot, by design, whenever a chunk carries "choices": []); `usage` what
# self.usage must hold afterwards; `companion` (for the shapes the old side
# dies on) the stream with the usage chunk taken out, whose reconstruction must
# be byte-identical to this one; `old_partial` how far the pinned side got
# before the empty-choices chunk killed its stream.
SHAPES = {
    "content": {
        "what": "three content deltas, no usage",
        "body": sse(chunk(text="mm-al"), chunk(text="pha-"), chunk(text="one")),
        "expect": assistant("mm-alpha-one"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "reasoning": {
        "what": "reasoning deltas then a content delta (extract_fields' elif ladder)",
        "body": sse(chunk(reasoning="mm-think-1"), chunk(reasoning="mm-think-2"),
                    chunk(text="mm-says")),
        "expect": assistant("mm-says", "mm-think-1mm-think-2"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "toolcalls": {
        "what": "tool_calls split across chunks: id/type/name + the FIRST argument "
                "fragment, then the SECOND argument fragment arriving ALONE",
        "body": sse(chunk(tool=[{"index": 0, "id": "call-mm-1", "type": "function",
                                 "function": {"name": "mm_read",
                                              "arguments": TOOL_ARGS_1}}]),
                    chunk(tool=[{"index": 0,
                                 "function": {"arguments": TOOL_ARGS_2}}],
                         finish=True)),
        "expect": assistant(tool_calls=TOOL_CALL),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "finishusage": {
        "what": "OLD llama.cpp: usage on the finish_reason chunk, choices NON-empty",
        "body": sse(chunk(text="mm-old-"), chunk(text="shape"),
                    chunk(text="", finish=True, usage=USAGE)),
        "expect": assistant("mm-old-shape"),
        "old_parses": True, "usage": USAGE, "companion": None, "old_partial": None,
    },
    "emptyusage": {
        "what": 'OpenAI / llama.cpp >= #15444: final chunk with "choices": [] carrying usage',
        "body": sse(chunk(text="mm-openai-"), chunk(text="shape"),
                    chunk(choices=False, usage=USAGE)),
        "expect": assistant("mm-openai-shape"),
        "old_parses": False, "usage": USAGE, "companion": "emptyusage-plain",
        # the usage chunk is LAST here, so the pinned side had already written
        # the whole text when it died: what it lost was the usage AND the
        # signal-0 finish (message_finish never ran) - not the text.
        "old_partial": "mm-openai-shape",
    },
    "emptyusage-plain": {
        "what": "companion of emptyusage: the same stream with the empty-choices "
                "usage chunk taken out - the read-anywhere rule must not move the text",
        "body": sse(chunk(text="mm-openai-"), chunk(text="shape")),
        "expect": assistant("mm-openai-shape"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "midusage": {
        "what": 'usage in an EMPTY-choices chunk in the MIDDLE of a reply '
                '(read-anywhere - this is what "no version detection" buys)',
        "body": sse(chunk(text="mm-left"), chunk(choices=False, usage=USAGE),
                    chunk(text="mm-right")),
        "expect": assistant("mm-leftmm-right"),
        "old_parses": False, "usage": USAGE, "companion": "midusage-plain",
        "old_partial": "mm-left",
    },
    "midusage-plain": {
        "what": "companion of midusage: the same deltas, no middle usage chunk",
        "body": sse(chunk(text="mm-left"), chunk(text="mm-right")),
        "expect": assistant("mm-leftmm-right"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "otherusage": {
        "what": "a SECOND, different usage object on an empty-choices chunk (t4: a "
                "second stream REPLACES the first usage, it never merges them)",
        "body": sse(chunk(text="mm-second-"), chunk(choices=False, usage=OTHER_USAGE)),
        "expect": assistant("mm-second-"),
        "old_parses": False, "usage": OTHER_USAGE, "companion": "otherusage-plain",
        "old_partial": "mm-second-",
    },
    "otherusage-plain": {
        "what": "companion of otherusage: the same delta, no usage chunk",
        "body": sse(chunk(text="mm-second-")),
        "expect": assistant("mm-second-"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "nousage": {
        "what": "a stream that says nothing about tokens",
        "body": sse(chunk(text="mm-no-usage"), chunk(text="", finish=True)),
        "expect": assistant("mm-no-usage"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "nospace": {
        "what": "`data:` lines with NO space after the colon",
        "body": sse_raw("data:" + json.dumps(chunk(text="mm-no-")) + "\n\n",
                        "data:" + json.dumps(chunk(text="space")) + "\n\n",
                        "data:[DONE]\n\n"),
        "expect": assistant("mm-no-space"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "junk": {
        "what": "junk between chunks: a blank line, a non-data line, a line that "
                "is not JSON at all, a data: line that is not JSON, then the chunks",
        "body": sse_raw("\n",
                        "hello, not an event\n",
                        "{not json at all}\n\n",
                        "data: still-not-json\n\n",
                        "data: " + json.dumps(chunk(text="mm-after-")) + "\n\n",
                        "data: " + json.dumps(chunk(text="junk")) + "\n\n",
                        "data: [DONE]\n\n"),
        "expect": assistant("mm-after-junk"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "done": {
        "what": "the stream is only the terminator: `data: [DONE]`",
        "body": sse_raw("data: [DONE]\n\n"),
        "expect": assistant(),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "flagless": {
        "what": "the reply of a server that refused stream_options (t6)",
        "body": sse(chunk(text="mm-noflag-reply")),
        "expect": assistant("mm-noflag-reply"),
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
    "echo-auth": {
        "what": "replies with the Authorization header it was sent (t9)",
        "body": None, "expect": None,
        "old_parses": True, "usage": None, "companion": None, "old_partial": None,
    },
}


# --------------------------------------------------------- canned server routes
# One scenario per first path segment, answering GET /<scenario>/props and
# GET /<scenario>/slots with (status, body). A str/bytes body is sent as it is,
# so a 200 that is NOT valid JSON is expressible; anything else is JSON-encoded.
SCENARIOS = {
    "props": {
        "props": (200, {"default_generation_settings": {"temperature": 0.8,
                                                        "n_ctx": 8192}}),
        "slots": (200, [{"id": 0, "n_ctx": 4096}]),
    },
    "props400": {
        "props": (400, {"error": {"message": "mm-unknown-model"}}),
        "slots": (200, [{"id": 0, "n_ctx": 4096}]),
    },
    "propsnone": {
        "props": (200, {"default_generation_settings": {"temperature": 0.8}}),
        "slots": (200, [{"id": 0}, {"id": 1, "n_ctx": 2048}]),
    },
    "slotjunk": {
        "props": (404, {"error": {"message": "mm-no-props"}}),
        "slots": (200, [{"id": 0, "n_ctx": 0}, {"id": 1, "n_ctx": "8192"},
                        {"id": 2, "n_ctx": -5}, {"id": 3, "n_ctx": 1024}]),
    },
    "propslist": {
        "props": (200, []),
        "slots": (200, [{"id": 0, "n_ctx": 512}]),
    },
    "garbage": {
        "props": (200, "this is {not json"),
        "slots": (200, "neither is {this"),
    },
    "nothing": {
        "props": (404, {"error": {"message": "mm-no-props"}}),
        "slots": (404, {"error": {"message": "mm-no-slots"}}),
    },
}


def post_reply(scenario: str, body: dict, headers, seen: int = 0) -> tuple:
    """(status, body, content-type) for one recorded POST.

    `seen` is how many POSTs this SAME scenario answered before this one (the
    canned server counts its own recording and passes it in), which is all a
    "fails first, works the second time" scenario needs - P19/WP-2's 503-then-200.
    It is derived from the request log rather than kept in a counter of its own,
    so `server.reset()` resets it exactly when it resets the log the counts are
    asserted on - a state a test cannot forget to clear is a state that cannot
    leak into the next check. 0 for every caller that does not care (all the
    scenarios that ever existed).
    """
    if scenario == "refuse-flag":
        if "stream_options" in body:
            return (400, {"error": {"message": "mm-refuses-stream_options"}},
                    "application/json")
        return (200, SHAPES["flagless"]["body"], "text/event-stream")
    if scenario == "refuse-always":
        return (403, {"error": {"message": "mm-denied-every-time"}}, "application/json")
    if scenario == "refuse-500":
        return (503, b"mm-unavailable", "text/plain")
    if scenario == "echo-auth":
        echo = headers.get("Authorization") or "<no-header>"
        return (200, sse(chunk(text=echo)), "text/event-stream")
    # ---- P19/WP-2 (t14): the failure CLASSES, one scenario each.
    if scenario == "refuse-400":
        # deterministic: a 4xx that is not 429 and says nothing about the window.
        return (400, {"error": {"message": "mm-bad-request-no-retry"}},
                "application/json")
    if scenario == "refuse-context":
        # the one deterministic refusal the app cannot answer for - named out of
        # the body text, the way a real llama.cpp/OpenAI server spells it.
        return (400, {"error": {"message": "mm-request: this model's context length "
                                           "is 4096; reduce the length of the input"}},
                "application/json")
    if scenario == "refuse-429":
        # transient by status, not by transport: the server is alive and says later.
        return (429, {"error": {"message": "mm-rate-limited-try-again"}},
                "application/json")
    if scenario == "flaky-503":
        if seen == 0:
            return (503, b"mm-unavailable-first-time", "text/plain")
        return (200, SHAPES["content"]["body"], "text/event-stream")
    if scenario == "stream-error":
        # accepted (200) and then the STREAM carries an `error` payload: the reply
        # half-exists when it dies, which is the corpse the rollback must take.
        return (200, sse(chunk(text="mm-before-the-error-"),
                         {"error": {"message": "mm-mid-stream-death",
                                    "type": "server_error", "code": 500}}),
                "text/event-stream")
    shape = SHAPES.get(scenario)
    if shape and shape["body"] is not None:
        return (200, shape["body"], "text/event-stream")
    return (404, {"error": {"message": f"mm-no-route {scenario}"}}, "application/json")


def scenario_of(path: str) -> str:
    return path.split("?")[0].strip("/").split("/")[0]


def model_of(path: str):
    return path.split("model=")[1].split("&")[0] if "model=" in path else None


class CannedServer:
    """The stdlib server: 127.0.0.1, port 0, daemon thread, shut down in the
    caller's `finally`. Records every request it saw as "METHOD /path?query"."""

    def __init__(self) -> None:
        self.lines = []
        self.bodies = []
        self.models = []
        self._server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self._server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> "CannedServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def reset(self) -> None:
        self.lines.clear()
        self.bodies.clear()
        self.models.clear()

    def posts(self) -> list:
        return [line for line in self.lines if line.startswith("POST ")]

    def gets(self) -> list:
        return [line for line in self.lines if line.startswith("GET ")]

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                pass

            def _send(self, code: int, body, ctype: str = "application/json") -> None:
                if isinstance(body, bytes):
                    raw = body
                elif isinstance(body, str):
                    raw = body.encode()
                else:
                    raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                self.wfile.flush()

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw or b"{}")
                except json.JSONDecodeError:
                    body = {"__not-json__": raw.decode("utf-8", "replace")}
                outer.lines.append(f"POST {self.path}")
                outer.bodies.append(body)
                # `seen` counts the POSTs this scenario answered BEFORE this one,
                # read out of the recording (so `reset()` clears it with it) - the
                # one bit of state the "503 first, 200 after" scenario needs.
                scenario = scenario_of(self.path)
                seen = sum(1 for line in outer.lines[:-1]
                           if line.startswith("POST ")
                           and scenario_of(line[len("POST "):]) == scenario)
                code, payload, ctype = post_reply(scenario, body, self.headers, seen)
                self._send(code, payload, ctype)

            def do_GET(self) -> None:
                outer.lines.append(f"GET {self.path}")
                route = self.path.split("?")[0]
                entry = SCENARIOS.get(scenario_of(self.path), {})
                if route.endswith("/props"):
                    outer.models.append(model_of(self.path))
                    status, body = entry.get("props", (404, {"error": {"message": "mm-no-props"}}))
                    self._send(status, body)
                    return
                if route.endswith("/slots"):
                    status, body = entry.get("slots", (404, {"error": {"message": "mm-no-slots"}}))
                    self._send(status, body)
                    return
                self._send(404, {"error": {"message": f"mm-no-route {route}"}})

        return Handler


def describe_shapes() -> str:
    """The differential's INPUT MAPPING, printed before it runs (TRAPS #13):
    shape -> route -> what it carries -> whether the pinned old side can parse
    it -> what it is compared against."""
    lines = ["shape -> POST /<shape>/v1/chat/completions (canned SSE body below)",
             describe_baseline()]
    for name, shape in SHAPES.items():
        if name == "echo-auth":
            continue
        lines.append(f"  {name:<17} old-parses={str(shape['old_parses']):<5} "
                     f"compare={'the pinned run itself' if shape['old_parses'] else 'companion:' + shape['companion']}  "
                     f"{shape['what']}")
    return "\n".join(lines)


def describe_context_scenarios() -> str:
    """The INPUT MAPPING of the t7 chain: which rung each scenario answers and
    which one it is built to miss."""
    lines = ["get_context_size chain: /props -> first /slots with a positive int "
             "n_ctx -> endpoint context_size > 0 -> None",
             describe_baseline(),
             "  scenario     /props                     /slots"]
    for name, routes in SCENARIOS.items():
        lines.append(f"  {name:<12} {routes['props'][0]:<23} {routes['slots'][0]}")
    lines.append(f"  (refused)    {DEAD_ADDRESS}  (nothing listens; refused, 39 ms)")
    return "\n".join(lines)


def describe_baseline() -> str:
    return (f"OLD side: git show {BASELINE_SHA}:{BASELINE_FILE} "
            f"(md5 {BASELINE_MD5}; parent of step 1 {STEP1_SHA}; byte-identical "
            f"to main's {MAIN_SHA})")
