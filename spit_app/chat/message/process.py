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
        self.old_content = ""
        self.target = None
        self.process_busy = False
        self.finish_pending = False

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
        self.old_content = content

    async def finish_content(self, content) -> None:
        self.pp.part = ""
        for pos in range(self.pos, len(content)):
            await self.pp.process_patterns(content[pos:])
        await self.target.append(self.pp.part)
        self.pos = pos

    async def finish(self, content) -> None:
        if len(content) == 0:
            return None
        if self.old_content == content and self.pos == len(content)-1:
            return None
        if not self.target:
            await self.mount(Part())
        if self.process_busy:
            self.finish_pending = True
        else:
            self.finish_pending = False
            await self.finish_content(content)
            self.target = None

    async def process(self, content) -> None:
        if self.old_content == content:
            return None
        if self.process_busy:
            return None
        self.process_busy = True
        if not self.old_content[:-self.pp.bsize] == content[:len(self.old_content)-self.pp.bsize]:
            await self.reset()
            self.process_busy = True
        if not self.target:
            await self.mount(Part())
        await self.process_content(content)
        self.process_busy = False
        if self.finish_pending:
            await self.finish()
