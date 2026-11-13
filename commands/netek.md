---
description: Cancel an Israeli service subscription (ניתוק) via netek.co.il — mobile, internet, landline, TV, water bar, newspaper or credit card
argument-hint: [provider] [service] — e.g. cellcom mobile, or leave empty to be asked
---

Help the user cancel a subscription with an Israeli provider through
netek.co.il.

Arguments, if given: `$ARGUMENTS`

Work through the `netek-disconnect` skill. In short:

1. Resolve the provider and the exact Hebrew service string
   (`scripts/netek.py providers` / `services`). If the provider isn't in
   Netek's catalogue, say so — there is no fallback.
2. Load the user's profile from `~/.claude-plugins/netek/profiles/`. If there
   isn't one, use `netek-profile` to build it. Ask for identity details; never
   infer a ת.ז., an address or card digits from anything on the machine.
3. For mobile or landline, ask which number is being cancelled.
4. `scripts/netek.py build …` and show the user the payload it prints. Clear
   every ERROR.
5. Ask for an explicit yes, naming the provider, the service and the person.
   Then `submit … --confirm`.
6. Tell them Netek has emailed an activation link and that **nothing reaches
   the provider until they click it**. Keep the returned guid.

Submit only for the person in this session, from a profile they supplied. Leave
the `בא לך לשמוע הצעה מחברה אחרת?` / `/p/leads/*` offer path alone unless they
ask for competing offers — it sends their details to other companies and has
nothing to do with cancelling.

This uses an unofficial, undocumented API (`docs/api-map.md`) — Netek's own
private backend, not a published one. If a call returns an HTTP error, an
unparseable response, or a 404 on an endpoint that used to work, switch to
`netek-browser-fallback` and fill the form in Chrome instead; that's the route
Netek supports. Don't fall back on a validation error — bad input fails the
same way in the browser.
