#!/usr/bin/env python3
"""Fetch PvPoke data and build a compact pvp_data.json for the ranker app."""
import json, urllib.request, sys, datetime

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def open_url(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)

RAW = "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data"
CPM = {
    1:0.0939999967813491,1.5:0.135137430784308,2:0.166397869586944,2.5:0.192650914456886,3:0.215732470154762,3.5:0.236572655026622,4:0.255720049142837,4.5:0.273530381100769,5:0.29024988412857,5.5:0.306057381335773,6:0.321087598800659,6.5:0.335445032295077,7:0.349212676286697,7.5:0.36245774877879,8:0.375235587358474,8.5:0.387592411085168,9:0.399567276239395,9.5:0.41119354951725,10:0.422500014305114,10.5:0.432926413410414,11:0.443107545375824,11.5:0.453059953871985,12:0.46279838681221,12.5:0.472336077786704,13:0.481684952974319,13.5:0.490855810259008,14:0.499858438968658,14.5:0.508701756943992,15:0.517393946647644,15.5:0.525942508771329,16:0.534354329109191,16.5:0.542635762230353,17:0.550792694091796,17.5:0.558830599438087,18:0.566754519939422,18.5:0.574569148039264,19:0.582278907299041,19.5:0.589887911977272,20:0.59740000963211,20.5:0.604823657502073,21:0.61215728521347,21.5:0.61940411056605,22:0.626567125320434,22.5:0.633649181622743,23:0.640652954578399,23.5:0.647580963301656,24:0.654435634613037,24.5:0.661219263506722,25:0.667934000492096,25.5:0.674581899290818,26:0.681164920330047,26.5:0.687684905887771,27:0.694143652915954,27.5:0.700542893277978,28:0.706884205341339,28.5:0.713169102333341,29:0.719399094581604,29.5:0.725575616972598,30:0.731700003147125,30.5:0.734741011137376,31:0.737769484519958,31.5:0.740785574597326,32:0.743789434432983,32.5:0.746781208702482,33:0.749761044979095,33.5:0.752729105305821,34:0.75568550825119,34.5:0.758630366519684,35:0.761563837528228,35.5:0.764486065255226,36:0.767397165298461,36.5:0.77029727397159,37:0.77318650484085,37.5:0.776064945942412,38:0.778932750225067,38.5:0.781790064808426,39:0.784636974334716,39.5:0.787473583646825,40:0.790300011634826,40.5:0.792803950958807,41:0.795300006866455,41.5:0.79780392148697,42:0.800300002098083,42.5:0.802803892322847,43:0.805299997329711,43.5:0.807803863460723,44:0.81029999256134,44.5:0.812803834895026,45:0.815299987792968,45.5:0.817803806620319,46:0.820299983024597,46.5:0.822803778631297,47:0.825299978256225,47.5:0.827803750922782,48:0.830299973487854,48.5:0.832803753381377,49:0.835300028324127,49.5:0.837803755931569,50:0.840300023555755,50.5:0.842803729034748,51:0.845300018787384,51.5:0.847803702398935,52:0.850300014019012,52.5:0.852803676019539,53:0.85530000925064,53.5:0.857803649892077,54:0.860300004482269,54.5:0.862803624012168,55:0.865299999713897,
}

