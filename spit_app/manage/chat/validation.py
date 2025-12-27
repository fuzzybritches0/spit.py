class ValidationMixIn:
    def valid_values(self) -> bool:
        if not self.query_one("#desc").is_valid:
            return False
        return True
