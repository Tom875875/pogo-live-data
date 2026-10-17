# pogo-live-data

Live data for the **PvP Ranker** app (`https://tpvp.netlify.app`).

A scheduled GitHub Action re-scrapes PvPoke (rankings, recommended movesets, cup
definitions) and the GBL cup schedule every 6 hours, then commits the result into
`live/`. The app fetches it at runtime, so rankings, movesets, cups and the
limited-time-cup schedule stay current without rebuilding or redeploying the site.

## Layout

    live/index.json      version, timestamp, per-key sizes/hashes, cup definitions, season schedule
    live/<key>.json      one league or cup: ranking order, recommended movesets, best/worst matchups

`<key>` is `1500` / `2500` / `10000` for Great/Ultra/Master, or a cup id such as
`little`, `willpower`, `catch`.

The app fetches `index.json` on boot (about 9 KB) and one `<key>.json` per league
you actually open (13–63 KB), so a phone only downloads what it is looking at.

## Setting it up

1. Create a new **public** repo on GitHub, e.g. `pogo-live-data`.
   (Public is fine and intended — this is all public game data. It contains no
   collection data; your box never leaves your device.)
2. From this folder:

       git init
       git add .
       git commit -m "initial live data"
       git branch -M main
       git remote add origin https://github.com/<YOUR-USER>/pogo-live-data.git
       git push -u origin main

3. Actions run automatically (Settings → Actions → General → Workflow permissions
   must allow *Read and write permissions* so the job can commit). You can also
   press **Run workflow** to populate `live/` immediately.

4. Tell the app where the data lives — one line in the app source:

       const LIVE_BASE = "https://raw.githubusercontent.com/<YOUR-USER>/pogo-live-data/main/live/";

   then rebuild and re-upload.

## Notes

- `pvp_data.json` is a build by-product and is git-ignored.
- `build_data.py`, `evolution_costs.json` and `cup_schedule.json` are copies from
  the app project so this repo is self-contained. If the scraper changes, copy
  them across again.
- If a run fails (source site down), the job fails and the previous `live/` stays
  in place, so the app keeps working.
