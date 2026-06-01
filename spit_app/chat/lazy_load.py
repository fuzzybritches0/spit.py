# SPDX-License-Identifier: GPL-2.0
import asyncio
from textual import work

class LazyLoadMixIn:
    async def lazy_clear_messages(self) -> None:
        for message in self.displayed_children:
            await message.reset()
            message.display = False

    async def lazy_load_home_end(self, end: int) -> None:
        if self.displayed_children:
            if end == 1 and self.displayed_children[-1] is self.children[-1]:
                return None
            if end == -1 and self.displayed_children[0] is self.children[0]:
                return None
        await self.lazy_clear_messages()
        if end == 1:
            messages = reversed(self.children)
        else:
            messages = self.children
        for message in messages:
            if not message.processing:
                await message.finish()
            message.display = True
            await message.wait_for_refresh()
            if self.max_scroll_y > self.app.size.height:
                break
        self.focus_message()

    @work
    async def lazy_load_messages(self) -> None:
        while True:
            await asyncio.sleep(.1)
            if self.stop_worker:
                await self.remove_children()
                self.stop_worker()
                break
            if not self.messages:
                self.lazy_scroll_home_end = 0
                continue
            if not self.lazy_scroll_home_end == 0:
                await self.lazy_load_home_end(self.lazy_scroll_home_end)
                if self.lazy_scroll_home_end == 1:
                    self.scroll_end(animate=False, immediate=True)
                else:
                    self.scroll_home(animate=False, immediate=True)
                self.lazy_scroll_home_end = 0
                continue
            if self.scroll_y == self.max_scroll_y:
                if self.displayed_children[-1] is self.children[-1]:
                    continue
                await self.lazy_load_direction(-1, 1, 0)
            elif self.scroll_y == 0:
                if self.displayed_children[0] is self.children[0]:
                    continue
                await self.lazy_load_direction(0, -1, -1)

    async def lazy_load_direction(self, direction: int, add: int, end: int) -> None:
        id = int(self.displayed_children[direction].id.split("-")[2]) + add
        if not self.children[id].processing:
            await self.children[id].finish()
        self.children[id].display = True
        if direction == 0:
            await self.children[id].wait_for_refresh()
            height = self.children[id].outer_size.height
            self.scroll_relative(y=height+1, animate=False, immediate=True)
        height = self.displayed_children[end].outer_size.height
        if self.max_scroll_y - height > self.app.size.height:
            await self.displayed_children[end].reset()
            self.displayed_children[end].display = False
            if direction == -1:
                self.scroll_relative(y=-height-1, animate=False, immediate=True)
