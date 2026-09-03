# SPDX-License-Identifier: GPL-2.0
"""Normalise tool call arguments against the tool's JSON schema.

`json.loads()` on `tool_call["function"]["arguments"]` is correct and must stay
the only parse of the whole blob -- but it can only give back what the encoder
put in. Decoders that cannot express a union such as
`"type": ["string", "array"]` fall back to string and serialise the list as
*text*, so `read_files` receives the string `'["a.txt", "b.txt"]'`, its
`if not type(path) is list` guard sees a string, and `open()` is handed one
absurd filename instead of two. Scalars are unaffected (booleans and integers
arrive properly typed), which is how the quirk stayed hidden.

Coercing here -- once, driven by the declared schema -- keeps every tool from
re-discovering the same decoder quirk in its own script.
"""
import ast
import json

CONTAINERS = (list, dict)


def declared_types(properties: dict, key: str) -> list:
    """The JSON-schema types declared for `key`, flattened to a list of names.

    `"type": "string"` -> ["string"], `"type": ["string", "array"]` ->
    ["string", "array"], `anyOf` -> the union of the sub-schemas. A property
    with no usable declaration yields [], which callers treat as "leave it be".
    """
    spec = properties.get(key)
    if not isinstance(spec, dict):
        return []
    types = spec.get("type", [])
    if isinstance(types, str):
        return [types]
    ret = [t for t in types if isinstance(t, str)] if isinstance(types, list) else []
    for sub in spec.get("anyOf", []):
        ret += declared_types({"_": sub}, "_")
    return sorted(set(ret))


def unwrap(value: str):
    """The container a container-shaped string denotes, or None.

    Only text that starts like a JSON container is attempted and the result has
    to actually be one, so a genuine filename such as `[v2].txt` passes through
    untouched. `json.loads()` handles the double-quoted form a model emits;
    `ast.literal_eval()` catches the single-quoted repr a UI round-trip leaves
    behind (`"['a', 'b']"`), which is valid Python but not valid JSON.
    """
    text = value.strip()
    if not text or text[0] not in "[{":
        return None
    for load in (json.loads, ast.literal_eval):
        try:
            parsed = load(text)
        except Exception:
            continue
        if isinstance(parsed, CONTAINERS):
            return parsed
    return None


def coerce(arguments: dict, properties: dict) -> dict:
    """Repair `arguments` in place so the values match the declared types.

    Three moves, and only three:
      * a container-shaped string becomes the container, but *only* when the
        schema allows one -- a string-only parameter such as the `replace` text
        of `search_replace` may legitimately hold `{"a": 1}` verbatim;
      * a bare scalar for an array-only parameter becomes a one-element list;
      * a one-element list for a string-only parameter becomes that string.

    Anything the schema does not declare is left exactly as it came in.
    """
    for key in list(arguments.keys()):
        types = declared_types(properties, key)
        if not types:
            continue
        value = arguments[key]
        if isinstance(value, str) and ("array" in types or "object" in types):
            unwrapped = unwrap(value)
            if unwrapped is not None:
                value = unwrapped
        if "array" in types and "string" not in types and isinstance(value, str):
            value = [value]
        elif "array" not in types and "string" in types and isinstance(value, list):
            if len(value) == 1:
                value = value[0]
        arguments[key] = value
    return arguments
