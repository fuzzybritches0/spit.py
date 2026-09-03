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
import os

CONTAINERS = (list, dict)
CONTAINER_TYPES = ("array", "object")
SCALAR_TYPES = ("string", "boolean", "integer", "number", "float")


def spec_types(spec) -> list:
    """The JSON-schema type names a property spec declares, flattened.

    `"type": "string"` -> ["string"], `"type": ["string", "array"]` ->
    ["string", "array"], `anyOf` -> the union of the sub-schemas. A property
    with no usable declaration yields [], which callers treat as "leave it be".
    """
    if not isinstance(spec, dict):
        return []
    types = spec.get("type", [])
    if isinstance(types, str):
        return [types]
    ret = [t for t in types if isinstance(t, str)] if isinstance(types, list) else []
    for sub in spec.get("anyOf", []):
        ret += spec_types(sub)
    return sorted(set(ret))


def declared_types(properties: dict, key: str) -> list:
    """spec_types() of the spec that `properties` declares for `key`."""
    return spec_types(properties.get(key))


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


# --- one argument shown in, and typed back from, a text field ----------------
#
# The tool-call editor holds every argument in a TextArea, so a value whose
# schema allows a container has to be flattened to text and parsed again. Both
# directions have to use JSON: str() renders a list with single quotes, which
# is not JSON, so saving turned ['a.txt', 'b.txt'] into the *text* of a list --
# feeding the editor's own output back into the defect coerce() repairs.

def scalar_valid(type_name: str, text: str) -> bool:
    if type_name == "integer":
        try:
            int(text)
        except ValueError:
            return False
    elif type_name in ("number", "float"):
        try:
            float(text)
        except ValueError:
            return False
    elif type_name == "boolean":
        if text.lower() not in ("true", "false"):
            return False
    return True


def scalar_parse(type_name: str, text: str):
    if type_name == "integer":
        try:
            return int(text)
        except ValueError:
            return text
    if type_name in ("number", "float"):
        try:
            return float(text)
        except ValueError:
            return text
    if type_name == "boolean":
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        return text
    return text


def field_valid(spec, text: str) -> bool:
    """Can `text` stand for a value of the property `spec` declares?

    Empty is left to the caller -- a blank field means "argument not given",
    not "invalid". A union is edited as text and parsed on save, so it passes
    when it parses as a container or when any one member would take the text;
    a union that offers `string` takes anything, as it must.
    """
    if not text:
        return True
    names = spec_types(spec)
    if not names:
        return True
    if any(n in CONTAINER_TYPES for n in names) and unwrap(text) is not None:
        return True
    if "string" in names:
        return True
    return any(scalar_valid(n, text) for n in names)


def field_parse(spec, text: str):
    """The value the field text denotes, in the shape `spec` declares."""
    if not text:
        return None
    names = spec_types(spec)
    if any(n in CONTAINER_TYPES for n in names):
        parsed = unwrap(text)
        if parsed is not None:
            return parsed
    if "array" in names and "string" not in names:
        return [text]
    for name in names:
        if name in SCALAR_TYPES:
            return scalar_parse(name, text)
    return text


def field_render(value) -> str:
    """The text a field should show for `value`."""
    if value is None:
        return ""
    if isinstance(value, CONTAINERS):
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# --- paths a model wrote as ~/something --------------------------------------

def expand_path(path):
    """Resolve `~`, `~user` and $VARs in a path, as a shell would have.

    open() does not expand a leading ~: it takes the two characters as part of
    the name, so read_files("~/notes.txt") is a FileNotFoundError that reads as
    though the file were missing rather than as though the argument was never a
    path at all. A model writes ~ because every shell example it has ever read
    uses it.

    Only the arguments a tool declares in PATH_ARGS are expanded. For anything
    else -- a grep pattern, the body of write_file, a URL -- ~ and $ are
    characters the caller meant literally and expanding them would corrupt the
    call. expandvars leaves a $VAR alone when it is not set, so the only names
    at risk are ones that really are in the environment.
    """
    if isinstance(path, list):
        return [expand_path(item) for item in path]
    if not isinstance(path, str):
        return path
    return os.path.expanduser(os.path.expandvars(path))


def expand_arguments(arguments: dict, path_args) -> dict:
    """Expand the arguments named in `path_args`, in place."""
    for key in path_args or []:
        if key in arguments:
            arguments[key] = expand_path(arguments[key])
    return arguments
