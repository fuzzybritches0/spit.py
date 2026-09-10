# SPDX-License-Identifier: GPL-2.0
import os
from collections import namedtuple

import libtmux

from .common import CommonMixIn

# The tmux server this spit.py process owns, named after its pid. A bare
# `libtmux.Server()` means the DEFAULT socket (/tmp/tmux-1000/default), and on
# that socket we would (a) create our windows among the user's own sessions,
# where a name that collides with one of theirs gets typed into by us, and
# (b) run `kill-server` there when the app quits: actions.py action_exit_app
# calls `self.tmux[chat_id]["server"].kill()`, and libtmux Server.kill() is
# literally `tmux kill-server` -- so quitting the app would have taken down
# every session of the user's tmux. The pid keeps it ours alone: two spit.py
# processes never share a server, and one process with five chats has five
# sessions in one server rather than five servers.
def server_socket() -> str:
    return f"spit-{os.getpid()}"

KEYS = ["Up", "Down", "Left", "Right", "Space", "Tab", "Delete", "End", "Enter", "Escape", "Esc", "F1",
        "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10" , "F11", "F12", "Home", "Insert", "PageDown",
        "PgDn", "PgUp", "PageUp"]
MODS = ["C-", "S-", "M-"]

# --------------------------------------------------------------------------------------
# The state layer: what tmux said, once, on the way to this call.
#
# The registry used to hold libtmux OBJECTS and the tools asked them questions.
# Objects lie. Measured on tmux 3.7b / libtmux 0.62: a cached `Pane` still read
# `pane_dead == '0'` after its shell had exited, and after a `respawn-window` the
# SAME `pane_id` belonged to a different pid; a cached `Window` went on reporting
# the name it had before somebody renamed it from outside. Membership
# (`window in session.windows`) is the one thing that cannot lie, because libtmux
# compares `window_id` and a window id is never reused -- and that is also why a
# window INDEX is a loaded gun: kill index 2 and the next window is index 2 again,
# with a different id.
#
# So `app.tmux[chat_id]` holds strings: the window name -> the `window_id` tmux
# gave it, plus the session and server those ids belong to. Every question is
# answered from ONE listing taken per call, and libtmux Pane/Window objects are
# built from ids, on demand, for the only three things they are good at: capture,
# send_keys, kill.
#
# The cost is the other half of the reason. One `term_screen()` built out of
# objects was 6 `tmux` invocations -- 3 of them libtmux's own ~100-field
# list-sessions/list-windows/list-panes -- for 45 ms, and the cursor splice was 2
# more `display-message` calls on top. ONE `list-panes -a` answers liveness, exit
# status, geometry and cursor for EVERY window of EVERY chat of the process in
# 7 ms (measured 4.9-7 ms with the format below; the ~125-field format libtmux
# would use for the same listing costs 12 ms, so asking only for what is read is
# worth a third of it).
#
# `pane_current_command` is the one value here that can contain arbitrary text --
# a process name is not a fixed alphabet -- so it is LAST and the line is split
# with a maxsplit: a stray separator can land only in the last field, never shift
# the twelve in front of it. `pid`/`start_time` are the SERVER's (tmux expands the
# format itself, so they name the daemon that answered, not this Python process --
# measured: pid 11 from a process whose own pid was 6); see Snapshot.
LISTING_SEPARATOR = "\x1f"
LISTING_TOKENS = ("pid", "start_time", "session_id", "window_id", "pane_id",
                  "pane_dead", "pane_dead_status", "pane_pid", "pane_width",
                  "pane_height", "cursor_x", "cursor_y", "pane_current_command")
PaneState = namedtuple("PaneState", " ".join(LISTING_TOKENS))
LISTING_FORMAT = LISTING_SEPARATOR.join("#{" + token + "}" for token in LISTING_TOKENS)

