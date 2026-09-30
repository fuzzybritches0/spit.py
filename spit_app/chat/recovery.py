# SPDX-License-Identifier: GPL-2.0
# P19/WP-4: the recovery. What happens when WP-2's retries are spent and the
# failure was one the app may yet grow into an answer for (DECISIONS 84 b/c):
# the work is carried on in a NEW chat built from this chat's settings, whose
# first message is a brief the app scaffolded from what it actually witnessed,
# and the chat that died says so IN-CHAT instead of pushing the modal that
# halted every chat in the app.
#
# WHY IT IS NOT THE `handoff` TOOL (DECISIONS 82 d). The tool is opt-in per
# chat, so a recovery that went through `ToolCall` would be missing exactly
# where it is needed most: a chat that never selected `handoff`, or that died
# on the request rather than in a tool loop. This module is called straight
# from `Work.report_failure` and touches no tool machinery.
#
# WHY IT IS IN-PROCESS AND ASYNC. It mounts widgets, it focuses, and it starts
# a worker: `create_and_submit` is the handoff's own sequence (P19/WP-1
# extracted it for this) and it belongs on the app's event loop. It is imported
# LOCALLY inside `Work.report_failure` and not at the top of `work.py`, because
# it reaches `chat.handoff` -> `chat.chat` -> Textual, and `work.py` has to stay
# importable by the bare-interpreter suite `unit:prompt` (TRAPS #19). Nothing
# here may pull anything that suite would have to stub.
#
# THE DEPTH CAP IS WHAT MAKES THIS SAFE TO RUN AT ALL. The new chat carries
# `recovered_from`, and a chat that already has it does NOT recover: it reports.
# Without that single test a dead endpoint would spawn one chat per failed
# request, forever, each inheriting the same dead endpoint.
from copy import deepcopy
from spit_app.chat.handoff import create_and_submit
from spit_app.chat.textual_message import StreamCallback
from spit_app.endpoints.llamacpp import get_models
from spit_app.tools.journal import effective_cap, journal_path, read_journal

# The brief is a message a fresh agent reads cold: enough of the transcript to
# know what the chat was DOING, never so much that it eats the window the
# recovery exists to have. Ten turns, four hundred characters each, newest last.
LAST_MESSAGES = 10
MESSAGE_CHARS = 400
TRUNCATED = " …[cut]"


def setting_text(chat, key: str) -> str:
    # `Chat.cs()` raises KeyError on a key the chat file never had, and a chat
    # file may predate any of these. Absent is an ordinary answer here, so this
    # reads the entry the way `cs()` does and answers "" for nothing.
    entry = chat.csettings.get(key)
    value = entry.get("value") if isinstance(entry, dict) else None
    return "" if value is None else str(value)


def message_text(message: dict) -> str:
    # The text a message carries, whatever shape its content is in: a plain
    # string, the multimodal list of parts, or nothing at all with the words
    # living in `tool_calls` instead.
    content = message.get("content")
    parts = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text") or ""))
    text = "\n".join(part for part in parts if part)
    if message.get("tool_calls"):
        names = ", ".join(call.get("function", {}).get("name", "?")
                          for call in message["tool_calls"])
        text = f"{text} [asked for tools: {names}]" if text else f"[asked for tools: {names}]"
    return text


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + TRUNCATED


def transcript(chat) -> str:
    # The last turns, oldest first, the newest at the bottom: the order a
    # reader of a conversation expects, and the order the recovery needs the
    # tail in. Note this is read AFTER `report_failure` posted the attempt's
    # rollback, so the corpse of the failed reply is not in it - the brief
    # describes the chat, not the wreckage.
    lines = []
    for message in chat.messages[-LAST_MESSAGES:]:
        lines.append(f"{message.get('role', '?')}: {clip(message_text(message), MESSAGE_CHARS)}")
    return "\n".join(lines) if lines else "(no messages)"


