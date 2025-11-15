# SPDX-License-Identifier: GPL-2.0
from textual_image.widget import Image
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll
import spit_app.latex_math as lm

def is_y_max(self) -> None:
    self.chat_view_y_max = False
    if self.chat_view.scroll_y + 1 >= self.chat_view.max_scroll_y:
        self.chat_view_y_max = True

def if_y_max_scroll_end(self) -> None:
    if self.chat_view_y_max:
        self.chat_view.scroll_end(animate=False)

async def mount(self, mtype: str, content: str = "") -> None:
    is_y_max(self)
    if self.edit:
        self.message_container = self.edit_container
    else:
        id=len(self.chat_view.children)
        if len(self.state) > 0 and self.state[0]["role"] == "system":
            id+=1
        self.message_container = VerticalScroll(classes="message-container-"+mtype, id="id_"+str(id))
    self.mwidget = Markdown(classes=mtype)
    self.mtype = mtype
    if not self.edit:
        await self.chat_view.mount(self.message_container)
    await self.message_container.mount(self.mwidget)
    self.message_container.focus()
    self.focused_message = self.message_container
    if content:
        await self.mwidget.update(content)
    if_y_max_scroll_end(self)

async def mount_next(self) -> None:
    is_y_max(self)
    self.mwidget = Markdown(classes=self.mtype)
    await self.message_container.mount(self.mwidget)
    if_y_max_scroll_end(self)

async def update(self, content: str) -> None:
    is_y_max(self)
    slen=len(self.mwidget.source)
    if self.mwidget.source == content[:slen]:
        await self.mwidget.append(content[slen:])
    else:
        await self.mwidget.update(content)
    if_y_max_scroll_end(self)

async def remove(self) -> None:
    is_y_max(self)
    await self.mwidget.remove()
    if_y_max_scroll_end(self)

async def mount_latex(self, latex_image: Image) -> None:
    is_y_max(self)
    await self.message_container.mount(latex_image)
    if_y_max_scroll_end(self)

async def remove_last_turn(self) -> None:
    if self.chat_view.children:
        is_y_max(self)
        if self.chat_view.children[-1] == self.focused_message:
            if len(self.chat_view.children) > 1:
                self.focused_message = self.chat_view.children[-2]
        await self.chat_view.children[-1].remove()
        if_y_max_scroll_end(self)