class Snapshot:
    """Every pane on the server, from ONE `list-panes -a`, keyed by `window_id`.

    A window's FIRST pane is the row kept, which is the pane the tools have always
    used (`window.panes[0]`); nothing here splits a window.

    `stamp` is the server's own identity as tmux reported it in that same listing:
    its pid and its start time. It is not decoration. A tmux server numbers from
    zero again when it starts, so after ours died the next session is `$0` and the
    window after it is `@1` (measured twice on this box). A name our registry kept
    from a dead server can therefore carry an id that belongs, on the new server,
    to ANOTHER CHAT's live window -- and without this stamp the capture of that
    name would read the other chat's screen and the send would type into it. A
    snapshot whose stamp is not the chat's answers "nothing" for every name, which
    is the truth: whatever that chat held died with that server.
    """

    def __init__(self, rows: dict, stamp):
        self.rows = rows
        self.stamp = stamp

    def is_the_server_of(self, chat: dict) -> bool:
        return self.stamp is not None and self.stamp == chat.get("stamp")

    def state_of(self, window_id):
        return self.rows.get(window_id)

    def holds_session(self, session) -> bool:
        """Does the server in this snapshot still have that session?

        A tmux session with no window cannot exist, so the pane listing answers
        this for every session at once -- which is how `retire()` can ask whether
        killing a window took the session with it without a second kind of listing.
        """
        return session is not None and any(
            state.session_id == session.session_id for state in self.rows.values())

def server_is_down(stderr: str) -> bool:
    """tmux's own two ways of saying there is nobody to ask (both measured here):
    `no server running on <socket>` when the socket file is left behind, and
    `error connecting to ... (No such file or directory)` when even that is gone."""
    return "no server running" in stderr or "error connecting to" in stderr

def pane_snapshot(server) -> Snapshot:
    """ONE `tmux list-panes -a`, asked through the chat's Server object so the
    socket stays the one libtmux was given (and the one the test suite forces)."""
    listing = server.cmd("list-panes", "-a", "-F" + LISTING_FORMAT)
    if listing.stderr:
        text = " ".join(str(line) for line in listing.stderr)
        # "no server running" is not a failure to answer: the answer is that
        # everything this process owned is gone, so an empty snapshot IS the truth
        # and every name reads as dead. Any OTHER complaint from tmux is not an
        # answer at all, and reading it as one would forget every live session in
        # the chat and destroy their windows -- the one mistake this layer must not
        # make. So it raises, and the caller says "tmux said: ..." instead of
        # pretending it knows.
        if server_is_down(text):
            return Snapshot({}, None)
        raise libtmux.exc.LibTmuxException(text)
    rows = {}
    stamp = None
    for line in listing.stdout:
        values = line.split(LISTING_SEPARATOR, len(LISTING_TOKENS) - 1)
        if len(values) != len(LISTING_TOKENS):
            continue        # not our format (a tmux too old for a token): no row
        state = PaneState(*values)
        stamp = (state.pid, state.start_time)
        if state.window_id and state.pane_id:
            rows.setdefault(state.window_id, state)   # the window's first pane
    return Snapshot(rows, stamp)

def pane_is_dead(state) -> bool:
    """Has this pane's process exited? '1' once it has, '0' while it runs.

    The one place that meaning is written (decision 67): `terminal` and `lsterm`
    both read liveness through here, and both read it from a snapshot row rather
    than from a cached object, because a cached object is the thing measured lying
    about it. tmux keeps the exit status of a retained pane in `pane_dead_status`
    and, on tmux >= 3.3, `pane_dead_signal` and `pane_dead_time`; a live screen can
    carry `pane_current_command`, `pane_pid` and the geometry from the same row, at
    no extra cost.
    """
    return state is not None and state.pane_dead == "1"

def window_is_ours(chat: dict, window_id, snapshot: Snapshot) -> bool:
    """Is `window_id` a window of THIS chat's session, on the server the snapshot
    came from? Both halves are load-bearing -- see Snapshot."""
    if not snapshot.is_the_server_of(chat):
        return False
    session = chat.get("session")
    if session is None:
        return False
    state = snapshot.state_of(window_id)
    return state is not None and state.session_id == session.session_id

