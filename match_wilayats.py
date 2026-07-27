#!/usr/bin/env python3
"""
Oman Entrepreneurship Atlas — Step 3b: Match Arabic wilayat names to GeoJSON
-----------------------------------------------------------------------------
Runs on YOUR Mac, in the same folder as atlas_data.json and oman_wilayat.geojson.

  python3 match_wilayats.py

It builds a bridge between your 64 Arabic wilayat names (from the data) and the
61 English names in the boundary file, using a curated Arabic->English mapping
plus fuzzy fallback. It prints:
  - matched pairs
  - Arabic names with NO boundary match (need a manual rule)
  - boundary names with NO data match (regions with zero businesses, usually fine)
and writes 'wilayat_crosswalk.csv' you can paste back to the chat.
"""

import json
import re
import sys
import unicodedata
from difflib import get_close_matches
from pathlib import Path

DATA = Path("atlas_data.json")
GEO = Path("oman_wilayat.geojson")
OUT = Path("wilayat_crosswalk.csv")

# Curated Arabic -> canonical English (lowercased, no 'wilayat' prefix).
# Covers Oman's wilayats; fuzzy matching catches the rest / transliteration drift.
AR2EN = {
    "مسقط": "muscat", "مطرح": "mutrah", "بوشر": "bawshar", "السيب": "seeb",
    "العامرات": "amarat", "قريات": "qurayyat",
    "صحار": "sohar", "صحم": "saham", "السويق": "suwayq", "الخابورة": "khaburah",
    "شناص": "shinas", "لوى": "liwa",
    "الرستاق": "rustaq", "العوابي": "awabi", "نخل": "nakhal",
    "وادي المعاول": "wadi al maawil", "المصنعة": "musannah", "بركاء": "barka",
    "نزوى": "nizwa", "بهلاء": "bahla", "منح": "manah", "الحمراء": "hamra",
    "أدم": "adam", "إزكي": "izki", "سمائل": "samail", "بدبد": "bidbid",
    "الجبل الأخضر": "jabal akhdar",
    "عبري": "ibri", "ينقل": "yanqul", "ضنك": "dhank",
    "صور": "sur", "ابراء": "ibra", "المضيبي": "mudaybi", "القابل": "qabil",
    "وادى بنى خالد": "wadi bani khalid", "دماء والطائيين": "dima wa al taiyyin",
    "بدية": "badiyah", "سناو": "sinaw",
    "جعلان بنى بوحسن": "jalan bani bu hassan",
    "جعلان بنى بوعلى": "jalan bani bu ali",
    "الكامل والوافي": "kamil wa al wafi", "مصيرة": "masirah",
    "صلالة": "salalah", "طاقة": "taqah", "مرباط": "mirbat", "ثمريت": "thumrayt",
    "رخيوت": "rakhyut", "ضلكوت": "dhalkut", "سدح": "sadah", "مقشن": "muqshin",
    "شليم وجزر الحلانيات": "shalim wa juzor al hallaniyat",
    "المزيونة": "mazyona",
    "خصب": "khasab", "دبا البيعة": "dibba", "بخا": "bukha", "مدحا": "madha",
    "البريمي": "buraimi", "محضة": "mahdah",
    "هيماء": "haima", "محوت": "mahawt", "الدقم": "duqm", "الجازر": "jazir",
}


def norm_ar(s):
    if not s:
        return None
    s = unicodedata.normalize("NFKC", str(s)).replace("\u0640", "")
    # drop diacritics
    s = "".join(c for c in s if not unicodedata.combining(c))
    # unify alef/ya/ta-marbuta variants for robust dict lookup
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
           .replace("ى", "ي").replace("ة", "ه"))
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def norm_en(s):
    if not s:
        return None
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace("wilayat", "").replace("wilayah", "")
    s = re.sub(r"\b(al| al-|el)\b", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def main():
    if not DATA.exists() or not GEO.exists():
        sys.exit(f"Need both {DATA} and {GEO} in this folder.")

    recs = json.loads(DATA.read_text(encoding="utf-8"))
    ar_names = sorted({r["wilayat"] for r in recs if r.get("wilayat")})

    gj = json.loads(GEO.read_text(encoding="utf-8"))
    feats = gj["features"]
    props0 = feats[0]["properties"]
    name_key = next((k for k in ("shapeName", "name", "NAME", "ADM2_EN")
                     if k in props0), list(props0)[0])
    en_names = sorted({str(f["properties"][name_key]) for f in feats})

    # normalized english -> original english
    en_norm = {norm_en(e): e for e in en_names}
    # normalized arabic dict -> english
    ar2en_norm = {norm_ar(k): v for k, v in AR2EN.items()}

    rows = []          # (arabic, english, method)
    unmatched_ar = []
    for ar in ar_names:
        key = norm_ar(ar)
        target = ar2en_norm.get(key)              # via curated dict
        en_match = None
        method = ""
        if target:
            # find the english feature whose normalized form contains target
            for en_n, en_orig in en_norm.items():
                if target in en_n or en_n in target:
                    en_match, method = en_orig, "dict"
                    break
            if not en_match:
                close = get_close_matches(target, list(en_norm), n=1, cutoff=0.6)
                if close:
                    en_match, method = en_norm[close[0]], "dict+fuzzy"
        if not en_match:
            # last resort: fuzzy the arabic-derived target if any, else skip
            unmatched_ar.append(ar)
            continue
        rows.append((ar, en_match, method))

    matched_en = {en for _, en, _ in rows}
    unmatched_en = [e for e in en_names if e not in matched_en]

    print("=" * 64)
    print(f"GeoJSON name field: {name_key!r} | features: {len(feats)}")
    print(f"Arabic wilayats in data: {len(ar_names)} | matched: {len(rows)}")
    print("=" * 64)
    print(f"\nMATCHED ({len(rows)}):")
    for ar, en, m in rows:
        print(f"  {ar:30}  ->  {en:35} [{m}]")
    print(f"\nUNMATCHED ARABIC ({len(unmatched_ar)})  (need a manual rule):")
    for ar in unmatched_ar:
        print(f"  {ar}")
    print(f"\nBOUNDARY REGIONS WITH NO DATA MATCH ({len(unmatched_en)}):")
    for en in unmatched_en:
        print(f"  {en}")

    with OUT.open("w", encoding="utf-8-sig") as f:
        f.write("arabic,english,method\n")
        for ar, en, m in rows:
            f.write(f"{ar},{en},{m}\n")
    print(f"\nWrote {OUT}. Paste the printed report (esp. the UNMATCHED lists) into the chat.")


if __name__ == "__main__":
    main()
