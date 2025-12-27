# SPDX-License-Identifier: GPL-2.0
import json
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import TextArea
import spit_app.chat.undo as undo
from spit_app.chat.actions import ActionsMixIn, ChatViewActionsMixIn, TextAreaActionsMixIn
from spit_app.chat.handlers import HandlersMixIn, ChatViewHandlersMixIn, TextAreaHandlersMixIn
from spit_app.chat.actions import bindings, bindings_chat_view, bindings_text_area
from spit_app.chat.patterns.pattern_processing import PatternProcessing


class ChatView(ChatViewHandlersMixIn, ChatViewActionsMixIn, VerticalScroll):
    BINDINGS = bindings_chat_view

    def __init__(self, chat):
        super().__init__()
        self.anchor()
        self.chat = chat
        self.id = "chat-view"
        self.focused_message = None
        self.watch(self.app, "theme", self.on_theme_changed, init=False)

class TextArea(TextAreaHandlersMixIn, TextAreaActionsMixIn, TextArea):
    BINDINGS = bindings_text_area

    def __init__(self, chat):
        super().__init__()
        self.chat = chat
        self.id = "text-area"
        self.tab_behavior = "indent"
        self.text_area_was_empty = True

class Chat(HandlersMixIn, ActionsMixIn, Vertical):
    BINDINGS = bindings

    def __init__(self, id):
        super().__init__()
        self.settings = self.app.settings
        self.classes = "chat"
        self.id = id
        chat = id + ".json"
        with open(self.app.settings.data_path / chat, "r") as file:
            content = json.load(file)
        self.chat_ctime = content["ctime"]
        self.chat_desc = content["desc"]
        self.chat_endpoint = content["endpoint"]
        self.chat_prompt = content["prompt"]
        self.messages = content["messages"]
        self.work = None
        self.edit = False
        self.code_listings = []
        self.latex_listings = []
        self.undo = []
        self.undo_index = -1
        self.system_prompt = "You are a helpful AI assistant."
        self.focused_message = None
        self.pattern_processing = PatternProcessing

    def compose(self) -> ComposeResult:
        yield ChatView(self)
        yield TextArea(self)

    def write_chat_history(self) -> None:
        file_name = self.id + ".json"
        file = self.settings.data_path / file_name
        content = {}
        content["ctime"] = self.chat_ctime
        content["desc"] = self.chat_desc
        content["endpoint"] = self.chat_endpoint
        content["prompt"] = self.chat_prompt
        content["messages"] = self.messages
        with open(file, "w") as f:
            json.dump(content, f)
    
    def save_message(self, umessage: dict) -> None:
        self.messages.append(umessage)
        undo.append_undo(self, "append", umessage)
        self.write_chat_history()
