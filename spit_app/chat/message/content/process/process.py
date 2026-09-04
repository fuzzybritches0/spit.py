import json
from textual.containers import VerticalScroll
from .actions import ActionsMixIn, bindings
from .containers.part import Part
from .pattern_processing import PatternProcessing
from .tool_call import ToolCall

class Process(ActionsMixIn, VerticalScroll):
    BINDINGS = bindings

    def __init__(self, chat, message, scontent: str) -> None:
        super().__init__()
        self.classes = "message-content-process"
        self.chat = chat
        self.chat_view = self.chat.chat_view
        self.message = message
        self.scontent = scontent
        self.is_removing = False
        self.init()

    @property
    def index(self) -> int:
        for count in range(0, len(self.parent.children)):
            if self is self.parent.children[count]:
                return count

    def tool_output_type_hint(self) -> None:
        self.output_type_hint = None
        if self.message.message["role"] == "tool":
            name = self.message.message["name"]
            self.output_type_hint = self.app.tool_call.tools[name]["output_type_hint"]
        # the hint fences are part of the string self.pos indexes: they must
        # be prepended on EVERY callback or the positions drift and each
        # boundary re-renders (or skips) the length of the prefix
        if self.output_type_hint:
            self.tool_start = f"~~~~~{self.output_type_hint}\n"
            self.tool_end = "\n~~~~~"
        else:
            self.tool_start = ""
            self.tool_end = ""

    def init(self) -> None:
        self.pp = PatternProcessing(self)
        self.pos = 0
        self.pp.part = ""
        self.tc = None
        self.target = None
        self.finished = False
        self.is_edit = False
        self.edit = None
        self.tool_output_type_hint()

    async def reset(self) -> None:
        await self.remove_children()
        self.init()

    async def process_content(self, content: str) -> None:
        content = self.tool_start + content
        self.pp.part = ""
        end = len(content) - self.pp.bsize
        if end > self.pos:
            for pos in range(self.pos, end):
                await self.pp.process_patterns(content[pos:])
            await self.target.stream.write(self.pp.part)
            self.pos = end

    async def finish_content(self, content: str) -> None:
        content = self.tool_start + content + self.tool_end
        self.pp.part = ""
        for pos in range(self.pos, len(content)):
            await self.pp.process_patterns(content[pos:])
        await self.target.stream.write(self.pp.part)
        await self.target.stream.stop()
        self.pos = len(content)

    def get_content(self, content: str|dict) -> str|None:
        if type(content) is str:
            return content
        elif type(content) is dict and self.scontent == "tool_calls":
            if not self.tc:
                self.tc = ToolCall(content)
            return self.tc.tool_call_arguments()
        return None

    async def finish(self, content: str|dict) -> None:
        if self.finished:
            return None
        if not self.target:
            await self.mount(Part())
        await self.finish_content(self.get_content(content))
        self.target = None
        self.finished = True

    async def process(self, content: str|dict) -> None:
        if not self.target:
            await self.mount(Part())
        await self.process_content(self.get_content(content))
