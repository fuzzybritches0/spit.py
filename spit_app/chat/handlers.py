# SPDX-License-Identifier: GPL-2.0
from textual import events
import spit_app.chat.render as render
import spit_app.latex_math as lm
from spit_app.overlays.loading_screen import LoadingScreen

class HandlersMixIn:
    async def on_mount(self) -> None:
        if not self.messages:
            self.query_one("#text-area").focus()
        loading_screen = LoadingScreen()
        await self.app.push_screen(loading_screen)
        await render.messages(self)
        await loading_screen.dismiss()

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if event.control is self.query_one("#chat-view"):
            if self.focused_message:
                self.focused_message.focus(scroll_visible=False)
            elif not self.messages:
                self.query_one("#text-area").focus()
        elif event.control.id and ("-listing-" in event.control.id or
                                   "message-id-" in event.control.id):
            self.focused_message = event.control

class TextAreaHandlersMixIn:
    def on_text_area_changed(self) -> None:
        if self.text:
            if self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = False
        else:
            if not self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = True

class ChatViewHandlersMixIn:
    async def on_theme_changed(self, old_value:str, new_value:str) -> None:
        cont_count=0
        for message_container in self.chat.latex_listings:
            latex_count=0
            for latex in message_container:
                id="latex-listing-"+str(cont_count)+"-"+str(latex_count)
                container = self.query_one(f"#{id}")
                color = container.parent.styles.color.css
                background = container.parent.styles.background.css
                sequence = self.chat.latex_listings[cont_count][latex_count]
                if sequence.startswith("$") and not sequence.startswith("$$"):
                    sequence = sequence[1:-1]
                else:
                    sequence = sequence[2:-2]
                latex_image = lm.latex_math(self, sequence.strip(" \n"), color, background)
                if latex_image:
                    await container.remove_children()
                    await container.mount(latex_image)
                latex_count+=1
            cont_count+=1