def fetch(url):
    print(f"  fetching {url.split('/src/data/')[-1]} ...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

print("Fetching PvPoke data...", file=sys.stderr)
gm = fetch(f"{RAW}/gamemaster.json")
rankings = {cap: fetch(f"{RAW}/rankings/all/overall/rankings-{cap}.json") for cap in (1500,2500,10000)}

# ---- moves table (index-addressed) ----
moveIds = [m["moveId"] for m in gm["moves"]]
moveIdx = {mid: i for i, mid in enumerate(moveIds)}
movesCompact = [[m["name"], m["type"], m.get("power"), m.get("energyGain"), m.get("energy"), m.get("turns")]
                for m in gm["moves"]]

# Species base stats, keyed by speciesId
species = {}
for p in gm["pokemon"]:
    species[p["speciesId"]] = {
        "name": p["speciesName"],
        "dex": p.get("dex"),
        "atk": p["baseStats"]["atk"],
        "def": p["baseStats"]["def"],
        "hp": p["baseStats"]["hp"],
        "types": p.get("types", []),
        "released": p.get("released", True),
    }

# Second-charged-move stardust cost + elite move ids, per species (compact, only where present)
t3 = {}
elite = {}
for p in gm["pokemon"]:
    sid = p["speciesId"]
    if p.get("thirdMoveCost"):
        t3[sid] = p["thirdMoveCost"]
    em = p.get("eliteMoves")
    if em:
        elite[sid] = [moveIdx[m] for m in em if m in moveIdx]

# League rankings as ordered speciesId lists (index = rank-1),
# plus per-rank detail: recommended moveset + best/worst matchups (opponents as rank indices)
leagues = {}
detail = {}
for cap, arr in rankings.items():
    key = str(cap)
    ids = [e["speciesId"] for e in arr]
    leagues[key] = ids
    pos = {sid: i for i, sid in enumerate(ids)}
    ms, best, worst = [], [], []
    for e in arr:
        ms.append([moveIdx.get(m, -1) for m in e.get("moveset", [])])
        best.append([pos.get(o["opponent"], -1) for o in e.get("matchups", [])[:5]])
        worst.append([pos.get(o["opponent"], -1) for o in e.get("counters", [])[:5]])
    detail[key] = {"ms": ms, "best": best, "worst": worst}

# ---- evolution tree (speciesId -> direct evolutions, with candy/item cost) ----
# PvPoke's gamemaster has family links but NO candy costs, so candy comes from a small
# vendored table (evolution_costs.json: "fromDex-toDex" -> [candy, item]) extracted once
# from pogoapi.net. Keeps builds deterministic / offline.
evo_costs = {}
try:
    with open("evolution_costs.json", encoding="utf-8") as f:
        _raw = json.load(f)
    evo_costs = {tuple(int(x) for x in k.split("-")): {"candy": v[0], "item": v[1]}
                 for k, v in _raw.items()}
except Exception as e:
    print(f"  WARN: evolution_costs.json unavailable ({e})", file=sys.stderr)

# dex pairs pogoapi is missing (newer species) — candy + special item
EVO_OVERRIDE = {
    (123, 900):  {"candy": 50,  "item": "Black Augurite"},   # Scyther -> Kleavor
    (203, 981):  {"candy": 50,  "item": None},               # Girafarig -> Farigiraf
    (234, 899):  {"candy": 50,  "item": None},               # Stantler -> Wyrdeer
    (550, 902):  {"candy": 50,  "item": None},               # Basculin -> Basculegion
    (884, 1018): {"candy": 50,  "item": "Metal Alloy"},      # Duraludon -> Archaludon
    (999, 1000): {"candy": None,"item": "999 Gimmighoul Coins"},  # Gimmighoul -> Gholdengo
}

evolutions = {}
for p in gm["pokemon"]:
    sid = p["speciesId"]
    if sid not in species:
        continue
    d1 = species[sid].get("dex")
    out = []
    for e in (p.get("family") or {}).get("evolutions") or []:
        if e not in species:
            continue                                   # target not in our table
        d2 = species[e].get("dex")
        info = evo_costs.get((d1, d2)) or EVO_OVERRIDE.get((d1, d2)) or {}
        out.append({"to": e, "candy": info.get("candy"), "item": info.get("item")})
    if out:
        evolutions[sid] = out

# ---- limited-time cups / special formats (LTMs) -------------------------------
# PvPoke publishes a ranking per cup at pvpoke.com/data/rankings/<cup>/overall/
# rankings-<cp>.json. We bake the ordered speciesId list + the recommended
# moveset for every ranked mon, plus best/worst matchups for the top of the list
# (that is all the app needs — the eligibility rules themselves live in the
# battle engine, which filters by the cup's include/exclude at runtime).
import re

LIVE = "https://pvpoke.com/data"
CUP_SKIP      = {"all", "custom", "gobattleleague"}
CUP_CP_ORDER  = [1500, 2500, 500, 10000]     # prefer the Great-League edition
CUP_MS_N      = None                          # offer-1: keep the moveset for every ranked mon
CUP_MATCH_N   = 200                           # best/worst matchups only for the top N
CUP_MATCH_K   = 4

def fetch_live(url, timeout=60):
    with open_url(url, timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def cup_short(title):
    t = str(title)
    m = re.search(r"\(([^)]+)\)", t)
    if t.startswith("Battle Frontier"):
        return "BF " + (m.group(1).strip() if m else "Frontier")
    if m: return m.group(1).strip()
    t = re.sub(r"^Mega\s+", "", t)
    t = re.sub(r"\s*Cup$", "", t, flags=re.I)
    t = re.sub(r"\s+Championship Series$", "", t, flags=re.I)
    return t.strip()

# the gamemaster title for a couple of formats is ambiguous in the UI
CUP_TITLE_FIX = {"mega": "Mega Great League"}
CUP_SHORT_FIX = {"mega": "Mega GL"}

# ---- short, human-readable summary of what a cup does and doesn't allow -------
# The eligibility itself is enforced by the battle engine at runtime; this is only
# the one-line explanation shown under the cup picker.
TYPE_LABEL = {
    "bug":"Bug","dark":"Dark","dragon":"Dragon","electric":"Electric","fairy":"Fairy",
    "fighting":"Fighting","fire":"Fire","flying":"Flying","ghost":"Ghost","grass":"Grass",
    "ground":"Ground","ice":"Ice","normal":"Normal","poison":"Poison","psychic":"Psychic",
    "rock":"Rock","steel":"Steel","water":"Water",
}
TAG_LABEL = {
    "mega":"Mega", "shadow":"Shadow", "legendary":"Legendary",
    "mythical":"Mythical", "ultrabeast":"Ultra Beast",
}
TAG_ORDER = ["mega", "shadow", "legendary", "mythical", "ultrabeast"]
EVO_LABEL = {1:"Unevolved Pokémon only", 2:"Second-stage evolutions only",
             3:"Final evolutions only"}
SP_NAME = {p.get("speciesId"): p.get("speciesName") for p in gm.get("pokemon", [])}

def join_and(items, word="and"):
    items = [str(i) for i in items]
    if not items: return ""
    if len(items) == 1: return items[0]
    if len(items) == 2: return items[0] + " " + word + " " + items[1]
    return ", ".join(items[:-1]) + " " + word + " " + items[-1]

def cup_rules(cdef, cp=None):
    """One short phrase per restriction, for the app's cup description.

    Some excludes carry a `leagues` list — they only apply at those CP caps
    (e.g. Mega Great League bans 5 overpowered megas, but Mega Ultra/Master
    don't).  Pass cp to drop the ones that don't apply to this edition.
    """
    out = []
    inc = cdef.get("include") or []
    exc = [f for f in (cdef.get("exclude") or [])
           if cp is None or not f.get("leagues") or cp in f["leagues"]]

    def vals(fs, kind):
        got = []
        for f in fs:
            if f.get("filterType") == kind:
                v = f.get("values") or []
                got += v if isinstance(v, list) else [v]
        return got

    inc_types, exc_types = vals(inc, "type"), vals(exc, "type")
    inc_ids, exc_ids     = vals(inc, "id"),   vals(exc, "id")

    # a type allow-list only reads as a rule when it is actually narrow
    if inc_types and len(set(inc_types)) < 15:
        out.append("Only " + join_and(sorted({TYPE_LABEL.get(t, t.title()) for t in inc_types})) + " types")
    else:
        banned = sorted(set(exc_types)) if exc_types else sorted(set(TYPE_LABEL) - set(inc_types))
        if banned and len(banned) < 18:
            out.append("No " + join_and([TYPE_LABEL.get(t, t.title()) for t in banned]) + " types")

    for stage in vals(inc, "evolution"):
        out.append(EVO_LABEL.get(stage, f"Evolution stage {stage} only"))

    if inc_ids:
        uniq  = list(dict.fromkeys(inc_ids))
        base  = list(dict.fromkeys(i.replace("_shadow", "") for i in uniq))
        megas = [i for i in base if "_mega" in i]
        if megas and len(megas) == len(base):
            out.append(f"plus {len(megas)} Mega Evolutions")
        elif inc_types:
            out.append(f"plus {len(base)} listed species")
        else:
            out.append(f"Curated list of {len(base)} species")

    tags = list(dict.fromkeys(vals(exc, "tag") + vals(inc, "tag")))
    if tags:
        ordered = [t for t in TAG_ORDER if t in tags] + [t for t in tags if t not in TAG_ORDER]
        out.append("No " + join_and([TAG_LABEL.get(t, t.title()) for t in ordered], "or") + " Pokémon")

    if exc_ids:
        uniq = list(dict.fromkeys(exc_ids))
        if len(uniq) <= 6:
            out.append("Excludes " + join_and([SP_NAME.get(i) or i.replace("_", " ").title() for i in uniq]))
        else:
            out.append(f"Excludes {len(uniq)} Pokémon")

    lc = cdef.get("levelCap")
    if lc and int(lc) < 50:
        out.append(f"Level {int(lc)} cap")
    return out


cups = {}

def emit_cup(name, cp, arr, cdef, title, short):
    """Store one published cup edition: its ranking order, movesets, matchups."""
    ids = [e["speciesId"] for e in arr]
    leagues[name] = ids
    pos = {sid: i for i, sid in enumerate(ids)}
    ms, best, worst = [], [], []
    for i, e in enumerate(arr):
        ms.append([moveIdx.get(m, -1) for m in e.get("moveset", [])])
        if i < CUP_MATCH_N:
            best.append([pos.get(o["opponent"], -1) for o in e.get("matchups", [])[:CUP_MATCH_K]])
            worst.append([pos.get(o["opponent"], -1) for o in e.get("counters", [])[:CUP_MATCH_K]])
    detail[name] = {"ms": ms, "best": best, "worst": worst}
    rules = cup_rules(cdef, cp)
    cups[name] = {"title": title, "short": short, "cp": cp, "n": len(ids),
                  "rules": rules, "desc": " · ".join(rules)}
    print(f"  cup {name:20s} {title[:34]:36s} CP {cp:<6} {len(ids):4d} ranked | {' · '.join(rules)}",
          file=sys.stderr)

# Mega League is ONE gamemaster format ("All Pokemon" = the whole league pool plus
# every Mega Evolution) that PvPoke publishes at all three CP caps.  We keep each
# edition as its own cup id so the app can treat Mega Great / Ultra / Master as
# three separate, individually-ranked formats.
MEGA_EDITIONS = [
    ("mega",        1500,  "Mega Great League", "Mega GL"),
    ("mega_ultra",  2500,  "Mega Ultra League", "Mega UL"),
    ("mega_master", 10000, "Mega Master League", "Mega ML"),
]

for cdef in gm.get("cups", []):
    name = cdef.get("name")
    if not name or name in CUP_SKIP:
        continue
    if name == "mega":
        for cid, cp, title, short in MEGA_EDITIONS:
            try:
                arr = fetch_live(f"{LIVE}/rankings/mega/overall/rankings-{cp}.json")
            except Exception:
                print(f"  WARN: no published rankings for '{title}' (CP {cp}) — skipped",
                      file=sys.stderr)
                continue
            if isinstance(arr, list) and arr:
                emit_cup(cid, cp, arr, cdef, title, short)
        continue
    picked = None
    for cp in CUP_CP_ORDER:
        try:
            arr = fetch_live(f"{LIVE}/rankings/{name}/overall/rankings-{cp}.json")
        except Exception:
            continue
        if isinstance(arr, list) and arr:
            picked = (cp, arr); break
    if not picked:
        print(f"  WARN: no published rankings for cup '{name}' — skipped", file=sys.stderr)
        continue
    cp, arr = picked
    title = CUP_TITLE_FIX.get(name) or cdef.get("title") or name
    emit_cup(name, cp, arr, cdef, title, CUP_SHORT_FIX.get(name) or cup_short(title))

# ---- GBL season schedule (which cup is live right now) ------------------------
# GBL rotations are not in PvPoke's data, so we read battleflow.app's calendar and
# cache the result in cup_schedule.json (re-runs work offline / keep the last copy).
SCHEDULE_URL = "https://battleflow.app/gbl-calendar/"
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])}

