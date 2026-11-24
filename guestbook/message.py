"""Message rules: one line, 1-200 Unicode code points after trimming."""

MAX_LEN = 200
EMPTY = "empty"
TOO_LONG = "too_long"

# Every line boundary ``str.splitlines`` recognises; "\r\n" is handled first
# so that it becomes one space, not two.
LINE_SEPARATORS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"


def normalise(raw):
    """Turn each line break into one space, then trim both ends."""
    text = raw.replace("\r\n", " ")
    for sep in LINE_SEPARATORS:
        text = text.replace(sep, " ")
    return text.strip()


def check(raw):
    """Return ``(text, error, length)`` for a submitted message.

    ``error`` is None when ``text`` may be saved, else ``EMPTY`` or
    ``TOO_LONG``; ``length`` is the normalised length in code points. A
    message is never cut.
    """
    text = normalise(raw)
    length = len(text)
    if length == 0:
        return text, EMPTY, length
    if length > MAX_LEN:
        return text, TOO_LONG, length
    return text, None, length
