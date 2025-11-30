# SPDX-License-Identifier: GPL-2.0
from textual_image.widget import Image
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll

async def mount(self, mtype: str, content: str = "") -> None:
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
        if self.chat_view.children[-1] == self.focused_message:
            if len(self.chat_view.children) > 1:
                self.focused_message = self.chat_view.children[-2]
        await self.chat_view.children[-1].remove()
        del self.code_listings[-1]
        del self.latex_listings[-1]
