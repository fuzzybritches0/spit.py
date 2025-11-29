def dot2obj(data: dict, dotpath: str, value: str|int|float|bool) -> None:
    path = dotpath.split(".")
    cur = data
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[path[-1]] = value
