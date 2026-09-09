# SPDX-License-Identifier: GPL-2.0
import os
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

def pane_is_dead(pane) -> bool:
    """Has this pane's process exited? '1' once it has, '0' while it runs.

    The one place that meaning is written. tmux keeps a retained pane's exit status
    (pane_dead_status) and, on tmux >= 3.3, pane_dead_signal and pane_dead_time.
    """
    return pane is not None and pane.pane_dead == "1"

def pane_of(tmux: dict, chat_id: str, name: str):
    """The pane of a registered window if tmux still holds that window, else None.

    Non-mutating on purpose: pane_active() forgets what it finds dead, and a caller
    that reads liveness that way can no longer reach the corpse to report its real
    final screen -- which is the whole point of remain-on-exit. So read first,
    decide afterwards.

    What makes the read fresh is the RE-LIST (`window.panes` asks tmux again, and a
    re-listed pane reports pane_dead '1' the moment the shell is gone). A cached
    Pane object is what goes stale: measured, `pane.pane_dead` still read '0' after
    the shell had exited, and after `respawn-window` the same pane_id belonged to a
    different pid. Nothing here holds a Pane across calls. The session listing is
    live in libtmux 0.62 -- `window in session.windows` was correct with no refresh
    at all, for a destroyed window and for a retained one alike -- so there is no
    refresh() here; the one that was in pane_active() was protecting nothing.
    """
    chat = tmux.get(chat_id)
    session = chat.get("session") if chat else None
    if session is None:
        return None
    window = chat.get("windows", {}).get(name)
    if window is None or window not in session.windows:
        return None
    return window.panes[0] if window.panes else None

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

def dead_report_text(tmux: dict, chat_id: str, name: str, pane):
    """The report for a retained corpse: its real final screen and exit status.

    None when nothing can be read from it (gone between the liveness read and this
    capture), which is the caller's cue to fall back to the cached screen.

    The exit status is `pane_dead_status`; it is empty for a death by signal, hence
    the guard, so a SIGKILLed shell does not report "Exit status: .". tmux's own
    `Pane is dead (status N, ...)` line is part of the captured screen and says the
    same thing in tmux's words, which is what a test asserts the code from rather
    than this prose.
    """
    try:
        lines = pane.capture_pane(start=f"-{DEAD_REPORT_HISTORY}",
                                  preserve_trailing=True, join_wrapped=True)
        status = pane.pane_dead_status
    except libtmux.exc.LibTmuxException:
        return None
    notice = "\n\nINFO: Session dead."
    if status not in (None, ""):
        notice += f" Exit status: {status}."
    # The notice is part of what is CACHED, not only of what is returned: the cache
    # holds what the tool last reported, so a repeat call says the same thing --
    # including the exit status, which the captured screen alone does not carry.
    # It is the dead rendering, with no cursor marker: a dead pane has no cursor,
    # and decision 66's marker is a live-screen affordance.
    return f"Session: {name}\n\n" + "\n".join(lines) + notice

def retire(tmux: dict, chat_id: str, name: str) -> None:
    """A dead name stops existing, in tmux and in the registry, here.

    DECISION, and the reason is the alternative. A retained window is destroyed by
    nothing else: measured, three chats and one death left 5 windows in the session
    and after the name was reused, 6, one of them an abandoned
    `sandbox_env.sh[dead]` -- and once the name is forgotten the registry has no
    handle on it, so forgetting makes a corpse unreachable, not gone. tmux keeps it
    for the whole run of the app, because the only other tmux teardown is actions.py
    at exit. So a corpse is destroyed at the moment somebody has established it is
    dead, and after that report has been taken. `Window.kill()` works on a corpse
    (measured; killing it twice raises `kill-window: can't find window`, hence the
    guard).

    The catch, measured: killing a corpse is harmless while the session still has
    another window, but killing the LAST window destroys the session, and when ours
    was the server's only session the server went with it -- leaving every later
    call indexing a `chat["session"]` that no longer exists. So check afterwards and
    rebuild the chat entry when that happened, keeping the screen cache: the next
    term_new starts a server and session again (measured: new_session() on the same
    Server object works; tmux starts the server back up).
    """
    chat = tmux.get(chat_id) or {}
    window = chat.get("windows", {}).get(name)
    session = chat.get("session")
    if window is not None:
        try:
            window.kill()
        except libtmux.exc.LibTmuxException:
            pass        # already gone: nothing left to destroy
    chat.get("windows", {}).pop(name, None)
    if session is None:
        return
    try:
        still_there = session.session_id in [s.session_id for s in session.server.sessions]
    except libtmux.exc.LibTmuxException:
        still_there = False
    if not still_there:
        tmux[chat_id] = {"windows": {},
                         "last_screen": chat.get("last_screen", {})}

def pane_active(tmux: dict, chat_id: str, name: str) -> bool:
    # One liveness rule, shared by `terminal` and `lsterm` since c948b3e. It used to
    # be "is the window still in the session", which was right only while tmux
    # destroyed a window when its shell exited. With `remain-on-exit` on the window
    # (term_new sets it) tmux KEEPS it, so membership now answers "is there still a
    # corpse" and would call a dead session live (measured: the retained window is
    # still in session.windows while its pane_dead is '1'). Liveness is pane_dead.
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
    pane = pane_of(tmux, chat_id, name)
    if pane is not None and not pane_is_dead(pane):
        return True
    if pane is not None:
        report = dead_report_text(tmux, chat_id, name, pane)
        if report is not None:
            chat.setdefault("last_screen", {})[name] = report
    retire(tmux, chat_id, name)
    return False

