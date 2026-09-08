# SPDX-License-Identifier: GPL-2.0
import libtmux
from .common import CommonMixIn

KEYS = ["Up", "Down", "Left", "Right", "Space", "Tab", "Delete", "End", "Enter", "Escape", "Esc", "F1",
        "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10" , "F11", "F12", "Home", "Insert", "PageDown",
        "PgDn", "PgUp", "PageUp"]
MODS = ["C-", "S-", "M-"]

def pane_active(tmux: dict, chat_id: str, name: str) -> bool:
    chat = tmux.get(chat_id)
    if not chat:
        return False
    windows = chat.get("windows", {})
    if not name in windows:
        return False
    chat["session"].refresh()
    if windows[name] in chat["session"].windows:
        return True
    del windows[name]
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
        return f"{last_screen}\n\nINFO: Session dead."

    def term_new(self, name: str) -> None|str:
        ret = self.check_bwrap(["bash"])
        if ret:
            return ret
        if self.sandbox:
            cmd_args = self.bwrap_args() + ["bash"]
        else:
            cmd_args = [self.SANDBOX_ENV] + ["bash"]
        cmd_args = " ".join(cmd_args)
        if not self.chat_id in self.tmux:
            self.tmux[self.chat_id] = {}
            self.tmux[self.chat_id]["server"] = libtmux.Server()
            self.tmux[self.chat_id]["session"] = self.tmux[self.chat_id]["server"].new_session()
            self.tmux[self.chat_id]["windows"] = {}
        self.forget_screen(name)
        windows = self.tmux[self.chat_id]["windows"]
        windows[name] = self.tmux[self.chat_id]["session"].new_window(attach=True, window_shell=cmd_args)

    def pane_active(self, name: str) -> bool:
        return pane_active(self.tmux, self.chat_id, name)

    def term_send_keys(self, name: str, keys: str, literal: bool) -> bool:
        if not self.pane_active(name):
            return False
        # the result is discarded on purpose: what this call is FOR is the cache
        # it writes. Keys can kill the pane -- exit, C-d, a command that takes the
        # shell down with it -- and the screen reported afterwards is this one.
        # Removing it as dead code empties every dead-session message again.
        self.term_screen(name)
        self.tmux[self.chat_id]["windows"][name].panes[0].send_keys(keys, enter=False, literal=literal)
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
        if not self.pane_active(name):
            return self.dead_session_message(name)
        pane = self.tmux[self.chat_id]["windows"][name].panes[0]
        _output = pane.capture_pane(preserve_trailing=True, join_wrapped=True)
        try:
            x = int(pane.display_message('#{cursor_x}', get_text=True)[0])
            y = int(pane.display_message('#{cursor_y}', get_text=True)[0])
        except:
            del self.tmux[self.chat_id]["windows"][name]
            return self.dead_session_message(name)
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
