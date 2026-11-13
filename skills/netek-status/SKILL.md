---
name: netek-status
description: Check what happened to a Netek cancellation request using the guid returned when it was submitted, and explain the activation-email step that gates it. Use when the user asks whether their disconnection went through, or says they never got a confirmation.
---

# Check a cancellation request

```bash
python3 scripts/netek.py status <guid>
```

The `guid` comes back in the response to a submit. If the user doesn't have it,
it is also in the activation link Netek emailed them —
`https://www.netek.co.il/he/Soon/<guid>`.

**Both this endpoint's response shape and the activation call are inferred from
Netek's JavaScript, not observed against the live server** (see
`docs/api-map.md`). Report whatever the API returns; don't dress it up as a
status you recognise if the shape is unfamiliar.

## "I submitted it but nothing happened"

Almost always the activation step. The sequence is:

1. Submit → Netek creates the request and emails the address in the payload.
2. **The account holder clicks the link in that email.**
3. Only then does Netek send the cancellation to the provider.

So walk through it in that order:

- Did they receive the email? Check spam — it comes from Netek, not the
  provider.
- Was the address in the payload right? A typo in `email` means the request
  exists and can never be activated. There is no resend; submit again with the
  correct address.
- Did they click the link? Confirm explicitly. "I got the email" is not the
  same as "I clicked it".

Do not click the activation link on the user's behalf, and do not call
`/p/request/activation` for them. That link is the account holder's consent
that the cancellation should go out — it is theirs to give.

## Before resubmitting

Check status first. A submit that errored may still have created a request; a
second one produces two cancellations for the same account, which providers
handle badly. If status is unreadable or the guid is lost, tell the user what
you know rather than firing another request to find out.

## Timing

Netek relays to the provider; the provider then has its own statutory process.
"Activated" means Netek has sent it, not that the service is off. For anything
beyond that, the user deals with the provider directly — Netek's status has
nothing further to say about it.
