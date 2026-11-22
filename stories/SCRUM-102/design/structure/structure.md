# Structure — Newsletter signup journey (SCRUM-102)

Three screens, no account: **Welcome → Signup form → Confirmation**, reached from a link in the site footer (R1). Each screen is designed at desktop and mobile widths and meets WCAG 2.1 AA (R4, AC 1, AC 3). The form has inline errors for an empty name, an empty email and a malformed email (R2, AC 2). If the address is already subscribed, the visitor sees the same Confirmation (R3). Storing signups and the CSV export belong to SCRUM-103 and are not designed here.

## Personas

| Persona | Who (source) | Needs | Pain points |
|---|---|---|---|
| **Site visitor** (main persona) | A visitor to the public site who wants the newsletter (story, PRD summary, R1) | Understand the newsletter in one sentence. Subscribe in under a minute with only a name and an email address. See clearly that it worked. | Today addresses are collected by hand over email (PRD summary). May be on a phone (R4, AC 1). Needs to know which field is wrong without losing what was already typed (R2). |
| **Visitor using a keyboard or screen reader** | The same visitor, reaching the journey without a mouse or by audio (R4, AC 3) | A logical focus order through every screen. Errors that are announced and tied to their field. Colour contrast that meets AA. | Errors shown only by colour. Focus that stays on the Subscribe button when a field above it is wrong. |
| **Returning subscriber** | A visitor whose address is already on the list and who submits again (R3, SCRUM-103 scenario 2) | Finish the journey without trouble. | Must not get an error, and must not learn whether the address was already on the list. They see the same Confirmation as anyone else. |

## User interaction

```mermaid
flowchart TD
    Footer["Site page — footer link<br/>'Newsletter'"] -- "click link" --> Welcome["Welcome<br/>one-sentence pitch + Subscribe"]
    Welcome -- "Subscribe" --> Form["Signup form<br/>name + email"]
    Welcome -- "Back to site" --> Footer

    Form -- "Back" --> Welcome
    Form -- "Submit" --> V{"Inline validation"}
    V -- "name empty" --> ErrName["Signup form — name empty<br/>error under Name"]
    V -- "email empty" --> ErrEmpty["Signup form — email empty<br/>error under Email"]
    V -- "email malformed" --> ErrFormat["Signup form — email malformed<br/>error under Email"]
    ErrName -- "fix and Submit" --> V
    ErrEmpty -- "fix and Submit" --> V
    ErrFormat -- "fix and Submit" --> V

    V -- "both valid" --> Loading["Signup form — submitting<br/>Submit disabled"]
    Loading -- "stored (new address)" --> Confirm["Confirmation"]
    Loading -- "already subscribed<br/>(nothing stored)" --> Confirm
    Loading -- "save failed" --> Failed["Signup form — submission failed<br/>message, values kept"]
    Failed -- "Submit again" --> V

    Confirm -- "Back to site" --> Footer
```

Several errors can show at once. For example, a name-empty and an email-malformed error can appear together, each under its own field. The diagram shows each error separately only for readability.

## Screen inventory

| Screen | Purpose | Main elements | States (default / loading / error / empty) | Based on |
|---|---|---|---|---|
| Site page — footer link | The entry point: the site footer links to the newsletter (R1, process step 1) | The existing page content plus a footer with a "Newsletter" link | default only. The page has no footer today, so this story adds one. | `test-repo-for-halo-7ad879b52d/docs/index.html` |
| Welcome | Explains the newsletter and starts the signup (R1) | Heading, one-sentence explanation, primary "Subscribe" button, "Back to site" link | default. No loading, error or empty state (static content). | new |
| Signup form | Collects the name and email address (R2) | Heading, Name field (1–80 characters), Email field, "Submit" button, "Back" link | default, plus the four states below | new |
| Signup form — name empty | Tells the visitor the name is missing (R2, AC 2) | Inline error under Name, linked to the field (`aria-describedby`); focus moves to the first field in error | error | new |
| Signup form — email empty | Tells the visitor the email is missing (R2, AC 2) | Inline error under Email, linked to the field; the name already typed is kept | error | new |
| Signup form — email malformed | Tells the visitor the address is not valid (R2, AC 2) | Inline error under Email with the expected format; the typed value is kept | error | new |
| Signup form — submitting | Shows the signup is being sent; stops a double submit | Submit disabled with a busy label; fields read-only | loading | new |
| Signup form — submission failed | The save did not go through (network or server) | Message above the form, values kept, "Submit" enabled again | error | new |
| Confirmation | Tells the visitor they are subscribed (R3), whether the address is new or already on the list | Success heading, short message, "Back to site" link | default. No loading, error or empty state. | new |

## Open branches

1. **Submission-failed state.** The PRD covers only valid, invalid and already-subscribed submissions. It does not say what the visitor sees when the save fails (network or server error). I added "Signup form — submission failed", which keeps what the visitor typed. I recommend keeping it: without it, a failed save leaves the visitor with no feedback. Drop it only if you want the design limited strictly to the three error states in AC 2.
2. **Name longer than 80 characters.** R2 limits the name to 1–80 characters, but AC 2 lists errors only for an empty name, an empty email and a malformed email. One option is to cap the field at 80 characters so a longer name can't be typed. The other is to add a "name too long" error. I recommend the cap: it keeps the three error states AC 2 asks for and makes the fourth one impossible. Choose the error instead if pasted names must never be cut off without a warning.
3. **Footer and visual base.** `docs/index.html` has no footer today. Story `0e4e726a` holds an approved newsletter design with an email-only form and a consent checkbox. Its `tokens.css` could serve as the visual base for these screens. I recommend reusing those tokens but not that form: R2 asks for name and email with no consent box. Tell me if the new screens should have their own look, or if the consent checkbox should come back.