def window_state(chat: dict, name: str, snapshot: Snapshot):
    """What tmux says about the window registered under `name`: its PaneState, or
    None when there is nothing to say -- the name is not registered, tmux no longer
    has that window, or the id belongs to a server that is not this chat's.

    This is the read that replaces asking a cached object, and it is the whole
    difference between "the tool forgot" and "the process exited". It is also
    deliberately non-mutating: deciding what to do about a death belongs to
    `pane_active()`, not to a read that a listing or a capture happens to call.
    """
    window_id = chat.get("windows", {}).get(name)
    if window_id is None:
        return None
    return snapshot.state_of(window_id) if window_is_ours(chat, window_id, snapshot) else None

# How far a dead session's report reaches above the visible screen, in lines. The
# number is measured, not stylistic: tmux writes its `Pane is dead (status N, ...)`
# notice INTO the pane, and that scrolls the grid up by one line -- so a
# visible-only capture of a corpse is missing the first line of everything it
# printed, and for a session that printed one line it is missing EVERYTHING.
# Measured on tmux 3.7b with 1/2/3/10 lines printed: the visible capture lost
# exactly LINE-1 in every case; capture(start="-50") had all of them. The same
# number caps the report: the history can be 2000 lines and a dead session's
# report must not dump that into the model's context.
DEAD_REPORT_HISTORY = "50"

def pane_of_id(server, pane_id):
    """A libtmux Pane for an id from the snapshot, for capturing or sending.

    Built from the id ALONE -- no lookup, so no tmux call -- and never READ from,
    because a field read off a cached object is a field that can be stale
    (decision 69(c)). `Pane.from_pane_id()` lists the whole server to build the
    same object, which is exactly what this layer exists to stop paying.
    """
    return libtmux.Pane(server=server, pane_id=pane_id)

def window_of_id(server, window_id):
    """The same, for the one thing a window is ever asked here: to be killed."""
    return libtmux.Window(server=server, window_id=window_id)

def dead_report_text(server, name: str, state) -> str|None:
    """The report for a retained corpse: its real final screen and exit status.

    None when nothing can be read from it (gone between the listing and this
    capture), which is the caller's cue to fall back to the cached screen.

    The exit status is the snapshot's `pane_dead_status`; it is empty for a death
    by signal, hence the guard, so a SIGKILLed shell does not report "Exit status:
    .". tmux's own `Pane is dead (status N, ...)` line is part of the captured
    screen and says the same thing in tmux's words, which is what a test asserts
    the code from rather than this prose.
    """
    try:
        lines = pane_of_id(server, state.pane_id).capture_pane(
            start=f"-{DEAD_REPORT_HISTORY}",
            preserve_trailing=True, join_wrapped=True)
    except libtmux.exc.LibTmuxException:
        return None
    status = state.pane_dead_status
    notice = "\n\nINFO: Session dead."
    if status not in (None, ""):
        notice += f" Exit status: {status}."
    # The notice is part of what is CACHED, not only of what is returned: the cache
    # holds what the tool last reported, so a repeat call says the same thing --
    # including the exit status, which the captured screen alone does not carry.
    # It is the dead rendering, with no cursor marker: a dead pane has no cursor,
    # and decision 66's marker is a live-screen affordance.
    return f"Session: {name}\n\n" + "\n".join(lines) + notice

def no_such_session_message(name: str) -> str:
    """The answer for a name this chat has never had, which is NOT "it died".

    The dead-session sentence used to cover this too and told the model an event
    that never happened -- and a reported death is something a model acts on, so it
    went looking for the crash of a session that was never a session. "No such
    session" and "session dead" are two answers now. A name that WAS ours keeps
    answering from the cache: `retire()` drops the name and keeps what was
    reported, and a repeat call repeats that (exit status included) rather than
    announcing a name that never existed.
    """
    return (f"Session: {name}\n\n"
            f"INFO: No such session. Nothing is registered under that name in this "
            f"chat, so there is no screen to report. Send input to that name to "
            f"start one.")

