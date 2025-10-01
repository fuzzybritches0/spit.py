from typing import Generator, Tuple, List, Dict, Any
from .base import BaseEndpoint

class LlamaCppEndpoint(BaseEndpoint):

    @property
    def api_endpoint(self) -> str:
        return self.config.config["configs"][self.active]["api"]["endpoint_url"] + "/v1/chat/completions"

    def prepare_payload(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {}
        payload["messages"] = messages
        for setting, value in self.config.config["configs"][self.active]["options"].items():
            if value:
                payload[setting] = value
        payload["n_predict"] = -1
        payload["cache_prompt"] = True
        payload["stream"] = True
        return payload

    def extract_fields(self, delta: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        try:
            choice = delta["choices"][0]["delta"]
        except (KeyError, IndexError, TypeError):
            return

        if content := choice.get("content"):
            yield "content", content
        elif content := choice.get("reasoning_content"):
            yield "reasoning_content", content
