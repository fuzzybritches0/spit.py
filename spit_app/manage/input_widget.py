import inspect
from textual.widgets import OptionList, Input, TextArea, Switch, Label, Select, SelectionList, Markdown
from .validation import rid, fid

class InputWidget:
    def __init__(self, methods, manage: dict, validators: callable):
        self.methods = methods
        self.manage = manage
        self.validators = validators

    def get_setting(self, setting: str) -> tuple:
        value = ""
        if "value" in self.manage[setting]:
            value = self.manage[setting]["value"]
        stype = self.manage[setting]["stype"]
        desc = self.manage[setting]["desc"]
        return str(value), stype, desc

    async def get_tuple(self, setting: str) -> tuple:
        if "ameth" in self.manage[setting]:
            ameth = getattr(self.methods, self.manage[setting]["ameth"])
            if inspect.iscoroutinefunction(ameth):
                return await ameth()
            else:
                return ameth()
        if "options" in self.manage[setting]:
            tup = ()
            for el in self.manage[setting]["options"]:
                tup += ((el, el),)
            return tup
        return ()

    def get_widget(self, stype: str) -> str:
        if stype in ["select", "select_no_default", "select_list", "boolean", "text"]:
            return stype
        else:
            return "string"

    async def setting(self, setting: str) -> list:
        id = rid(setting)
        value, stype, desc = self.get_setting(setting)
        tup = await self.get_tuple(setting)
        ret = [Label(f"{desc}: ({stype})", id="label-" + id)]
        return ret + getattr(self, self.get_widget(stype))(id, value, stype, desc, tup)

    def select(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        if not value or not value in (i for n, i in tup):
            value = Select.NULL
        return [Select(tup, id=id, value=value, prompt="Default")]
        
    def select_no_default(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        if not value or not value in (i for n, i in tup):
            value = tup[0][1]
        return [Select(tup, id=id, value=value, allow_blank=False)]

    def select_list(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        if not value:
            value = []
        ltup = ()
        for n, i in tup:
            if n in value:
                ltup += ((n, i, True),)
            else:
                ltup += ((n, i, False),)
        return [SelectionList(*ltup, id=id)]

    def boolean(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        return [Switch(id=id, value=value)]

    def text(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        return [TextArea(value, id=id, classes="text-area"), Markdown(id=f"val-{id}")]

    def string(self, id: str, value: str, stype: str, desc: str, tup: tuple) -> list:
        validators = self.validators(fid(id), id, stype)
        return [Input(validators=validators, id=id, value=value), Markdown(id=f"val-{id}")]
