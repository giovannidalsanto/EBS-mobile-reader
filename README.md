# EBS Rundown

Personal mobile reader for the EBS / EBS+ daily schedule. One chronological scroll,
both channels merged, Brussels time, red playhead at "now".

## Files
- `index.html` — the page (works standalone; ships with embedded sample data, then reads `feed.json` when present)
- `build_feed.py` — fetches both channel grids from the EC Audiovisual API and writes `feed.json`
- `.github/workflows/update.yml` — refreshes `feed.json` every 15 min on weekdays via GitHub Actions

## Setup
1. Open `build_feed.py` and set `API_BASE` to the grid endpoint URL (DevTools → Network → the
   `grid?channelName=...` request → Copy URL → keep everything up to and including `grid?`).
2. Create a GitHub repo, push these files.
3. Settings → Pages → deploy from branch `main`, root.
4. Open the Pages URL on your phone → share → Add to Home screen.

Local test without the API: `python build_feed.py local ebs.json ebsplus.json`
