# SPDX-License-Identifier: GPL-2.0
import libtmux
from .common import CommonMixIn

KEYS = ["Up", "Down", "Left", "Right", "Space", "Tab", "Delete", "End", "Enter", "Escape", "Esc", "F1",
        "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10" , "F11", "F12", "Home", "Insert", "PageDown",
        "PgDn", "PgUp", "PageUp"]
MODS = ["C-", "S-", "M-"]

class Terminal(CommonMixIn):
    def __init__(self, app, chat_id: str, sandbox: bool = True) -> None:
        super().__init__(app, sandbox, chat_id)
        self.tmux = app.tmux
        self.output = ""

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
        windows = self.tmux[self.chat_id]["windows"]
        windows[name] = self.tmux[self.chat_id]["session"].new_window(attach=True, window_shell=cmd_args)

    def pane_active(self, name: str) -> bool:
        if not name in self.tmux[self.chat_id]["windows"]:
            return False
        self.tmux[self.chat_id]["session"].refresh()
        if self.tmux[self.chat_id]["windows"][name] in self.tmux[self.chat_id]["session"].windows:
            return True
        else:
            del self.tmux[self.chat_id]["windows"][name]
            return False

    def term_send_keys(self, name: str, keys: str, literal: bool) -> bool:
        if not self.pane_active(name):
            return False
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
        _inp = inp
        for key in KEYS:
            _inp.replace(key, "")
        for mod in MODS:
            _inp.replace(mod, "")
        if len(_inp) <= 1:
            return self.term_send_keys(name, inp, False)
        return self.term_send_keys(name, inp, True)

    def term_screen(self, name: str) -> str:
        if not self.pane_active(name):
            return f"{self.output}\n\nINFO: Session dead."
        pane = self.tmux[self.chat_id]["windows"][name].panes[0]
        _output = pane.capture_pane(preserve_trailing=True, join_wrapped=True)
        try:
            x = int(pane.display_message('#{cursor_x}', get_text=True)[0])
            y = int(pane.display_message('#{cursor_y}', get_text=True)[0])
        except:
            del self.tmux[self.chat_id]["windows"][name]
            return f"{self.output}\n\nINFO: Session dead."
        output = f"Session: {name}\n\n```text\n"
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
        self.output = output + "\n```"
        return self.output
