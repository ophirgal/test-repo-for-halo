"""Render the /guestbook page: one full HTML document for every state.

Every message and the kept field value are HTML-escaped here, on output.
The page carries no script; the look follows the site's plain style.
"""

import html

from .message import EMPTY, MAX_LEN, TOO_LONG

STYLE = """\
  html, body { margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; }
  main { padding: 1rem; max-width: 40rem; margin: 0 auto; }
  h1 { overflow-wrap: anywhere; }
  label { display: block; font-weight: 600; margin-bottom: 0.25rem; }
  .row { display: flex; gap: 0.5rem; }
  .row input { flex: 1; min-width: 0; font: inherit; padding: 0.5rem; }
  .row button { flex: none; font: inherit; padding: 0.5rem 1rem; }
  input[aria-invalid="true"] { outline: 2px solid #b00020; }
  .hint, .empty, time { color: #595959; font-size: 0.875rem; }
  .error { color: #b00020; overflow-wrap: anywhere; }
  ol { list-style: none; margin: 0; padding: 0; }
  li { display: flex; gap: 1rem; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #ddd; }
  .msg { min-width: 0; overflow-wrap: anywhere; }
  time { flex: none; }
  .empty { text-align: center; }
  @media (max-width: 30rem) { li { flex-direction: column-reverse; gap: 0.25rem; } }
"""

ERRORS = {
    EMPTY: ("Message is empty.", "Nothing was saved. Write at least one character and press Send."),
    TOO_LONG: (
        f"Message is too long — {MAX_LEN} characters at most.",
        "Yours has {n}. Nothing was saved or cut; shorten it and press Send.",
    ),
}
EMPTY_LINE = "No messages yet. Be the first to leave one."

def _esc(text):
    return html.escape(text, quote=True)

def _item(record):
    local = record.time.astimezone()
    stamp = record.time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f'    <li><span class="msg" dir="auto">{_esc(record.text)}</span>'
        f'<time datetime="{stamp}">{local.strftime("%Y-%m-%d %H:%M")}</time></li>\n'
    )

def render(records, error=None, value="", length=0):
    """Return the page as UTF-8 bytes.

    ``records`` are newest first; ``error`` is None, ``EMPTY`` or ``TOO_LONG``;
    ``value`` is the text kept in the field and ``length`` the count shown in
    the "too long" error.
    """
    if error is None:
        field_state = ' aria-describedby="message-hint"'
        under = '    <p class="hint" id="message-hint">One line, up to 200 characters.</p>\n'
    else:
        title, detail = ERRORS[error]
        field_state = ' aria-invalid="true" aria-describedby="message-error"'
        under = (
            f'    <p class="error" id="message-error" role="alert"><strong>{_esc(title)}</strong> '
            f"{_esc(detail.format(n=length))}</p>\n"
        )
    if records:
        listing = '  <ol>\n' + "".join(_item(r) for r in records) + "  </ol>\n"
    else:
        listing = f'  <p class="empty">{EMPTY_LINE}</p>\n'
    page = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Guestbook</title>\n"
        f"<style>\n{STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        "  <h1>Guestbook</h1>\n"
        '  <form method="post" action="/guestbook">\n'
        '    <label for="message">Your message</label>\n'
        '    <div class="row">\n'
        '      <input type="text" id="message" name="message" placeholder="Write one line…" '
        f'autocomplete="off" value="{_esc(value)}"{field_state}>\n'
        '      <button type="submit">Send</button>\n'
        "    </div>\n"
        f"{under}"
        "  </form>\n"
        '  <section aria-labelledby="latest">\n'
        '  <h2 id="latest">Latest messages</h2>\n'
        f"{listing}"
        "  </section>\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
    return page.encode("utf-8")

__all__ = ["render", "EMPTY_LINE", "ERRORS"]

