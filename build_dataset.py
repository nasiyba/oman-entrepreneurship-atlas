#!/usr/bin/env python3
"""
Oman Entrepreneurship Atlas — Step 2: Clean & Unify
----------------------------------------------------
Reads the five SMEs Development Authority XLSX files, normalizes geography,
tags each record with its source dataset and a women-led flag, aggregates to
counts, and writes one tidy long-format file (atlas_data.csv / .json).

Run:  python build_dataset.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent
OUT_CSV = DATA_DIR / "atlas_data.csv"
OUT_JSON = DATA_DIR / "atlas_data.json"

# Sheets that are never data (metadata + variable dictionary)
NON_DATA_SHEETS = {"البيانات الوصفية", "المتغيرات"}

# Column header aliases -> canonical role
GOV_HEADERS = {"المحافظة"}
WIL_HEADERS = {"الولاية"}
ACT_HEADERS = {"النشاط الحرفي", "النشاط السياحي", "نشاط المشروع"}

# Each source file -> the activity-category label we tag its records with,
# and whether records are women-led. Women file is handled specially per-sheet.
FILES = {
    "Craft_Enterprises_Data_in_the_Sultanate_of_Oman.xlsx": {
        "category": "craft", "women": False,
    },
    "HomeBased_Productive_Business_Licenses_Data_in_the_Sultanate_of_Oman.xlsx": {
        "category": "home_based", "women": False,
    },
    "Tourism_Activities_Establishments_Data_in_the_Sultanate_of_Oman.xlsx": {
        "category": "tourism", "women": False,
    },
    "Startups_Data_in_the_Sultanate_of_Oman.xlsx": {
        "category": "startup", "women": False,
    },
    # Women file: map each data sheet to a category
    "Omani_Women_Entrepreneurs_Data.xlsx": {
        "per_sheet": {
            "المؤسسات الحرفية": "craft",
            "التراخيص المنزلية": "home_based",
            "الشركات الناشئة": "startup",
        },
        "women": True,
    },
}


def normalize_arabic(s):
    """Normalize Arabic text for reliable joins: strip whitespace (incl. the
    stray internal spacing in some wilayat names), unify forms, drop tatweel."""
    if pd.isna(s):
        return None
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("\u0640", "")          # tatweel (ـ)
    s = re.sub(r"\s+", " ", s).strip()    # collapse whitespace
    return s or None


def strip_gov_prefix(s):
    """'محافظة مسقط' -> 'مسقط' for a clean governorate key (keep full name too)."""
    if s is None:
        return None
    return re.sub(r"^محافظة\s+", "", s).strip()


def pick_columns(df):
    """Identify governorate / wilayat / activity columns by header name."""
    gov = wil = act = None
    for c in df.columns:
        name = normalize_arabic(c)
        if name in GOV_HEADERS:
            gov = c
        elif name in WIL_HEADERS:
            wil = c
        elif name in ACT_HEADERS:
            act = c
    return gov, wil, act


def load_sheet(path, sheet, category, women):
    df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    gov, wil, act = pick_columns(df)
    if gov is None or act is None:
        print(f"    !! skipped sheet {sheet!r}: missing gov/activity column")
        return None

    out = pd.DataFrame()
    out["activity"] = df[act].map(normalize_arabic)
    out["governorate"] = df[gov].map(normalize_arabic).map(strip_gov_prefix)
    out["wilayat"] = df[wil].map(normalize_arabic) if wil is not None else None
    out["category"] = category
    out["is_women_led"] = women
    out = out.dropna(subset=["activity", "governorate"])
    return out


def main():
    frames = []
    for fname, cfg in FILES.items():
        path = DATA_DIR / fname
        if not path.exists():
            sys.exit(f"Missing file: {fname}")
        print(f"FILE: {fname}")
        xl = pd.ExcelFile(path)
        data_sheets = [s for s in xl.sheet_names
                       if normalize_arabic(s) not in NON_DATA_SHEETS]
        if "per_sheet" in cfg:
            for sheet in data_sheets:
                cat = cfg["per_sheet"].get(normalize_arabic(sheet))
                if cat is None:
                    continue
                f = load_sheet(path, sheet, cat, cfg["women"])
                if f is not None:
                    print(f"    sheet {sheet!r}: {len(f)} records -> {cat} (women)")
                    frames.append(f)
        else:
            # single data sheet expected
            for sheet in data_sheets:
                f = load_sheet(path, sheet, cfg["category"], cfg["women"])
                if f is not None:
                    print(f"    sheet {sheet!r}: {len(f)} records -> {cfg['category']}")
                    frames.append(f)

    raw = pd.concat(frames, ignore_index=True)
    print(f"\nTotal raw records: {len(raw):,}")

    # Aggregate to counts: one row per (category, women, activity, gov, wilayat)
    tidy = (raw.groupby(
                ["category", "is_women_led", "activity", "governorate", "wilayat"],
                dropna=False)
               .size().reset_index(name="count"))

    tidy.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    tidy.to_json(OUT_JSON, orient="records", force_ascii=False, indent=2)
    print(f"Wrote {OUT_CSV.name} and {OUT_JSON.name}: {len(tidy):,} aggregated rows")

    # ---- Reconciliation check: are women craft counts a subset of all craft? ----
    print("\n--- Reconciliation: women-led vs total, by category & governorate ---")
    for cat in ["craft", "home_based", "startup"]:
        tot = (raw[(raw.category == cat) & (~raw.is_women_led)]
               .groupby("governorate").size())
        wom = (raw[(raw.category == cat) & (raw.is_women_led)]
               .groupby("governorate").size())
        govs = sorted(set(tot.index) | set(wom.index))
        breaches = [g for g in govs if wom.get(g, 0) > tot.get(g, 0)]
        print(f"  {cat}: total={int(tot.sum())}, women={int(wom.sum())}, "
              f"governorates where women>total: {len(breaches)}")
        if breaches:
            for g in breaches[:5]:
                print(f"      {g}: women={int(wom.get(g,0))} > total={int(tot.get(g,0))}")


if __name__ == "__main__":
    main()
