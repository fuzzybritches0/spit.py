from .common import Common
from .actions import ActionsMixIn
from .handlers import HandlersMixIn
from .screens import ScreensMixIn
from .validation import ValidationMixIn
from spit_app.manage.manage import Manage

class Endpoints(Common, ActionsMixIn, HandlersMixIn, ScreensMixIn, ValidationMixIn, Manage):
    NEW = {
            "name": {"stype": "string", "empty": False, "desc": "Name"},
            "endpoint_url": { "stype": "url", "empty": False, "desc": "Endpoint URL",
                            "value": "http://127.0.0.1:8080"},
            "key": {"stype": "string", "desc": "API Access Key"},
            "timeout": {"stype": "uinteger", "empty": False,"desc": "Timeout (0 = no timeout)", "value": 0},
            "reasoning_key": { "stype": "select_no_default", "desc": "Reasoning Key",
                            "options":["reasoning_content", "reasoning"]}
    }

    def __init__(self) -> None:
        super().__init__("endpoint")
        self.managed = self.app.settings.endpoints
        self.save_managed = self.app.settings.save_endpoints
