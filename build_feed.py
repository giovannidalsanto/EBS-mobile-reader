#!/usr/bin/env python3
"""
EBS rundown feed builder.

Two modes:
  python build_feed.py local ebs.json ebsplus.json   -> build feed.json from saved files
  python build_feed.py                               -> fetch live from the API (set API_BASE below)

Output: feed.json  (flat, chronological, both channels merged, today + DAYS_AHEAD days)
"""
import json, re, sys, html, datetime, urllib.request

# Paste the URL you copied from DevTools up to (and including) "grid?",
# e.g. "https://audiovisual.ec.europa.eu/<whatever-path>/grid?"
API_BASE = "PASTE_BASE_URL_ENDING_IN_grid?_HERE"

CHANNELS = ["ebs", "ebsplus"]
DAYS_AHEAD = 6   # fetch today + this many days in one request per channel

def clean(s):
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def pick_en(items, key="content"):
    if not items: return ""
    for it in items:
        if it.get("language") == "EN":
            return clean(it.get(key, ""))
    return clean(items[0].get(key, ""))

def parse_grid(data):
    out = []
    for day in data:
        ch_name = (day.get("channel") or {}).get("name", "?")
        for p in day.get("programs", []):
            start = p.get("startDatetime")
            if not start: continue
            dur = int(round(p.get("duration") or 0))
            subs, seen = [], set()
            for t in p.get("transmissions", []):
                m = t.get("media") or {}
                ref = m.get("reference")
                if not ref or ref in seen: continue
                seen.add(ref)
                subs.append({
                    "ref": ref,
                    "title": pick_en(m.get("titles", [])),
                    "summary": pick_en(m.get("summaries", [])),
                })
            out.append({
                "start": start,
                "durationSec": dur,
                "channel": ch_name,
                "status": p.get("broadcastStatus", ""),
                "title": pick_en(p.get("titles", [])),
                "languages": p.get("languages", []),
                "items": subs[:15],
            })
    return out

def main():
    events = []
    if len(sys.argv) >= 2 and sys.argv[1] == "local":
        for path in sys.argv[2:]:
            with open(path, encoding="utf-8") as f:
                events += parse_grid(json.load(f))
    else:
        if "PASTE_" in API_BASE:
            sys.exit("STOP: open build_feed.py and set API_BASE first. "
                     "See Part 1 and Part 4 of the setup guide.")
        today = datetime.datetime.now(datetime.timezone.utc).date()
        d_from = today.strftime("%Y%m%d")
        d_to = (today + datetime.timedelta(days=DAYS_AHEAD)).strftime("%Y%m%d")
        for ch in CHANNELS:
            url = f"{API_BASE}channelName={ch}&dateFrom={d_from}&dateTo={d_to}&thesaurusAsObject=true"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (personal EBS schedule reader)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                events += parse_grid(json.load(r))
    events.sort(key=lambda e: e["start"])
    feed = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "events": events,
    }
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"feed.json written: {len(events)} events")

if __name__ == "__main__":
    main()
