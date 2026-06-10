#!/usr/bin/env python3
"""
EBS rundown feed builder.

Modes:
  python build_feed.py local ebs.json ebsplus.json   -> build feed.json from saved files
  python build_feed.py                               -> fetch live from the API

Output: feed.json (flat, chronological, both channels merged, today + DAYS_AHEAD days)
"""
import json, re, sys, html, gzip, time, datetime, urllib.request

API_BASE = "https://8hwk2cyeyb.execute-api.eu-west-1.amazonaws.com/parrotfish-prod/grid?"

CHANNELS = ["ebs", "ebsplus"]
DAYS_AHEAD = 6

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Accept-Language": "en",
    "Origin": "https://audiovisual.ec.europa.eu",
    "Referer": "https://audiovisual.ec.europa.eu/",
}

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

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        status = getattr(r, "status", "?")
        ctype = r.headers.get("Content-Type", "?")
        cenc = r.headers.get("Content-Encoding", "")
    if cenc == "gzip" or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Not JSON (status {status}, type {ctype}, encoding {cenc!r}). "
            f"First 300 chars: {text[:300]!r}")

def main():
    events = []
    if len(sys.argv) >= 2 and sys.argv[1] == "local":
        for path in sys.argv[2:]:
            with open(path, encoding="utf-8") as f:
                events += parse_grid(json.load(f))
    else:
        today = datetime.datetime.now(datetime.timezone.utc).date()
        failures = 0
        for ch in CHANNELS:
            for offset in range(DAYS_AHEAD + 1):
                d = (today + datetime.timedelta(days=offset)).strftime("%Y%m%d")
                url = f"{API_BASE}channelName={ch}&dateFrom={d}&dateTo={d}&thesaurusAsObject=true"
                for attempt in (1, 2):
                    try:
                        events += parse_grid(fetch_json(url))
                        break
                    except Exception as e:
                        if attempt == 2:
                            failures += 1
                            print(f"WARN {ch} {d}: {e}")
                        else:
                            time.sleep(3)
                time.sleep(0.5)
        if not events:
            sys.exit(f"All requests failed ({failures}). See warnings above.")
        if failures:
            print(f"Completed with {failures} failed day(s); feed written from the rest.")
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
