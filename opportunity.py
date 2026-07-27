import json

d = json.load(open('embed_data.json', encoding='utf-8'))
cats = ['craft', 'home_based', 'tourism', 'startup']


def build_lq(level):
    src = d[level]
    M = {r: {c: src[r].get(c, [0, 0])[0] for c in cats} for r in src}
    region_tot = {r: sum(M[r].values()) for r in M}
    cat_tot = {c: sum(M[r][c] for r in M) for c in cats}
    grand = sum(region_tot.values())
    lq = {}
    for r in M:
        if region_tot[r] == 0:
            continue
        lq[r] = {}
        for c in cats:
            denom = (cat_tot[c] / grand) if grand else 0
            share = (M[r][c] / region_tot[r]) if region_tot[r] else 0
            lq[r][c] = round(share / denom, 2) if denom > 0 else 0
    return M, region_tot, cat_tot, grand, lq


M, rt, ct, grand, lq = build_lq('gov')
GOV_EN = d['gov_names']

print("=== Location Quotients by governorate (LQ<1 = under-served) ===")
print(f'{"governorate":22}' + ''.join(f'{c:>11}' for c in cats))
for r in sorted(lq, key=lambda x: -rt[x]):
    print(f'{GOV_EN.get(r, r):22}' + ''.join(f'{lq[r][c]:>11}' for c in cats))

print("\n=== Top opportunities (under-served, weighted by sector size) ===")
opps = []
for r in lq:
    for c in cats:
        if lq[r][c] < 0.8:
            gap = 0.8 - lq[r][c]
            weight = ct[c] / grand
            score = round(gap * weight * 100, 2)
            target = rt[r] * (ct[c] / grand)
            shortfall = max(0, round(target - M[r][c]))
            opps.append((score, GOV_EN.get(r, r), c, lq[r][c], shortfall))
opps.sort(reverse=True)
for s, r, c, l, sf in opps[:12]:
    print(f'  {r:20} {c:12} LQ={l:<5} score={s:<6} ~{sf} below parity')
