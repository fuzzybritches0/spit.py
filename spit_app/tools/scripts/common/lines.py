def detect_newline(text):
    first_lf = text.find("\n")
    first_cr = text.find("\r")
    if first_lf == -1 and first_cr == -1:
        return "\n"
    if first_cr != -1 and (first_lf == -1 or first_cr < first_lf):
        return "\r\n" if first_cr + 1 == first_lf else "\r"
    return "\n"

def ends_with_newline(text):
    return text.endswith(("\n", "\r"))

def strip_newline(text):
    for terminator in ("\r\n", "\r", "\n"):
        if text.endswith(terminator):
            return text[:-len(terminator)]
    return text

def read_text_raw(path):
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read()

def write_text_raw(path, text):
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(text)
