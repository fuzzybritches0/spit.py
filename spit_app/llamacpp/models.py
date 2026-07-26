MODELS = {
    "oq4LVj9KYJmczNlVkOH0paBrfI21NjAj": {
        "name": "Gemma-4-E2B-it",
        "org": "google",
        "model": "gemma-4-E2B-it-qat-q4_0-gguf",
        "files": ["gemma-4-E2B_q4_0-it.gguf", "gemma-4-E2B-it-mmproj.gguf"]
    },
    "YkCx4J7XuBMW3T2gVTuYc2Amj9aon5H6": {
        "name": "Gemma-4-E4B-it",
        "org": "google",
        "model": "gemma-4-E4B-it-qat-q4_0-gguf",
        "files": ["gemma-4-E4B_q4_0-it.gguf", "gemma-4-E4B-it-mmproj.gguf"]
    },
    "DGbza622FFHxzwY75n1DB1PW3hkPa7zN": {
        "name": "Gemma-4-12B-it",
        "org": "google",
        "model": "gemma-4-12B-it-qat-q4_0-gguf",
        "files": ["gemma-4-12b-it-qat-q4_0.gguf", "mmproj-gemma-4-12b-it-qat-q4_0.gguf"]
    },
    "J8S1Wpe3mCcB8DFeg1b7ZA3jCZTERrZS": {
        "name": "Gemma-4-26B-A4B-it",
        "org": "google",
        "model": "gemma-4-26B-A4B-it-qat-q4_0-gguf",
        "files": ["gemma-4-26B_q4_0-it.gguf", "gemma-4-26B-it-mmproj.gguf"]
    },
    "zslSpCORNddn8CPeBr2zYsRJ9RFZdzRz": {
        "name": "Gemma-4-31B-it",
        "org": "google",
        "model": "gemma-4-31B-it-qat-q4_0-gguf",
        "files": ["gemma-4-31B_q4_0-it.gguf", "gemma-4-31B-it-mmproj.gguf"]
    }
}

MODELS_SETTINGS = {
    "1777914370-480791": {
        "name": {"stype": "string", "empty": False, "desc": "Name", "value": "Gemma-4"},
        "temperature": {"stype": "float", "desc": "Temperature", "value": 1.0},
        "top_p": {"stype": "float", "desc": "TOP-P", "value": 0.95},
        "top_k": {"stype": "float", "desc": "TOP-K", "value": 64.0},
        "chat_template_kwargs.enable_thinking": {"stype": "boolean", "desc": "Enable Thinking", "value": True},
        "repetition_penalty": {"stype": "float", "desc": "Repetition Penalty", "value": 1.1}
    }
}
