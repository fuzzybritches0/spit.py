import json
from textual.widgets import TextArea as _TextArea, Markdown
from textual.containers import Vertical
from .tool_call import ToolCall

class TextArea(_TextArea):
    def __init__(self, id: str, required: bool = False) -> None:
        super().__init__()
        self.id = id
        self.required = required
        self._background = self.styles.background

    def on_text_area_changed(self) -> None:
        if not self.text:
            self.styles.background = "red"
        else:
            self.styles.background = self._background

class TextAreaTool():
    def __init__(self, process, tool: dict):
        self.process = process
        self.chat_view = process.chat_view
        self.message = process.message
        self.chat = process.chat
        self.tool = tool
        self.init()

    def init(self) -> None:
        self.ori_tool = self.tool
        self.old_tool = json.dumps(self.tool)
        self.arguments =  json.loads(self.tool["function"]["arguments"])
        self.tool_name = self.tool["function"]["name"]
        self.unknown_tool = True
        if self.tool_name in self.process.app.tool_call.tools:
            self.unknown_tool = False
            self.known_tool = self.process.app.tool_call.tools[self.tool_name]
            self.properties = self.known_tool["desc"]["function"]["parameters"]["properties"]
            self.required = self.known_tool["desc"]["function"]["parameters"]["required"]

    async def mount(self) -> None:
        if self.unknown_tool:
            await self.process.mount(TextArea("unkdnown", True))
            self.process.children[0].styles.height = "auto"
            self.process.children[0].text = self.old_tool
            self.process.children[0].focus()
        else:
            await self.process.mount(Markdown(f"### function: `{self.tool_name}`\n#### arguments:"))
            for prop in self.properties.keys():
                value = ""
                if prop in self.arguments:
                    value = self.arguments[prop]
                await self.process.mount(Markdown(f"`{prop}`"))
                if prop in self.required:
                    await self.process.mount(TextArea(prop, True))
                else:
                    await self.process.mount(TextArea(prop))
                self.process.children[-1].text = value
                self.process.children[-1].styles.height = "auto"
            self.process.children[2].focus()

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
        arguments = json.dumps(arguments)
        index = self.chat_view.messages.index(self.message.message)
        self.chat.undo.append_undo("change", self.message.message, index)
        self.tool["function"]["arguments"] = arguments
        self.message.message["tool_calls"][self.process.count]["function"]["arguments"] = arguments
        return True

    async def save(self) -> None:
        if self.unknown_tool:
            if not self.save_unknown():
                return None
        else:
            if not self.save_known():
                return None
        self.chat.write_chat_history()
        await self.cancel()

    async def cancel(self) -> None:
        async with self.process.batch():
            await self.process.reset()
            tc = ToolCall(self.tool["function"])
            tc.format_tool_call()
            await self.process.finish(tc.formatted_tool_call)
        self.message.is_edit -= 1
        self.process.is_edit = False
