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
        self.unesc_pos = 0
        self.unesc_skip = False
        self.unesc_last_char = ""
        self.unesc_tool_call = ""

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
                    self.key = True
                    self.mark += 1
                self.skip = True
            elif len(self.json) == 1:
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
                elif char == "," and self.mark % 2 == 0:
                    if not self.key:
                        self.skip = True
                        self.key = True
                        ret += "\n~~~~\n"
                    else:
                        self.skip = True
            self.last_char = char
            if not self.skip:
                ret+=char
            self.skip = False
        self.pos = len(arguments)
        self.formatted_tool_call += ret
        return self.unescaped()

    def unescaped(self) -> str:
        newlines = self.formatted_tool_call[self.unesc_pos:].rstrip(r"\\")
        self.unesc_pos += len(newlines)
        newlines = newlines.replace(r"\n", "\n")
        newlines = newlines.replace(r"\t", "\t")
        newlines = newlines.replace(r"\\\\", "\\")
        newlines = newlines.replace(r'\"', '"')
        for pos in range(0, len(newlines)):
            char = newlines[pos:pos+1]
            if self.unesc_last_char == "\\" and char == "\n":
                self.unesc_skip = True
                self.unesc_tool_call = self.unesc_tool_call[:-1] + r"\n"
            if self.unesc_last_char == "\\" and char == "\t":
                self.unesc_skip = True
                self.unesc_tool_call = self.unesc_tool_call[:-1] + r"\t"
            if self.unesc_last_char == "\\" and char == "\\":
                self.unesc_skip = True
                self.unesc_tool_call = self.unesc_tool_call[:-1] + r"\\"
            if not self.unesc_skip:
                self.unesc_tool_call += char
            self.unesc_skip = False
            self.unesc_last_char = char
        return self.unesc_tool_call
