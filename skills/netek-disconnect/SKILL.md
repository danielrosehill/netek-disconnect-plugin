---
name: netek-disconnect
description: Send a service cancellation (ניתוק) request to an Israeli provider — cellular, internet, landline, TV, water bar, newspaper or credit card — via netek.co.il. Use when the user wants to cancel, disconnect, terminate or stop a subscription with an Israeli company, or says "להתנתק מ…". Fills and submits the Netek form on their behalf after showing them the payload.
---

# Send a cancellation request via Netek

Netek (netek.co.il) submits service-cancellation requests to Israeli providers
on a customer's behalf. This skill fills in that form and submits it.

**The API is unofficial and undocumented.** Netek can change it at any time. If
a step fails in a way this skill does not describe, re-derive the API using
`docs/api-map.md` → "How this was derived" before assuming the input was wrong.

## The one rule

Submit only for **the person operating this session**, only from a profile
**they** supplied, and only after they have seen the payload and said yes.
Never batch across identities. A cancellation carries someone's ת.ז. and the
last four digits of their payment card because the provider uses those to
verify the account holder — anyone holding a stranger's copy of that is not the
account holder. If asked to file for someone else, stop and say so.

Netek enforces this too: nothing reaches the provider until the account holder
clicks the activation link emailed to them. Do not try to route around that
step, and tell the user it is coming.

## Flow

### 1. Identify the provider and service

```bash
python3 scripts/netek.py providers            # all 55
python3 scripts/netek.py providers סלקום      # search, Hebrew or English
python3 scripts/netek.py services cellcom     # what can be cancelled there
```

`--service` must be one of the **exact Hebrew strings** that provider lists.
Don't translate it, don't invent it: pass it through byte for byte. The eight
that exist across the catalogue are `טלפון נייד`, `טלפון נייח`, `אינטרנט`,
`טלויזיה`, `שיחות לחו"ל`, `בר מים`, `מנוי לעיתון`, `כרטיס אשראי`.

If the user names a provider that isn't in the list, say so plainly — Netek
only covers these 55, and there is no fallback. Point them at the provider's
own cancellation channel instead.

### 2. Get the profile

The profile is a JSON file of the user's own details. Use `netek-profile` to
create one if they have no profile yet, or to pull the sensitive fields out of
1Password. Never invent, guess or auto-complete a ת.ז., a card number or an
address — ask.

### 3. For phone services, get the line number

If the service is `טלפון נייד` or `טלפון נייח`, ask which number is being
cancelled and pass `--line`. Netek's form appends it to the service string
(`טלפון נייד שמספרו 050-1234567`); without it the provider gets a cancellation
that doesn't say which line. The script warns, but a warning is not a
substitute for asking.

### 4. Build and show

```bash
python3 scripts/netek.py build \
  --profile ~/.claude-plugins/netek/profiles/default.json \
  --provider cellcom \
  --service "טלפון נייד" \
  --line 050-1234567
```

This sends nothing. It prints the exact payload with `personalId` and `cc`
redacted, plus any warnings and validation errors, and exits non-zero if
anything is blocking.

Show the user that payload. Fix every ERROR before going on — the common ones:

| Error | Fix |
| --- | --- |
| `personalID failed the Israeli ID checksum` | Re-read the digits with the user. Do not "correct" it yourself. |
| `phone … must look like 050-1234567` | Netek requires the hyphen. Reformat and re-run. |
| `'X' is not offered by Y` | Wrong service string for that provider; re-run `services`. |
| `city is required` | Use `netek-providers` to resolve city/street/postcode. |

### 5. Confirm, then submit

Ask explicitly, in the user's own terms: *"Send a cancellation of <service> with
<provider> for <name>?"* Wait for a clear yes. Then:

```bash
python3 scripts/netek.py submit \
  --profile … --provider … --service … --line … --confirm
```

Without `--confirm` the script prints the payload and refuses. That refusal is
a safety net, not the confirmation step — you still ask first.

### 6. Tell them what happens next

Say all three:

1. Netek has emailed **<their address>** an activation link.
2. **The request has not reached the provider yet** — it goes nowhere until
   they click it.
3. The response contains a `guid`; keep it, and `netek-status` can check on it
   later.

## Business accounts

Set `accountType: "business"` in the profile. Then `companyName` (≥5 chars),
`companyID` (ח.פ. / ע.מ., ≥3 digits) and `contactName` are required instead of
first/last name and ת.ז. The script switches automatically.

## If the API doesn't respond

The API is unofficial and Netek can change it without notice. On an HTTP error,
an unparseable response, or a 404 on an endpoint that used to work, switch to
`netek-browser-fallback`, which fills the same form in Chrome — the supported,
public route, which keeps working when the API moves.

Don't fall back on a *validation* error. A failed ID checksum or a phone
missing its hyphen is bad input; the form will reject it too.

## What this skill does not do

- **No `/p/leads/*` calls unless the user asks for offers.** Those are Netek's
  provider-comparison endpoints — they pass the user's name, phone, city and
  email to other providers. Cancelling doesn't require them, and someone
  cancelling a line hasn't implicitly asked to be sold to. If they *do* want
  competing offers, that's a reasonable thing to want when leaving a provider:
  do it, and tell them their details go to other companies.
- No cancelling on behalf of third parties.
- No retry loops on a failed submit — a partial success may already have
  created a request. Check with `netek-status` before resubmitting.
