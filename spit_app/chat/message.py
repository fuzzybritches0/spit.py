# SPDX-License-Identifier: GPL-2.0
from textual_image.widget import Image
from textual.widgets import Markdown
from textual.containers import VerticalScroll

async def mount(self, mtype: str, scroll_visible: bool, content: str = "") -> None:
    if self.edit:
        self.message_container = self.edit_container
        id = int(self.message_container.id[11:])
        self.code_listings[id] = []
        self.latex_listings[id] = []
        await self.edit_container.remove_children()
    else:
        id=len(self.query_one("#chat-view").children)
        self.message_container = VerticalScroll(classes="message-container-"+mtype,
                                                       id="message-id-"+str(id))
    self.mwidget = Markdown(classes=mtype)
    self.mtype = mtype
    if not self.edit:
        await self.query_one("#chat-view").mount(self.message_container)
        self.code_listings.append([])
        self.latex_listings.append([])
    await self.message_container.mount(self.mwidget)
    self.message_container.focus(scroll_visible=scroll_visible)
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
    code_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    self.mwidget = Markdown(classes=self.mtype)
    await self.message_container.mount(code_listing_container)
    await code_listing_container.mount(self.mwidget)

async def mount_latex(self, latex_image: Image) -> None:
    turn_id=len(self.latex_listings)-1
    latex_id=len(self.latex_listings[turn_id])
    id="latex-listing-"+str(turn_id)+"-"+str(latex_id)
    latex_listing_container = VerticalScroll(classes="code-listing-"+self.mtype, id=id)
    await self.message_container.mount(latex_listing_container)
    await latex_listing_container.mount(latex_image)

async def remove_last_turn(self) -> None:
    if self.query_one("#chat-view").children:
        if self.query_one("#chat-view").children[-1] is self.focused_message:
            if len(self.query_one("#chat-view").children) > 1:
                self.focused_message = self.query_one("#chat-view").children[-2]
        await self.query_one("#chat-view").children[-1].remove()
        del self.code_listings[-1]
        del self.latex_listings[-1]
