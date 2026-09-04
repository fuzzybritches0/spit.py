# SPDX-License-Identifier: GPL-2.0
FENCE = "\n~~~~~\n"


class ToolCall:
    # The render is a sequence of `key` label lines and fenced value blocks:
    # every `:` opens a value fence and the fence closes again when the value
    # ends - before the next key or at the closing brace. Fences are the code
    # block language of the render pipeline (pattern_methods), so they must
    # always balance: one more emitted newline-fence than values would leave
    # the last value inside an unclosed block. 5 tildes match the tool hint
    # fences of Process (process.py) and out-length the `~~~~` runs that tool
    # arguments and tool output contain, so those stay literal inside the
    # block (a fence only closes against one of the same character and at
    # least its length).
    def __init__(self, tool_call: list) -> None:
        self.tool_call = tool_call
        text = f"\n### function: `{self.tool_call['name']}`\n#### arguments:\n"
        self.formatted_tool_call = text
        self.pos = 0
        self.json = []
        self.in_string = False
        self.escaped = False
        self.key = False
        self.in_value_fence = False

    def decoded_escape(self, char: str) -> str:
        if char == "n":
            return "\n"
        if char == "t":
            return "\t"
        if char == "\\" or char == '"':
            return char
        return "\\" + char

    def close_value_fence(self, ret: str) -> str:
        if self.in_value_fence:
            self.in_value_fence = False
            return ret + FENCE
        return ret

    def tool_call_arguments(self) -> str:
        arguments = self.tool_call.get("arguments", "")
        ret = ""
        for pos in range(self.pos, len(arguments)):
            char = arguments[pos:pos+1]
            if self.escaped:
                self.escaped = False
                ret += self.decoded_escape(char)
            elif self.in_string:
                if char == "\\":
                    self.escaped = True
                elif char == '"':
                    self.in_string = False
                    if self.key:
                        ret += "`"
                    elif len(self.json) > 1:
                        ret += char
                else:
                    ret += char
            elif not self.json:
                if char == "{" or char == "[":
                    self.json += [char]
                    self.key = True
                else:
                    ret += char
            elif char == '"':
                self.in_string = True
                if self.key:
                    ret += "`"
                elif len(self.json) > 1:
                    ret += char
            elif char == "{" or char == "[":
                self.json += [char]
                ret += char
            elif char == "}" or char == "]":
                del self.json[-1]
                if self.json:
                    ret += char
                    if len(self.json) == 1:
                        ret = self.close_value_fence(ret)
                        self.key = True
                else:
                    ret = self.close_value_fence(ret)
            elif len(self.json) == 1 and char == ":" and self.key:
                ret += FENCE
                self.key = False
                self.in_value_fence = True
            elif len(self.json) == 1 and char == ",":
                if not self.key:
                    ret = self.close_value_fence(ret)
                self.key = True
            elif len(self.json) == 1 and char == " " and not self.key:
                None
            else:
                ret += char
        self.pos = len(arguments)
        self.formatted_tool_call += ret
        return self.formatted_tool_call
