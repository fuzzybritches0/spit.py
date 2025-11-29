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
        self.chat_view.scroll_end(animate=False, force=True)

async def mount(self, mtype: str, content: str = "") -> None:
    is_y_max(self)
    if self.edit:
        self.message_container = self.edit_container
        id = int(self.message_container.id[3:])
        self.code_listings[id] = []
        self.latex_listings[id] = []
    else:
        id=len(self.chat_view.children)
        if len(self.messages) > 0 and self.messages[0]["role"] == "system":
            id+=1
        self.message_container = VerticalScroll(classes="message-container-"+mtype, id="message-id-"+str(id))
    self.mwidget = Markdown(classes=mtype)
    self.mtype = mtype
    if not self.edit:
        await self.chat_view.mount(self.message_container)
        self.code_listings.append([])
        self.latex_listings.append([])
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

async def mount_code(self) -> None:
    is_y_max(self)
    turn_id=len(self.code_listings)-1
    code_id=len(self.code_listings[turn_id])
    id="code-listing-"+str(turn_id)+"-"+str(code_id)
    self.code_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    self.mwidget = Markdown(classes=self.mtype)
    await self.message_container.mount(self.code_listing_container)
    await self.code_listing_container.mount(self.mwidget)
    if_y_max_scroll_end(self)

async def mount_latex(self, latex_image: Image) -> None:
    is_y_max(self)
    turn_id=len(self.latex_listings)-1
    latex_id=len(self.latex_listings[turn_id])
    id="latex-listing-"+str(turn_id)+"-"+str(latex_id)
    self.latex_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    await self.message_container.mount(self.latex_listing_container)
    await self.latex_listing_container.mount(latex_image)
    if_y_max_scroll_end(self)

async def remove_last_turn(self) -> None:
    if self.chat_view.children:
        is_y_max(self)
        if self.chat_view.children[-1] == self.focused_message:
            if len(self.chat_view.children) > 1:
                self.focused_message = self.chat_view.children[-2]
        await self.chat_view.children[-1].remove()
        del self.code_listings[-1]
        del self.latex_listings[-1]
        if_y_max_scroll_end(self)
