---
name: netek-browser-fallback
description: Fill in the Netek cancellation form directly in Chrome instead of calling the API — the fallback for when the unofficial API changes, starts erroring, or an endpoint disappears. Use when scripts/netek.py fails with an HTTP error, an unexpected response shape, or a 404 on an endpoint that used to work.
---

# Fill the Netek form in the browser

The API this plugin normally uses is unofficial and undocumented (see
`docs/api-map.md`). Netek can change it whenever they like, and when they do,
`scripts/netek.py` breaks. **The form on the website keeps working** — it is the
supported, public way to do this. This skill drives it in Chrome.

Same rules as the API path: only for the person operating this session, only
from a profile they supplied, only after they see what will be submitted.

## When to reach for this

Switch here when `scripts/netek.py` gives you any of:

- HTTP 4xx/5xx from `/p/request` or a lookup endpoint;
- a response that doesn't parse, or parses to an unexpected shape;
- a 404 on an endpoint that used to work — the surest sign the API moved.

Don't switch on a *validation* error. If the script says the ID checksum failed
or the phone needs a hyphen, the input is wrong and the browser will reject it
too, just later and less clearly.

When you do fall back, say so plainly: *"the API path isn't responding, so I'll
fill the form in your browser instead"* — the user is about to see Chrome do
things and should know why.

## Tools

Uses the Chrome MCP. Load what you need in **one** call:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__form_input,mcp__claude-in-chrome__computer
```

Call `tabs_context_mcp` first, then `tabs_create_mcp` for a new tab. Don't reuse
a tab id from an earlier session.

This drives the user's **own visible Chrome**. They can see it and intervene —
which is a feature here, not a problem.

## Where to start

Straight to the provider's page:

```
https://www.netek.co.il/he/d/<page_slug_he>
```

`page_slug_he` is in `data/providers.json` (percent-encode it). Only 27 of 55
providers have one. For the rest, start at `https://www.netek.co.il/` and pick
the provider from the list.

The site is Hebrew and **right-to-left**. Match fields by their visible label
text, not by position or by CSS selector — Netek ships a new hashed bundle on
every deploy, so class names are worthless, but the labels are stable.

## The form

Three steps: choose provider and service → fill details → confirm.

Labels, exactly as they appear on screen:

| Field | Hebrew label | Notes |
| --- | --- | --- |
| Account type | `סוג חשבון` | radio: `פרטי` (private) / `עסקי` (business) |
| First name | `שם פרטי` | private only |
| Surname | `שם משפחה` | private only |
| ID | `ת.ז.` | private only, 9 digits |
| Company name | `שם חברה` | business only |
| Company number | `ח.פ. או ע.מ.` | business only |
| Contact | `איש קשר` | business only |
| City | `ישוב` | autocomplete — pick from the dropdown |
| Street | `רחוב` | autocomplete — pick from the dropdown |
| House number | `מספר בית` | |
| Postcode | `מיקוד` | usually auto-fills from the street |
| Contact phone | `טלפון ליצירת קשר` | |
| Email | `דואר אלקטרוני` / `דוא״ל` | the activation link goes here |
| Payment card | `4 ספרות אחרונות של אמצעי המשמש לתשלום` | **last 4 digits only** |
| Service | `בחר שירות לניתוק` | dropdown |
| Number to cancel | `טלפון לניתוק` | appears for mobile/landline |
| Submit | `שלח` | |

Two things worth knowing:

- **`ישוב` and `רחוב` are autocompletes.** Type a few characters and *select
  from the dropdown* — typing the full name and moving on can leave the field
  unset, and the postcode won't populate.
- **`טלפון לניתוק` is its own field here.** In the API you fold the number into
  the service string (`טלפון נייד שמספרו 050-1234567`); in the form you don't.
  Put the number in this field and leave the service dropdown alone.

## The "offer from another company" checkbox

The form carries a checkbox labelled **`בא לך לשמוע הצעה מחברה אחרת?`** —
"would you like to hear an offer from another company?"

What's known about it: its internal key is `chooseLeadProviders`, and it drives
Netek's `/p/leads/*` endpoints, which pass the user's name, phone, city and
email to other providers. On that evidence it solicits competing offers rather
than cancelling anything.

**Leave it at its default (unticked) unless the user tells you they want
offers.** If they do want them, tick it — it's their call, and comparing
providers is a reasonable thing to want when you're leaving one. Just don't
decide it for them in either direction, and if you tick it, say what it does:
their contact details go to other companies.

Cancelling does not depend on this checkbox. If it's ever presented as
mandatory, that's a change worth recording in `docs/api-map.md`.

## Before submitting

Read the filled form back with `read_page` and show the user what it says —
same standard as `netek.py build`. When you repeat it back, mask the ת.ז. and
the card digits; they're on screen for the user, they don't need to be in the
transcript in full.

Then ask, naming the provider, the service and the person. Only click `שלח`
after a clear yes.

**Avoid triggering browser dialogs.** A JS `alert`/`confirm` blocks the
extension and the session stops responding. If one appears, tell the user to
dismiss it in Chrome.

## Afterwards

Identical to the API path: Netek emails an activation link, and **the request
reaches the provider only when the account holder clicks it**. Don't click it
for them.

If the page shows a request id or guid, note it — `netek-status` may be able to
use it, assuming that endpoint still works.

## Record what you learned

You came here because the API broke. That's worth writing down. Update
`docs/api-map.md` in the same session:

- which endpoint failed and how (status, body, or the shape you got);
- anything on the form that no longer matches the tables above;
- the date.

The file's "How this was derived" section is the recipe for re-reading Netek's
bundle and repairing `scripts/netek.py`. A fallback that silently papers over a
broken API just means the next person rediscovers the same breakage.
