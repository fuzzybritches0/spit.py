# SPDX-License-Identifier: GPL-2.0
from copy import deepcopy

class Undo:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.app = chat.app
        self.messages = chat.messages
        self.undo_list = []
        self.undo_index = -1

    # Each primitive changes the DATA and then brings the widget tree along. The
    # data half is window-blind by design and stays that way - it is the whole
    # history, and `write_chat_history` persists it. The widget half asks
    # `widget()` where it used to ask `children[...]`, and does NOTHING when the
    # message has no widget: an update to an unmounted message is data-only and
    # the widget rebuilds from its dict on re-entry (UI-ONDEMAND-LOADING.md
    # fact 6). All three hold `page_operations_held()` over their awaits, per
    # WP-D's hazard: `_grow_up` writes lo ABSOLUTELY while prune ADDS to it, so
    # a settled-scroll prune landing inside one of these is the corrupted
    # mounted range `t20` pins.

    async def _change(self, operation: str,message: dict, index: int) -> None:
        temp_message = deepcopy(self.messages[index])
        self.messages[index] = deepcopy(message)
        self.undo_list[self.undo_index] = [operation, deepcopy(temp_message), index]
        message_widget = self.chat_view.widget(index)
        if message_widget is None:
            # No widget, no redraw - and NO FOCUS. The old `require_widget` made
            # this raise (after the data and the undo entry had already been
            # written, so the entry was consumed and nothing persisted);
            # answering "unmounted" instead costs nothing, and a `focus()` here
            # would drag the reader across the history to a message they were
            # not looking at. The widget appears, already correct, when the
            # window reaches this index again.
            return None
        # The guard is what keeps a settled-scroll prune from evicting this
        # widget in the middle of its rebuild (prune asks the same flag before it
        # starts its removal batch); no per-widget lock is added here, because
        # nothing measured needs one.
        async with self.chat_view.page_operations_held():
            message_widget.message = self.messages[index]
            await message_widget.reset()
            await message_widget.finish()
            message_widget.focus()

    async def _insert(self, message: dict, index: int) -> None:
        if index == len(self.messages):
            self.messages.append(deepcopy(message))
        else:
            self.messages.insert(index, deepcopy(message))
        # The dict is in the data BEFORE the widget is asked for - that is
        # `mount_message`'s precondition, and what lets it tell an insert below
        # the window top from an insert above the bottom. Before that, this site
        # mounted with a bare `mount()`: at the open window the append landed at
        # the TAIL, `require_widget(index)` raised, and the chat came back with
        # the data changed, `lo` never slid and `write_chat_history()` never
        # reached (window (950,1001), 51 children, child0 projecting 951,
        # consistent=False).
        #
        # A far insert therefore costs the mount of everything between the
        # window and the index - measured on the 1k fixture at (80,24): 997
        # widgets in ~23.5 s headless, 0 bad frames, the reader still on 997
        # until the `focus()` below takes it to top=3. That is the price of
        # undoing an edit to a message the window released long ago, and it is
        # the same `materialize` the abort and submit paths already pay for the
        # tail. The window holds the anchor while it grows, so what the reader
        # was looking at does not move.
        async with self.chat_view.page_operations_held():
            inserted = await self.chat_view.mount_message(index)
            await inserted.finish()
            inserted.focus()

    async def _remove(self, index: int) -> None:
        view = self.chat_view
        # DECIDE FIRST, delete second. `del self.messages[index]` used to run
        # before the accessor, so a removal outside the window took the message
        # out of the history, raised, and left the data shorter than the widget
        # tree with nothing persisted (measured at the open window: 200 -> 199
        # messages, consistent=False, lo unchanged, no write).
        #
        # The three cases are asked of the WINDOW, not of a child count: below
        # it the data shifts under the mounted range and lo slides with it
        # (mirroring `on_remove_message` and `mount_message`); inside it the
        # widget goes under its own lock, which is what `prune()` takes when it
        # evicts; above it nothing is mounted and nothing moves.
        child = view.widget(index)
        async with view.page_operations_held():
            if child is not None:
                async with child.lock:
                    await child.remove()
            elif index < view.window_start:
                view.window_start -= 1
            del self.messages[index]
            # The vacated position: the message that followed took it, so
            # `widget(index)` is the neighbour to focus and removing the tail
            # leaves the one before it - the rule `on_remove_message` uses too,
            # so the two paths cannot disagree. Inside the guard, because a
            # prune that lands between the removal and the focus could evict the
            # widget the cursor is about to land on.
            view.focus_after_removal(index, child is not None)

    async def undo(self) -> None:
        if self.undo_index >= 0:
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._insert(message, index)
            elif operation == "insert":
                await self._remove(index)
            elif operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.undo_index-=1
            self.chat.refresh_bindings()

    async def redo(self) -> None:
        if self.undo_index < len(self.undo_list)-1:
            self.undo_index+=1
            operation, message, index = self.undo_list[self.undo_index]
            if operation == "remove":
                await self._remove(index)
            elif operation == "insert":
                await self._insert(message, index)
            elif operation == "change":
                await self._change(operation, message, index)
            self.chat.write_chat_history()
            self.chat.refresh_bindings()

    def append_undo(self, operation: str, message: dict, index: int) -> None:
        while len(self.undo_list)-1 > self.undo_index:
            del self.undo_list[-1]
        while len(self.undo_list) > 100:
            del self.undo_list[0]
        self.undo_list.append([operation, deepcopy(message), index])
        self.undo_index=len(self.undo_list)-1
