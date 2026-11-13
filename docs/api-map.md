# Netek unofficial API map

**Unofficial. Reverse-engineered. Not endorsed by or affiliated with Netek.**

Nothing here comes from Netek documentation — there is none published. Every
endpoint and field below was recovered by reading the site's own JavaScript
bundle and by issuing read-only requests. Netek can change or remove any of it
without notice, and probably will. Treat this file as a snapshot, not a
contract: if a skill in this plugin starts failing, assume this document went
stale before you assume the request was wrong, and re-derive it with
`scripts/refresh_providers.py` and the method in "How this was derived" below.

**This is not a public API.** `service.netek.co.il` is the private backend of
Netek's own website. It is undocumented, unversioned and unannounced; there is
no developer portal, no terms covering third-party use, and nobody to request
access from. It happens to be unauthenticated and CORS-open because the SPA
needs it that way, which is not the same as being offered for general use.
Anything built on it is running on borrowed time by design — hence
`skills/netek-browser-fallback/`, which uses the supported public route (the
website) when this stops working. Keep request volumes to what a person
cancelling their own subscriptions would generate.

**Verified 2026-07-30.** Parts marked *(inferred)* were read out of the bundle
but not exercised against the live server.

## What Netek is

`netek.co.il` is an Israeli consumer service that submits service-cancellation
("ניתוק") requests to telecoms, ISPs, TV providers, water-bar companies,
newspapers and credit-card issuers on a customer's behalf. The customer fills
one form; Netek sends the cancellation to the provider. Israeli consumer
protection law obliges those providers to accept a cancellation through a
channel like this.

