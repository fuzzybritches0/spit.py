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
    },
    "sdfapi8ajdaSD3eFD3094jfkjfaDSF34": {
        "name": "Qwen3.6-35B-A3B-Q4_K_M",
        "org": "ggml-org",
        "model": "Qwen3.6-35B-A3B-GGUF",
        "files": ["Qwen3.6-35B-A3B-Q4_K_M.gguf", "mmproj-Qwen3.6-35B-A3B-Q8_0.gguf"]
    },
    "feT7f0Ba3fkl56GLcxtshmqG13fDDkju": {
        "name": "Muse-Glimmer-30B",
        "org": "meta-models",
        "model": "Muse-Glimmer-30B-GGUF",
        "files": ["Muse-Glimmer-30B-KQuant-Dynamic-Q4_K_XL.gguf", "mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"]
    }
}

NEW_MODELS_SERVER_SETTINGS = {
    "device": {"stype": "select_list", "desc": "Use Vulkan devices", "options": [], "value": []},
    "parallel": {"stype": "uinteger", "desc": "Parallel Inference Threads (0 = auto/default)", "value": 1},
    "kv-unified": {"stype": "boolean", "desc": "Divide single KV Cache amongst Threads", "value": False},
    "ctx-size": {"stype": "uinteger", "empty": False, "desc": "Prompt Size (0 = default)", "value": 0},
    "jinja": {"stype": "boolean", "desc": "Use Model Chat Template", "value": True},
    "mmproj-offload": {"stype": "boolean", "desc": "Multimodal Projector GPU Offloading", "value": True},
    "swa-full": {"stype": "boolean", "desc": "Use full-size SWA cache", "value": False},
    "cache-prompt": {"stype": "boolean", "desc": "Cache Prompt (default: True)", "value": True},
    "cache-reuse": {"stype": "uinteger", "desc": "Min chunk size to reuse (default: 0)", "value": 256}
}

MODELS_SERVER_SETTINGS = {}

MODELS_SETTINGS = {
    "1773183764-9087174": {
        "name": {"stype": "string", "empty": False, "desc": "Name", "value": "qwen3.6"},
        "temperature": {"stype": "float", "desc": "Temperature", "value": 0.6},
        "top_p": {"stype": "float", "desc": "TOP-P", "value": 0.95},
        "min_p": {"stype": "float", "desc": "MIN-P", "value": 0.0},
        "top_k": {"stype": "float", "desc": "TOP-K", "value": 20.0},
        "presence_penalty": {"stype": "float", "desc": "Presence Penalty", "value": 0.0},
        "repetition_penalty": {"stype": "float", "desc": "Repetition Penalty", "value": 1.0},
        "chat_template_kwargs.enable_thinking": {"stype": "boolean", "desc": "Enable Thinking", "value": True},
        "chat_template_kwargs.preserve_thinking": {"stype": "boolean", "desc": "Preserve Thinking", "value": True}
    },
    "1777914370-480791": {
        "name": {"stype": "string", "empty": False, "desc": "Name", "value": "Gemma-4"},
        "temperature": {"stype": "float", "desc": "Temperature", "value": 1.0},
        "top_p": {"stype": "float", "desc": "TOP-P", "value": 0.95},
        "top_k": {"stype": "float", "desc": "TOP-K", "value": 64.0},
        "repetition_penalty": {"stype": "float", "desc": "Repetition Penalty", "value": 1.1},
        "chat_template_kwargs.enable_thinking": {"stype": "boolean", "desc": "Enable Thinking", "value": True},
        "chat_template_kwargs.preserve_thinking": {"stype": "boolean", "desc": "Preserve Thinking", "value": True}
    },
    "1779183334-9089754": {
        "name": {"stype": "string", "empty": False, "desc": "Name", "value": "muse-glimmer"},
        "temperature": {"stype": "float", "desc": "Temperature", "value": 1.0},
        "top_p": {"stype": "float", "desc": "TOP-P", "value": 0.95},
        "top_k": {"stype": "float", "desc": "TOP-K", "value": 64.0},
        "chat_template_kwargs.reasoning_strength": {"stype": "select_no_default", "desc": "Thinking Strength",
            "value": "high", "options": ["low", "medium", "high", "xhigh"]}
    }
}
