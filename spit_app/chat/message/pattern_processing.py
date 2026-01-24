import inspect
from .pattern_methods import *

patterns = [
        #PATTERN     ESCAPE  CODELI CODEBL ROSTER LATEX  METHOD ARGS...
        ("\\",       None,   False, False, None,  None,  escape),
        ("\n|",      False,  False, False, None,  False, is_roster),
        ("`",        False,  None,  None,  False, False, code_fence),
        ("~",        False,  None,  None,  False, False, code_fence),
        ("(",        True,   False, False, False, False, latex_start),
        (")",        True,   False, False, False, True,  latex_end, "("),
        ("[",        True,   False, False, False, False, latex_start),
        ("]",        True,   False, False, False, True,  latex_end, "[", True),
        ("$$",       False,  False, False, False, None,  latex_start_end, True),
        ("$",        False,  False, False, False, None,  latex_start_end),
        ("\n\n",     False,  False, False, None,  False, end_roster)
]

class PatternProcessing():
    def __init__(self, message) -> None:
        self.message = message
        self.escaped = False
        self.codelisting = False
        self.codeblock = False
        self.cur_code_fence = ""
        self.done_code_fence = False
        self.proc_code_fence = ""
        self.latex = False
        self.cur_latex_fence = ""
        self.seqstart = -1
        self.roster = False
        self.pp_last = ""
        self.bsize = 8
        self.part = ""
        self.skip_add_part = 0
        self.skip_pp = 0

    def add_part(self, buffer) -> None:
        if self.skip_add_part > 0:
            self.skip_add_part -= 1
        else:
            self.part += buffer[:1]

    def process_patterns_end(self, buffer) -> None:
        if not buffer[:1] == "\\":
            self.escaped = False
            self.pp_last = buffer[:1]

    async def process_patterns(self, buffer: str) -> None:
        if self.skip_pp > 0:
            self.skip_pp -= 1
        else:
            conditions = (self.escaped, self.codelisting, self.codeblock, self.roster, self.latex)
            c = [None, None, None, None, None]
            for pattern, c[0], c[1], c[2], c[3], c[4], method, *args in patterns:
                if buffer.startswith(pattern):
                    for pos in range(5):
                        if c[pos] is None:
                            continue
                        else:
                            if not conditions[pos] is c[pos]:
                                self.process_patterns_end(buffer)
                                self.add_part(buffer)
                                return None
                    self.pp_next = buffer[len(pattern):len(pattern)+1]
                    self.skip_pp = len(pattern) - 1
                    if inspect.iscoroutinefunction(method):
                        await method(self, buffer, pattern, *args)
                    else:
                        method(self, buffer, pattern, *args)
                    break
            self.process_patterns_end(buffer)
        self.add_part(buffer)
