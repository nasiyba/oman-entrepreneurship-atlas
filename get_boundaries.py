#!/usr/bin/env python3
"""
Oman Entrepreneurship Atlas — Step 3a: Fetch & inspect wilayat boundaries
--------------------------------------------------------------------------
Runs on YOUR Mac (it can reach the data sources the build sandbox can't).

  pip3 install requests        # if not already installed
  python3 get_boundaries.py

It downloads Oman ADM2 (wilayat) boundaries as GeoJSON, saves them as
'oman_wilayat.geojson' in this folder, then prints how many regions it has,
the property keys, and every region name. Copy that printed output back into
the chat so we can build the Arabic<->English name-matching bridge.
"""

import json
import sys

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip3 install requests")

OUT = "oman_wilayat.geojson"

# geoBoundaries API: returns metadata JSON that contains the real download URL
API = "https://www.geoboundaries.org/api/current/gbOpen/OMN/ADM2/"


def download():
    print(f"Querying geoBoundaries API for Oman ADM2 ...")
    meta = requests.get(API, timeout=60).json()
    # Prefer simplified geometry (smaller, fine for a web map); fall back to full
    url = meta.get("simplifiedGeometryGeoJSON") or meta.get("gjDownloadURL")
    if not url:
        sys.exit(f"Could not find a download URL in API response. Keys: {list(meta)}")
    print(f"Downloading geometry from:\n  {url}")
    gj = requests.get(url, timeout=120).json()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    print(f"Saved -> {OUT}\n")
    return gj


def inspect(gj):
    feats = gj.get("features", [])
    print("=" * 60)
    print(f"FEATURE COUNT: {len(feats)}")
    if not feats:
        return
    props = feats[0].get("properties", {})
    print(f"PROPERTY KEYS: {list(props.keys())}")
    print("=" * 60)
    # geoBoundaries uses 'shapeName'; print whatever name-like field exists
    name_key = next((k for k in ("shapeName", "name", "NAME", "ADM2_EN")
                     if k in props), None)
    print(f"NAME FIELD: {name_key}")
    print("-" * 60)
    names = sorted(str(f["properties"].get(name_key, "?")) for f in feats)
    for n in names:
        print(f"  {n}")
    print("-" * 60)
    print(f"Total names listed: {len(names)}")
    print("\n>> Copy everything from FEATURE COUNT down, and paste it into the chat.")


if __name__ == "__main__":
    inspect(download())
