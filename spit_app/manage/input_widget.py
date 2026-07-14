import inspect
from textual.widgets import OptionList, Input, TextArea, Switch, Label, Select, SelectionList, Markdown
from .validation import rid, fid

class SelectMethod(Select):
    def __init__(self, *args, **kwargs):
        if "method" in kwargs:
            self.method = kwargs["method"]
            del kwargs["method"]
        super().__init__(*args, **kwargs)

    async def method_get_options(self) -> tuple:
            if inspect.iscoroutinefunction(self.method):
                return await self.method()
            else:
                return self.method()

    async def method_update_options(self) -> None:
        if self.method:
            options = await self.method_get_options()
            if not self._allow_blank and not options:
                options = (("None", "none"),)
            self.set_options(options)
            if not self.value or not self.value in (i for n, i in options):
                if self._allow_blank:
                    self._value = self.NULL
                else:
                    self._value = options[0][1]

class InputWidget:
    def __init__(self, methods, manage: dict, validators: callable) -> None:
        self.methods = methods
        self.manage = manage
        self.validators = validators

    def get_setting(self, setting: str) -> tuple:
        value = ""
        if "value" in self.manage[setting]:
            value = self.manage[setting]["value"]
        stype = self.manage[setting]["stype"]
        desc = self.manage[setting]["desc"]
        if stype == "boolean":
            return value, stype, desc
        else:
            return str(value), stype, desc

    def get_method(self, setting: str) -> callable:
        if "ameth" in self.manage[setting]:
            return getattr(self.methods, self.manage[setting]["ameth"])
        return None

    async def get_method_options(self, setting: str, method: callable) -> tuple:
        if inspect.iscoroutinefunction(method):
            return await method()
        else:
            return method()

    def get_options(self, setting: str) -> tuple|None:
        if "options" in self.manage[setting]:
            tup = ()
            for el in self.manage[setting]["options"]:
                tup += ((el, el),)
            return tup
        return None

    def get_widget(self, stype: str) -> str:
        if stype in ["select", "select_no_default", "select_list", "boolean", "text"]:
            return stype
        else:
            return "string"

    async def setting(self, setting: str, svalue: any = "__NONE__") -> list:
        id = rid(setting)
        value, stype, desc = self.get_setting(setting)
        if not svalue == "__NONE__":
            value = svalue
        tup = self.get_options(setting)
        method = self.get_method(setting)
        if method:
            tup = await self.get_method_options(setting, method)
        ret = [Label(f"{desc}: ({stype})", id="label-" + id)]
        return ret + getattr(self, self.get_widget(stype))(id, value, stype, method, tup)

    def select(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        if not value or not value in (i for n, i in tup):
            value = Select.NULL
        return [SelectMethod(tup, id=id, value=value, prompt="Default", method=method)]
        
    def select_no_default(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        if not value or not value in (i for n, i in tup):
            value = tup[0][1]
        return [SelectMethod(tup, id=id, value=value, allow_blank=False, method=method)]

    def select_list(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        if not value:
            value = []
        ltup = ()
        for n, i in tup:
            if n in value:
                ltup += ((n, i, True),)
            else:
                ltup += ((n, i, False),)
        return [SelectionList(*ltup, id=id)]

    def boolean(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        return [Switch(id=id, value=value)]

    def text(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        return [TextArea(value, id=id, classes="text-area"), Markdown(id=f"val-{id}")]

    def string(self, id: str, value: str, stype: str, method: callable, tup: tuple) -> list:
        validators = self.validators(id, stype)
        return [Input(validators=validators, id=id, value=value), Markdown(id=f"val-{id}")]
