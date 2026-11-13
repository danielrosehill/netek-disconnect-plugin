# netek-disconnect-plugin

A Claude Code plugin for cancelling Israeli service subscriptions through
[netek.co.il](https://www.netek.co.il/) — mobile, internet, landline, TV,
international calling, water bars, newspaper subscriptions and credit cards.

It fills in the Netek cancellation form for you: resolves the provider and
service, validates your ת.ז. and address, shows you the exact request, and
submits it once you say yes.

> **Unofficial.** This project is not affiliated with, endorsed by, or
> supported by Netek. It talks to an undocumented API that was reverse-
> engineered from the site's own JavaScript, and **that API can change or
> disappear without notice**. Everything known about it is written down in
> [`docs/api-map.md`](docs/api-map.md), along with the date it was last
> verified and the method for re-deriving it when it breaks. See
> [Provenance](#provenance) for how it was found and what that implies.

## Provenance

Being straight about where this came from, because it changes what you should
expect from it.

**Netek publishes no API.** There is no developer portal, no documentation, no
OpenAPI document (`/swagger`, `/api-docs` and the usual paths all 404), and no
public statement that `service.netek.co.il` is meant to be called by anything
other than their own website. Nobody granted permission for this, because there
is nobody to ask.

**How it was mapped.** By reading the JavaScript that Netek serves to every
visitor — `https://www.netek.co.il/static/ga/main.<hash>.chunk.js` — and by
issuing read-only `GET` requests to the catalogue and autocomplete endpoints.
The endpoint list, the request payload shape, the field-name mapping and the
validation rules all came out of that bundle. No credentials were bypassed
(there are none — every endpoint is unauthenticated), no private traffic was
captured, and no account was needed.

**What was deliberately not done.** `POST /p/request` has never been called.
A success sends a real cancellation for a real person to a real company, and
there is no unsend, so it isn't something to fire a test at. Its response shape
— and the status and activation endpoints downstream of it — are therefore
marked *inferred* in `docs/api-map.md` rather than confirmed.

**What this means for you.** The API can be changed, restricted or switched off
at any time and nothing here would be owed a deprecation notice. That is the
normal condition of an undocumented API, not a defect in this plugin — but it
is why [`netek-browser-fallback`](skills/netek-browser-fallback/SKILL.md)
exists, filling the same form in Chrome through the supported public route when
the API stops answering. Please don't hammer the endpoints; this is built for
one person cancelling their own subscriptions, and it deliberately does not
batch.

If Netek would rather this didn't exist, open an issue and it comes down.

## Install

```bash
git clone https://github.com/danielrosehill/netek-disconnect-plugin
```

Add it as a plugin directory in Claude Code, then:

```
/netek
```

No dependencies — the scripts are Python 3 standard library only.

## Use

```
/netek
/netek cellcom mobile
"cancel my HOT TV subscription"
"אני רוצה להתנתק מפרטנר"
```

First run will ask for your details and save a profile to
`~/.claude-plugins/netek/profiles/default.json` (outside this repo — see
[`references/user-data-layout.md`](references/user-data-layout.md)). After that
it reuses them.

The CLI underneath is usable on its own:

```bash
python3 scripts/netek.py providers              # all 55 providers
python3 scripts/netek.py services cellcom       # what can be cancelled there
python3 scripts/netek.py city ירושלים           # city code
python3 scripts/netek.py street 3000 יפו        # street + postcode
python3 scripts/netek.py check-id 030764534     # validate an Israeli ID

python3 scripts/netek.py build  --profile … --provider cellcom \
                                --service "טלפון נייד" --line 050-1234567
python3 scripts/netek.py submit --profile … --provider … --service … --confirm
```

`build` never sends anything. `submit` refuses without `--confirm`.

## How a cancellation actually works

1. You (or Claude) submit the request to Netek.
2. **Netek emails you an activation link.**
3. You click it. Only then does the cancellation go to the provider.
4. The provider processes it under Israeli consumer protection law.

Step 2 is not a formality — the request is inert until the account holder
clicks. The plugin will not click it for you, and neither should anything built
on this code. That link is your consent.

## Scope

**Does:** cancellation requests, for the person operating the session, from a
profile they supplied, after showing them the payload.

**Doesn't:** file on behalf of third parties; batch across identities; touch
Netek's `/p/leads/*` endpoints, which pass your details to competing providers
as a sales lead. Cancelling is not shopping, and the two are kept apart
deliberately.

Netek covers 55 providers. If yours isn't among them, the plugin says so rather
than guessing — see [`data/providers.json`](data/providers.json).

## Your data

There is **no Netek account and no Netek credential** — the API is
unauthenticated. What the form does need is your own identity: name, ת.ז. (or
ח.פ.), address, phone, email and the **last four digits** of your payment card,
because the provider uses those to check you are the account holder.

That lives in `~/.claude-plugins/netek/profiles/`, never in this repo.
Optionally the sensitive fields can be kept in 1Password and read at submit
time instead of sitting in a JSON file — see
[`skills/netek-profile/SKILL.md`](skills/netek-profile/SKILL.md). Nothing here
ever wants a full card number.

## Layout

```
commands/netek.md              slash command
skills/
  netek-disconnect/            the main flow: build, confirm, submit
  netek-browser-fallback/      fill the form in Chrome when the API breaks
  netek-profile/               store and read your details (incl. 1Password)
  netek-providers/             provider, service and address lookup
  netek-status/                check a request by guid
scripts/
  netek.py                     CLI: lookup, validate, build, submit
  refresh_providers.py         re-pull the catalogue, report drift
data/providers.json            catalogue snapshot (55, 2026-07-30)
docs/api-map.md                the unofficial API, and how it was derived
schema/profile.schema.json     profile shape
references/user-data-layout.md where personal data lives, and why
```

## When it breaks

Netek ships a new hashed JS bundle on every deploy, and the API is theirs to
change. Two things happen, in this order:

1. **You still get the cancellation done.** `netek-browser-fallback` fills the
   same form in your own Chrome via the Chrome MCP, matching fields by their
   visible Hebrew labels rather than by selectors — so it survives the rebuilds
   that break the API. Slower and interactive, but it's the route Netek
   actually supports.
2. **Then the API gets repaired.** Check catalogue drift first:

   ```bash
   python3 scripts/refresh_providers.py --check
   ```

   Then re-derive the endpoints using the recipe at the end of
   [`docs/api-map.md`](docs/api-map.md) and update that file's "verified" date
   in the same commit.

The fallback skill asks you to record what broke while you're there. Skipping
that turns a one-off repair into a permanent detour.

## Licence

MIT. See [LICENSE](LICENSE).

Use it for your own subscriptions. Israeli consumer protection law gives you
the right to cancel; this is a convenience wrapper around exercising it, not
legal advice.