def norm_key(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

# battleflow's display names -> gamemaster cup ids (when the names disagree)
CUP_ALIAS = {
    "colorcup": "colormega", "littlecup": "little", "fantasycup": "fantasy",
    "catchcup": "catch", "willpowercup": "willpower", "retrocup": "retro",
    "spectralcup": "spectral", "cauldroncup": "cauldron",
    "halloweencup": None,                      # PvPoke has no definition for it (yet)
    "2027golaiccup": "laic2027", "golaiccup": "laic2027", "laic2027cup": "laic2027",
}

def resolve_cup(name):
    k = norm_key(name)
    if k in CUP_ALIAS:
        return CUP_ALIAS[k]
    kk = re.sub(r"cup$", "", k)
    for cid, c in cups.items():
        if kk == cid or kk == norm_key(c["title"]): return cid
    if k in cups: return k
    for cid, c in cups.items():
        nt = norm_key(c["title"])
        if kk and len(kk) > 4 and (kk in nt or nt in kk): return cid
    return None

# GBL swaps formats at 1pm Pacific, not at midnight. The calendar only carries
# dates, so on a swap day everything below would flip to the next week up to ~20
# hours early. Treat the day as not-yet-turned until 1pm Pacific has passed.
def rotation_today():
    now = datetime.datetime.now(datetime.timezone.utc)
    pac = now - datetime.timedelta(hours=7)          # PDT (UTC-7); PST would be -8
    if pac.hour < 13:                                # before 1pm Pacific the day hasn't turned
        pac -= datetime.timedelta(days=1)
    return pac.date().isoformat()

def parse_calendar(html, year):
    out = {"season": None, "start": None, "end": None, "weeks": []}
    m = re.search(r'uppercase tracking-\[0\.25em\][^>]*>Season</div>\s*<div[^>]*>([^<]+)</div>', html)
    if m: out["season"] = m.group(1).strip()
    m = re.search(r'text-white/50 shrink-0 text-right">([^<]+)</div>', html)
    if m:
        rng = re.findall(r"([A-Z][a-z]{2}) (\d+)", m.group(1))
        if len(rng) == 2:
            out["start"] = (rng[0][0], int(rng[0][1]))
            out["end"]   = (rng[1][0], int(rng[1][1]))
    def iso(mon, day):
        mm = MONTHS.get(mon)
        y = year + (1 if mm and out.get("start") and mm < MONTHS.get(out["start"][0], mm) else 0)
        return f"{y:04d}-{mm:02d}-{day:02d}" if mm else None
    today = rotation_today()
    for wk in re.split(r'data-testid="calendar-week"', html)[1:]:
        m = re.search(r'flex-1">([A-Z][a-z]{2} \d+)\s*[–-]\s*([A-Z][a-z]{2} \d+)</span>', wk)
        if not m: continue
        s_mon, s_day = m.group(1).split(); e_mon, e_day = m.group(2).split()
        ws, we = iso(s_mon, int(s_day)), iso(e_mon, int(e_day))
        entries, leagues = [], []
        # each league / cup is one row; the row carries the icon and any badge
        for row in re.split(r'flex items-start gap-4 py-3\.5', wk)[1:]:
            nm = re.search(r'class="font-bold text-white">([^<]+)</span>', row)
            if not nm: continue
            nm = nm.group(1).strip()
            cp = re.search(r'text-white/40">([^<]+)</span>', row)
            cp = cp.group(1) if cp else ""
            icon = re.search(r'cups/([a-z0-9_]+)\.webp', row)
            # "Mega Edition" seasons flag the *slot*, not just the format: an open
            # league marked mega is Mega Great/Ultra/Master League that week.
            mega = bool(re.search(r'>(Mega Edition)<', row)) or bool(
                    icon and re.search(r'_mega$', icon.group(1)) and "League" in nm)
            mc = re.search(r"(\d+)", cp.replace(",", ""))
            is_cup = "League" not in nm
            cpn = int(mc.group(1)) if mc else None
            entries.append({"name": nm, "cp": cpn, "mega": mega,
                            "cup": resolve_cup(nm) if is_cup else None})
            if not is_cup:
                # an open-league slot; "Unlimited" means no CP cap
                leagues.append({"name": nm, "cap": cpn if cpn else 10000, "mega": mega})
        out["weeks"].append({
            "start": ws, "end": we,
            "current": bool(ws and we and ws <= today < we),
            "label": f"{m.group(1)} – {m.group(2)}",
            "leagues": leagues,
            "cups": [e for e in entries if e["cup"] or "League" not in e["name"]],
        })
    if out["start"]:
        out["seasonStart"] = iso(*out["start"])
        out["seasonEnd"]   = iso(out["end"][0], out["end"][1]) if out.get("end") else None
    return out

schedule = None
try:
    with open_url(SCHEDULE_URL, 60) as r:
        html = r.read().decode("utf-8", "replace")
    schedule = parse_calendar(html, datetime.date.today().year)
    if not schedule.get("weeks"):
        schedule = None
except Exception as e:
    print(f"  WARN: could not read the GBL calendar ({e})", file=sys.stderr)

try:
    if schedule is None:
        with open("cup_schedule.json", encoding="utf-8") as f:
            schedule = json.load(f)
            print("  using cached cup_schedule.json", file=sys.stderr)
    else:
        with open("cup_schedule.json", "w", encoding="utf-8") as f:
            json.dump(schedule, f, separators=(",", ":"), ensure_ascii=False)
except Exception as e:
    print(f"  WARN: no cup schedule available ({e})", file=sys.stderr)

# annotate each cup with when it is/was live (for the picker labels)
# GBL rotates at 1pm Pacific, not midnight: on a swap day the cup is not live yet
# until that moment, so shift the comparison day accordingly.
if schedule:
    today = rotation_today()
    for cid in cups:
        hits = [w for w in schedule["weeks"]
                if any(x.get("cup") == cid for x in w.get("cups", []))]
        cur = next((w for w in hits if w["start"] and w["end"] and w["start"] <= today < w["end"]), None)
        if cur:
            cups[cid]["current"] = True
            cups[cid]["when"] = cur["start"]
            cups[cid]["ends"] = cur["end"]
        else:
            past = [w for w in hits if w["end"] and w["end"] <= today]
            fut  = [w for w in hits if w["start"] and w["start"] > today]
            if past: cups[cid]["when"] = past[-1]["start"]
            if fut:  cups[cid]["next"] = fut[0]["start"]

    # mega leagues are *league slots*, not cups — annotate them from the slot flag
    for cid, cp, _t, _s in MEGA_EDITIONS:
        if cid not in cups: continue
        hits = [w for w in schedule["weeks"]
                if any(l.get("cap") == cp and l.get("mega") for l in w.get("leagues", []))]
        cur = next((w for w in hits if w["start"] and w["end"] and w["start"] <= today < w["end"]), None)
        if cur:
            cups[cid]["current"] = True
            cups[cid]["when"] = cur["start"]
            cups[cid]["ends"] = cur["end"]
        else:
            past = [w for w in hits if w["end"] and w["end"] <= today]
            fut  = [w for w in hits if w["start"] and w["start"] > today]
            if past: cups[cid]["when"] = past[-1]["start"]
            if fut:  cups[cid]["next"] = fut[0]["start"]
        # when a mega league is live, the *normal* league of that cap is displaced:
        # record when it comes back, so the tab can say "returns Oct 20"
        off = [w for w in schedule["weeks"]
               if any(l.get("cap") == cp and not l.get("mega") for l in w.get("leagues", []))]
        fut_off = [w for w in off if w["start"] and w["start"] > today]
        if cur and fut_off:
            cups[cid]["displacedBack"] = fut_off[0]["start"]
        elif cur:
            cups[cid]["displacedBack"] = None   # normal league is out for the season

data = {
    "timestamp": gm.get("timestamp"),
    "cpm": CPM,
    "species": species,
    "leagues": leagues,
    "glIneligible": gm.get("greatLeagueIneligible", []),
    "moveIds": moveIds,
    "moves": movesCompact,
    "t3": t3,
    "elite": elite,
    "detail": detail,
    "evolutions": evolutions,
    "cups": cups,
    # the app's own app_data.json ships the schedule *with* the open-league slots,
    # so the live copy must carry them too — otherwise a live update would drop
    # the mega flags and the rotation would lose its Mega Editions.
    "schedule": ({
        **schedule,
        "weeks": [
            {**w, "leagues": [dict(l) for l in w.get("leagues", [])]}
            for w in schedule.get("weeks", [])
        ],
    } if schedule else None),
}

out = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
with open("pvp_data.json", "w", encoding="utf-8") as f:
    f.write(out)
print(f"\nWrote pvp_data.json  ({len(out)/1024:.0f} KB)", file=sys.stderr)
print(f"  species: {len(species)}  moves: {len(moveIds)}  evolutions: {len(evolutions)}", file=sys.stderr)
for cap, lst in leagues.items():
    print(f"  league {cap}: {len(lst)} ranked", file=sys.stderr)
