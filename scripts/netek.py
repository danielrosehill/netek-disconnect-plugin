#!/usr/bin/env python3
"""Build, validate and submit Netek cancellation requests.

Talks to an UNOFFICIAL, undocumented API that Netek may change without notice.
See docs/api-map.md. Standard library only — no install step.

Submitting is gated behind --confirm. Everything else is read-only.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://service.netek.co.il/api/v2"
UA = "netek-disconnect-plugin/0.1 (+https://github.com/danielrosehill/netek-disconnect-plugin)"

# Services whose Netek form appends the line number to the service string.
PHONE_SERVICES = {"טלפון נייד", "טלפון נייח"}
NUMBER_INFIX = " שמספרו "

LETTERS = re.compile(r"[^a-zA-Zא-ת\-\s]")
DIGITS = re.compile(r"[^\d]")
PHONE_RE = re.compile(r"^([0-9]{2,3}-[0-9]{7})$")
EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


# --------------------------------------------------------------------------- http


def _get(path, params=None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _post(path, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


# --------------------------------------------------------------- validation helpers


def valid_israeli_id(value):
    """Israeli ת.ז. check digit. Mirrors Netek's own validator."""
    s = DIGITS.sub("", str(value))
    if not s or int(s) == 0 or len(s) > 9 or len(s) < 5:
        return False
    s = s.zfill(9)
    total = 0
    for i, ch in enumerate(s):
        n = int(ch) * (i % 2 + 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def clean_name(v):
    return LETTERS.sub("", v) if v else v


def clean_digits(v):
    return DIGITS.sub("", str(v)) if v else v


# ------------------------------------------------------------------ payload building


def load_providers():
    return _get("/p/providers")


def find_provider(providers, needle):
    n = str(needle).strip().lower()
    for p in providers:
        if str(p["ID"]) == n or p["Name"].lower() == n or p["HebName"].strip() == needle.strip():
            return p
    matches = [p for p in providers if n in p["Name"].lower() or needle.strip() in p["HebName"]]
    if len(matches) == 1:
        return matches[0]
    if matches:
        names = ", ".join(f"{p['Name']} ({p['HebName']})" for p in matches)
        raise SystemExit(f"'{needle}' is ambiguous — matches: {names}")
    raise SystemExit(f"No provider matching '{needle}'. Try: netek.py providers")


def services_of(provider):
    return [s for s in (provider.get("Services") or "").split("|") if s.strip()]


def build_payload(profile, provider, service, line_number=None, language="he", notes=None):
    """Assemble the exact POST /p/request body. Returns (payload, warnings)."""
    warn = []
    acct = profile.get("accountType", "private")

    if acct == "business":
        full_name = clean_name(profile.get("contactName", ""))
        personal_id = clean_digits(profile.get("companyID", ""))
    else:
        first = clean_name(profile.get("firstName", ""))
        last = clean_name(profile.get("lastName", ""))
        full_name = f"{first} {last}".strip()
        personal_id = clean_digits(profile.get("personalID", ""))

    address = profile.get("street", "").strip()
    if profile.get("houseNumber"):
        address = f"{address} {profile['houseNumber']}".strip()

    service_str = service
    if service in PHONE_SERVICES:
        if not line_number:
            warn.append(
                f"service '{service}' is a phone service but no --line was given; "
                "the provider will not know which number to cancel"
            )
        else:
            service_str = f"{service}{NUMBER_INFIX}{line_number}"

    payload = {
        "fullName": full_name,
        "personalId": personal_id,
        "myCompanyName": profile.get("companyName", "") or "",
        "address": address,
        "city": profile.get("city", "").strip(),
        "zip": profile.get("zip", "") or "",
        "telephone": profile.get("phone", ""),
        "email": profile.get("email", "").strip(),
        "cc": clean_digits(profile.get("cc", "")),
        "language": language,
        "company": provider["Name"],
        "service": service_str,
        "companyID": profile.get("companyID"),
        "contactName": profile.get("contactName"),
        "providerID": provider["ID"],
        "utm": {},
    }
    if notes:
        payload["service"] = f"{payload['service']} — {notes}"
    return payload, warn


def validate(profile, payload, provider, service):
    """Return a list of blocking errors."""
    errs = []
    acct = profile.get("accountType", "private")

    if acct == "business":
        if len(profile.get("companyName", "") or "") < 5:
            errs.append("companyName is required and must be at least 5 characters")
        if len(clean_digits(profile.get("companyID", "")) or "") < 3:
            errs.append("companyID is required and must be at least 3 digits")
        if len(clean_name(profile.get("contactName", "")) or "") < 2:
            errs.append("contactName is required and must be at least 2 letters")
    else:
        for f in ("firstName", "lastName"):
            if len(clean_name(profile.get(f, "")) or "") < 2:
                errs.append(f"{f} is required and must be at least 2 letters")
        if not valid_israeli_id(profile.get("personalID", "")):
            errs.append("personalID failed the Israeli ID checksum")

    phone = profile.get("phone", "")
    if not phone:
        errs.append("phone is required")
    elif not PHONE_RE.match(phone):
        errs.append(f"phone '{phone}' must look like 050-1234567 (2-3 digits, hyphen, 7 digits)")

    email = (profile.get("email", "") or "").strip()
    if not email:
        errs.append("email is required — the activation link is sent there")
    elif "@." in email or ".@" in email or "." not in email or not EMAIL_RE.match(email):
        errs.append(f"email '{email}' is not valid")

    cc = clean_digits(profile.get("cc", ""))
    if cc and len(cc) != 4:
        errs.append("cc must be exactly the last 4 digits of the payment method")

    if not payload["address"]:
        errs.append("street/houseNumber are required")
    if not payload["city"]:
        errs.append("city is required")

    available = services_of(provider)
    if service not in available:
        errs.append(
            f"'{service}' is not offered by {provider['Name']}. "
            f"Available: {', '.join(available) or '(none listed)'}"
        )
    return errs


def load_profile(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def redact(payload):
    """Copy of the payload safe to print in a shared transcript."""
    out = dict(payload)
    if out.get("personalId"):
        out["personalId"] = "*" * max(0, len(out["personalId"]) - 3) + out["personalId"][-3:]
    if out.get("cc"):
        out["cc"] = "**" + out["cc"][-2:]
    return out


# ------------------------------------------------------------------------- commands


def cmd_providers(args):
    providers = load_providers()
    rows = providers
    if args.search:
        q = args.search.lower()
        rows = [p for p in providers if q in p["Name"].lower() or args.search in p["HebName"]]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    for p in sorted(rows, key=lambda x: x["ID"]):
        print(f"{p['ID']:>4}  {p['Name']:<22} {p['HebName']:<20} {' | '.join(services_of(p))}")
    print(f"\n{len(rows)} provider(s).")


def cmd_services(args):
    p = find_provider(load_providers(), args.provider)
    print(f"{p['Name']} ({p['HebName']}), providerID={p['ID']}")
    for s in services_of(p):
        tag = "  [needs --line]" if s in PHONE_SERVICES else ""
        print(f"  - {s}{tag}")


def cmd_city(args):
    for c in _get("/p/common/cities", {"q": args.query}):
        print(f"{c['code']:>6}  {c['name']}")


def cmd_street(args):
    rows = _get("/p/common/streets", {"city": args.city_code, "q": args.query})
    if not rows:
        print(
            "No results. Note: --city-code must be the numeric code from "
            "`netek.py city`, not the city name — a name returns an empty list, not an error.",
            file=sys.stderr,
        )
    for r in rows:
        print(f"{r['address']:<30} {r['city']:<14} postal={r['postal']}")


def cmd_check_id(args):
    ok = valid_israeli_id(args.value)
    print("valid" if ok else "INVALID")
    sys.exit(0 if ok else 1)


def _prepare(args):
    profile = load_profile(args.profile)
    provider = find_provider(load_providers(), args.provider)
    payload, warns = build_payload(
        profile, provider, args.service, args.line, args.language, args.notes
    )
    errs = validate(profile, payload, provider, args.service)
    return profile, provider, payload, warns, errs


def cmd_build(args):
    _, provider, payload, warns, errs = _prepare(args)
    shown = payload if args.unredacted else redact(payload)
    print(json.dumps(shown, ensure_ascii=False, indent=2))
    if not args.unredacted:
        print("\n(personalId and cc redacted; pass --unredacted to see them)", file=sys.stderr)
    for w in warns:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errs:
        print(f"ERROR: {e}", file=sys.stderr)
    print(
        f"\nWould POST to {API}/p/request for "
        f"{provider['Name']} ({provider['HebName']}) — nothing was sent.",
        file=sys.stderr,
    )
    sys.exit(1 if errs else 0)


def cmd_submit(args):
    _, provider, payload, warns, errs = _prepare(args)
    for w in warns:
        print(f"WARNING: {w}", file=sys.stderr)
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit("Refusing to submit: fix the errors above.")
    if not args.confirm:
        print(json.dumps(redact(payload), ensure_ascii=False, indent=2))
        raise SystemExit(
            f"\nRefusing to submit without --confirm. This would send a real "
            f"cancellation request to {provider['HebName']} on behalf of "
            f"{payload['fullName']}."
        )
    try:
        resp = _post("/p/request", payload)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} from /p/request: {e.read().decode('utf-8', 'replace')[:500]}")
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    print(
        f"\nSubmitted. Netek will email {payload['email']} with an activation "
        "link. The request does NOT reach the provider until that link is "
        "clicked by the account holder.",
        file=sys.stderr,
    )


def cmd_status(args):
    print(json.dumps(_get(f"/p/request/status/{args.guid}"), ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("providers", help="list or search providers")
    p.add_argument("search", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_providers)

    p = sub.add_parser("services", help="services a provider can be cancelled for")
    p.add_argument("provider")
    p.set_defaults(func=cmd_services)

    p = sub.add_parser("city", help="look up a city code")
    p.add_argument("query")
    p.set_defaults(func=cmd_city)

    p = sub.add_parser("street", help="look up a street and its postcode")
    p.add_argument("city_code")
    p.add_argument("query")
    p.set_defaults(func=cmd_street)

    p = sub.add_parser("check-id", help="validate an Israeli ID checksum")
    p.add_argument("value")
    p.set_defaults(func=cmd_check_id)

    for name, fn, extra in (("build", cmd_build, False), ("submit", cmd_submit, True)):
        p = sub.add_parser(name, help=f"{name} a cancellation request")
        p.add_argument("--profile", required=True, help="path to profile JSON")
        p.add_argument("--provider", required=True, help="ID, slug or Hebrew name")
        p.add_argument("--service", required=True, help="exact Hebrew service string")
        p.add_argument("--line", help="phone number being cancelled (phone services)")
        p.add_argument("--language", default="he", choices=["he", "en", "ar", "ru"])
        p.add_argument("--notes", help="free text appended to the service field")
        if extra:
            p.add_argument("--confirm", action="store_true", help="actually send it")
        else:
            p.add_argument("--unredacted", action="store_true")
        p.set_defaults(func=fn)

    p = sub.add_parser("status", help="check a request by guid")
    p.add_argument("guid")
    p.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
