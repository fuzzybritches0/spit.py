import json
from copy import deepcopy
from textual.widgets import TextArea as _TextArea, Label, Select
from textual.containers import Vertical
from .tool_call import ToolCall
from spit_app.chat.textual_message import RemoveProcess

class TextArea(_TextArea):
    def __init__(self, id: str, required: bool = False) -> None:
        super().__init__()
        self.id = id
        self.required = required
        self._background = self.styles.background

    def on_text_area_changed(self) -> None:
        if not self.text and self.required:
            self.styles.background = "red"
        else:
            self.styles.background = self._background

class TextAreaTool():
    def __init__(self, process, new: bool = False):
        self.new = new
        self.process = process
        self.chat = process.chat
        self.chat_view = process.chat_view
        self.message = process.message
        self.chat = process.chat
        self.tool_change = None

    def init(self) -> None:
        self.tool = deepcopy(self.message.message["tool_calls"][self.process.count])
        if self.tool_change:
            self.tool["function"]["name"] = self.tool_change
        self.ori_tool = deepcopy(self.tool)
        self.old_tool = json.dumps(self.tool)
        self.arguments =  json.loads(self.tool["function"]["arguments"])
        tool_name = self.tool["function"]["name"]
        self.unknown_tool = True
        if tool_name in self.process.app.tool_call.tools:
            self.unknown_tool = False
            self.known_tool = self.process.app.tool_call.tools[tool_name]
            self.properties = self.known_tool["desc"]["function"]["parameters"]["properties"]
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
                    value = ""
                    await self.process.mount(Label(f"{prop}:"))
                    if prop in self.arguments:
                        value = self.arguments[prop]
                    if prop in self.required:
                        await self.process.mount(TextArea(prop, True))
                    else:
                        await self.process.mount(TextArea(prop))
                    self.process.children[-1].text = value
                    self.process.children[-1].styles.height = "auto"
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
                index = self.chat_view.messages.index(self.message.message)
                self.chat.undo.append_undo("change", self.message.message, index)
                self.message.message["tool_calls"][self.process.count] = self.tool
        return True

    def save_known(self) -> bool:
        arguments = {}
        for prop in self.properties.keys():
            text = self.process.query_one(f"#{prop}").text
            required = self.process.query_one(f"#{prop}").required
            if required and not text:
                return False
            arguments[prop] = text
        save_arguments = {}
        for prop in arguments:
            if prop in self.properties.keys() and arguments[prop]:
                save_arguments[prop] = arguments[prop]
        self.tool["function"]["arguments"] = json.dumps(save_arguments)
        index = self.chat_view.messages.index(self.message.message)
        self.chat.undo.append_undo("change", self.message.message, index)
        self.message.message["tool_calls"][self.process.count] = self.tool
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
        if self.new:
            self.message.post_message(RemoveProcess(self.process.scontent, self.process.count))
            return None
        async with self.process.batch():
            await self.process.reset()
            tc = ToolCall(self.tool["function"])
            tc.format_tool_call()
            await self.process.finish(tc.formatted_tool_call)
        self.message.is_edit -= 1
        self.process.is_edit = False
