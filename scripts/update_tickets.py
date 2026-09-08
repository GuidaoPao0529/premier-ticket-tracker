#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Premier Ticket Tracker official-source updater.

Design rule:
- Official club sources only.
- Never invent dates/times.
- If a page cannot be read, keep the previous verified value.
- Automatic edits are intentionally conservative.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, re, urllib.request, urllib.error

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tickets.json"
AUDIT = ROOT / "last-audit.json"

UA = "Mozilla/5.0 (Premier Ticket Tracker; official-source monitor)"

STABLE_SOURCES = {
    "Arsenal": "https://www.arsenal.com/tickets/men",
    "Chelsea": "https://www.chelseafc.com/en/tickets",
    "Manchester United": "https://tickets.manutd.com/",
    "Manchester City": "https://www.mancity.com/tickets/mens/all/home",
}

def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def contains_match(text: str, home: str, away: str) -> bool:
    t = text.lower()
    # Conservative: opponent must be visible on the official page.
    return away.lower() in t and (home.lower() in t or "tickets" in t)

def infer_status(text: str, current: str) -> str:
    t = text.lower()
    # Only broad status words. Exact dates are NOT inferred here.
    if "ballot closed" in t:
        return "BALLOT CLOSED"
    if "application window" in t and ("open now" in t or "applications are open" in t):
        return "APPLICATION OPEN"
    if "buy now" in t or "tickets available" in t or "on sale" in t:
        return "BUY NOW"
    if "coming soon" in t or "notify me" in t:
        return "COMING SOON"
    return current

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    cache = {}
    audit = {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "changes": []
    }

    # Fetch each stable official page once.
    for club, url in STABLE_SOURCES.items():
        status, html = fetch(url)
        cache[club] = (status, norm(html))
        audit["sources"][club] = {"url": url, "httpStatus": status, "readable": bool(html)}

    changed = False
    for x in data:
        club = x.get("home")
        if club not in cache:
            continue
        status_code, text = cache[club]
        if status_code != 200 or not text:
            continue
        if not contains_match(text, x.get("home",""), x.get("away","")):
            continue

        old = x.get("ticketStatus","")
        new = infer_status(text, old)

        # Preserve specific active/closed ballot/application states over generic BUY NOW.
        specific = {"APPLICATION OPEN","APPLICATION CLOSED","BALLOT OPEN","BALLOT CLOSED","BALLOT NOTICE"}
        if old in specific and new == "BUY NOW":
            new = old

        if new != old:
            x["ticketStatus"] = new
            x["autoCheckedAt"] = audit["checkedAt"]
            audit["changes"].append({
                "match": f'{x.get("home")} vs {x.get("away")}',
                "date": x.get("date"),
                "old": old,
                "new": new,
                "officialSource": STABLE_SOURCES[club],
            })
            changed = True

    if changed:
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed": changed, "changes": audit["changes"], "audit": str(AUDIT)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