def journal_file(app, chat_id: str):
    # `journal_path` needs `settings.path["data"]`. An app without a data
    # directory has no journal, which is an ordinary answer and not a crash -
    # and the check is done HERE rather than by catching, because a recovery
    # that swallowed its own bugs would also swallow the ones that matter.
    path = getattr(getattr(app, "settings", None), "path", None)
    if not isinstance(path, dict) or "data" not in path:
        return None
    return journal_path(app, chat_id)


def journal_part(app, chat) -> str:
    # The journal rides the brief when the FILE exists and never otherwise:
    # `read_journal`'s answer for a chat that kept none is a paragraph addressed
    # to the agent who is writing one, and pasting that into a recovery brief
    # would tell the successor a journal exists and reads like that (DECISIONS
    # 85 e: the journal is an improvement on this brief, never its source).
    file = journal_file(app, chat.id)
    if file is None or not file.exists():
        return "No journal was kept for the chat this recovery came from."
    return read_journal(app, chat.id, effective_cap(app))


def recovery_brief(app, chat, exception: Exception, attempts: int) -> str:
    # The message the continuation chat opens with. Everything in it is a fact
    # the app holds: the id it is continuing from, the transcript path it can
    # read with `read_files`, the failure as the endpoint spelled it, how many
    # requests were asked for it, the token counts, the last turns, the journal.
    # Nothing is a summary of what the chat was about - the app was not there.
    usage = getattr(chat, "token_usage", {}) or {}
    lines = [
        "Recovery: a chat of this app died on an endpoint failure and this chat "
        "carries its work on.",
        "",
        f"Recovered from: `{chat.id}`",
        f"Transcript: `chats/{chat.id}.json` - read it with `read_files` for the "
        "whole conversation, not only the excerpt below.",
        f"Failure: {type(exception).__name__}: {exception}",
        f"Requests made for it: {attempts}",
        f"Token counts when it died: context {usage.get('context')}, "
        f"generated {usage.get('generated')}, cached {usage.get('cached')}",
        f"This chat inherited the dead chat's endpoint and model: "
        f"`{setting_text(chat, 'endpoint')}` / `{setting_text(chat, 'model')}`.",
        "",
        "The last messages of the chat it came from, oldest first:",
        transcript(chat),
        "",
        journal_part(app, chat),
        "",
        "Continue the work.",
    ]
    return "\n".join(lines)


def continuation_settings(chat) -> dict:
    # The dead chat's settings, whole, with exactly two differences (DECISIONS
    # 86 d): the sidebar says what this chat is, and `recovered_from` names the
    # chat it came from - which is BOTH the provenance a human can see and the
    # flag the depth cap reads. `ChatSettings.set_selects`/`update_models`
    # rewrite this file after the mount, so the shape of every inherited entry
    # is preserved and only `desc`'s value moves.
    settings = deepcopy(chat.csettings)
    desc = settings.get("desc")
    settings["desc"] = {"stype": "string", "empty": False, "desc": "Description"}
    settings["desc"].update(desc if isinstance(desc, dict) else {})
    settings["desc"]["value"] = f"Recovery: {setting_text(chat, 'desc')}"
    settings["recovered_from"] = {"value": chat.id, "stype": "string",
                                  "desc": "Recovered from"}
    return settings


def recovered_from(chat):
    entry = chat.csettings.get("recovered_from")
    return entry.get("value") if isinstance(entry, dict) else None


def can_recover(app) -> bool:
    # The manage surface the continuation chat has to be written through: a
    # settings home with a `chats` directory. An app that has none is not an app
    # that can hold a second chat, and answering False HERE - before the probe -
    # is what keeps the headless suites that drive `Work` on a bare `StubSettings`
    # on the report they have always got: no request spent probing, no sleep, no
    # message, no undo entry (DECISIONS 86 b).
    path = getattr(getattr(app, "settings", None), "path", None)
    return isinstance(path, dict) and "chats" in path


