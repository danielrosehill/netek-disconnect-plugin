---
name: netek-providers
description: Look up which Israeli providers Netek can send cancellations to, which services each one covers, and resolve Hebrew city/street names to the codes and postcodes the form needs. Use to answer "can I cancel X through this?" or to fill in an address correctly.
---

# Look up providers, services and addresses

Read-only. Nothing here submits anything.

## Providers

```bash
python3 scripts/netek.py providers            # all of them
python3 scripts/netek.py providers סלקום      # search by Hebrew name
python3 scripts/netek.py providers cell       # or English slug
python3 scripts/netek.py providers --json     # raw
```

55 providers as of 2026-07-30, in eight categories: mobile, landline,
internet, TV, international calls, water bars, newspaper subscriptions and
credit cards. A cached snapshot is in `data/providers.json`; the commands above
hit the live API, which is the source of truth. Refresh the snapshot with
`scripts/refresh_providers.py`.

If a provider isn't listed, Netek cannot cancel it. Say that directly rather
than looking for a near-match — sending a cancellation to the wrong company
does nothing useful and hands them the user's details.

## Services

```bash
python3 scripts/netek.py services cellcom
```

Prints the exact Hebrew strings that provider accepts. Pass one of these
verbatim to `--service`; the API matches on the string, so a translation or a
paraphrase produces a request the provider can't route.

Services flagged `[needs --line]` are the phone ones — `netek-disconnect` must
also collect the number being cancelled.

## Addresses

Two-step, and the order matters:

```bash
python3 scripts/netek.py city ירושלים      # -> 3000  ירושלים
python3 scripts/netek.py street 3000 יפו   # -> street names + postcodes
```

The street lookup takes the **numeric city code**, not the city name. Passing
the name returns an empty list with HTTP 200 — an empty result, not an error,
so it looks like "no such street" when it's really "wrong parameter". The
script prints a hint when it gets nothing back.

The `postal` column is the postcode for that street; use it for the profile's
`zip`. `zip` is optional in the request, so if the lookup genuinely finds
nothing, leave it empty rather than guessing a nearby one.

## Caveat

This is an unofficial API — the catalogue, the service strings and the
endpoints themselves can change without notice. `docs/api-map.md` records what
was verified and when.
