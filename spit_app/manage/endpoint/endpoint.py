from .common import Common, bindings, buttons
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.manage import Manage

class Endpoints(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
    BINDINGS = bindings
    BUTTONS = buttons
    NEW = {
            "name": {"stype": "string", "empty": False, "desc": "Name"},
            "endpoint_url": {"stype": "url", "empty": False, "desc": "Endpoint URL",
                "value": "http://127.0.0.1:8080/v1"},
            "key": {"stype": "string", "desc": "API Access Key"},
            "timeout": {"stype": "uinteger", "empty": False,"desc": "Timeout (0 = no timeout)", "value": 0},
            "context_size": {"stype": "uinteger", "empty": False,
                             "desc": "Context Size (0 = auto-detect)", "value": 0},
            "reasoning_key": {"stype": "select_no_default", "desc": "Reasoning Key",
                            "options":["reasoning_content", "reasoning"]},
            "save_cache_prompt": {"stype": "boolean", "desc": "Save and restore Prompt Cache from file",
                "value": False},
            "parallel": {"stype": "uinteger", "desc": "Parallel Inference Threads (0 = auto/default)", "value": 0},
            # Per endpoint, like `timeout` and `context_size` (DECISIONS 84 a): a
            # flaky host and a local server on the same machine want different
            # numbers, and a global would give one of them the wrong one. Counted as
            # REQUESTS, so 1 is "no retry" and 3 is the owner's "at least 3 times".
            # Neither is ever sent to the server - both are on construct_payload's
            # skip list, and both are read with .get() so an endpoint saved before
            # they existed keeps working.
            "retry_attempts": {"stype": "uinteger",
                               "desc": "Requests per Reply on a Transient Failure (1 = no retry)",
                               "value": 3},
            "retry_delay": {"stype": "ufloat", "desc": "Delay Between Requests, Seconds", "value": 1.0}
    }

    def __init__(self) -> None:
        super().__init__("endpoint")
        self.managed = self.app.settings.endpoints
        self.save_managed = self.app.settings.save_endpoints
