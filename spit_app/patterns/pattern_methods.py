import spit_app.message as message
import spit_app.latex_math as lm

async def latex_start_end(self, buffer: str, pattern: str, is_display: bool = False) -> None:
    self.pp_skip = len(pattern)-1
    pp_next = buffer[len(pattern):len(pattern)+1]
    if (not self.pp_last.isalnum() and
        not pp_next == "'" and
        not pp_next == '"' and
        not pp_next == "`" and
        self.seqstart == -1):
        latex_start(self, buffer, pattern)
    elif (not pp_next.isalnum() and
          not self.pp_last == "'" and
          not self.pp_last == '"' and
          not self.pp_last == "`" and
          self.seqstart > -1):
        await latex_end(self, buffer, pattern, is_display)
    elif (not self.pp_last.isalnum() and
          not pp_next == "'" and
          not pp_next == '"' and
          not pp_next == "`"):
        latex_start(self, buffer, pattern)

def latex_start(self, buffer: str, pattern: str) -> None:
    self.seqstart = len(self.paragraph) + len(pattern)

async def latex_end(self, buffer: str, pattern: str, is_display: bool = False) -> None:
    if self.seqstart > -1:
        lenepat = len(pattern)
        lenpat = len(pattern)-2
        if self.escapeS:
            lenpat+=2
            lenepat+=1
        sequence = self.paragraph[self.seqstart:len(self.paragraph)-lenpat].strip("\n ")
        if not is_display and "\n" in sequence:
            if pattern == "$":
                sequence = None
                latex_start(self, buffer, pattern)
        if (sequence == "..." or sequence == "…" or sequence == "and"):
            sequence = None
        latex_image = None
        if sequence:
            latex_image = lm.latex_math(sequence)
        if latex_image:
            self.paragraph = self.paragraph[:self.seqstart-lenepat]
            if not self.paragraph.strip(" \n"):
                await message.remove(self.app)
            else:
                await message.update(self.app, self.paragraph)
            await message.mount_latex(self.app, latex_image)
            await message.mount_next(self.app)
            self.paragraph = ""
        self.skip_buff_p = len(pattern)
        self.seqstart = -1

async def code_block_start_end(self, buffer: str, pattern: str) -> None:
    pp_next = buffer[len(pattern):len(pattern)+1]
    self.pp_skip = 2
    if not self.paragraph.strip("\n` "):
        code_block_start(self, buffer, pattern)
    elif buffer.startswith("```\n"):
        await code_block_end(self, buffer, pattern)
    elif self.paragraph.rstrip(" `").endswith("\n") and pp_next.isalnum():
        await new_paragraph(self, buffer, pattern, 0)
        code_block_start(self, buffer, pattern)
    elif self.paragraph.rstrip(" `").endswith("\n"):
        await code_block_end(self, buffer, pattern)

def code_block_start(self, buffer: str, pattern: str) -> None:
    self.multiparagraph = True
    self.codelisting = True

async def code_block_end(self, buffer: str, pattern: str) -> None:
    self.multiparagraph = False
    self.codelisting = False
    self.skip_buff_p = 3
    self.paragraph += "```"
    await new_paragraph(self, buffer, pattern, 0)

def code_listing(self, buffer: str, pattern: str) -> None:
    self.codelisting = not self.codelisting

async def new_paragraph(self, buffer: str, pattern: str, skip: int = 1) -> None:
    if self.paragraph.strip("\n "):
        await message.update(self.app, self.paragraph)
        await message.mount_next(self.app)
    self.paragraph = ""
    self.pp_skip = skip
    self.seqstart = -1
    self.roster = False
    self.codelisting = False
    self.escapeS = False

def is_thinking(self, buffer: str, pattern: str) -> None:
    if not self.thinkingdone:
        self.thinking = True
    self.pp_skip = 6
    self.skip_buff_c = 7

def is_not_thinking(self, buffer: str, pattern: str) -> None:
    self.thinking = False
    self.thinkingdone = True
    self.pp_skip = 7
    self.skip_buff_c = 8

def is_roster(self, buffer: str, pattern: str) -> None:
    if self.seqstart == -1:
        self.pp_skip = 1
        self.roster = True

def escape(self, buffer: str, pattern: str) -> None:
    self.escapeS = not self.escapeS
