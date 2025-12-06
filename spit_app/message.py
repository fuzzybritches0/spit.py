# SPDX-License-Identifier: GPL-2.0
import json
from textual_image.widget import Image
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll
from spit_app.patterns.pattern_processing import PatternProcessing

async def render_messages(self) -> None:
    for umessage in self.messages:
        await render_message(self, umessage)

async def render_message(self, umessage) -> None:
    if umessage["role"] == "user" and umessage["content"]:
        await _render_message(self, "request", umessage["content"])
    elif umessage["role"] == "assistant" and "content" in umessage and umessage["content"]:
        await _render_message(self, "response", umessage["content"])
    elif umessage["role"] == "assistant" and "tool_calls" in umessage and umessage["tool_calls"]:
        await _render_tool_calls(self, umessage["tool_calls"])
    elif umessage["role"] == "tool" and "content" in umessage and umessage["content"]:
        await _render_tool_response(self, umessage["content"])

async def _render_tool_calls(self, tool_calls) -> None:
    for tool_call in tool_calls:
        await _render_message(self, "response", "- TOOL CALL: `" + json.dumps(tool_call) + "`")

async def _render_tool_response(self, tool_response) -> None:
    await _render_message(self, "request", "- RESULT: `" + json.dumps(tool_response) + "`")

async def _render_message(self, mtype: str, messagec: str) -> None:
    buffer = ""
    pp = PatternProcessing(self)
    await mount(self, mtype)
    for char in messagec:
        buffer += char
        if len(buffer) < 8:
            continue
        await pp.process_patterns(False, buffer)
        if pp.skip_buff_p > 0:
            pp.skip_buff_p -= 1
        else:
            pp.paragraph += buffer[:1]
        buffer = buffer[1:]

    for char in buffer:
        await pp.process_patterns(False, buffer)
        if pp.skip_buff_p > 0:
            pp.skip_buff_p -= 1
        else:
            pp.paragraph += buffer[:1]
        buffer = buffer[1:]
    if not pp.paragraph:
        await remove(self)
    else:
        await update(self, pp.paragraph)

async def mount(self, mtype: str, content: str = "") -> None:
    if self.edit:
        self.message_container = self.edit_container
        id = int(self.message_container.id[11:])
        self.code_listings[id] = []
        self.latex_listings[id] = []
        await self.edit_container.remove_children()
    else:
        id=len(self.chat_view.children)
        self.message_container = VerticalScroll(classes="message-container-"+mtype, id="message-id-"+str(id))
    self.mwidget = Markdown(classes=mtype)
    self.mtype = mtype
    if not self.edit:
        await self.chat_view.mount(self.message_container)
        self.code_listings.append([])
        self.latex_listings.append([])
    await self.message_container.mount(self.mwidget)
    self.message_container.focus(scroll_visible=False)
    self.focused_message = self.message_container
    if content:
        await self.mwidget.update(content)

async def mount_next(self) -> None:
    self.mwidget = Markdown(classes=self.mtype)
    await self.message_container.mount(self.mwidget)

async def update(self, content: str) -> None:
    slen=len(self.mwidget.source)
    if self.mwidget.source == content[:slen]:
        await self.mwidget.append(content[slen:])
    else:
        await self.mwidget.update(content)

async def remove(self) -> None:
    await self.mwidget.remove()

async def mount_code(self) -> None:
    turn_id=len(self.code_listings)-1
    code_id=len(self.code_listings[turn_id])
    id="code-listing-"+str(turn_id)+"-"+str(code_id)
    self.code_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    self.mwidget = Markdown(classes=self.mtype)
    await self.message_container.mount(self.code_listing_container)
    await self.code_listing_container.mount(self.mwidget)

async def mount_latex(self, latex_image: Image) -> None:
    turn_id=len(self.latex_listings)-1
    latex_id=len(self.latex_listings[turn_id])
    id="latex-listing-"+str(turn_id)+"-"+str(latex_id)
    self.latex_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    await self.message_container.mount(self.latex_listing_container)
    await self.latex_listing_container.mount(latex_image)

async def remove_last_turn(self) -> None:
    if self.chat_view.children:
        if self.chat_view.children[-1] is self.focused_message:
            if len(self.chat_view.children) > 1:
                self.focused_message = self.chat_view.children[-2]
        await self.chat_view.children[-1].remove()
        del self.code_listings[-1]
        del self.latex_listings[-1]
