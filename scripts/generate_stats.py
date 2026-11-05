#!/usr/bin/env python3
"""Génère les cartes SVG (stats, langages, activité, badges) depuis l'API GitHub.

Usage :
  GH_TOKEN=... GH_USER=Daabzfn python scripts/generate_stats.py
  python scripts/generate_stats.py --empty   # cartes vides (placeholders)
  python scripts/generate_stats.py --demo    # fausses données (test du rendu)
Aucune dépendance externe (stdlib uniquement).
"""
import json, math, os, sys, urllib.request
from datetime import date

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "generated")
BG, PINK, PINK2, VIOLET = "#0d0d0f", "#ff2e93", "#ff9be0", "#b517ff"
TEXT, MUTED, TRACK = "#ffffff", "#8a8a95", "#1c1c22"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'Courier New',Consolas,monospace"

QUERY = """
query($login:String!){
  user(login:$login){
    followers{totalCount}
    repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
      totalCount
      nodes{
        stargazerCount
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}
      }
    }
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}
    }
  }
}"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-readme-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    u = payload["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for rp in repos:
        for e in rp["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "user": user,
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "stars": sum(rp["stargazerCount"] for rp in repos),
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda x: -x[1]),
        "days": [(d["date"], d["contributionCount"]) for d in days][-30:],
    }


def demo(user):
    import random
    random.seed(4)
    d = date.today().toordinal()
    return {
        "user": user, "commits": 212, "prs": 6, "issues": 3, "stars": 9, "repos": 14, "followers": 7,
        "langs": [("C", 52000), ("TypeScript", 31000), ("Python", 18000), ("CSS", 9000), ("HTML", 7000), ("JavaScript", 4000)],
        "days": [(date.fromordinal(d - 29 + i).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8, 4])) for i in range(30)],
    }


# ---------- helpers ----------
def head(w, h, extra=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>
  <linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PINK}" stop-opacity="0.45"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient>
  <filter id="n" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  {extra}
</defs>
<style>.t{{font:600 15px {SANS};letter-spacing:3px;fill:{PINK}}} .l{{font:400 14px {SANS};fill:{MUTED}}} .v{{font:700 15px {SANS};fill:{TEXT}}} .s{{font:400 11px {MONO};fill:{MUTED};letter-spacing:1px}}</style>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="{BG}" stroke="{PINK}" stroke-opacity="0.55" stroke-width="1.5"/>
'''


def fade(i, step=0.12):
    return f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{i*step:.2f}s" fill="freeze"/>'


def fmt(v):
    return "—" if v is None else (f"{v/1000:.1f}k" if v >= 10000 else f"{v:,}".replace(",", " "))


# ---------- cartes ----------
def card_stats(d):
    rows = [("Commits (12 mois)", "commits"), ("Pull requests", "prs"), ("Issues", "issues"),
            ("Étoiles reçues", "stars"), ("Repos publics", "repos"), ("Followers", "followers")]
    out = [head(480, 235), '<text class="t" x="28" y="40">GITHUB STATS</text>',
           f'<rect x="28" y="50" width="60" height="2" rx="1" fill="url(#g)"/>']
    for i, (label, key) in enumerate(rows):
        y = 84 + i * 26
        v = d[key] if d else None
        out.append(f'<g opacity="0">{fade(i)}<text class="l" x="28" y="{y}">{label}</text>'
                   f'<text class="v" x="290" y="{y}" text-anchor="end">{fmt(v)}</text></g>')
    score = 0
    if d:
        score = d["commits"] + 3 * d["prs"] + 2 * d["issues"] + 4 * d["stars"] + 2 * d["followers"] + 2 * d["repos"]
    tiers = [(2000, "S"), (800, "A"), (300, "B"), (100, "C"), (0, "D")]
    letter = next(l for t, l in tiers if score >= t) if d else "?"
    pct = max(0.04, min(score / 1000, 1)) if d else 0.04
    r = 44; c = 2 * math.pi * r
    out.append(f'''<g transform="translate(390 124)">
  <circle r="{r}" fill="none" stroke="{TRACK}" stroke-width="8"/>
  <circle r="{r}" fill="none" stroke="url(#g)" stroke-width="8" stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{c:.1f}" transform="rotate(-90)" filter="url(#n)">
    <animate attributeName="stroke-dashoffset" from="{c:.1f}" to="{c*(1-pct):.1f}" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>
  </circle>
  <text y="12" text-anchor="middle" style="font:800 34px {SANS};fill:{TEXT}">{letter}</text>
  <text y="64" text-anchor="middle" class="s">NIVEAU</text>
</g></svg>''')
    return "\n".join(out)


def card_langs(d):
    out = [head(480, 235), '<text class="t" x="28" y="40">TOP LANGAGES</text>',
           f'<rect x="28" y="50" width="60" height="2" rx="1" fill="url(#g)"/>']
    langs = d["langs"][:6] if d else []
    if not langs:
        out.append(f'<text class="l" x="240" y="130" text-anchor="middle">En attente de la 1re mise à jour…</text>')
    else:
        tot = sum(s for _, s in d["langs"]) or 1
        for i, (name, size) in enumerate(langs):
            y = 84 + i * 24
            p = size / tot
            w = max(4, 270 * p / (langs[0][1] / tot))
            out.append(f'''<g opacity="0">{fade(i)}
  <text class="l" x="28" y="{y}" style="fill:{TEXT}">{name}</text>
  <rect x="140" y="{y-10}" width="270" height="9" rx="4.5" fill="{TRACK}"/>
  <rect x="140" y="{y-10}" width="0" height="9" rx="4.5" fill="url(#g)">
    <animate attributeName="width" from="0" to="{w:.1f}" dur="1.1s" begin="{i*0.12:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.8 0.2 1"/>
  </rect>
  <text class="s" x="452" y="{y}" text-anchor="end">{p*100:.1f}%</text></g>''')
    out.append("</svg>")
    return "\n".join(out)


def card_activity(d):
    W, H, x0, x1, yb, yt = 1000, 270, 50, 950, 215, 80
    out = [head(W, H), '<text class="t" x="28" y="40">ACTIVITÉ — 30 DERNIERS JOURS</text>']
    days = d["days"] if d and d["days"] else [(date.today().isoformat(), 0)] * 2
    vals = [c for _, c in days]
    vmax = max(max(vals), 4)
    n = len(vals)
    for k in range(5):
        y = yt + (yb - yt) * k / 4
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{PINK}" stroke-opacity="0.08"/>')
        out.append(f'<text class="s" x="{x0-10}" y="{y+4:.1f}" text-anchor="end">{round(vmax*(1-k/4))}</text>')
    pts = [(x0 + (x1 - x0) * i / (n - 1), yb - (yb - yt) * v / vmax) for i, v in enumerate(vals)]
    p = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        mx = (ax + bx) / 2
        p += f" C{mx:.1f} {ay:.1f} {mx:.1f} {by:.1f} {bx:.1f} {by:.1f}"
    out.append(f'<path d="{p} L{x1} {yb} L{x0} {yb}Z" fill="url(#ar)" opacity="0"><animate attributeName="opacity" from="0" to="1" dur="1.2s" begin="0.6s" fill="freeze"/></path>')
    out.append(f'<path d="{p}" pathLength="1" fill="none" stroke="{PINK}" stroke-width="3" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1" filter="url(#n)">'
               f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur="2s" fill="freeze"/></path>')
    for i, ((x, y), v) in enumerate(zip(pts, vals)):
        if v > 0:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{BG}" stroke="{PINK2}" stroke-width="2" opacity="0"><animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{0.3+i*0.06:.2f}s" fill="freeze"/></circle>')
    for idx in (0, n // 2, n - 1):
        dt = days[idx][0]
        out.append(f'<text class="s" x="{pts[idx][0]:.1f}" y="{yb+26}" text-anchor="middle">{dt[8:10]}/{dt[5:7]}</text>')
    total = sum(vals) if d else None
    out.append(f'<text class="s" x="{W-28}" y="40" text-anchor="end" style="fill:{PINK2}">{fmt(total)} CONTRIBUTIONS</text>')
    if not d:
        out.append(f'<text class="l" x="{W/2}" y="150" text-anchor="middle">En attente de la 1re mise à jour…</text>')
    out.append("</svg>")
    return "\n".join(out)


def hexpath(cx, cy, r):
    return "M" + " L".join(f"{cx + r*math.cos(math.radians(-90+60*k)):.1f} {cy + r*math.sin(math.radians(-90+60*k)):.1f}" for k in range(6)) + "Z"


def card_badges(d):
    items = [("COMMITS", "commits", [1, 50, 300]), ("PULL REQ.", "prs", [1, 5, 20]), ("REPOS", "repos", [1, 5, 15]),
             ("ÉTOILES", "stars", [1, 5, 25]), ("FOLLOWERS", "followers", [1, 5, 20])]
    W, H = 1000, 190
    out = [head(W, H), '<text class="t" x="28" y="40">TROPHÉES</text>']
    for i, (label, key, th) in enumerate(items):
        cx, cy = 100 + i * 200, 95
        v = d[key] if d else 0
        tier = sum(v >= t for t in th)
        on = tier > 0
        stroke = "url(#g)" if on else "#2a2a32"
        out.append(f'<g opacity="0">{fade(i, 0.15)}')
        out.append(f'<path d="{hexpath(cx, cy, 40)}" fill="{PINK if on else "none"}" fill-opacity="0.08" stroke="{stroke}" stroke-width="3"' + (' filter="url(#n)"' if on else '') + '>')
        if on:
            out.append('<animate attributeName="stroke-opacity" values="1;0.5;1" dur="3s" repeatCount="indefinite"/>')
        out.append('</path>')
        out.append(f'<text x="{cx}" y="{cy+7}" text-anchor="middle" style="font:800 20px {SANS};fill:{TEXT if on else "#4a4a55"}">{fmt(v if d else None)}</text>')
        out.append(f'<text class="s" x="{cx}" y="{cy+62}" text-anchor="middle" style="fill:{PINK2 if on else MUTED}">{label}</text>')
        for k in range(3):
            out.append(f'<circle cx="{cx-12+k*12}" cy="{cy+74}" r="3" fill="{PINK if k < tier else TRACK}"/>')
        out.append('</g>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    user = os.environ.get("GH_USER", "Daabzfn")
    if "--empty" in sys.argv:
        d = None
    elif "--demo" in sys.argv:
        d = demo(user)
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("GH_TOKEN manquant")
        d = fetch(user, token)
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("stats", card_stats), ("langs", card_langs), ("activity", card_activity), ("trophies", card_badges)):
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn(d))
    print("OK")


if __name__ == "__main__":
    main()
