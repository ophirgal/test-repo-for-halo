"""Render the newsletter journey: Welcome, the signup Form in every state and
Confirmation, plus the static progressive-enhancement script ``FORM_JS``.

Ported from the approved SCRUM-102 screens (split layout, its colour tokens
and copy). The design's separate mobile pages become one media query. Every
echoed value is HTML-escaped here, on output. Pages carry no inline script;
``FORM_JS`` is served same-origin at ``/newsletter/form.js``.
"""

import html

from .signup import EMAIL_EMPTY, EMAIL_MALFORMED, MAX_NAME, NAME_EMPTY, NAME_TOO_LONG

WELCOME_PATH = "/newsletter"
SIGNUP_PATH = "/newsletter/signup"
THANKS_PATH = "/newsletter/thanks"
SCRIPT_PATH = "/newsletter/form.js"

# Colour tokens of the approved screens (WCAG 2.1 AA: text 4.5:1, focus 3:1).
TOKENS = {
    "bg": "#f6f7f9", "surface": "#ffffff", "text": "#1b1f27", "muted": "#5a6270",
    "border": "#8a93a3", "divider": "#d5d9e0", "primary": "#2b4fd8", "primary-dark": "#1f3cae",
    "focus": "#1f3cae", "accent-bg": "#eef2ff", "success": "#1d7a46",
    "error": "#b3261e", "error-bg": "#fdecea", "disabled": "#5a6270",
}

STYLE = (
    ":root{" + "".join(f"--c-{k}:{v};" for k, v in TOKENS.items()) + "\n"
    "  --font:system-ui,-apple-system,\"Segoe UI\",Roboto,Helvetica,Arial,sans-serif;\n"
    "  --fs-sm:.875rem;--fs-md:1rem;--fs-lg:1.25rem;--fs-xl:1.75rem;\n"
    "  --sp-1:4px;--sp-2:8px;--sp-3:12px;--sp-4:16px;--sp-5:24px;--sp-6:32px;--sp-7:48px;\n"
    "  --radius:10px;--tap:48px}\n"
    """*{box-sizing:border-box}
html,body{margin:0}
body{font-family:var(--font);font-size:var(--fs-md);line-height:1.5;color:var(--c-text);background:var(--c-bg);overflow-x:hidden}
a{color:var(--c-primary)}
a:focus-visible,input:focus-visible,.btn:focus-visible{outline:3px solid var(--c-focus);outline-offset:2px}
h1{font-size:var(--fs-xl);line-height:1.2;margin:0;overflow-wrap:anywhere}
p{margin:0 0 var(--sp-4)}
.muted{color:var(--c-muted)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-2);min-height:var(--tap);padding:0 var(--sp-5);border-radius:var(--radius);background:var(--c-primary);color:#fff;text-decoration:none;border:0;font:inherit;font-weight:600;cursor:pointer}
.btn:hover{background:var(--c-primary-dark)}
.btn:disabled,.btn[aria-disabled="true"]{background:var(--c-disabled);cursor:not-allowed}
.btn-block{width:100%}
.btn-busy{display:inline-flex;align-items:center;gap:var(--sp-2)}
[hidden]{display:none!important}
.link-back{display:inline-flex;align-items:center;min-height:var(--tap);font-weight:600}
.actions{display:flex;flex-direction:column;gap:var(--sp-2);margin-top:var(--sp-4)}
.split-page{max-width:60rem;margin:0 auto;padding:var(--sp-7) var(--sp-4)}
.split{display:grid;grid-template-columns:5fr 7fr;background:var(--c-surface);border:1px solid var(--c-divider);border-radius:var(--radius);overflow:hidden;min-height:440px}
.context{background:var(--c-accent-bg);padding:var(--sp-6);display:flex;flex-direction:column;gap:var(--sp-4);border-right:1px solid var(--c-divider);min-width:0}
.context .link-back{align-self:flex-start;margin:calc(-1*var(--sp-3)) 0 0}
.context p{margin:0}
.action{padding:var(--sp-6) var(--sp-7);display:flex;flex-direction:column;justify-content:center;min-width:0}
.action .lead{font-size:var(--fs-lg);font-weight:600;margin:0 0 var(--sp-4)}
.vsteps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:var(--sp-1);font-size:var(--fs-sm);color:var(--c-muted)}
.vsteps li{display:flex;align-items:center;gap:var(--sp-3);min-height:32px}
.vsteps .dot{flex:none;width:24px;height:24px;border-radius:50%;border:2px solid var(--c-border);display:inline-flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;background:var(--c-surface);color:var(--c-muted)}
.vsteps li.done .dot{background:var(--c-primary-dark);border-color:var(--c-primary-dark);color:#fff}
.vsteps li.current{color:var(--c-text);font-weight:600}
.vsteps li.current .dot{border-color:var(--c-primary);color:var(--c-primary);box-shadow:0 0 0 3px #c9d4fb}
.field{margin:0 0 var(--sp-5)}
.field label{display:block;font-weight:600;margin-bottom:var(--sp-2)}
.input{width:100%;min-height:var(--tap);padding:0 var(--sp-3);border:1px solid var(--c-border);border-radius:var(--radius);font:inherit;color:var(--c-text);background:var(--c-surface)}
.input[readonly]{background:var(--c-bg);color:var(--c-muted)}
.hint{font-size:var(--fs-sm);color:var(--c-muted);margin-top:var(--sp-2)}
.field.has-error .input{border:2px solid var(--c-error)}
.error-msg{display:flex;gap:var(--sp-2);align-items:flex-start;font-size:var(--fs-sm);font-weight:600;color:var(--c-error);margin-top:var(--sp-2)}
.error-msg svg{flex:none;margin-top:2px}
.alert{display:flex;gap:var(--sp-3);align-items:flex-start;background:var(--c-error-bg);border:1px solid var(--c-error);border-left-width:4px;border-radius:var(--radius);padding:var(--sp-3) var(--sp-4);margin:0 0 var(--sp-5)}
.alert svg{flex:none;margin-top:2px}
.alert strong{display:block;color:var(--c-error)}
.alert p{margin:var(--sp-1) 0 0;font-size:var(--fs-sm)}
.spinner{animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.spinner{animation:none}}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.success-icon{display:block}
@media (max-width:40rem){
  .split-page{max-width:30rem;padding:var(--sp-4) var(--sp-3) var(--sp-6)}
  .split{grid-template-columns:minmax(0,1fr);min-height:0}
  .context{border-right:0;border-bottom:1px solid var(--c-divider);padding:var(--sp-5) var(--sp-4)}
  h1{font-size:1.5rem}
  .vsteps{flex-direction:row;gap:var(--sp-3)}
  .vsteps li .label{display:none}
  .vsteps li.current .label{display:inline}
  .action{padding:var(--sp-5) var(--sp-4)}
  .action .lead{font-size:var(--fs-md)}
}
"""
)

