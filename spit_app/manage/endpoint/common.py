class Common:
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("escape", "cancel", "Cancel"),
        ("ctrl+t", "duplicate", "Duplicate"),
        ("ctrl+i", "remove_setting", "Remove Setting"),
        ("ctrl+o", "add_setting", "Add Setting")
    ]
    BUTTONS = (
        ("save", "Save"),
        ("cancel", "Cancel"),
        ("delete", "Delete"),
        ("duplicate", "Duplicate")
    )

    def add_custom_setting(self, setting: str, stype: str, desc: str, sarray: list = []) -> None:
        if not sarray:
            self.manage[setting] = { "stype": stype, "desc": desc }
        else:
            self.manage[setting] = { "stype": stype, "desc": desc , "options": sarray}

    async def remove_custom_setting(self, setting: str) -> None:
        del self.manage[setting]
        await self.query_one(f"#val-{setting}").remove()
