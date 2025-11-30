# SPDX-License-Identifier: GPL-2.0
from textual import events
import spit_app.utils as utils
import spit_app.latex_math as lm

class HandlersMixIn:
    async def on_ready(self) -> None:
        await utils.render_messages(self)
        if len(self.chat_view.children) == 0:
            self.text_area.focus()

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        if self.chat_view == event.control:
            if self.focused_message:
                self.focused_message.focus(scroll_visible=False)
        elif not self.text_area == event.control and not self.chat_view == event.control and not self.edit:
            self.focused_message = event.control
        elif self.edit and not event.control == self.text_area:
            self.focused_message.focus(scroll_visible=False)

    def on_text_area_changed(self) -> None:
        if self.text_area.text:
            if self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = False
        else:
            if not self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = True

    async def on_theme_changed(self, old_value:str, new_value:str) -> None:
        cont_count=0
        self.app.settings.theme = self.theme
        self.app.settings.save()
        for message_container in self.latex_listings:
            latex_count=0
            for latex in message_container:
                id="latex-listing-"+str(cont_count)+"-"+str(latex_count)
                container=self.query_one("#"+id)
                color = container.parent.styles.color.css
                background = container.parent.styles.background.css
                sequence = self.latex_listings[cont_count][latex_count]
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