PITCH = "News and updates from the site, sent to your inbox."
NAME_HINT = f"Up to {MAX_NAME} characters."
EMAIL_HINT = "For example, name@example.com. We only use it to send the newsletter."
BUSY_LABEL = "Submitting…"
BUSY_STATUS = "Sending your details. This usually takes a second or two."
ERROR_TEXT = {
    NAME_EMPTY: "Enter your name.",
    NAME_TOO_LONG: f"Enter a name of {MAX_NAME} characters or fewer.",
    EMAIL_EMPTY: "Enter your email address.",
    EMAIL_MALFORMED: "Enter an email address in the format name@example.com.",
}
FAILED_TITLE = "Your signup didn’t go through"
FAILED_TEXT = ("We couldn’t reach the server. Check your connection, then select Submit again. "
               "Your name and email address are still filled in.")
THANKS_TEXT = "Thanks for subscribing. The next newsletter will be sent to the email address you entered."

ERROR_ICON = ('<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7.5" '
              'fill="#b3261e"/><path d="M8 4v5" stroke="#fff" stroke-width="2" stroke-linecap="round"/>'
              '<circle cx="8" cy="11.8" r="1.1" fill="#fff"/></svg>')
ALERT_ICON = ('<svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 1.5L19 17.5H1z" '
              'fill="#b3261e"/><path d="M10 7v5" stroke="#fff" stroke-width="2" stroke-linecap="round"/>'
              '<circle cx="10" cy="14.6" r="1.1" fill="#fff"/></svg>')
SPINNER = ('<svg class="spinner" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" '
           'r="7" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="2.5"/><path d="M9 2a7 7 0 0 1 7 7" '
           'fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/></svg>')
SUCCESS_ICON = ('<svg class="success-icon" width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"><circle '
                'cx="24" cy="24" r="22" fill="#1d7a46"/><path d="M14 25l7 7 13-15" fill="none" stroke="#fff" '
                'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>')

STEPS = ("1. Welcome", "2. Your details", "3. Done")


def _esc(text):
    return html.escape(text, quote=True)


def _steps(current):
    """The progress stepper; ``current`` is 1, 2 or 3."""
    items = []
    for number, label in enumerate(STEPS, start=1):
        if number < current:
            items.append(f'<li class="done"><span class="dot" aria-hidden="true">✓</span><span class="label">{label}</span></li>')
        elif number == current:
            items.append(f'<li class="current" aria-current="step"><span class="dot" aria-hidden="true">{number}</span>'
                         f'<span class="label">{label}</span></li>')
        else:
            items.append(f'<li><span class="dot" aria-hidden="true">{number}</span><span class="label">{label}</span></li>')
    return f'<ol class="vsteps" aria-label="Progress, step {current} of 3">{"".join(items)}</ol>\n'


def _page(title, context, action, script=False):
    head_script = f'<script src="{SCRIPT_PATH}" defer></script>\n' if script else ""
    page = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n"
        f"<style>\n{STYLE}</style>\n"
        f"{head_script}"
        "</head>\n"
        "<body>\n"
        '<main class="split-page">\n'
        '<div class="split">\n'
        f'<section class="context">\n{context}</section>\n'
        f"{action}"
        "</div>\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
    return page.encode("utf-8")


