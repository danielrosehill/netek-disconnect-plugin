#!/usr/bin/env python3
"""Refresh data/providers.json from the live Netek API.

The catalogue is served by an unofficial endpoint that can change shape without
notice. Run this when a provider looks missing or a service string stops
matching, and commit the diff — the snapshot's `retrieved` date is what tells
the next reader how stale the docs are.

    python3 scripts/refresh_providers.py [--check]

--check exits 1 if the live data differs from the snapshot, without writing.
"""

import argparse
import datetime
import json
import pathlib
import sys
import urllib.request

API = "https://service.netek.co.il/api/v2/p/providers"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "providers.json"


def fetch():
    req = urllib.request.Request(
        API,
        headers={
            "User-Agent": "netek-disconnect-plugin/0.1 "
            "(+https://github.com/danielrosehill/netek-disconnect-plugin)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def normalise(raw):
    """Drop the SEO fields; keep what the request actually needs."""
    providers = [
        {
            "id": p["ID"],
            "slug": p["Name"],
            "name_he": p["HebName"],
            "name_ar": p.get("ArName") or "",
            "name_ru": p.get("RuName") or "",
            "services_he": [s for s in (p.get("Services") or "").split("|") if s.strip()],
            "page_slug_he": (p.get("URL") or "").strip(),
        }
        for p in sorted(raw, key=lambda x: x["ID"])
    ]
    return {
        "source": API,
        "retrieved": datetime.date.today().isoformat(),
        "count": len(providers),
        "providers": providers,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report drift without writing; exit 1 if different")
    args = ap.parse_args()

    live = normalise(fetch())

    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        old_ids = {p["id"]: p for p in old.get("providers", [])}
        new_ids = {p["id"]: p for p in live["providers"]}

        added = sorted(set(new_ids) - set(old_ids))
        removed = sorted(set(old_ids) - set(new_ids))
        changed = sorted(
            i for i in set(old_ids) & set(new_ids)
            if old_ids[i]["services_he"] != new_ids[i]["services_he"]
            or old_ids[i]["slug"] != new_ids[i]["slug"]
        )

        for i in added:
            print(f"+ {i} {new_ids[i]['slug']} ({new_ids[i]['name_he']})")
        for i in removed:
            print(f"- {i} {old_ids[i]['slug']} ({old_ids[i]['name_he']})")
        for i in changed:
            print(f"~ {i} {new_ids[i]['slug']}: "
                  f"{old_ids[i]['services_he']} -> {new_ids[i]['services_he']}")

        drift = bool(added or removed or changed)
        if not drift:
            print(f"No change. {live['count']} providers.")
        if args.check:
            sys.exit(1 if drift else 0)
    elif args.check:
        print(f"{OUT} does not exist.", file=sys.stderr)
        sys.exit(1)

    OUT.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({live['count']} providers, retrieved {live['retrieved']}).")


if __name__ == "__main__":
    main()
