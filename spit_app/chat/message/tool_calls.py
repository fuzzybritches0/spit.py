class ToolCalls:
    def __init__(self, message) -> None:
        self.message = message.message
        self.cur_tool_call = 1
        self.cur_tool_call_head = 1
        self.parsed_tool_calls = ""

    def new_arguments(self) -> None:
        self.cur_tool_call_head += 1
        self.keyvalue = 0
        self.last_char = ""
        self.pos = 0
        self.skip = False

    def tool_call_arguments(self, arguments: str) -> None:
        ret = ""
        pos = self.pos
        for pos in range(self.pos, len(arguments)):
            char = arguments[pos:pos+1]
            if char == '"' and not self.last_char == "\\":
                self.skip = True
                self.keyvalue += 1
                if self.keyvalue % 4 == 1:
                    ret += "\n`"
                elif self.keyvalue % 4 == 2:
                    ret += "`:\n"
                else:
                    ret += "\n```\n"
            if self.keyvalue % 2 == 1:
                if self.skip:
                    self.skip = False
                else:
                    ret += char
            self.last_char = char
        self.pos = pos+1
        self.parsed_tool_calls += ret
        

    def format_tool_calls(self) -> None:
        if not self.parsed_tool_calls:
            self.parsed_tool_calls = "## TOOL CALLS\n"
        for tool_call in self.message["tool_calls"][self.cur_tool_call-1:]:
            if self.cur_tool_call == self.cur_tool_call_head:
                self.parsed_tool_calls += f"\n### function: `{tool_call['function']['name']}`\n#### arguments:\n"
                self.new_arguments()
            self.tool_call_arguments(tool_call["function"]["arguments"])
            self.parsed_tool_calls = self.parsed_tool_calls.replace(r'\"', '"')
            self.parsed_tool_calls = self.parsed_tool_calls.replace("\\n", "\n")
            if len(self.message["tool_calls"]) > self.cur_tool_call:
                self.cur_tool_call+=1

