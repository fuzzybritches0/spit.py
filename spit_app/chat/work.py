# SPDX-Liicense-Identifier: GPL-2.0
import os
import asyncio
from spit_app.endpoints.llamacpp import LlamaCppEndpoint
from spit_app.modal_screens import LoadProgressBarScreen
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
            if self.cs("model") in self.app.server.active_models:
                return None
            if self.app.server.active_models and not self.app.server.gets("keep_models_loaded"):
                for model in self.app.server.active_models:
                    self.app.action_notify(f"Unloading {model}...")
                    await self.app.server.model_action(model, "unload")
            model = self.cs("model")
            await self.app.server.model_action(model, "load")
            self.app.load_progress_bar_screen = LoadProgressBarScreen()
            self.app.push_screen(self.app.load_progress_bar_screen)
            self.app.load_progress_bar_screen.update_text(f"Loading {model}...")
            self.app.load_progress_bar_screen.update_total(100)
            while True:
                if model in self.app.server.active_models:
                    break
                if self.app.load_progress_bar_screen:
                    self.app.load_progress_bar_screen.update_progress(self.app.server.model_load_progress)
                else:
                    return None
                await asyncio.sleep(1)
            await self.app.load_progress_bar_screen.dismiss()
            self.app.load_progress_bar_screen = None

    async def maybe_restore_cache(self) -> None:
        if self.local_server_active() and self.app.server.gets("save_cache_prompt"):
            if self.app.server.current_cache_id == self.chat.id:
                return None
            if os.path.isfile(self.path["prompt_cache"] / self.chat.id):
                self.app.action_notify("Restoring prompt cache...")
                await self.app.server.cache_action(self.chat.id, "restore")
            self.app.server.current_cache_id = self.chat.id

    async def maybe_save_cache(self) -> None:
        if self.local_server_active() and self.app.server.gets("save_cache_prompt"):
            await self.app.server.cache_action(self.chat.id, "save")

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
        await self.maybe_restore_cache()
        try:
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
        await self.maybe_save_cache()
        if "tool_calls" in self.messages[-1]:
            await self.work_stream()
