import json
from textual.containers import Vertical
from .containers.part import Part
from .pattern_processing import PatternProcessing

class Process(Vertical):
    def __init__(self, display: bool = True) -> None:
        super().__init__()
        self.classes = "message-section"
        self.display = display
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

    async def process_content(self, content) -> None:
        self.pp.part = ""
        if len(content)-self.pos-self.pp.bsize > 0:
            for pos in range(self.pos, len(content) - self.pp.bsize):
                await self.pp.process_patterns(content[pos:])
            await self.target.append(self.pp.part)
            self.pos=pos+1

    async def finish_content(self, content) -> None:
        self.pp.part = ""
        for pos in range(self.pos, len(content)):
            await self.pp.process_patterns(content[pos:])
        await self.target.append(self.pp.part)
        self.pos = pos

    async def finish(self, content) -> None:
        if not self.finished:
            if not self.target:
                await self.mount(Part())
            await self.finish_content(content)
            self.target = None
            self.finished = True

    async def process(self, content) -> None:
        if not self.target:
            await self.mount(Part())
        await self.process_content(content)
