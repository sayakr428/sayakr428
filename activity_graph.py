"""Generate a 31-day contribution activity graph SVG (Tokyo Night style).

Runs inside GitHub Actions. Needs env GH_TOKEN and GH_USER.
Set MOCK=1 to render with random data for local testing.
"""
import datetime as dt
import json
import os
import random
import urllib.request

USER = os.environ.get("GH_USER", "sayakr428")
OUT = os.environ.get("OUT", "assets/activity-graph.svg")
DAYS = 31

# Tokyo Night palette, matching the rest of the profile
BG, GRID, TEXT, MUTED = "#1a1b26", "#2a2e42", "#c0caf5", "#565f89"
LINE, POINT = "#36BCF7", "#bb9af7"


def fetch():
    end = dt.datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
    start = (end - dt.timedelta(days=DAYS - 1)).replace(hour=0, minute=0, second=0)
    query = """query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {
        "login": USER, "from": start.isoformat() + "Z", "to": end.isoformat() + "Z"}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return [(d["date"], d["contributionCount"]) for d in days][-DAYS:]


def mock():
    today = dt.date.today()
    return [((today - dt.timedelta(days=DAYS - 1 - i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8]))
            for i in range(DAYS)]


def render(days):
    W, H = 1200, 360
    L, R, T, B = 70, 30, 70, 60
    pw, ph = W - L - R, H - T - B
    counts = [c for _, c in days]
    top = max(4, max(counts))
    step = max(1, -(-top // 4))
    top = step * 4
    x = lambda i: L + pw * i / (len(days) - 1)
    y = lambda c: T + ph - ph * c / top
    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{L},{T + ph} " + line + f" {L + pw},{T + ph}"

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{USER} contribution graph">',
         '<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{LINE}" stop-opacity=".35"/><stop offset="1" stop-color="{LINE}" stop-opacity="0"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" rx="8" fill="{BG}"/>',
         f'<text x="{W/2}" y="40" text-anchor="middle" fill="{TEXT}" font-family="Segoe UI,Ubuntu,Helvetica,Arial,sans-serif" font-size="20" font-weight="600">Contributions in the last {DAYS} days</text>']
    for k in range(5):
        v = step * k
        gy = y(v)
        o.append(f'<line x1="{L}" y1="{gy:.1f}" x2="{L + pw}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        o.append(f'<text x="{L - 12}" y="{gy + 4:.1f}" text-anchor="end" fill="{MUTED}" font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">{v}</text>')
    for i, (d, _) in enumerate(days):
        if i % 3 == 0 or i == len(days) - 1:
            o.append(f'<text x="{x(i):.1f}" y="{T + ph + 22}" text-anchor="middle" fill="{MUTED}" font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">{int(d[8:])}</text>')
    o.append(f'<text x="{L + pw/2}" y="{H - 10}" text-anchor="middle" fill="{MUTED}" font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">'
             f'{dt.date.fromisoformat(days[0][0]):%b %d} – {dt.date.fromisoformat(days[-1][0]):%b %d, %Y}</text>')
    o.append(f'<polygon points="{area}" fill="url(#a)"/>')
    o.append(f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>')
    for (px, py), (d, c) in zip(pts, days):
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{POINT}"><title>{d}: {c} contributions</title></circle>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    days = mock() if os.environ.get("MOCK") else fetch()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w").write(render(days))
    print(f"Wrote {OUT} ({sum(c for _, c in days)} contributions)")
