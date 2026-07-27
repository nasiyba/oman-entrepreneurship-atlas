import json
import csv
import pandas as pd
from collections import defaultdict

df = pd.read_csv("atlas_data.csv")
cats = ["craft", "home_based", "tourism", "startup"]

xwalk = {}
with open("wilayat_crosswalk.csv", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    header = next(reader)
    # find the arabic column and the english/shape column by position/name
    cols = [h.strip().lstrip("\ufeff").lower() for h in header]
    def find_col(*names):
        for n in names:
            if n in cols:
                return cols.index(n)
        return None
    ar_i = find_col("arabic", "ar", "wilayat_ar", "name_ar")
    en_i = find_col("shapename", "english", "en", "shape", "wilayat", "name")
    # fallback: assume first col = arabic, second = english
    if ar_i is None:
        ar_i = 0
    if en_i is None:
        en_i = 1 if len(header) > 1 else 0
    for row in reader:
        if len(row) > max(ar_i, en_i) and row[ar_i].strip():
            xwalk[row[ar_i].strip()] = row[en_i].strip()
print(f"crosswalk loaded: {len(xwalk)} wilayat mappings "
      f"(arabic col {ar_i}, english col {en_i})")

GOV_EN = {"مسقط": "Muscat", "ظفار": "Dhofar", "مسندم": "Musandam", "البريمي": "Al Buraimi",
          "الداخلية": "Ad Dakhiliyah", "شمال الباطنة": "North Al Batinah",
          "جنوب الباطنة": "South Al Batinah", "الظاهرة": "Ad Dhahirah",
          "شمال الشرقية": "North Ash Sharqiyah", "جنوب الشرقية": "South Ash Sharqiyah",
          "الوسطى": "Al Wusta"}
CAT_EN = {"craft": "Craft Enterprises", "home_based": "Home-Based Businesses",
          "tourism": "Tourism", "startup": "Startups"}
CAT_AR = {"craft": "المؤسسات الحرفية", "home_based": "الأعمال المنزلية",
          "tourism": "السياحة", "startup": "الشركات الناشئة"}


def region_block(rows):
    """Build {category:[all,women]} plus top activities per category for a slice."""
    block = {}
    acts = {}
    for cat in cats:
        sub = rows[rows.category == cat]
        allc = int(sub["count"].sum())
        women = int(sub[sub.is_women_led == True]["count"].sum())
        if allc:
            block[cat] = [allc, women]
        # top activities (sum across women/non-women)
        ta = (sub.groupby("activity")["count"].sum().sort_values(ascending=False).head(5))
        if len(ta):
            acts[cat] = [[a, int(c)] for a, c in ta.items()]
    return block, acts


# Wilayat level (apply crosswalk merges)
df["shape"] = df["wilayat"].map(xwalk)
wil_data = {}
wil_acts = {}
for shape, rows in df[df["shape"].notna()].groupby("shape"):
    b, a = region_block(rows)
    wil_data[shape] = b
    wil_acts[shape] = a

# Governorate level
gov_data = {}
gov_acts = {}
for gov, rows in df.groupby("governorate"):
    b, a = region_block(rows)
    gov_data[gov] = b
    gov_acts[gov] = a

# National summary
nat = {}
for cat in cats:
    sub = df[df.category == cat]
    allc = int(sub["count"].sum())
    women = int(sub[sub.is_women_led == True]["count"].sum())
    nat[cat] = [allc, women]
grand = sum(v[0] for v in nat.values())

# National top activities per category (for activity drill-down lists)
nat_acts = {}
for cat in cats:
    sub = df[df.category == cat]
    ta = sub.groupby("activity")["count"].sum().sort_values(ascending=False)
    nat_acts[cat] = [[a, int(c)] for a, c in ta.items()]

embed = {
    "wil": wil_data, "wil_acts": wil_acts,
    "gov": gov_data, "gov_acts": gov_acts,
    "gov_names": GOV_EN, "cat_en": CAT_EN, "cat_ar": CAT_AR,
    "nat": nat, "grand": grand, "nat_acts": nat_acts,
}
json.dump(embed, open("embed_rich.json", "w", encoding="utf-8"), ensure_ascii=False)
print("national:", {k: v for k, v in nat.items()}, "grand:", grand)
print("wilayats:", len(wil_data), "governorates:", len(gov_data))
print("bytes:", len(open("embed_rich.json", encoding="utf-8").read()))
print("sample gov_acts (Muscat craft):", gov_acts.get("مسقط", {}).get("craft", [])[:3])
