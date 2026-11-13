# Design notes

Decisions that aren't obvious from the code, and the constraints that settled
them.

## Why a CLI under the skills rather than skills alone

The skills could have told Claude to `curl` the endpoint directly. They don't,
because three things need to happen identically every time and are easy to get
subtly wrong in prose:

- the **Israeli ID checksum**, which fails silently at the provider days later
  if wrong;
- the **`שמספרו` service-string mangling** for phone lines, which is the kind
  of detail a model paraphrases;
- **redaction** of `personalId` and `cc` before the payload is shown in a
  transcript.

Putting them in `scripts/netek.py` makes them deterministic and testable.
Standard library only, so there's no install step between a clone and a working
plugin.

## Why `submit` needs `--confirm`

The skill already requires an explicit yes from the user. `--confirm` is a
second, mechanical gate that doesn't depend on a model having read the skill
carefully. A POST here sends a real cancellation, with a real person's ID, to a
real company; there is no unsend. Cheap insurance.

`build` and `submit` share `_prepare()` so the payload the user approves is
byte-identical to the one that gets posted — not a re-derivation that might
drift.

## Why the activation email is left alone

`POST /p/request/activation` is callable, and the guid comes back from the
submit. The plugin deliberately does not call it, and `netek-status` says so.

Netek's design puts consent in that link: the request is inert until the person
who owns the mailbox clicks it. That is the property that makes it safe for an
agent to prepare and submit a cancellation at all. Automating the click would
remove the only step an agent structurally cannot fake, and turn "assistant
fills in a form" into "assistant cancels services autonomously". Keeping the
gate is the point, not an oversight.

The same reasoning is why `personalId` and `cc` are never inferred from files
on the machine — the provider uses them to verify the account holder, so
guessing them is impersonation with extra steps.

## Why `/p/leads/*` is off by default rather than forbidden

Netek's business model has two halves. One relays cancellations. The other —
`/p/leads/request`, `request-multiple`, `request-token`, reached from the
`בא לך לשמוע הצעה מחברה אחרת?` checkbox — passes the user's name, phone, city
and email to *other* providers.

An earlier draft banned them outright. That was one step too paternalistic:
someone leaving a provider is exactly the person who might want to see competing
offers, and refusing on their behalf is its own kind of wrong answer. What
actually matters is that it isn't decided *for* them silently, in either
direction.

So: default off, never ticked without being asked, and if it is ticked the user
is told their details go to other companies. Cancellation never depends on it —
`POST /p/request` works with the box unticked, which is what makes "off by
default" a free choice rather than a degraded one.

## Why there are two paths to the same form

`scripts/netek.py` (API) is the fast path; `netek-browser-fallback` (Chrome MCP)
is the durable one. They are not redundant — they fail in opposite conditions.

The API is a private backend that Netek owes nobody stability on. The website is
the supported public route: slower, needs a visible browser, but it is what
Netek actually maintains, and it will outlive any endpoint shape recorded here.
Building only the API path would mean the plugin silently dies on Netek's next
deploy; building only the browser path would mean a heavyweight, interactive
flow for a task that is really one POST.

The fallback skill deliberately triggers on *transport* failures (HTTP errors,
unparseable responses, 404s on known endpoints) and not on *validation* failures
— a bad ID checksum fails identically in both paths, and falling back would just
reach the same rejection more slowly and less legibly.

It also asks the operator to update `docs/api-map.md` when it fires. A fallback
that quietly absorbs a broken API converts a one-time repair into a permanent
detour.

## Why the provider catalogue is snapshotted *and* fetched live

`scripts/netek.py` hits the live API — it's the source of truth, and a stale
service string produces a request the provider can't route.
`data/providers.json` exists for a different job: it makes catalogue drift
visible in git history. `refresh_providers.py --check` exits non-zero on drift,
so it works in CI or as a periodic check.

The snapshot drops the SEO fields (`Title`, `Keywords`, `Description`, `Txt`
and the `_arab`/`_rus` variants). They're mostly empty and pure noise in a
diff.

## Why profiles live outside the repo

`~/.claude-plugins/netek/profiles/`, never the working tree. This repo is
public; a profile is a person's ת.ז., address and card digits. `.gitignore`
covers the obvious names as a backstop, but the layout is what actually keeps
them apart — a file that was never in the tree can't be committed by accident.

Vault integration is optional and is *not* authentication. Netek has no
account, no key, no session — every endpoint used here is unauthenticated. The
vault protects the user's own identity fields from sitting in plaintext, and
that's its whole scope.

## Validation is client-side and mirrors Netek's

Every rule in `validate()` is lifted from Netek's own JS validators (see
`api-map.md` § Validation rules). The server's behaviour on bad input was never
tested, because testing it means submitting. Mirroring the client's rules is
the closest thing to correctness available without sending a live request.

Netek's form *parses* as well as validates — it strips non-letters from names
and non-digits from numeric fields rather than rejecting them. `netek.py` does
the same in `clean_name`/`clean_digits`, so a payload built here matches what
the site would have sent for the same input.

## What was never exercised

`POST /p/request`, `/p/request/status/{guid}` and `/p/request/activation` are
documented from the bundle, not from live calls — the first sends a real
cancellation, and the other two need a guid that only the first produces. They
are marked *(inferred)* in `api-map.md`, and `netek-status` tells Claude to
report whatever comes back rather than assume a shape.

If someone cancels something real with this and captures the redacted
responses, that's the gap worth closing.
