import spit_app.patterns.pattern_methods as pm

patterns = [
        #PATTERN     STREAM THINK  ESCAPE  CODELI ROSTER AWAIT  METHOD ARGS...
        ("<think>",  True,  None,  None,   None,  None,  False, pm.is_thinking),
        ("</think>", True,  None,  None,   None,  None,  False, pm.is_not_thinking),
        ("\\",       None,  False, None,   False, None,  False, pm.escape),
        ("\n|",      None,  False, False,  False, None,  False, pm.is_roster),
        ("````",     None,  False, False,  None,  False, False, pm.code_block_start_end),
        ("```",      None,  False, False,  None,  False, False, pm.code_block_start_end),
        ("~~~~",     None,  False, False,  None,  False, False, pm.code_block_start_end),
        ("~~~",      None,  False, False,  None,  False, False, pm.code_block_start_end),
        ("`",        None,  False, False,  None,  None,  False, pm.code_listing),
        ("<",        None,  False, False,  False, None,  False, pm.escape_ltgt),
        (">",        None,  False, False,  False, None,  False, pm.escape_ltgt),
        ("(",        None,  False, True,   False, False, False, pm.latex_start),
        (")",        None,  False, True,   False, False, True,  pm.latex_end, "("),
        ("[",        None,  False, True,   False, False, False, pm.latex_start),
        ("]",        None,  False, True,   False, False, True,  pm.latex_end, "[", True),
        ("$$",       None,  False, False,  False, False, True,  pm.latex_start_end, True),
        ("$",        None,  False, False,  False, False, True,  pm.latex_start_end),
        ("\n\n",     None,  False, False,  False, None,  False, pm.end_roster)
]

class PatternProcessing:
    def __init__(self, app) -> None:
        self.app = app.app
        self.tool_call = False
        self.thinking = False
        self.escaped = False
        self.codelisting = False
        self.cur_code_fence = ""
        self.cur_latex_fence = ""
        self.roster = False
        self.thinkingdone = False
        self.seqstart = -1
        self.pp_skip = 0
        self.skip_buff_p = 0
        self.skip_buff_c = 0
        self.paragraph = ""
        self.pp_last = ""
    
    def process_patterns_end(self, buffer) -> None:
        if not buffer[:1] == "\\":
            self.escaped = False
            self.pp_last = buffer[:1]

    async def process_patterns(self, streaming: bool, buffer: str) -> None:
        if self.tool_call:
            return None
        if self.pp_skip > 0:
            self.pp_skip -= 1
            self.pp_last = ""
            return None
        conditions = (streaming, self.thinking, self.escaped, self.codelisting, self.roster)
        c = [None, None, None, None, None]
        for pattern, c[0], c[1], c[2], c[3], c[4], awaitm, method, *args in patterns:
            if buffer.startswith(pattern):
                for pos in range(5):
                    if c[pos] == None:
                        continue
                    else:
                        if not conditions[pos] == c[pos]:
                            self.process_patterns_end(buffer)
                            return None
                self.pp_skip = len(pattern)-1
                self.pp_next = buffer[len(pattern):len(pattern)+1]
                if awaitm:
                    await method(self, buffer, pattern, *args)
                else:
                    method(self, buffer, pattern, *args)
                break
        self.process_patterns_end(buffer)