def retire(tmux: dict, chat_id: str, name: str, snapshot: Snapshot = None) -> None:
    """A dead name stops existing, in tmux and in the registry, here.

    DECISION, and the reason is the alternative. A retained window is destroyed by
    nothing else: measured, three chats and one death left 5 windows in the session
    and after the name was reused, 6, one of them an abandoned
    `sandbox_env.sh[dead]` -- and once the name is forgotten the registry has no
    handle on it, so forgetting makes a corpse unreachable, not gone. tmux keeps it
    for the whole run of the app, because the only other tmux teardown is actions.py
    at exit. So a corpse is destroyed at the moment somebody has established it is
    dead, and after that report has been taken.

    The kill goes by the id in the registry, and ONLY after a listing says that id
    is a window of this chat's session on this server: an id kept from a dead server
    can name another chat's live window (tmux numbers a new server from zero again),
    and destroying that would be the exact defect this file exists to remove,
    pointed at a fellow chat instead of at the user.

    The catch, measured: killing a corpse is harmless while the session still has
    another window, but killing the LAST window destroys the session, and when ours
    was the server's only session the server went with it -- leaving every later
    call indexing a `chat["session"]` that no longer exists. Since the window tmux
    creates along with every session is now destroyed instead of left behind to
    hold it open, that is the NORMAL path: a chat whose last terminal was reported
    has no session left. So check afterwards -- with the listing, because the
    listing is the only thing that knows -- and rebuild the chat entry when that
    happened, keeping the screen cache AND the Server object. The cache, because
    what was reported is still what was reported; the Server object, because
    `new_session()` on the same one starts the server again on the same socket, and
    actions.py's exit path reads `chat["server"]` unguarded, so the key has to
    still be there.
    """
    chat = tmux.get(chat_id) or {}
    server = chat.get("server")
    window_id = chat.get("windows", {}).get(name)
    chat.get("windows", {}).pop(name, None)
    if server is None or window_id is None:
        return
    if snapshot is None:
        snapshot = pane_snapshot(server)
    if window_is_ours(chat, window_id, snapshot):
        try:
            window_of_id(server, window_id).kill()
        except libtmux.exc.LibTmuxException:
            pass        # gone between the listing and the kill: nothing to destroy
        snapshot = pane_snapshot(server)   # that kill may have taken the session
    session = chat.get("session")
    if session is None or snapshot.holds_session(session):
        return
    tmux[chat_id] = {"server": server, "session": None, "stamp": None,
                     "windows": {}, "last_screen": chat.get("last_screen", {})}

def session_is_live(server, session) -> bool:
    """Does tmux still hold that session? One listing answers it for every chat."""
    return pane_snapshot(server).holds_session(session)

def pane_active(tmux: dict, chat_id: str, name: str, snapshot: Snapshot = None) -> bool:
    # One liveness rule, shared by `terminal` and `lsterm` since c948b3e. It used to
    # be "is the window still in the session", which was right only while tmux
    # destroyed a window when its shell exited. With `remain-on-exit` on the window
    # (term_new sets it) tmux KEEPS it, so membership now answers "is there still a
    # corpse" and would call a dead session live (measured: the retained window is
    # still in session.windows while its pane_dead is '1'). Liveness is pane_dead --
    # read from this call's snapshot, never from a cached object, which was measured
    # still reading '0' after the shell was gone.
    #
    # Discovering a death here also REPORTS and DESTROYS it, which matters more than
    # it looks: `lsterm` is the tool the model is told to call first, so the listing
    # is often the only thing that ever sees the death. Forget the name without
    # harvesting and the evidence goes unread and the corpse stays unreachable.
    chat = tmux.get(chat_id)
    if not chat:
        return False
    windows = chat.get("windows", {})
    if not name in windows:
        return False
    if chat.get("server") is None:
        return False
    if snapshot is None:
        snapshot = pane_snapshot(chat["server"])
    state = window_state(chat, name, snapshot)
    if state is not None and not pane_is_dead(state):
        return True
    if state is not None:
        report = dead_report_text(chat["server"], name, state)
        if report is not None:
            chat.setdefault("last_screen", {})[name] = report
    retire(tmux, chat_id, name, snapshot)
    return False

