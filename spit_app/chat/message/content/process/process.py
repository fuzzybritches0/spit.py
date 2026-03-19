import json
from textual.containers import VerticalScroll
from .actions import ActionsMixIn, bindings
from .containers.part import Part
from .pattern_processing import PatternProcessing

class Process(ActionsMixIn, VerticalScroll):
    BINDINGS = bindings

    def __init__(self, message, scontent, count) -> None:
        super().__init__()
        self.classes = "message-content-process"
        self.message = message
        self.messages = message.messages
        self.chat = message.chat
        self.scontent = scontent
        self.count = count
        self.reset_state()

    def reset_state(self) -> None:
        self.pp = PatternProcessing(self)
        self.pos = 0
        self.pp.part = ""
        self.target = None
        self.finished = False

    async def reset(self) -> None:
        await self.remove_children()
        self.reset_state()

    async def process_content(self, content: str) -> None:
        if not self.display:
            return None
        if not self.chat.chat_view.has_focus_within:
            return None
        if not self.app.screen.can_view_partial(self.parent):
            return None
        self.pp.part = ""
        if len(content)-self.pos-self.pp.bsize > 0:
            for pos in range(self.pos, len(content) - self.pp.bsize):
                await self.pp.process_patterns(content[pos:])
            await self.target.stream.write(self.pp.part)
            self.pos=pos+1

    async def finish_content(self, content: str) -> None:
        self.pp.part = ""
        pos = 0
        for pos in range(self.pos, len(content)):
            await self.pp.process_patterns(content[pos:])
        await self.target.stream.write(self.pp.part)
        await self.target.stream.stop()
        self.pos = pos

    def get_content(self, content: str|list) -> str|None:
        if type(content) is str:
            return content
        elif content[self.count]["type"] == "text":
            return content[self.count]["text"]
        return None

    async def finish(self, content: str|list) -> None:
        if self.finished:
            return None
        if not self.target:
            await self.mount(Part())
        await self.finish_content(self.get_content(content))
        self.target = None
        self.finished = True

    async def process(self, content: str|list) -> None:
        if not self.target:
            await self.mount(Part())
        await self.process_content(self.get_content(content))