The consumer flow is three steps: **pick provider → fill details → confirm by
email**. The email confirmation is not decorative — a request is inert until
the account holder clicks the link. See [Consent](#consent-and-the-activation-gate).

## Hosts

| Thing | Value |
| --- | --- |
| Site (React SPA) | `https://www.netek.co.il` |
| API base | `https://service.netek.co.il/api/v2` |
| Dev base seen in bundle | `http://localhost:8000` (not usable) |

The SPA sets `withCredentials: true` on its axios client, but no endpoint used
by this plugin requires a cookie, session or API key. Reads and the submit call
all work unauthenticated. There is **no Netek account and no Netek
credential** — see [Credentials](#credentials-what-a-vault-is-actually-for).

No `swagger`, `swagger/v1/swagger.json`, `api-docs` or `openapi.json` is served
(all 404, checked 2026-07-30).

## Endpoints

All paths are relative to `https://service.netek.co.il/api/v2`.

| Method | Path | Purpose | Exercised |
| --- | --- | --- | --- |
| GET | `/p/providers` | Full provider catalogue | yes |
| GET | `/p/common/cities?q=` | City autocomplete | yes |
| GET | `/p/common/streets?city=&q=` | Street autocomplete + postcode | yes |
| POST | `/p/request` | **Submit a cancellation request** | no — see note |
| GET | `/p/request/status/{guid}` | Request status | no *(inferred)* |
| POST | `/p/request/activation` | Activate via emailed guid | no *(inferred)* |
| GET | `/p/page/list` | CMS article index | yes |
| GET | `/p/page?slug=` | CMS article body | no *(inferred)* |
| POST | `/p/remove-email` | Unsubscribe an address | no *(inferred)* |
| POST | `/p/leads/request` | Marketing lead (comparison offers) | no — out of scope |
| POST | `/p/leads/request-multiple` | Lead to several providers | no — out of scope |
| POST | `/p/leads/request-token` | Lead token | no — out of scope |

> `POST /p/request` was deliberately **not** exercised while writing this. A
> successful call sends a real cancellation for a real person to a real
> company. The payload below was read out of the bundle, not observed on the
> wire; the field names are exact, the server's response shape is inferred.

### The `/p/leads/*` endpoints and the offer checkbox

The form carries a checkbox labelled **`בא לך לשמוע הצעה מחברה אחרת?`** —
"would you like to hear an offer from another company?" Its i18n key is
`chooseLeadProviders` and it drives the `/p/leads/*` endpoints, which submit the
user's name, phone, city and email under `source: "step2"`.

On that evidence — the label, the key name, and Netek's own word "leads" — these
solicit competing offers rather than cancelling anything, and they pass the
user's contact details to other companies. Cancellation does not depend on them:
`POST /p/request` works with the box unticked.

The plugin therefore leaves it **off by default and treats it as the user's
call**. Someone leaving a provider may well want to see what the others are
offering, and that's a legitimate thing to want; it just shouldn't be decided
for them, in either direction, and if it's turned on they should be told their
details go to other companies. The API skills never call `/p/leads/*` unless
asked for offers in those terms; `netek-browser-fallback` leaves the checkbox at
its default.

If this ever becomes mandatory for a cancellation, record that here — it would
change the analysis.

### GET /p/providers

No parameters. Returns a JSON array; 55 providers as of 2026-07-30.

```json
[
  {
    "ID": 7,
    "Name": "cellcom",
    "HebName": "סלקום",
    "ArName": "سيلكوم",
    "RuName": "Селком",
    "Services": "טלפון נייד|טלפון נייח|אינטרנט|טלויזיה",
    "URL": "להתנתק_מסלקום",
    "Image": "cellcom.png",
    "Title": "", "Keywords": "", "Description": "", "Txt": "…"
  }
]
```

- `ID` — integer, goes into the request as `providerID`. **Not contiguous**:
  the set runs 1–8, 10–14, 16–21, 28–30, 37, 59, 73, 75, 78, 94, 112–139, 153.
  Never assume `ID == index`.
- `Name` — lowercase English slug, goes into the request as `company`.
- `Services` — pipe-separated **Hebrew** service names. One of these strings is
  what goes into the request as `service`. There are 8 distinct values across
  the catalogue; see [`data/providers.json`](../data/providers.json).
- `URL` — Hebrew slug for the provider's marketing page,
  `https://www.netek.co.il/he/d/<percent-encoded URL>`. Present on 27 of 55.
  `/he/c/<slug>` also resolves.
- `Title`/`Keywords`/`Description`/`Txt` and the `_arab`/`_rus` variants are SEO
  copy. Mostly empty. Ignore them.

`data/providers.json` is a normalised snapshot of this response with the SEO
noise dropped. Refresh it with `scripts/refresh_providers.py`.

### GET /p/common/cities

`?q=<hebrew prefix>` → `[{"code": "3000", "name": "ירושלים"}]`

`code` is the Israeli Ministry of the Interior settlement code. You need it for
the streets lookup. Returns `[]` for an empty or non-matching `q`.

### GET /p/common/streets

`?city=<code>&q=<hebrew prefix>` → 

```json
[{"citycode": "3000", "city": "ירושלים", "postal": "1784", "address": "בן יפונה"}]
```

`city` **must be the numeric code** from the cities lookup. Passing the city
*name* returns `[]` with HTTP 200 — a silent empty result, not an error. This
is the single easiest thing to get wrong here.

`postal` is the 7-digit postcode for that street, which is where the form's
`zip` field gets auto-filled from.

### POST /p/request

The submit. Body is JSON. Field names are exact — they are *not* the same as
the form input names, the SPA renames several on the way out.

| Wire field | Source | Notes |
| --- | --- | --- |
| `fullName` | `firstName + " " + lastName`, or `contactName` for business | |
| `personalId` | `personalID` (ת.ז.), or `companyID` for business | note the lowercase `d` |
| `myCompanyName` | `companyName` | `""` for private accounts |
| `address` | `street + " " + houseNumber` | single joined string |
| `city` | city label | Hebrew name, not the code |
| `zip` | `zip` | `""` if unknown |
| `telephone` | `phone` | contact number |
| `email` | `email`, trimmed | activation link goes here |
| `cc` | `cc` | **last 4 digits of the payment method**, not a full card |
| `language` | UI language | `he` / `en` / `ar` / `ru` |
| `company` | provider `Name` | English slug, e.g. `cellcom` |
| `service` | chosen Hebrew service string | see mangling below |
| `companyID` | `companyID` | sent even when private (usually `undefined`) |
| `contactName` | `contactName` | sent even when private |
| `providerID` | provider `ID` | integer |
| `utm` | tracking params | send `{}` |

Both `personalId` and `companyID` appear because the SPA populates `personalId`
from whichever of the two applies and *also* passes the raw fields through.

**Service string mangling.** If the chosen service is `טלפון נייד` (mobile) or
`טלפון נייח` (landline), the SPA appends the number being cancelled to the
service string rather than sending it as its own field:

```
service = "טלפון נייד שמספרו 050-1234567"
```

That is a literal `" שמספרו "` (`" whose number is "`) between the service name
and the number. Miss this and the provider receives a cancellation with no
indication of which line to cancel.

**Response** *(inferred)*: a `guid` identifying the request, which the SPA
carries to `/he/Soon/{guid}`. Not confirmed against the live server.

### The activation gate

After a successful POST, Netek emails the address in `email`. The link lands on
`https://www.netek.co.il/he/Soon/{guid}`, which POSTs `/p/request/activation`
with `{"guid": "…"}`. **Until that happens the request is not sent to the
provider.** `GET /p/request/status/{guid}` reports where it has got to.

## Validation rules

Lifted from the bundle's validators. Enforce these client-side; the server's
own behaviour on bad input is unknown.

| Field | Rule |
| --- | --- |
| `firstName`, `lastName`, `contactName` | required, ≥2 chars, `[a-zA-Zא-ת\-\s]` only |
| `companyName` | required (business), ≥5 chars |
| `companyID` | required (business), numeric, ≥3 chars |
| `personalID` | required (private), 5–9 digits, checksum below |
| `cc` | numeric, exactly 4 digits |
| `phone` | `^([0-9]{2,3}-[0-9]{7})$` — **hyphen required**, e.g. `050-1234567`, `02-1234567` |
| `email` | standard, plus explicit rejection of `@.`, `.@`, and any address with no `.` |
| `zip` | optional |

Names are *parsed* (not just validated) by stripping anything outside the
letter class, and numeric fields by stripping non-digits — so the SPA silently
discards stray characters rather than complaining. `scripts/netek.py` does the
same, and tells you when it did.

**Israeli ID checksum** — the standard ת.ז. check digit. Right-pad to 9 with
leading zeros, multiply digits alternately by 1 and 2, subtract 9 from any
product over 9, sum, and require `sum % 10 == 0`. Implemented in
`scripts/netek.py --check-id`.

## Consent and the activation gate

Two properties of this API do the consent work, and neither should be
engineered around:

1. **The activation email.** A request is inert until the person who owns the
   mailbox clicks the link. An agent can prepare and submit; only the account
   holder can arm it.
2. **`personalId` and `cc`.** Netek asks for the ת.ז. and the last four digits
   of the payment method because the provider uses them to verify the requester
   is the account holder. Anyone with those details for a stranger is not the
   account holder.

So the plugin's rule is: submit only for the person operating the session, only
against a profile they supplied, only after showing them the exact payload, and
never batched across identities. `scripts/netek.py` refuses to POST without
`--confirm` for this reason.

## Credentials: what a vault is actually for

There is no Netek login. The vault integration in this plugin is not for
authenticating to Netek — it is for keeping the *user's own* identity details
(ת.ז., card last-4, address) out of a plaintext JSON file on disk, since a
cancellation request needs all of them. See
[`references/user-data-layout.md`](../references/user-data-layout.md).

## How this was derived

Repeatable, in case this document goes stale:

1. `curl https://www.netek.co.il/` → the HTML names two bundles under
   `/static/ga/`. The `main.*.chunk.js` one has the application code.
2. Grep it for quoted paths. `baseURL` assembly (`"…/api/v2"`) and the
   `Yu`/`Vu` (GET/POST) wrappers sit together, so every endpoint is defined in
   one contiguous run of the minified source — search for `/p/providers` and
   read forward.
3. The request payload is built in one object literal. Search for
   `fullName:` and read the surrounding `useCallback`.
4. Validators are single-expression functions near the form component; search
   for `"Invalid personal ID"` and read backwards for the rest of the set.
5. Field labels in all four languages are in one i18n blob; search `"Step2"`.

The bundle is hashed (`main.8410a054.chunk.js` on 2026-07-30), so the filename
changes on every Netek deploy. Re-read it from the homepage HTML rather than
hardcoding.

## Things that were checked and are not true

- No Swagger/OpenAPI document is served.
- `GET /p/common/cities` with no `q` returns `[]`, not the full city list.
- `GET /p/common/streets` with a city *name* returns `[]` and HTTP 200 — it
  does not error.
- Provider `ID`s are not contiguous and do not match array position.
- `Image` is a bare filename, not a URL.
