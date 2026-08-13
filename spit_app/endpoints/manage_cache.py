import httpx

class ManageCache:
    def __init__(self, app, endpoint_id, server_settings: any, address: str, api_key: str|None = None):
        self.app = app
        self.server_settings = server_settings
        self.address = address
        self.api_key = api_key
        if not endpoint_id in self.app.slots:
            self.app.slots[endpoint_id] = {}
        self.slots = self.app.slots[endpoint_id]

    async def cache_action(self, slot: int, cache_id: str, model: str, action: str) -> bool:
        endpoint = f"{self.address}/slots/{slot}?action={action}"
        headers = {}
        headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        json = {"filename": f"{cache_id}", "model": model}
        try:
            async with httpx.AsyncClient(timeout=720) as client:
                response = await client.post(endpoint, headers=headers, json=json)
        except:
            return False
        if response.status_code == 200:
            return True
        else:
            return False

    def clean_out_model_change(self, chat_id: str, model_id: str) -> None:
        for model in self.slots.keys():
            if model == model_id:
                continue
            count = 0
            for slot in self.slots[model]:
                if slot[0] == chat_id:
                    self.slots[model][count] = (None, False)
                    break
                count += 1

    async def restore_cache(self, slot: int, chat_id: str, model_id: str) -> None:
        if await self.cache_action(slot, chat_id, model_id, "restore"):
            self.app.action_notify("Restoring prompt cache...")

    async def save_cache(self, slot: int, chat_id: str, model_id: str) -> None:
        self.clean_out_model_change(chat_id, model_id)
        await self.cache_action(slot, chat_id, model_id, "save")

    async def return_slot(self, model_id: str, chat_id: str, slot: int) -> None:
        await self.save_cache(slot, chat_id, model_id)
        self.slots[model_id][slot] = (chat_id, False)

    async def get_slot(self, model_id: str, chat_id: str) -> int:
        parallel = self.server_settings["parallel"]["value"]
        if parallel == 0 or parallel == None:
            return await self.get_slot_unlimited(model_id, chat_id)
        else:
            return await self.get_slot_limited(parallel, model_id, chat_id)

    async def get_slot_unlimited(self, model_id: str, chat_id: str) -> int:
        if not model_id in self.slots:
            self.slots[model_id] = []
        for slot in range(0, len(self.slots[model_id])):
            if self.slots[model_id][slot][0] == chat_id:
                return slot
        self.slots[model_id].append((chat_id, True))
        slot = len(self.slots[model_id])-1
        await self.restore_cache(slot, chat_id, model_id)
        return slot

    async def get_slot_limited(self, parallel: int, model_id: str, chat_id: str) -> int:
        if not model_id in self.slots:
            self.slots[model_id] = []
            for slot in range(0, parallel):
                self.slots[model_id].append((None, False))
        for slot in range(0, parallel):
            if self.slots[model_id][slot][0] == chat_id:
                self.slots[model_id][slot] = (chat_id, True)
                return slot
        for slot in range(0, parallel):
            if self.slots[model_id][slot][0] == None:
                self.slots[model_id][slot] = (chat_id, True)
                await self.restore_cache(slot, chat_id, model_id)
                return slot
        for slot in range(0, parallel):
            if self.slots[model_id][slot][1] == False:
                self.slots[model_id][slot] = (chat_id, True)
                await self.restore_cache(slot, chat_id, model_id)
                return slot
        return -1
