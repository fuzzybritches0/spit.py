# SPDX-Liicense-Identifier: GPL-2.0
import os
from spit_app.endpoints.llamacpp import LlamaCppEndpoint
from .textual_message import RemoveMessage

TOOL_PROMPT = "# FUNCTION CALLING INSTRUCTIONS\n\nAll of your function calls are rendered in human-readable form for the user to inspect. The user is also informed about the function call results and can see the tool response message. DO NOT REPEAT THEM!\n\n"

class Work:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.cs = chat.cs
        self.app = chat.app
        self.settings = chat.app.settings
        self.path = chat.app.path
        self.messages = chat.messages
        self.busy = False
        self.exit_after_busy = False
        prompt = self.prompt()
        endpoint = self.app.get_endpoint(self.cs("endpoint"))
        self.slot = -2
        model_settings = {}
        if self.cs("model_settings"):
            model_settings = self.settings.models[self.cs("model_settings")]
        tools_descs = []
        for _tool in self.app.tool_call.tools.keys():
            tool = self.app.tool_call.tools[_tool]
            if tool["desc"]["function"]["name"] in self.cs("tools") and self.req_mm_image(_tool):
                tools_descs.append(tool["desc"])
        self.endpoint = LlamaCppEndpoint(self.messages, endpoint, self.cs("model"), model_settings, prompt,
                                         tools_descs, self.chat_view.callback)

    def req_mm_image(self, tool: dict) -> bool:
        if self.app.tool_call.tools[tool]["requires_multimodal_image"] and not self.chat.has_cap("image"):
            return False
        return True

    def prompt_inst(self, tool) -> str:
        prompt = ""
        if "prompt_inst" in self.app.tool_call.tools[tool]:
            prompt = self.app.tool_call.tools[tool]["prompt_inst"]
            for setting in self.app.tool_call.tools[tool]["settings"].keys():
                value = self.app.tool_call.tools[tool]["settings"][setting]["value"]
                if tool in self.settings.tool_settings:
                    if setting in self.settings.tool_settings[tool]:
                        value = self.settings.tool_settings[tool][setting]["value"]
                prompt = prompt.replace(f"[{setting}]", str(value))
        return prompt

    def prompt(self) -> str:
        prompt = ""
        for tool in self.app.tool_call.tools.keys():
            if tool in self.cs("tools") and self.req_mm_image(tool):
                tool_prompt = self.app.tool_call.tools[tool]["settings"]["prompt"]["value"]
                if tool in self.settings.tool_settings:
                    if "prompt" in self.settings.tool_settings[tool]:
                        tool_prompt = self.settings.tool_settings[tool]["prompt"]["value"]
                prompt += f"## {tool}\n\n" + tool_prompt
                prompt += self.prompt_inst(tool)
        if prompt:
            prompt = TOOL_PROMPT + prompt
        if self.cs("prompt") and self.cs("prompt") in self.settings.prompts:
            chat_prompt = self.settings.prompts[self.cs("prompt")]["text"]["value"]
            prompt =  "# INSTRUCTIONS\n\n" + chat_prompt + "\n\n" + prompt
        return prompt

    def local_server_active(self) -> bool:
        if self.cs("endpoint") == "0" and self.app.server.is_running():
            return True
        return False

    async def maybe_load_model(self) -> None:
        if self.local_server_active():
            await self.app.server.load_model(self.cs("model"))

    async def before_work(self) -> None:
        if self.local_server_active() and self.app.server.gets("save_cache_prompt"):
            self.slot = await self.app.server.manage_cache.get_slot(self.cs("model"), self.chat.id)
            self.endpoint.endpoint["slot_id"] = {"stype": "uinteger", "value": self.slot}

    async def after_work(self) -> None:
        if self.local_server_active() and self.app.server.gets("save_cache_prompt"):
            await self.app.server.manage_cache.return_slot(self.cs("model"), self.chat.id, self.slot)

    async def work_stream(self) -> None:
        if "tool_calls" in self.messages[-1]:
            for tool_call in self.messages[-1]["tool_calls"]:
                self.busy = True
                await self.app.tool_call.call(self.messages, tool_call, self.chat.id, self.chat_view.callback)
                self.busy = False
                if self.exit_after_busy:
                    return None
        count = len(self.messages)
        await self.maybe_load_model()
        await self.before_work()
        try:
            if self.endpoint == -1:
                self.app.exception = Exception("No free slot for inference available! Please try again later!")
            await self.endpoint.stream()
        except Exception as exception:
            if type(exception).__name__ in ("TimeoutError", "ReadTimeout", "ConnectError",
                                            "RuntimeError", "ConnectTimeout",
                                            "RemoteProtocolError"):
                self.app.exception = exception
                if len(self.messages) > count:
                    self.chat_view.post_message(RemoveMessage(len(self.messages)-1))
                self.chat.chat_settings.update_models()
                return None
            else:
                raise exception
        await self.after_work()
        if "tool_calls" in self.messages[-1]:
            await self.work_stream()
