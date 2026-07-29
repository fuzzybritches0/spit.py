class ToolCall:
    def __init__(self, tool_call: list) -> None:
        self.tool_call = tool_call
        text = f"\n### function: `{self.tool_call['name']}`\n#### arguments:\n"
        self.formatted_tool_call = text
        self.last_char = ""
        self.pos = 0
        self.skip = False
        self.mark = 0
        self.key = False
        self.value = False
        self.json = []

    def tool_call_arguments(self) -> None:
        arguments = self.tool_call["arguments"]
        ret = ""
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
                    else:
                        self.value = not self.value
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
            if not self.skip:
                ret+=char
            self.skip = False
        self.pos = len(arguments)
        self.formatted_tool_call += ret
        return self.escaped()

    def escaped(self) -> str:
        ret = self.formatted_tool_call.rstrip("\\")
        ret = ret.replace(r'\"', '"')
        ret = ret.replace("\\n", "\n")
        ret = ret.replace("\\t", "\t")
        return ret.replace("\\\\", "\\")
