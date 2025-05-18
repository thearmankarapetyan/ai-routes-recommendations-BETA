#!/usr/bin/env python3
"""
dataFetcher.py  –  v2  (adds routes linked to outings)
─────────────────────────────────────────────────────────────────────
Existing files produced:
  • data/outings_user15.json
  • data/summits_chamonix.json
  • data/routes_by_summit.json

NEW:
  • data/routes_from_outings.json   dict { route_id: route_obj }
"""

from __future__ import annotations
import json, sys, pathlib, requests, time

# ─────────────────────────── config ───────────────────────────
API   = "https://api.whympr.com"
TOKEN = "Bearer BlaBla"
HEAD  = {"Authorization": TOKEN}
TIMEOUT = 30
DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

# output paths -------------------------------------------------
OUTINGS_JSON        = DATA_DIR / "outings_user15.json"
SUMMITS_JSON        = DATA_DIR / "summits_chamonix.json"
ROUTES_BY_SUMMIT    = DATA_DIR / "routes_by_summit.json"
ROUTES_FROM_OUTINGS = DATA_DIR / "routes_from_outings.json"


# ───────────────────────── HTTP helpers ───────────────────────
def get_json(url: str, params: dict | None = None) -> dict | list:
    r = requests.get(url, headers=HEAD, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def page_through(url: str, page_size: int = 100) -> list[dict]:
    page, acc = 1, []
    while True:
        chunk = get_json(url, {"page-size": page_size, "page-index": page})
        if not chunk:
            break
        acc.extend(chunk)
        if len(chunk) < page_size:
            break
        page += 1
    return acc


# ─────────────────────── summit auto-probe ────────────────────
def load_summits(lat: float, lng: float, radius_m: int) -> list[dict]:
    for path in ("/summits", "/summits/", "/summit", "/summit/"):
        try:
            data = get_json(f"{API}{path}", {
                "lat": lat, "lng": lng, "radius": radius_m,
                "page-size": 200, "page-index": 1,
            })
            print(f"✅  endpoint ‘{path}’ works – {len(data)} summits")
            return data
        except requests.HTTPError as e:
            if e.response.status_code != 404:
                raise
    raise RuntimeError("No /summits endpoint responded with 200")


# ───────────────────────────── main ───────────────────────────
def main() -> None:

    # 1️⃣  Tim’s outings ----------------------------------------------------
    outings = page_through(f"{API}/user/15/outings/")
    print(f"🔹 Retrieved {len(outings)} outings for user 15")
    OUTINGS_JSON.write_text(json.dumps(outings, indent=2, ensure_ascii=False))

    # 2️⃣  Summits around Chamonix -----------------------------------------
    summits = load_summits(45.92375, 6.86933, 20_000)
    SUMMITS_JSON.write_text(json.dumps(summits, indent=2, ensure_ascii=False))

    # 3️⃣  Routes for each summit ------------------------------------------
    routes_by_summit: dict[str, list[dict]] = {}
    for s in summits:
        sid, name = s["id"], s["name"]
        routes = page_through(f"{API}/summit/{sid}/routes/", 100)
        routes_by_summit[str(sid)] = routes
        print(f"   • summit {sid:<7} «{name}» → {len(routes)} route(s)")
    ROUTES_BY_SUMMIT.write_text(
        json.dumps(routes_by_summit, indent=2, ensure_ascii=False)
    )

    # 4️⃣  Routes linked directly to outings -------------------------------
    route_ids = {o.get("route_id") for o in outings if o.get("route_id")}
    print(f"\n🔹 Unique route_ids in outings: {len(route_ids)}")

    routes_from_outings: dict[str, dict] = {}
    for rid in sorted(route_ids):
        try:
            routes_from_outings[str(rid)] = get_json(f"{API}/route/{rid}/")
            print(f"   • fetched route {rid}")
            time.sleep(0.15)                 # tiny pause -> polite to API
        except requests.HTTPError as e:
            print(f"   ! route {rid} → {e.response.status_code}")
    ROUTES_FROM_OUTINGS.write_text(
        json.dumps(routes_from_outings, indent=2, ensure_ascii=False)
    )
    print(f"\n💾  saved {len(routes_from_outings)} route objects "
          f"to {ROUTES_FROM_OUTINGS.relative_to(DATA_DIR.parent)}")


# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n💥  {exc}", file=sys.stderr)
        sys.exit(1)
