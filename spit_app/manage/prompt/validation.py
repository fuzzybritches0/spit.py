class ValidationMixIn:
    def valid_values_edit(self) -> bool:
        if not self.query_one("#name").is_valid:
            return False
        if not self.query_one("#text").text:
            return False
        return True

    def is_not_empty(self, value) -> bool:
        if value:
            return True
        return False
