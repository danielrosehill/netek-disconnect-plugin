# Where user data lives

Nothing personal belongs in this repo. It is public.

## Layout

```
~/.claude-plugins/netek/
├── profiles/
│   ├── default.json          # the user's own details
│   └── business.json         # optional, one file per identity
└── requests/
    └── <guid>.json           # optional record of what was submitted
```

The plugin repo holds only code, docs and the provider catalogue. The
`~/.claude-plugins/netek/` tree holds everything about a person. That split is
the whole point: the repo can be cloned, forked and pushed without ever
carrying someone's ת.ז.

## What a profile contains

Name, Israeli ID (ת.ז.) or company number, street address, phone, email, and
the last four digits of a payment card. A cancellation request needs all of it,
because the provider uses the ID and the card digits to verify the requester is
the account holder.

Two constraints on that, both practical:

- **`cc` is four digits.** Never store, ask for, or pass a full card number.
  Nothing in the Netek form or API takes one. If a user offers one, keep the
  last four and say you discarded the rest.
- **One profile is one person.** The plugin submits on behalf of whoever is
  operating the session. A directory of profiles for other people is a
  different thing entirely and this plugin does not support it.

## Keeping the sensitive fields in a vault

Optional, and orthogonal to Netek — there is no Netek account to authenticate
to. If the user prefers, `personalID` and `cc` can live in 1Password and be
read at submit time with `op read "op://<vault>/<item>/<field>"`, assembled
into a temp profile, and deleted after. The mechanics are in
`skills/netek-profile/SKILL.md`.

Always scope `op` reads to a vault. Without `--vault` or a fully-qualified
`op://` reference, `op` searches every vault and can return a different item
with the same name.

## Records of what was sent

If you keep `requests/<guid>.json`, store the **redacted** payload — the same
form `scripts/netek.py build` prints by default, with `personalId` and `cc`
masked. The guid, provider, service and date are what make a record useful
later; the ID digits are already in the profile and don't need a second copy.

## Never

- Commit a profile, a filled payload, or a real ת.ז. to this repo or any other.
- Paste an unredacted payload into a shared transcript, issue or PR.
- Write profiles into the repo working tree "temporarily".

`.gitignore` blocks the obvious filenames, but the layout above is what
actually keeps them apart.