def live_window_names(tmux: dict, chat_id: str) -> list:
    # the names are snapshotted first: pane_active() drops a dead window from the
    # very dict a listing loop walks, and a dict that changes size mid-iteration
    # raises RuntimeError out of what is supposed to be a read-only listing.
    return [name for name in list(tmux.get(chat_id, {}).get("windows", {}))
            if pane_active(tmux, chat_id, name)]

class Terminal(CommonMixIn):
    def __init__(self, app, chat_id: str, sandbox: bool = True) -> None:
        super().__init__(app, sandbox, chat_id)
        self.tmux = app.tmux

    def chat_state(self) -> dict:
        return self.tmux.get(self.chat_id, {})

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

    def dead_report(self, name: str, pane) -> str:
        """What a dead session answers with.

        A pane tmux retained (`remain-on-exit`, which term_new sets on the window)
        still holds the session's REAL final screen and its exit status, so both are
        reported verbatim: a session that died after printing a traceback and one
        that printed nothing no longer look alike, and the answer is no longer
        limited to the last screen WE happened to capture. With no pane to read --
        the window was destroyed, or it died before this option existed -- fall back
        to the cached screen and the wording that has always been used for it.

        dead_report_text() and retire() do the work, because discovering a death in
        pane_active() -- inside `lsterm`, the tool the model is told to call first --
        has to report and destroy it exactly the same way. Two implementations is how
        one of them stops harvesting the evidence.
        """
        if pane is None:
            # The window is gone: its shell exited without the option, or the user
            # killed it from outside. This is the path that used to report the death
            # and LEAVE the entry in the registry, naming a window nothing would
            # ever list again.
            self.forget_window(name)
            return self.dead_session_message(name)
        report = dead_report_text(self.tmux, self.chat_id, name, pane)
        if report is None:
            # gone between the liveness read and the capture: cache fallback, and it
            # is still dead, so it still goes
            retire(self.tmux, self.chat_id, name)
            return self.dead_session_message(name)
        self.remember_screen(name, report)
        retire(self.tmux, self.chat_id, name)
        return report

    def forget_window(self, name: str) -> None:
        # Drop a name from the registry only: the listing stops reporting it and the
        # name becomes reusable. The screen cache stays -- it is the fallback for
        # every later call once there is nothing left to read. Anything that must
        # also destroy the window calls retire().
        self.chat_state().get("windows", {}).pop(name, None)

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
        # dispose_corpse: taking the session's last window takes the session, and on
        # our socket the last window is sometimes ours), needs both rebuilt. The
        # screen cache survives that: the entry keeps it, term_new keeps it out.
        if not self.tmux.get(self.chat_id, {}).get("session"):
            self.tmux[self.chat_id] = {}
            self.tmux[self.chat_id]["server"] = libtmux.Server(socket_name=server_socket())
            self.tmux[self.chat_id]["session"] = self.tmux[self.chat_id]["server"].new_session()
            self.tmux[self.chat_id]["windows"] = {}
        self.forget_screen(name)
        windows = self.tmux[self.chat_id]["windows"]
        # A reused name is a NEW session, never the old one (TOOLS.md 8, and t7 in
        # test_screen). tmux reuses window INDEXES -- measured: kill index 2, the
        # next window is index 2 again with a different window_id -- so an old window
        # left in place is not just untidy, it sits exactly where a lookup by number
        # would later land. Destroy it before respawning.
        old = windows.get(name)
        if old is not None:
            try:
                old.kill()
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
        try:
            windows[name] = self.tmux[self.chat_id]["session"].new_window(
                attach=True, window_shell=cmd_args)
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
            windows[name].set_option("remain-on-exit", "on")
        except libtmux.exc.LibTmuxException as exc:
            windows.pop(name, None)
            return (f"ERROR: session `{name}` died as it started: the command that "
                    f"should run in it exited immediately or could not be started. "
                    f"Nothing is running under that name. ({exc})")

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
        pane = pane_of(self.tmux, self.chat_id, name)
        if pane is None or pane_is_dead(pane):
            self.dead_report(name, pane)
            return False
        # the result is discarded on purpose: what this call is FOR is the cache
        # it writes. Keys can kill the pane -- exit, C-d, a command that takes the
        # shell down with it -- and the screen reported afterwards is this one.
        # Removing it as dead code empties every dead-session message again.
        self.term_screen(name)
        # the capture above may itself have found it dead, reported and disposed
        pane = pane_of(self.tmux, self.chat_id, name)
        if pane is None or pane_is_dead(pane):
            return False
        pane.send_keys(keys, enter=False, literal=literal)
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
        # pane_of, not pane_active: the latter FORGETS a name it finds dead, and a
        # name forgotten before it is read is a corpse whose real screen nobody can
        # report -- which is the whole point of remain-on-exit. Read first, decide
        # after. Both dead shapes come through dead_report: a retained corpse (real
        # screen, real exit status) and a window that is gone (the cached screen).
        pane = pane_of(self.tmux, self.chat_id, name)
        if pane is None or pane_is_dead(pane):
            return self.dead_report(name, pane)
        _output = pane.capture_pane(preserve_trailing=True, join_wrapped=True)
        try:
            x = int(pane.display_message('#{cursor_x}', get_text=True)[0])
            y = int(pane.display_message('#{cursor_y}', get_text=True)[0])
        except Exception:
            # a pane that cannot answer for its cursor is not there any more: report
            # it dead the same way, through the cache
            return self.dead_report(name, None)
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