async def endpoint_answers(app, chat) -> bool:
    # The probe is the question the counts row already asks: `get_models` at its
    # own `timeout=3`, which answers [] on any failure at all (DECISIONS 84 b).
    # No new timeout plumbing, because there is nothing new to time out on.
    endpoint = app.get_endpoint(setting_text(chat, "endpoint"))
    return bool(await get_models(endpoint))


def post_notice(chat, text: str) -> None:
    # The in-chat notice of 84 c, appended through the ONE shape
    # `Chat.action_add_image` uses for a message the human did not type: append
    # the dict, write the history, post signal 1 (mount) and signal 0 (finish)
    # and let the ChatView's handlers do the mount through the sliding window.
    # The notice is therefore A MESSAGE: the window's invariant - the mounted
    # range is a slice of the data - holds without this module knowing anything
    # about windows, and the notice survives a reload. Its honest cost is in
    # DECISIONS 86 a: it rides the next request if a human continues that chat.
    # No `append_undo`: a notice is not an edit to undo, and signal 0's own
    # `message_finish` records the insert the way every other append is recorded.
    chat.messages.append({"role": "user", "content": [{"type": "text", "text": text}]})
    index = len(chat.messages) - 1
    chat.write_chat_history()
    chat.chat_view.post_message(StreamCallback(index, 1))
    chat.chat_view.post_message(StreamCallback(index, 0))


def notice_text(exception: Exception, attempts: int, new_id: str, submitted: bool) -> str:
    failure = f"{type(exception).__name__}: {exception}"
    head = f"Recovery: the endpoint failed after {attempts} request(s) - {failure}."
    if new_id is None:
        return (f"{head} This chat is itself a recovery from another chat, so the "
                "chain ends here: no further chat was created. The transcript is "
                "still on disk and can be continued by hand.")
    if submitted:
        return (f"{head} The work continues in the new chat `{new_id}`, which has "
                "this chat's settings and opens with a brief of what was happening.")
    return (f"{head} The endpoint did not answer, so nothing was sent: the new chat "
            f"`{new_id}` holds that brief as a DRAFT - send it when the server is up.")


async def continue_in_new_chat(app, chat, exception: Exception, attempts: int) -> tuple:
    # (the new chat's id or None, whether the brief was SUBMITTED). The probe
    # answer is carried out with the id because it is the ONE question asked of
    # the endpoint and the notice has to say which of the two things happened -
    # asking again would spend a second probe and could be answered differently.
    settings = continuation_settings(chat)
    brief = recovery_brief(app, chat, exception, attempts)
    submitted = await endpoint_answers(app, chat)
    # `create_and_submit` returns None only when the file could not be written.
    # A draft that could not be written is as useless as a submitted one, so the
    # same None means the same thing to the caller either way: no recovery.
    new_id = await create_and_submit(app, settings, brief, submit=submitted)
    return new_id, submitted


async def recover(chat, exception: Exception, attempts: int) -> bool:
    # Answers True when the failure was carried by the in-chat notice instead of
    # by the modal - which includes the depth cap, where the notice is all there
    # is. Answers False when recovery cannot run or did not happen, and the
    # caller reports the failure the way it always did. Raises on nothing it does
    # not intend: the caller's fallback is the safety net for the bugs this
    # module could have.
    app = chat.app
    if not can_recover(app):
        return False
    if recovered_from(chat):
        # Depth 1, and no further: the chat that is already the recovery for
        # another one reports, it does not recover again (alteration 2 of the
        # P19 entry). It still does not get the modal - the notice is the report.
        post_notice(chat, notice_text(exception, attempts, None, False))
        return True
    new_id, submitted = await continue_in_new_chat(app, chat, exception, attempts)
    if new_id is None:
        return False
    post_notice(chat, notice_text(exception, attempts, new_id, submitted))
    return True
