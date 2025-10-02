from spit_app.config.validation import Validation

def get_settings(self) -> dict:
    val = Validation(self)
    return [
        ("name", str, "Config name", "default config", val.is_not_empty, val.is_unique_name),
        ("endpoint_url", str, "API Endpoint URL", "http://127.0.0.1:8080", val.is_url),
        ("key", str, "API Access Key", "none", val.is_anything),
        ("temperature", float, "Temperature", "default", val.is_valid_float),
        ("top_p", float, "TOP-P", "default", val.is_valid_float),
        ("min_p", float, "MIN-P", "default", val.is_valid_float),
        ("top_k", float, "TOP-K", "default", val.is_valid_float)
    ]
