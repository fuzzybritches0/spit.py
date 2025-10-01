from textual import work
from spit_app.workstream import WorkStream
from spit_app.patterns.pattern_processing import PatternProcessing
import spit_app.message as message
import spit_app.utils as utils

@work(exclusive=True)
async def stream_response(self):
    self.streaming = True
    pp = PatternProcessing(self)
    content = ""
    reasoning_content = ""
    was_reasoning_content = False
    display_thinking = False
    self.refresh_bindings()
    await message.mount(self, "response", "")
    self.uisocket = ("response", "")

    workstream = WorkStream(self.config)
    async for ctype, buffer, part in workstream.stream(self.state["messages"]):
        if not self.streaming:
            break
        if buffer:
            await pp.process_patterns(True, buffer)
            if ctype == "content" and was_reasoning_content:
                pp.thinking = False
            if ctype == "reasoning_content":
                was_reasoning_content = True
                pp.thinking = True
            if not pp.thinking:
                if pp.skip_buff_p > 0:
                    pp.skip_buff_p -= 1
                else:
                    pp.paragraph += buffer[:1]
                if pp.skip_buff_c > 0:
                    pp.skip_buff_c -= 1
                else:
                    content += buffer[:1]
            else:
                content = ""
                pp.paragraph = ""
                if pp.skip_buff_c > 0:
                    pp.skip_buff_c -= 1
                else:
                    reasoning_content+=buffer[:1]
        if part:
            if pp.thinking:
                if not display_thinking == True:
                    dislplay_thinking = True
                    await message.update(self, "Thinking...")
            else:
                await message.update(self, pp.paragraph)

    self.streaming = False
    self.refresh_bindings()
    await message.update(self, pp.paragraph)
    if content:
        self.state["messages"].append({"role": "assistant",
                            "content": content})
    if reasoning_content:
        self.state["thoughts"].append({"role": "assistant",
                            "reasoning_content": reasoning_content})
    utils.write_chat_history(self)
