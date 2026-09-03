import json
from copy import deepcopy
from textual.widgets import TextArea as _TextArea, Label, Select
from textual.containers import Vertical
from .tool_call import ToolCall
from spit_app.arguments import field_parse, field_render, field_valid
from spit_app.chat.textual_message import ResetProcess

class TextArea(_TextArea):
    def __init__(self, id: str, required: bool, spec: dict = None) -> None:
        super().__init__()
        self.id = id
        self.required = required
        # the property's whole schema spec, never just its type name: a union
        # such as ["string", "array"] and an anyOf are the spec's business
        self.spec = spec or {}
        self._background = self.styles.background

    def on_text_area_changed(self, event: _TextArea.Changed) -> None:
        if (self.required and not self.text) or \
           (self.text and not field_valid(self.spec, self.text)):
            self.styles.background = "red"
        else:
            self.styles.background = self._background

class TextAreaTool():
    def __init__(self, process, new: bool = False):
        self.new = new
        self.process = process
        self.chat = process.chat
        self.message = process.message
        self.chat = process.chat
        self.tool_change = None

    def init(self) -> None:
        self.tool = deepcopy(self.message.message["tool_calls"][self.process.index])
        if self.tool_change:
            self.tool["function"]["name"] = self.tool_change
        self.ori_tool = deepcopy(self.tool)
        self.old_tool = json.dumps(self.tool)
        self.arguments = {}
        if "arguments" in self.tool["function"]:
            self.arguments =  json.loads(self.tool["function"]["arguments"])
        tool_name = self.tool["function"]["name"]
        self.unknown_tool = True
        if tool_name in self.process.app.tool_call.tools:
            self.unknown_tool = False
            self.known_tool = self.process.app.tool_call.tools[tool_name]
            self.properties = {}
            self.required = {}
            if ("parameters" in self.known_tool["desc"]["function"] and
                "properties" in self.known_tool["desc"]["function"]["parameters"]):
                self.properties = self.known_tool["desc"]["function"]["parameters"]["properties"]
                if "required" in self.known_tool["desc"]["function"]["parameters"]:
                    self.required = self.known_tool["desc"]["function"]["parameters"]["required"]

    async def select_tool(self) -> None:
        tools = ()
        for tool in self.chat.cs("tools"):
            tools += ((tool, tool),)
        await self.process.mount(Select(tools, id="select-tool", value=self.tool["function"]["name"],
                                allow_blank=False))

    async def mount(self, mount_select: bool = True, initial: bool = True) -> None:
        self.init()
        if self.unknown_tool:
            await self.process.mount(TextArea("unkdnown", True))
            self.process.children[0].styles.height = "auto"
            self.process.children[0].text = self.old_tool
            self.process.children[0].focus()
        else:
            if mount_select:
                await self.process.mount(Label("\n[bold $accent]function:"))
                await self.select_tool()
            if initial:
                return None
            await self.process.mount(Label("\n[bold $accent-lighten-1]arguments:\n"))
            async with self.process.batch():
                for prop in self.properties.keys():
                    spec = self.properties[prop]
                    # None, not "": an argument that was never sent has to look
                    # different from one whose value is False or 0
                    value = None
                    await self.process.mount(Label(f"{prop}:"))
                    if prop in self.arguments:
                        value = self.arguments[prop]
                    if prop in self.required:
                        await self.process.mount(TextArea(prop, True, spec))
                    else:
                        await self.process.mount(TextArea(prop, False, spec))
                    self.process.children[-1].text = field_render(value)
                    self.process.children[-1].styles.height = "auto"
            if len(self.process.children) > 4:
                self.process.children[4].focus()

    def save_unknown(self) -> bool:
        text = self.process.children[0].text
        required = self.process.children[0].required
        if required and not text:
            return False
        if not text == self.old_tool:
            self.tool = None
            try:
                self.tool = json.loads(text)
            except:
                self.process.app.exception = Exception("no valid JSON!")
                self.tool = self.ori_tool
                return False
            if self.tool:
                index = self.chat.message_index(self.message.message)
                self.chat.undo.append_undo("change", self.message.message, index)
                self.message.message["tool_calls"][self.process.index] = self.tool
        return True

    def save_known(self) -> bool:
        arguments = {}
        for prop in self.properties.keys():
            widget = self.process.query_one(f"#{prop}")
            spec = self.properties[prop]
            if widget.required and not widget.text:
                return False
            if widget.text and not field_valid(spec, widget.text):
                return False
            arguments[prop] = field_parse(spec, widget.text)
        save_arguments = {}
        for prop in arguments:
            # None and "" mean the field was left empty. False and 0 are values:
            # a bare truthiness test here dropped them and let the default win.
            if prop in self.properties.keys() and arguments[prop] is not None \
               and arguments[prop] != "":
                save_arguments[prop] = arguments[prop]
        if save_arguments:
            self.tool["function"]["arguments"] = json.dumps(save_arguments)
        index = self.chat.message_index(self.message.message)
        self.chat.undo.append_undo("change", self.message.message, index)
        self.message.message["tool_calls"][self.process.index] = self.tool
        return True

    async def save(self) -> None:
        self.new = False
        if self.unknown_tool:
            if not self.save_unknown():
                return None
        else:
            if not self.save_known():
                return None
        self.chat.write_chat_history()
        await self.cancel()

    async def cancel(self) -> None:
        self.message.is_edit -= 1
        self.process.is_edit = False
        if self.new:
            self.message.post_message(ResetProcess(self.process.scontent, self.process.index, None))
        else:
            tc = ToolCall(self.tool["function"])
            text = tc.tool_call_arguments()
            self.message.post_message(ResetProcess(self.process.scontent, self.process.index, text))
