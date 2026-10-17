#!/usr/bin/env python3
"""Regenerate the live data the app fetches at runtime.

Reuses the normal build (build_data.py) so the numbers come from exactly the same
pipeline that produces the baked-in copy, then splits the parts that actually move
-- ranking order, recommended movesets, best/worst matchups, cup definitions and the
cup schedule -- into a small tree:

    live/index.json      {v, updated, source, keys:{<key>:{n,sha}}, cups, schedule}
    live/<key>.json      {key, v, order:[speciesId...], ms, best, worst}

The app fetches index.json on boot (tiny) and one <key>.json per league/cup it
actually shows, so a phone never downloads more than the league it is looking at.

    python3 scrape_live.py                 # runs build_data.py first
    python3 scrape_live.py --skip-build    # reuse an existing pvp_data.json
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pvp_data.json")
OUT = os.path.join(HERE, "live")
LIVE_VERSION = 1


def sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-build", action="store_true",
                    help="do not run build_data.py; use the existing pvp_data.json")
    ap.add_argument("--out", default=OUT, help="output directory (default: ./live)")
    args = ap.parse_args()

    if not args.skip_build:
        print("running build_data.py ...", file=sys.stderr)
        subprocess.run([sys.executable, "build_data.py"], cwd=HERE, check=True)

    with open(SRC, encoding="utf-8") as fh:
        d = json.load(fh)

    leagues = d.get("leagues", {})
    detail = d.get("detail", {})

    os.makedirs(args.out, exist_ok=True)

    # stale files from a removed cup should not linger
    for name in os.listdir(args.out):
        if name.endswith(".json") and name != "index.json":
            os.remove(os.path.join(args.out, name))

    keys = {}
    total = 0
    for key, order in leagues.items():
        det = detail.get(key) or {}
        payload = {
            "key": key,
            "v": LIVE_VERSION,
            "order": order,
            "ms": det.get("ms", []),
            "best": det.get("best", []),
            "worst": det.get("worst", []),
        }
        blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        path = os.path.join(args.out, key + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
        size = len(blob.encode("utf-8"))
        total += size
        keys[key] = {"n": len(order), "sha": sha16(blob), "bytes": size}

    # the app maps movesets by move id, not by index, because PvPoke inserts moves
    # into the middle of its list; it needs this list to build that mapping
    move_ids = d.get("moveIds", [])

    index = {
        "v": LIVE_VERSION,
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": d.get("timestamp"),
        "keys": keys,
        "moveIds": move_ids,
        "moveSha": sha16(",".join(move_ids)),
        "cups": d.get("cups", {}),
        "schedule": d.get("schedule", {}),
    }
    ib = json.dumps(index, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as fh:
        fh.write(ib)

    print("live/ written: %d keys, %.0f KB total, index %.1f KB"
          % (len(keys), total / 1024.0, len(ib.encode("utf-8")) / 1024.0), file=sys.stderr)
    biggest = sorted(keys.items(), key=lambda kv: -kv[1]["bytes"])[:5]
    for k, v in biggest:
        print("  %-20s %6.1f KB  n=%d" % (k, v["bytes"] / 1024.0, v["n"]), file=sys.stderr)


if __name__ == "__main__":
    main()
