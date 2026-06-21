class ToolCalls:
    def __init__(self, message) -> None:
        self.message = message.message
        self.cur_tool_call = 1
        self.cur_tool_call_head = 1
        self.parsed_tool_calls = []

    def new_arguments(self) -> None:
        self.cur_tool_call_head += 1
        self.last_char = ""
        self.pos = 0
        self.skip = False
        self.mark = 0
        self.key = False
        self.value = False
        self.json = []

    def tool_call_arguments(self, arguments: str) -> None:
        ret = ""
        pos = self.pos
        for pos in range(self.pos, len(arguments)):
            char = arguments[pos:pos+1]
            if (char == "{" or char == "[") and not self.value and not self.key:
                if len(self.json) == 0:
                    self.skip = True
                    self.key = True
                if len(self.json) == 1 and self.mark % 2 == 0:
                    self.mark += 1
                self.json += [char]
            elif (char == "}" or char == "]") and not self.value and not self.key:
                del self.json[-1]
                if len(self.json) == 1 and self.mark % 2 == 1:
                    ret += f"{char}\n~~~~\n"
                    self.skip = True
                    self.mark += 1
                elif len(self.json) == 0:
                    self.skip = True
            if len(self.json) == 1:
                if char == '"' and not self.last_char == "\\":
                    self.mark += 1
                    self.skip = True
                    if self.key:
                        ret += "`"
                    elif self.value:
                        self.value = False
                    else:
                        self.value = True
                elif char == "`" and self.key:
                    self.mark +=1
                elif char == ":" and self.mark % 2 == 0 and self.key:
                    self.skip = True
                    self.key = False
                    ret += "\n~~~~\n"
                elif char == " " and not self.value and not self.key:
                    self.skip = True
                elif char == "," and self.mark % 2 == 0 and not self.key:
                    self.skip = True
                    self.key = True
                    ret += "\n~~~~\n"
            self.last_char = char
            if self.skip:
                self.skip = False
                continue
            ret+=char
        self.pos = pos+1
        self.parsed_tool_calls[-1]["text"] += ret
        
    def format_tool_calls(self) -> None:
        for tool_call in self.message["tool_calls"][self.cur_tool_call-1:]:
            if self.cur_tool_call == self.cur_tool_call_head:
                self.parsed_tool_calls.append({"type": "text", "text": ""})
                text = f"\n### function: `{tool_call['function']['name']}`\n#### arguments:\n"
                self.parsed_tool_calls[-1]["text"] += text
                self.new_arguments()
            self.tool_call_arguments(tool_call["function"]["arguments"])
            self.parsed_tool_calls[-1]["text"] = self.parsed_tool_calls[-1]["text"].replace(r'\"', '"')
            self.parsed_tool_calls[-1]["text"] = self.parsed_tool_calls[-1]["text"].replace("\\n", "\n")
            if len(self.message["tool_calls"]) > self.cur_tool_call:
                self.cur_tool_call+=1

