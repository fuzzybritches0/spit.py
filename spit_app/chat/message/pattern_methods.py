from .containers.part import Part
from .containers.code import Code
from .containers.latex import LaTeX

def complete(self) -> str:
    return self.message.target.source + self.part

async def latex_start_end(self, buffer: str, pattern: str, is_display: bool = False) -> None:
    if (not self.pp_last.isalnum() and
        not self.pp_next == "'" and
        not self.pp_next == '"' and
        not self.pp_next == "`" and
        self.seqstart == -1):
        latex_start(self, buffer, pattern)
    elif (not self.pp_next.isalnum() and
          not self.pp_last == "'" and
          not self.pp_last == '"' and
          not self.pp_last == "`" and
          self.seqstart > -1):
        await latex_end(self, buffer, pattern, pattern, is_display)
    elif (not self.pp_last.isalnum() and
          not self.pp_next == "'" and
          not self.pp_next == '"' and
          not self.pp_next == "`"):
        latex_start(self, buffer, pattern)

def latex_start(self, buffer: str, pattern: str) -> None:
    if not self.cur_latex_fence:
        self.latex = True
        self.cur_latex_fence = pattern
        self.seqstart = len(complete(self)) + len(pattern)

async def latex_end(self, buffer: str, pattern: str, exp_latex_fence: str, is_display: bool = False) -> None:
    if self.seqstart > -1 and self.cur_latex_fence == exp_latex_fence:
        sequence = complete(self)[self.seqstart:]
        escaped = 0
        if self.escaped:
            sequence = sequence[:-1]
            escaped = 1
        if  not sequence.strip() == "..." and not sequence.strip() == "…" and not sequence.strip() == "and":
            await self.message.target.update(complete(self)[:self.seqstart-len(pattern)-escaped])
            self.part = ""
            await self.message.mount(LaTeX(self.message.chat, sequence, exp_latex_fence, pattern))
            await self.message.mount(Part())
            self.skip_add_part = len(pattern)+escaped
        self.latex = False
        self.seqstart = -1
        self.cur_latex_fence = ""

async def code_fence(self, buffer: str, pattern: str) -> None:
    if not self.pp_last == pattern and not self.pp_next == pattern:
        self.proc_code_fence = pattern
        self.done_code_fence = True
    elif not self.pp_last == pattern and self.pp_next == pattern:
        self.proc_code_fence = pattern
    elif self.pp_last == pattern and self.pp_next == pattern:
        self.proc_code_fence += pattern
    elif self.pp_last == pattern and not self.pp_next == pattern:
        self.proc_code_fence += pattern
        self.done_code_fence = True
    if self.done_code_fence:
        if len(self.proc_code_fence) < 3:
            code_listing(self, self.proc_code_fence)
            self.proc_code_fence = ""
        else:
            await code_block_start_end(self, self.proc_code_fence)
            self.proc_code_fence = ""
        self.done_code_fence = False

async def code_block_start_end(self, pattern: str) -> None:
    if not self.cur_code_fence:
        _complete = complete(self)[:-len(pattern)+1]
        if not _complete or _complete[-1] == "\n":
            await code_block_start(self, pattern)
        elif _complete.rstrip(" ").endswith("\n") or _complete.rstrip(" ") == "":
            await code_block_start(self, pattern)
    elif self.cur_code_fence == pattern:
        await code_block_end(self, pattern)

async def code_block_start(self, pattern: str) -> None:
    await self.message.target.append(self.part)
    await self.message.target.update(self.message.target.source[:-len(pattern)+1])
    self.part = pattern[1:]
    await self.message.mount(Code(self.message.chat))
    self.cur_code_fence = pattern
    self.codeblock = True

async def code_block_end(self, pattern: str) -> None:
    self.cur_code_fence = ""
    self.codeblock = False
    self.skip_add_part = 1
    await self.message.target.append(self.part+pattern[:1])
    self.part = ""
    await self.message.target.update_code()
    await self.message.mount(Part())

def code_listing(self, pattern: str) -> None:
    if not self.codeblock:
        if not self.cur_code_fence:
            self.cur_code_fence = pattern
            self.codelisting = True
        elif self.cur_code_fence == pattern:
            self.cur_code_fence = ""
            self.codelisting = False

def is_roster(self, buffer: str, pattern: str) -> None:
    self.roster = True

def end_roster(self, buffer: str, pattern: str) -> None:
    self.roster = False

def escape(self, buffer: str, pattern: str) -> None:
    self.escaped = not self.escaped
