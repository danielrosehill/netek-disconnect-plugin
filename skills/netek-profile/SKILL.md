---
name: netek-profile
description: Create, read or update the stored personal details used to fill Netek cancellation forms — name, Israeli ID, address, phone, email, card last-4 — including pulling them from a 1Password vault instead of a plaintext file. Use before netek-disconnect when the user has no profile yet, or when their details have changed.
---

# Manage the Netek profile

A cancellation request needs the account holder's name, ת.ז. (or ח.פ.),
address, phone, email and the last four digits of the payment method. This
skill assembles that once so `netek-disconnect` can reuse it.

## Where it lives

```
~/.claude-plugins/netek/profiles/<name>.json
```

`default.json` is the one used when the user doesn't name a profile. More than
one is fine — a person may hold accounts as both a private individual and a
business. **One profile is one identity.** Never merge two people into one
file, and never keep a profile for someone who is not the user.

This path is deliberately outside the plugin repo. Nothing under
`~/.claude-plugins/` is ever committed. See `references/user-data-layout.md`.

## Fields

Start from `examples/profile.example.json`. Schema in
`schema/profile.schema.json`.

| Field | Private | Business | Notes |
| --- | --- | --- | --- |
| `accountType` | `"private"` | `"business"` | |
| `firstName`, `lastName` | required, ≥2 letters | — | Hebrew or Latin, no digits |
| `personalID` | required | — | ת.ז., checksum-validated |
| `companyName` | — | required, ≥5 chars | |
| `companyID` | — | required, ≥3 digits | ח.פ. or ע.מ. |
| `contactName` | — | required, ≥2 letters | |
| `city`, `street`, `houseNumber` | required | required | Hebrew |
| `zip` | optional | optional | `netek-providers` can look it up |
| `phone` | required | required | **`050-1234567` — hyphen required** |
| `email` | required | required | activation link goes here |
| `cc` | required by most providers | same | last 4 digits only, never a full card |

Two things trip people up: the phone format needs the hyphen, and `cc` is four
digits, not a card number. If a user pastes a full card number, take the last
four and tell them you discarded the rest.

## Building one

Ask for the fields you're missing — do not infer them from other files on the
machine, from a git config, or from anything the user hasn't offered for this
purpose. A ת.ז. guessed wrong produces a cancellation request that gets
rejected by the provider, silently, days later.

Validate the ID before saving:

```bash
python3 scripts/netek.py check-id 030764534
```

Resolve the address so the postcode is right:

```bash
python3 scripts/netek.py city ירושלים       # -> 3000
python3 scripts/netek.py street 3000 יפו     # -> street + postal
```

Then write the JSON. Confirm the saved path back to the user.

## Keeping it in 1Password instead

If the user would rather not have their ת.ז. and card last-4 sitting in a JSON
file, keep the profile file for the non-sensitive fields and pull the rest at
build time from the `op` CLI.

Check first — the CLI must be present and signed in:

```bash
op --version && op vault list
```

Then reference items rather than copying values. The references are the user's own, so they
come from the environment, never from this plugin. Set them once, for example in the user's
shell profile or secrets wrapper:

```bash
export NETEK_PERSONAL_ID_REF="op://<vault>/<item>/personalID"
export NETEK_CC_REF="op://<vault>/<item>/cc"
op read "$NETEK_PERSONAL_ID_REF"
op read "$NETEK_CC_REF"
```

Assemble a complete profile into a temp file for the length of one submit, use
it, and delete it:

```bash
TMP=$(mktemp /tmp/netek-profile.XXXXXX.json)
python3 - "$TMP" <<'PY'
import json, subprocess, sys
p = json.load(open("~/.claude-plugins/netek/profiles/default.json".replace("~", __import__("os").path.expanduser("~"))))
for field, env in (("personalID", "NETEK_PERSONAL_ID_REF"), ("cc", "NETEK_CC_REF")):
    ref = __import__("os").environ[env]
    p[field] = subprocess.run(["op", "read", ref], capture_output=True, text=True, check=True).stdout.strip()
json.dump(p, open(sys.argv[1], "w"), ensure_ascii=False)
PY
python3 scripts/netek.py submit --profile "$TMP" … --confirm
rm -f "$TMP"
```

Gotchas that will cost you time:

- Always pass `--vault` (or a full `op://vault/item/field` reference). Without
  it `op` searches every vault and can return the wrong item silently.
- A vault name containing `&` breaks `op read` reference parsing — use the
  vault's ID instead of its name.
- `op` may prompt for biometric/desktop unlock. If it hangs, it is waiting on
  the user — tell them, don't retry.

**Netek itself has no login.** There is no Netek account, API key or password
to store. The vault here protects the user's own identity details, nothing
else.

## Updating

Read the existing file first, change only what the user asked for, and show a
before/after of the changed fields (redacting `personalID` and `cc` to their
last digits) so they can catch a typo before it reaches a provider.
