#!/usr/bin/env python3
"""Génère les cartes SVG (stats, langages, activité, badges) depuis l'API GitHub.

Usage :
  GH_TOKEN=... GH_USER=Daabzfn python scripts/generate_stats.py
  python scripts/generate_stats.py --empty   # cartes vides (placeholders)
  python scripts/generate_stats.py --demo    # fausses données (test du rendu)
Aucune dépendance externe (stdlib uniquement).
"""
from xml.sax.saxutils import escape
import json, os, sys, urllib.request
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


def label(x, y, value, size=15, color=TEXT, anchor="start", bold=False):
    weight = 700 if bold else 400
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def rect(x, y, w, h, color, radius=0):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius}" fill="{color}"/>'


def panel(w, h, command, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="Consolas, monospace">',
            f'<title>{title}</title>', rect(0, 0, w, h, "#292831", 10),
            rect(1, 1, w-2, h-2, BG, 9), rect(0, 20, 4, 20, PINK),
            label(24, 34, "$", 18, PINK, bold=True), label(48, 34, command, 17),
            rect(24, 50, w-48, 1, "#302c37")]


def fmt(v):
    return "—" if v is None else f"{v:,}".replace(",", " ")


def card_stats(d):
    out = panel(480, 240, "cat stats.c", "Statistiques GitHub")
    out.extend([label(24, 76, "t_profil", 18, PINK2),
                label(125, 76, "github = {", 18)])
    fields = [("commits", "commits"), ("pull_requests", "prs"), ("issues", "issues"),
              ("repos_publics", "repos"), ("etoiles", "stars"), ("followers", "followers")]
    for i, (field, key) in enumerate(fields):
        y = 100 + i*21
        value = str(d[key]) if d else "?"
        out.extend([label(48, y, "." + field, 17),
                    label(211, y, "=", 17, MUTED),
                    label(239, y, value + ",", 17, PINK2, bold=True)])
        if i in (0, 3):
            out.append(label(337, y, "/* 12 mois */" if i == 0 else "/* profil */", 14, MUTED))
    out.append(label(24, 229, "};", 18))
    return "\n".join(out + ["</svg>"])


def card_langs(d):
    out = panel(480, 240, "cat langages.json", "Répartition des langages en pourcentage du code")
    langs = d["langs"] if d else []
    total = sum(size for _, size in langs)
    shown = langs if len(langs) <= 5 else langs[:4] + [("Autres", sum(s for _, s in langs[4:]))]
    out.append(rect(55, 62, 1, 159, TRACK))
    if total:
        # Format the file as a short editor listing, including the line numbers.
        y = 114 if len(shown) == 1 else 79
        rows = [label(72, y, "{", 19, MUTED)]
        for i, (name, size) in enumerate(shown, 1):
            row_y = y + i*22
            key = name if len(name) <= 23 else name[:22] + "…"
            comma = "," if i < len(shown) else ""
            rows.append(label(91, row_y, f'"{key}":', 17, PINK2))
            rows.append(label(450, row_y, f'"{100*size/total:.1f}%"{comma}', 17, TEXT, "end"))
        rows.append(label(72, y + (len(shown)+1)*22, "}", 19, MUTED))
        for i, row in enumerate(rows):
            out.extend([label(40, y+i*22, i+1, 13, MUTED, "end"), row])
    else:
        out.append(label(72, 133, "Aucune donnée de langage", 16, MUTED))
    return "\n".join(out + ["</svg>"])


def card_activity(d):
    out = panel(1000, 192, "./activité --jours 30", "Contributions sur les 30 derniers jours")
    days = d["days"][-30:] if d else []
    if days:
        counts = [v for _, v in days]
        out.append(label(976, 34, f"{fmt(sum(counts))} contributions", 16, PINK2, "end"))
        peak = max(counts) or 1
        for i, (day, count) in enumerate(days):
            x = 24 + i*32
            height = max(4, 66*count/peak)
            out += [f'<g><title>{day} · {count}</title>', rect(x, 76, 21, 66, TRACK, 2),
                    rect(x, 142-height, 21, height, PINK if count else "#514453", 2), '</g>']
            if i in {0, 7, 14, 21, len(days)-1} and (i == len(days)-1 or len(days)-1-i >= 2):
                out.append(label(x+10, 170, day[8:10]+"/"+day[5:7], 13, MUTED, "middle"))
    else:
        out.append(label(24, 118, "En attente de données", 17, MUTED))
    return "\n".join(out + ["</svg>"])


def card_badges(d):
    out = panel(1000, 180, "./trophées", "Trophées et progression")
    out.append(label(976, 34, "3 paliers par trophée", 14, MUTED, "end"))
    items = [("Commits", "commits", (1, 50, 300)), ("Pull requests", "prs", (1, 5, 20)),
             ("Dépôts", "repos", (1, 5, 15)), ("Étoiles", "stars", (1, 5, 25)),
             ("Followers", "followers", (1, 5, 20))]
    cup = "M2 0h10v2h2v4h-2v2h-2v2H8v2h3v2H3v-2h3v-2H4V8H2V6H0V2h2z M2 3v2h1V3z M11 3v2h1V3z"
    for i, (name, key, thresholds) in enumerate(items):
        x = 24 + i*192
        v = d[key] if d else None
        tier = sum(v >= t for t in thresholds) if d else 0
        color = [MUTED, PINK2, PINK, "#d392ff"][tier]
        out += [f'<path d="{cup}" transform="translate({x} 72) scale(2)" fill="{color}" fill-rule="evenodd"/>',
                label(x+40, 99, fmt(v), 26, bold=True), label(x, 128, name, 15)]
        for j in range(3):
            out.append(rect(x+j*48, 147, 42, 5, color if j < tier else TRACK, 1))
    return "\n".join(out + ["</svg>"])


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
