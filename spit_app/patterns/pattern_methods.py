import spit_app.message as message
import spit_app.latex_math as lm

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
        self.cur_latex_fence = pattern
        self.seqstart = len(self.paragraph) + len(pattern)

async def latex_end(self, buffer: str, pattern: str, exp_latex_fence: str, is_display: bool = False) -> None:
    if self.seqstart > -1 and self.cur_latex_fence == exp_latex_fence:
        lenepat = len(pattern)
        lenpat = len(pattern)-2
        if self.escapeS:
            lenpat+=2
            lenepat+=1
        sequence = self.paragraph[self.seqstart:len(self.paragraph)-lenpat]
        if not is_display and "\n" in sequence:
            if pattern == "$":
                sequence = None
                latex_start(self, buffer, pattern)
        if (sequence == "..." or sequence == "…" or sequence == "and"):
            sequence = None
        latex_image = None
        if sequence:
            latex_image = lm.latex_math(sequence.strip(" \n"))
            self.paragraph = self.paragraph[:self.seqstart-lenepat]
        if latex_image:
            if not self.paragraph.strip(" \n"):
                await message.remove(self.app)
            else:
                await message.update(self.app, self.paragraph)
            await message.mount_latex(self.app, latex_image)
            await message.mount_next(self.app)
            self.paragraph = ""
        else:
            self.paragraph += ("\n```latex\nINFO: unable to render!\n" +
                               exp_latex_fence + sequence + pattern + "\n```\n")
        self.skip_buff_p = len(pattern)
        self.seqstart = -1
        self.cur_latex_fence = ""

def code_block_start_end(self, buffer: str, pattern: str) -> None:
    if not self.pp_last or self.pp_last == "\n":
        if not self.cur_code_fence:
            code_block_start(self, buffer, pattern)
        elif self.cur_code_fence == pattern:
            code_block_end(self, buffer, pattern)

def code_block_start(self, buffer: str, pattern: str) -> None:
    self.cur_code_fence = pattern
    self.codelisting = True

def code_block_end(self, buffer: str, pattern: str) -> None:
    self.cur_code_fence = ""
    self.codelisting = False
    self.skip_buff_p = len(pattern)
    self.paragraph += pattern

def code_listing(self, buffer: str, pattern: str) -> None:
    self.codelisting = not self.codelisting

def is_thinking(self, buffer: str, pattern: str) -> None:
    if not self.thinkingdone:
        self.thinking = True
    self.skip_buff_c = 7

def is_not_thinking(self, buffer: str, pattern: str) -> None:
    self.thinking = False
    self.thinkingdone = True
    self.skip_buff_c = 8

def is_roster(self, buffer: str, pattern: str) -> None:
    if self.seqstart == -1:
        self.roster = True

def escape(self, buffer: str, pattern: str) -> None:
    self.escapeS = not self.escapeS

def escape_ltgt(self, buffer: str, pattern: str) -> None:
    if pattern == "<" and self.pp_next.isalnum():
        self.paragraph+="\\"
    elif pattern == ">" and self.pp_last.isalnum():
        self.paragraph+="\\"
