# SPDX-License-Identifier: GPL-2.0
import abc
import json
import httpx
from typing import Generator, Tuple, List, Dict, Any

class BaseEndpoint(abc.ABC):
    api_key: str | None
    timeout: float | None = None
    extra_headers: Dict[str, str] = {}

    def __init__(self, app, timeout: float | None = None,
                 extra_headers: Dict[str, str] | None = None):
        self.config = app.config
        self.app = app
        self.active = self.config.active_endpoint
        self.api_key = None
        if "key" in self.config.endpoints[self.active]["values"]:
            self.api_key = self.config.endpoints[self.active]["values"]["key"]
        if timeout is not None:
            self.timeout = timeout
        if extra_headers:
            self.extra_headers = extra_headers
        self.extra_init()

    @abc.abstractmethod
    def extra_init(self) -> None:
        ...

    @property
    @abc.abstractmethod
    def api_endpoint(self) -> str:
        ...

    @abc.abstractmethod
    def prepare_payload(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def extract_fields(self, delta: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        ...

    @abc.abstractmethod
    def tool_calls(self, content: str) -> Generator[Tuple[str, str], None, None]:
        ...

    async def stream(self, messages: List[Dict[str, Any]]) -> Generator[Tuple[str, str], None, None]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        headers.update(**self.extra_headers)
        payload = self.prepare_payload(messages)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", self.api_endpoint, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    raise RuntimeError(f"Endpoint returned {resp.status_code}: {resp.text}")

                async for raw_line in resp.aiter_lines():
                    if not raw_line or not raw_line.startswith("data:"):
                        continue

                    line = raw_line[5:].strip()
                    if not line:
                        continue

                    try:
                        delta = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    for field, value in self.extract_fields(delta):
                        yield field, value
