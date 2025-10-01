class Validation:
    def __init__(self, app) -> None:
        self.config = app.config
        self.app = app

    def is_url(self, value) -> bool:
        if self.is_default(value):
            return True
        if value.startswith("http://"):
            return True
        if value.startswith("https://"):
            return True
        return False
    
    def is_default(self, value) -> bool:
        if (value.lower() == "default" or
            value == ""):
            return True
        return False
    
    def is_float(self, value: str) -> bool:
        try:
            value = float(value)
            return True
        except:
            return False
    
    def is_int(self, value: str) -> bool:
        if "." in value:
            return False
        try:
            value = int(value)
            return True
        except:
            return False
    
    def is_valid_int(self, value: str) -> bool:
        if self.is_default(value):
            return True
        if self.is_int(value):
            return True
        return False
    
    def is_valid_float(self, value: str) -> bool:
        if self.is_default(value):
            return True
        if self.is_float(value):
            return True
        return False
    
    def is_anything(self, value: str) -> bool:
        return True

    def is_not_empty(self, value: str) -> bool:
        if not value or value.lower() == "default" or value.lower() == "none":
            return False
        return True

    def is_unique_name(self, value: str) -> bool:
        count = 0
        same = 0
        for config in self.config.config["configs"]:
            if (not count == self.app.cconfig and
                    config["api"]["name"] == value):
                same+=1
            count+=1
        if same > 0:
            return False
        return True
