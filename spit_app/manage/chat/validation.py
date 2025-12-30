class ValidationMixIn:
    def valid_values(self) -> bool:
        if not self.query_one("#desc").is_valid:
            return False
        return True

    def is_not_empty(self, value) -> bool:
        if value:
            return True
        return False