def render_welcome():
    """Welcome: the pitch, "Subscribe" to the form and "Back to site"."""
    context = (
        '<a class="link-back" href="/">← Back to site</a>\n'
        + _steps(1)
        + "<h1>Get our newsletter</h1>\n"
        f"<p>{PITCH}</p>\n"
    )
    action = (
        '<section class="action" aria-label="Subscribe">\n'
        '<p class="lead">You only need your name and email address. It takes less than a minute.</p>\n'
        f'<div class="actions"><a class="btn btn-block" href="{SIGNUP_PATH}">Subscribe</a></div>\n'
        "</section>\n"
    )
    return _page("Newsletter", context, action)


def _field(field, label, attrs, hint, value, error, focus):
    hint_id, error_id = f"{field}-hint", f"{field}-error"
    if error is None:
        state, under = f' aria-describedby="{hint_id}"', ""
        wrapper = "field"
    else:
        state = f' aria-describedby="{error_id} {hint_id}" aria-invalid="true"' + (" autofocus" if focus else "")
        under = (f'<div class="error-msg" id="{error_id}">{ERROR_ICON}<span><span class="sr-only">Error: </span>'
                 f"{_esc(ERROR_TEXT[error])}</span></div>")
        wrapper = "field has-error"
    return (
        f'<div class="{wrapper}">\n'
        f'<label for="{field}">{label}</label>\n'
        f'<input class="input" id="{field}" name="{field}" {attrs} required value="{_esc(value)}"{state}>\n'
        f'{under}<div class="hint" id="{hint_id}">{hint}</div>\n'
        "</div>\n"
    )


def render_form(values=None, errors=None, failed=False):
    """The signup form, as UTF-8 bytes.

    ``values`` maps ``name``/``email`` to the typed text (kept, escaped);
    ``errors`` maps a field to its error code (``signup.check``); ``failed``
    shows the "submission failed" alert. The first field in error gets
    ``autofocus``.
    """
    values = values or {}
    errors = errors or {}
    first = next((f for f in ("name", "email") if f in errors), None)
    context = (
        f'<a class="link-back" href="{WELCOME_PATH}">← Back</a>\n'
        + _steps(2)
        + "<h1>Subscribe to the newsletter</h1>\n"
        f'<p class="muted">{PITCH}</p>\n'
    )
    alert = ""
    if failed:
        alert = (f'<div class="alert" role="alert">{ALERT_ICON}<div><strong>{FAILED_TITLE}</strong>'
                 f"<p>{FAILED_TEXT}</p></div></div>")
    action = (
        '<section class="action" aria-label="Your details">\n'
        f'{alert}<form id="signup" action="{SIGNUP_PATH}" method="post" novalidate>\n'
        + _field("name", "Name", f'type="text" autocomplete="name" maxlength="{MAX_NAME}"', NAME_HINT,
                 values.get("name", ""), errors.get("name"), first == "name")
        + _field("email", "Email address", 'type="email" autocomplete="email" inputmode="email"', EMAIL_HINT,
                 values.get("email", ""), errors.get("email"), first == "email")
        + '<div class="actions"><button class="btn btn-block" type="submit">'
        f'<span class="btn-label">Submit</span><span class="btn-busy" hidden>{SPINNER}{BUSY_LABEL}</span></button>'
        '<p class="hint" role="status" id="signup-status"></p></div>\n'
        "</form>\n"
        "</section>\n"
    )
    return _page("Subscribe to the newsletter", context, action, script=True)


def render_thanks():
    """Confirmation: the same bytes for every visitor, new or already subscribed."""
    context = _steps(3) + SUCCESS_ICON + "\n<h1>You’re subscribed</h1>\n"
    action = (
        '<section class="action" role="status">\n'
        f'<p class="lead">{THANKS_TEXT}</p>\n'
        '<div class="actions"><a class="btn btn-block" href="/">Back to site</a></div>\n'
        "</section>\n"
    )
    return _page("You’re subscribed", context, action)


# The "submitting" state: on submit, disable Submit with the busy label and
# make the fields read-only. Without script the form still posts normally.
FORM_JS = (
    """\
(function () {
  "use strict";
  var form = document.getElementById("signup");
  if (!form) { return; }
  var button = form.querySelector('button[type="submit"]');
  var label = form.querySelector(".btn-label");
  var busy = form.querySelector(".btn-busy");
  var status = document.getElementById("signup-status");
  var inputs = form.querySelectorAll("input");
  function setBusy(on) {
    form.setAttribute("aria-busy", on ? "true" : "false");
    button.disabled = on;
    label.hidden = on;
    busy.hidden = !on;
    status.textContent = on ? "%s" : "";
    for (var i = 0; i < inputs.length; i++) { inputs[i].readOnly = on; }
  }
  form.addEventListener("submit", function (event) {
    if (button.disabled) { event.preventDefault(); return; }
    setBusy(true);
  });
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) { setBusy(false); }
  });
})();
"""
    % BUSY_STATUS
).encode("utf-8")

__all__ = ["FORM_JS", "render_form", "render_thanks", "render_welcome", "ERROR_TEXT", "TOKENS"]