def live_window_names(tmux: dict, chat_id: str) -> list:
    # The names are snapshotted first: pane_active() drops a dead window from the
    # very dict a listing loop walks, and a dict that changes size mid-iteration
    # raises RuntimeError out of what is supposed to be a read-only listing.
    chat = tmux.get(chat_id) or {}
    names = list(chat.get("windows", {}))
    if not names or chat.get("server") is None:
        return []
    # ONE listing for the whole listing: pane_active() takes it as an argument, so
    # checking five terminals is one `tmux` round-trip and not the two per window
    # (list-windows, then a list-panes for each) that the object layer paid.
    snapshot = pane_snapshot(chat["server"])
    return [name for name in names if pane_active(tmux, chat_id, name, snapshot)]

def cursor_of(state):
    """The cursor as (x, y), or (-1, -1) when tmux did not say.

    -1/-1 renders a live screen with NO marker, deliberately. The old code
    reported the session DEAD when it could not read a cursor, because that cursor
    came from a `display-message` whose only way to fail is a pane that is already
    gone. Here the cursor comes from the same listing that has just said the pane
    is alive, so a missing cursor is a missing cursor and not a death: inventing a
    death would forget a live window's name and destroy a live window.
    """
    try:
        return int(state.cursor_x), int(state.cursor_y)
    except (TypeError, ValueError):
        return -1, -1

