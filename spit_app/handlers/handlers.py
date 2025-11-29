# SPDX-License-Identifier: GPL-2.0
from textual import events
import spit_app.message as message
import spit_app.utils as utils

class HandlersMixIn:
    async def on_ready(self) -> None:
        await utils.render_messages(self)

    def on_worker_state_changed(self) -> None:
        self.refresh_bindings()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        message.is_y_max(self)
        if self.chat_view == event.control:
            if self.focused_message:
                self.focused_message.focus()
        message.if_y_max_scroll_end(self)

    def on_text_area_changed(self) -> None:
        if self.text_area.text:
            if self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = False
        else:
            if not self.text_area_was_empty:
                self.refresh_bindings()
                self.text_area_was_empty = True
