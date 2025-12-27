import spit_app.chat.message as message
import spit_app.latex_math as lm

async def _remove_empty(self) -> None:
    if not self.paragraph.strip(" \n"):
        await message.remove(self.chat)
    else:
        await message.update(self.chat, self.paragraph)
    self.paragraph = ""

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
        esc=""
        if self.escaped:
            esc="\\"
            lenpat+=2
            lenepat+=1
        sequence = self.paragraph[self.seqstart:len(self.paragraph)-lenpat].strip("\n ")
        if not is_display and "\n" in sequence:
            if pattern == "$":
                sequence = None
                latex_start(self, buffer, pattern)
        render = True
        if (sequence == "..." or sequence == "…" or sequence == "and"):
            render = False
        latex_image = None
        self.paragraph = self.paragraph[:self.seqstart-lenepat]
        if sequence and render:
            color = self.chat.message_container.styles.color.css
            background = self.chat.message_container.styles.background.css
            latex_image = lm.latex_math(self, sequence.strip(" \n"), color, background)
        if latex_image:
            await _remove_empty(self)
            await message.mount_latex(self.chat, latex_image)
            turn_id=len(self.chat.latex_listings)-1
            self.chat.latex_listings[turn_id].append(esc + exp_latex_fence + sequence + esc + pattern)
            await message.mount_next(self.chat)
        else:
            await _remove_empty(self)
            await message.mount_code(self.chat)
            if pattern == "$$" or pattern == "]":
                exp_latex_fence += "\n"
                pattern = "\n" + pattern
            self.paragraph += "\n```latex\n" + esc + exp_latex_fence + sequence + esc + pattern + "\n```\n"
            await _code_block_end(self)
        self.skip_buff_p = len(pattern)
        self.seqstart = -1
        self.cur_latex_fence = ""

async def code_block_start_end(self, buffer: str, pattern: str) -> None:
    if not self.cur_code_fence:
        self.code_line_offset = 0
        if not self.pp_last or self.pp_last == "\n":
            await code_block_start(self, buffer, pattern)
        elif self.paragraph.rstrip(" ").endswith("\n"):
            self.code_line_offset = len(self.paragraph) - len(self.paragraph.rstrip(" "))
            await code_block_start(self, buffer, pattern)
    elif self.cur_code_fence == pattern:
        await code_block_end(self, buffer, pattern)

async def code_block_start(self, buffer: str, pattern: str) -> None:
    await _remove_empty(self)
    await message.mount_code(self.chat)
    self.cur_code_fence = pattern
    self.codelisting = True

def _code_line_offset(offset, code) -> str:
    code_lines = code.split("\n")
    code_ret = []
    for code_line in code_lines:
        code_ret.append(code_line[offset:])
    return "\n".join(code_ret)

async def _code_block_end(self) -> None:
    await message.update(self.chat, self.paragraph)
    turn_id=len(self.chat.code_listings)-1
    code = self.paragraph.strip("`~")
    code = code.split("\n",1)
    if len(code) == 2:
        code = code[1]
    else:
        code = code[0]
    if self.code_line_offset > 0:
        code = _code_line_offset(self.code_line_offset, code)
    self.chat.code_listings[turn_id].append(code.strip("\n"))
    self.paragraph = ""
    await message.mount_next(self.chat)

async def code_block_end(self, buffer: str, pattern: str) -> None:
    self.cur_code_fence = ""
    self.codelisting = False
    self.skip_buff_p = len(pattern)
    self.paragraph += pattern
    await _code_block_end(self)

def code_listing(self, buffer: str, pattern: str) -> None:
    if not self.cur_code_fence:
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

def end_roster(self, buffer: str, pattern: str) -> None:
    if self.seqstart == -1:
        self.roster = False

def escape(self, buffer: str, pattern: str) -> None:
    self.escaped = not self.escaped

def escape_ltgt(self, buffer: str, pattern: str) -> None:
    if buffer.startswith("<br>"):
        return None
    if self.paragraph.endswith("<br"):
        return None
    if pattern == "<" and self.pp_next.isalnum():
        self.paragraph+="\\"
    elif pattern == ">" and self.pp_last.isalnum():
        self.paragraph+="\\"