class Terminal(CommonMixIn):
    def __init__(self, app, chat_id: str, sandbox: bool = True) -> None:
        super().__init__(app, sandbox, chat_id)
        self.tmux = app.tmux

    def chat_state(self) -> dict:
        return self.tmux.get(self.chat_id, {})

    def server(self):
        return self.chat_state().get("server")

    def snapshot(self) -> Snapshot:
        """This call's view of tmux: ONE `list-panes -a`, and no `tmux` call at all
        for a chat that has no server yet -- there is nothing of ours to list, and
        asking would be asking the user's default socket."""
        server = self.server()
        return pane_snapshot(server) if server is not None else Snapshot({}, None)

    def window_state(self, name: str, snapshot: Snapshot = None):
        if snapshot is None:
            snapshot = self.snapshot()
        return window_state(self.chat_state(), name, snapshot)

    def last_screen(self, name: str) -> str:
        return self.chat_state().get("last_screen", {}).get(name, "")

    def remember_screen(self, name: str, screen: str) -> None:
        self.chat_state().setdefault("last_screen", {})[name] = screen

    def forget_screen(self, name: str) -> None:
        self.chat_state().get("last_screen", {}).pop(name, None)

    def dead_session_message(self, name: str) -> str:
        last_screen = self.last_screen(name)
        if not last_screen:
            return f"Session: {name}\n\nINFO: Session dead. It closed before anything was captured from it."
        # A cache entry written by dead_report() already carries the notice (and the
        # exit status, which the captured screen alone does not): the cache holds
        # what the tool LAST REPORTED, so a repeat call says exactly the same thing
        # instead of appending a second notice to the first.
        if "INFO: Session dead." in last_screen:
            return last_screen
        return f"{last_screen}\n\nINFO: Session dead."

    def unreached_screen(self, name: str) -> str:
        """What a capture answers for a name with no pane to read.

        Nothing cached under it means this chat has never had that name at all, and
        the answer is "no such session" -- not a death that never happened.
        Something cached means the name WAS ours: `retire()` drops the name and
        keeps what was reported, so a repeat call repeats the report (decision 69 d)
        instead of announcing a name that never existed.
        """
        if not self.last_screen(name):
            return no_such_session_message(name)
        return self.dead_session_message(name)

    def dead_report(self, name: str, state, snapshot: Snapshot = None) -> str:
        """What a dead session answers with.

        A pane tmux retained (`remain-on-exit`, which term_new sets on the window)
        still holds the session's REAL final screen and its exit status, so both are
        reported verbatim: a session that died after printing a traceback and one
        that printed nothing no longer look alike, and the answer is no longer
        limited to the last screen WE happened to capture. With nothing to read --
        the window was destroyed, or it died before this option existed, or the id
        belongs to a server that has gone -- fall back to the cached screen and the
        wording that has always been used for it.

        dead_report_text() and retire() do the work, because discovering a death in
        pane_active() -- inside `lsterm`, the tool the model is told to call first --
        has to report and destroy it exactly the same way. Two implementations is how
        one of them stops harvesting the evidence.
        """
        if state is None:
            # Nothing to read: the shell exited without the option, somebody
            # destroyed the window from outside, or our server died and took it.
            # This is the path that used to report the death and LEAVE the entry in
            # the registry, naming a window nothing would ever list again.
            message = self.dead_session_message(name)
            self.remember_screen(name, message)
            self.forget_window(name)
            return message
        report = dead_report_text(self.server(), name, state)
        if report is None:
            # gone between the listing and the capture: cache fallback, and it
            # is still dead, so it still goes
            retire(self.tmux, self.chat_id, name, snapshot)
            return self.dead_session_message(name)
        self.remember_screen(name, report)
        retire(self.tmux, self.chat_id, name, snapshot)
        return report

    def forget_window(self, name: str) -> None:
        # Drop a name from the registry only: the listing stops reporting it and the
        # name becomes reusable. The screen cache stays -- it is the fallback for
        # every later call once there is nothing left to read. Anything that must
        # also destroy the window calls retire().
        self.chat_state().get("windows", {}).pop(name, None)

    def ensure_session(self) -> dict:
        """The chat's tmux entry, with a session tmux actually has.

        Rebuilt when the chat has no entry, or when tmux no longer has the session
        it names: killing the last window of a session destroys the session, and on
        our socket the last window is often all the server had, so the server goes
        with it (measured: the next listing answers `no server running on
        /tmp/tmux-1000/spit-...`). Since the window tmux creates along with every
        session is destroyed rather than left behind holding the session open, that
        is the ordinary path now, not a corner case.

        The `Server` object SURVIVES a rebuild -- that is what keeps one chat on one
        socket handle for its whole life: `new_session()` on the same object starts
        the server again on the same socket (measured, decision 69). The screen
        cache survives too: what was reported before the rebuild is still what was
        reported. The `windows` map does not, because a window of a session that is
        gone is not a window, and its id may already be somebody else's.
        """
        chat = self.tmux.get(self.chat_id)
        if chat is None:
            chat = self.tmux[self.chat_id] = {}
        if chat.get("server") is None:
            chat["server"] = libtmux.Server(socket_name=server_socket())
        chat.setdefault("windows", {})
        chat.setdefault("last_screen", {})
        if chat.get("session") is not None and session_is_live(chat["server"], chat["session"]):
            return chat
        session = chat["server"].new_session()
        chat["session"] = session
        chat["stamp"] = (session.pid, session.start_time)
        chat["windows"] = {}
        # `new_session()` always makes a window of its own first: index 0, named
        # `bash` (or `tmux` on a revived server), belonging to nobody. Nothing
        # registers it, nothing lists it, and while it lives the session cannot die
        # -- so it held the session open after its last real terminal was reported,
        # and it sat on the index that the next window lands on. Its id comes out of
        # the session row tmux just printed, so recording it costs nothing;
        # `remove_stray_window()` destroys it once there is a window of ours to
        # leave in the session. Not before then: killing the only window of a
        # session destroys the session with it, and the failure path of `new_window`
        # needs a session to still be there to report the error from.
        chat["stray_window"] = session.window_id
        return chat

    def remove_stray_window(self, chat: dict) -> None:
        stray = chat.pop("stray_window", None)
        if stray is None:
            return
        try:
            window_of_id(chat["server"], stray).kill()
        except libtmux.exc.LibTmuxException:
            pass        # already gone: nothing to destroy, and nothing left to do

    def term_new(self, name: str) -> None|str:
        ret = self.check_bwrap(["bash"])
        if ret:
            return ret
        if self.sandbox:
            cmd_args = self.bwrap_args() + ["bash"]
        else:
            cmd_args = [self.SANDBOX_ENV] + ["bash"]
        cmd_args = " ".join(cmd_args)
        # A chat with no tmux entry, or with one whose session was destroyed (see
        # ensure_session: the last window of a session takes the session, and on our
        # socket the last window is usually all the server had). The screen cache
        # survives that; `forget_screen` below keeps it out of THIS name's way.
        chat = self.ensure_session()
        self.forget_screen(name)
        windows = chat["windows"]
        # A reused name is a NEW session, never the old one (TOOLS.md 8, and t7 in
        # test_screen). tmux reuses window INDEXES -- measured: kill index 2, the
        # next window is index 2 again with a different window_id -- so an old
        # window left in place is not just untidy: it is a window nobody will ever
        # list, parked on an index that looks meaningful. Destroy it by the id the
        # registry holds (and the registry is only trustworthy for the server
        # ensure_session has just identified).
        old = windows.get(name)
        if old is not None:
            try:
                window_of_id(chat["server"], old).kill()
            except libtmux.exc.LibTmuxException:
                pass    # a window whose shell exited without the option is already gone
        # new_window() asks tmux for the window it just created, and tmux has
        # already destroyed it if its shell died while we were asking: a
        # sandbox_env.sh that cannot exec, a bash that is gone, a command that
        # exits before tmux answers. libtmux then raises TmuxObjectDoesNotExist
        # (measured, tmux 3.7b/libtmux 0.62: the raise comes from new_window
        # itself, for both a shell that cannot exec and one that exits at once,
        # and it is what this looked like BEFORE this guard too -- it is not
        # specific to any option set on the window). An exception here escapes
        # term_new and call() and the model gets a traceback where it should get
        # the reason, so report it as term_new's own error string (the contract
        # check_bwrap() established).
        #
        # `window_name=name` is what makes the two truths one truth: before it, tmux
        # called our windows `bash` (or `tmux`) while the registry called them
        # `alpha`, so anyone looking at tmux -- a user on our socket, a test -- saw
        # something the tool never said. The tmux name is display: the registry
        # resolves by its own name and looks tmux up by `window_id`, so a rename
        # from outside can no longer desynchronise anything.
        try:
            window = chat["session"].new_window(attach=True, window_name=name,
                                                window_shell=cmd_args)
            # Keep the window when its shell exits, so a session that dies with
            # nobody watching can still report what it actually printed and with
            # what status (dead_report). WINDOW scope is the only scope that works
            # here, and the obvious one does not: `tmux setw -t <session>
            # remain-on-exit on` BEFORE creating the window reports the session
            # option as `on` and the next window is STILL destroyed when its shell
            # exits (measured, tmux 3.7b), and libtmux 0.62 has no
            # Session.set_window_option to set it per-window ahead of creation. Set
            # on the window just after creation it holds; other windows on this
            # server keep tmux's default, which is what the user's own windows want.
            window.set_option("remain-on-exit", "on")
        except libtmux.exc.LibTmuxException as exc:
            return (f"ERROR: session `{name}` died as it started: the command that "
                    f"should run in it exited immediately or could not be started. "
                    f"Nothing is running under that name. ({exc})")
        windows[name] = window.window_id
        self.remove_stray_window(chat)

    def pane_active(self, name: str) -> bool:
        return pane_active(self.tmux, self.chat_id, name)

    def term_send_keys(self, name: str, keys: str, literal: bool) -> bool:
        # Not live -- and the way this refuses matters. pane_active() would forget
        # the name and leave the cache holding some EARLIER live capture, so
        # terminal.call()'s unconsumed-input message would show the model a screen
        # from before the death and never say what killed the session. dead_report()
        # reports the corpse's real final screen and exit status into that cache
        # first, then forgets the name and destroys it.
        #
        # Measured, tmux 3.7b: a send_keys into a retained corpse is ACCEPTED and
        # delivers NOTHING (byte-identical screen afterwards), so returning True
        # here would report input that reached nobody.
        snapshot = self.snapshot()
        state = self.window_state(name, snapshot)
        if state is None or pane_is_dead(state):
            self.dead_report(name, state, snapshot)
            return False
        # the result is discarded on purpose: what this call is FOR is the cache
        # it writes. Keys can kill the pane -- exit, C-d, a command that takes the
        # shell down with it -- and the screen reported afterwards is this one.
        # Removing it as dead code empties every dead-session message again.
        self.term_screen(name)
        # the capture above may itself have found it dead, reported and disposed
        state = self.window_state(name)
        if state is None or pane_is_dead(state):
            return False
        pane_of_id(self.server(), state.pane_id).send_keys(keys, enter=False,
                                                           literal=literal)
        return True

    def term_input(self, name: str, inp: list) -> str|None:
        if inp in KEYS:
            if inp == "Esc":
                return self.term_send_keys(name, "Escape", False)
            return self.term_send_keys(name, inp, False)
        if not inp[:2] in MODS:
            return self.term_send_keys(name, inp, True)
        if "Esc" in inp and not "Escape" in inp:
            inp = inp.replace("Esc", "Escape")
        key_body = inp
        for key in KEYS:
            key_body = key_body.replace(key, "")
        for mod in MODS:
            key_body = key_body.replace(mod, "")
        if len(key_body) <= 1:
            return self.term_send_keys(name, inp, False)
        return self.term_send_keys(name, inp, True)

    def term_screen(self, name: str) -> str:
        # One listing, then read -- and `window_state()`, not `pane_active()`: the
        # latter FORGETS a name it finds dead, and a name forgotten before it is
        # read is a corpse whose real screen nobody can report, which is the whole
        # point of remain-on-exit. Liveness, cursor and exit status all come from
        # the SAME snapshot, so they cannot disagree with each other the way three
        # separate reads could.
        snapshot = self.snapshot()
        chat = self.chat_state()
        state = window_state(chat, name, snapshot)
        if state is None:
            if name not in chat.get("windows", {}):
                # no pane, no registration, and it may still have a report cached
                return self.unreached_screen(name)
            return self.dead_report(name, None)
        if pane_is_dead(state):
            return self.dead_report(name, state, snapshot)
        return self.live_screen(name, state, snapshot)

    def live_screen(self, name: str, state, snapshot: Snapshot = None) -> str:
        # The splice is byte-for-byte what it has always been -- same capture flags,
        # same `█`, same rule for the character under it -- and only WHERE x and y
        # come from has changed: the snapshot carries `cursor_x`/`cursor_y`, measured
        # equal to `display_message('#{cursor_x}')` for a fresh prompt, a half-typed
        # line, after Enter, a wrapped line and a screenful (identical in all five).
        # Two fewer tmux invocations per capture, same bytes out -- TRAPS #14: a
        # refactor is proven by comparing the output, not by a green suite.
        _output = pane_of_id(self.server(), state.pane_id).capture_pane(
            preserve_trailing=True, join_wrapped=True)
        x, y = cursor_of(state)
        output = f"Session: {name}\n\n"
        count_y = 0
        for line in _output:
            if count_y == y:
                output += line[0:x] + "█"
                if len(line)-1 >= x+1:
                    output += line[x+1:]
                output += "\n"
            else:
                output += line + "\n"
            count_y += 1
        self.remember_screen(name, output)
        return output
