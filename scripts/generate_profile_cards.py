#!/usr/bin/env python3
"""Generate self-hosted profile SVG cards from GitHub's GraphQL API.

Uses only Python's standard library and the built-in GitHub Actions token.
The generated SVGs are stored in the profile repository, not on a third-party server.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import time
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
ORANGE = "#F59E0B"
BLUE = "#38BDF8"
TEXT = "#E6EDF3"
MUTED = "#8B949E"
BG = "#0D1117"
BORDER = "#30363D"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 1, ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""


def h(value: object) -> str:
    return html.escape(str(value), quote=True)


def fetch_data(username: str, token: str) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"login": username}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-visuals",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=35) as res:
                result = json.load(res)
            break
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == 2:
                raise RuntimeError("GitHub API unavailable after 3 attempts; existing cards preserved") from error
            time.sleep(2 ** attempt)
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user not found: {username}")
    return user


def svg_open(width: int, height: int, title: str, *, prefix: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{h(title)}">',
        f'<title>{h(title)}</title>',
        '<defs>',
        f'<linearGradient id="{prefix}-top" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#F97316"/><stop offset=".5" stop-color="#EF4444"/><stop offset="1" stop-color="#38BDF8"/></linearGradient>',
        f'<linearGradient id="{prefix}-surface" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#161B22"/><stop offset="1" stop-color="{BG}"/></linearGradient>',
        '</defs>',
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="13" fill="url(#{prefix}-surface)" stroke="{BORDER}"/>',
        f'<rect x="1" y="1" width="{width-2}" height="3" rx="1.5" fill="url(#{prefix}-top)" opacity=".92"/>',
    ]


def txt(x: int | float, y: int | float, text: object, *, size: int = 14, color: str = TEXT,
        weight: int = 400, anchor: str = "start") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" '
            f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif" '
            f'font-weight="{weight}" text-anchor="{anchor}">{h(text)}</text>')


def small_metric(x: int, y: int, width: int, label: str, value: object, color: str) -> str:
    return "".join([
        f'<rect x="{x}" y="{y}" width="{width}" height="63" rx="9" fill="#161B22" stroke="#242B35"/>',
        txt(x + 14, y + 29, value, size=23, color=color, weight=700),
        txt(x + 14, y + 49, label, size=11, color=MUTED),
    ])


def card_stats(username: str, info: dict, total: int) -> str:
    parts = svg_open(520, 222, f"{username} GitHub statistics", prefix="s")
    parts += [txt(22, 41, "GitHub Stats", size=19, weight=700),
              txt(498, 40, f"@{username}", size=12, color=MUTED, anchor="end"),
              txt(22, 61, "Contributions and public profile", size=11, color=MUTED)]
    metrics = [
        ("Contributions · 12 mo", f"{total:,}", ORANGE),
        ("Public repositories", f"{info['repositories']['totalCount']:,}", BLUE),
        ("Commit contributions · 12 mo", f"{info['contributionsCollection']['totalCommitContributions']:,}" if info['contributionsCollection']['totalCommitContributions'] is not None else "Unavailable", BLUE),
        ("Followers", f"{info['followers']['totalCount']:,}", ORANGE),
    ]
    for i, (name, val, color) in enumerate(metrics):
        x, y = 22 + 245 * (i % 2), 74 + 72 * (i // 2)
        parts.append(small_metric(x, y, 231, name, val, color))
    parts.append('</svg>')
    return ''.join(parts)


def streak_data(days: list[tuple[dt.date, int]]) -> tuple[int, int, int]:
    today = dt.datetime.now(dt.timezone.utc).date()
    days = [(day, count) for day, count in sorted(days) if day <= today]
    if not days:
        return 0, 0, 0

    longest = current = 0
    previous = None
    for day, count in days:
        if previous is not None and day != previous + dt.timedelta(days=1):
            current = 0
        previous = day
        if count > 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    # An in-progress, empty today does not end the streak achieved yesterday.
    end_idx = len(days) - 1
    if days[end_idx][0] < today - dt.timedelta(days=1):
        return 0, longest, sum(count > 0 for _, count in days)
    if days[end_idx][0] == today and days[end_idx][1] == 0:
        end_idx -= 1
    last_streak = 0
    while end_idx >= 0 and days[end_idx][1] > 0:
        last_streak += 1
        if end_idx > 0 and days[end_idx][0] - days[end_idx - 1][0] != dt.timedelta(days=1):
            break
        end_idx -= 1
    active = sum(count > 0 for _, count in days)
    return last_streak, longest, active


def card_streak(username: str, days: list[tuple[dt.date, int]]) -> str:
    current, longest, active = streak_data(days)
    parts = svg_open(520, 222, f"{username} contribution streak", prefix="t")
    parts += [txt(22, 41, "Contribution Streak", size=19, weight=700),
              txt(498, 40, "Last 12 months", size=12, color=MUTED, anchor="end"),
              txt(22, 61, "Consistency over time", size=11, color=MUTED)]
    parts.append('<rect x="22" y="74" width="476" height="132" rx="9" fill="#161B22" stroke="#242B35"/>')
    parts.append(f'<line x1="180" x2="180" y1="96" y2="183" stroke="{BORDER}"/>')
    parts.append(f'<line x1="339" x2="339" y1="96" y2="183" stroke="{BORDER}"/>')
    for x, value, label, color in [
        (101, current, "Current · days", ORANGE),
        (259, longest, "Longest · days", BLUE),
        (418, active, "Active days", ORANGE),
    ]:
        parts.append(txt(x, 143, value, size=33, color=color, weight=700, anchor="middle"))
        parts.append(txt(x, 169, label, size=12, color=MUTED, anchor="middle"))
    parts.append('</svg>')
    return ''.join(parts)


def weekly_data(days: list[tuple[dt.date, int]], num_weeks: int = 32) -> list[tuple[dt.date, int]]:
    if not days:
        return []
    last_date = max(day for day, _ in days)
    # Weeks run Sunday–Saturday in the GitHub contribution calendar.
    last_sunday = last_date - dt.timedelta(days=(last_date.weekday() + 1) % 7)
    grouped: dict[dt.date, int] = {}
    for day, count in days:
        sunday = day - dt.timedelta(days=(day.weekday() + 1) % 7)
        grouped[sunday] = grouped.get(sunday, 0) + count
    starts = [last_sunday - dt.timedelta(weeks=num_weeks - 1 - i) for i in range(num_weeks)]
    return [(start, grouped.get(start, 0)) for start in starts]


def card_activity(username: str, days: list[tuple[dt.date, int]]) -> str:
    points = weekly_data(days)
    parts = svg_open(1060, 290, f"{username} GitHub contribution activity", prefix="a")
    parts += [txt(28, 48, "Activity Graph", size=21, weight=700),
              txt(1032, 45, "Weekly contributions · last 32 weeks", size=12, color=MUTED, anchor="end")]
    if not points:
        parts.append(txt(530, 160, "Contribution data unavailable", size=17, color=MUTED, anchor="middle"))
        return ''.join(parts + ['</svg>'])
    x0, x1, y0, y1 = 40, 1020, 94, 234
    max_value = max(1, max(count for _, count in points))
    cap = max(4, math.ceil(max_value / 4) * 4)
    for i in range(5):
        y = y1 - (y1 - y0) * i / 4
        parts.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="#30363D" opacity=".55" stroke-dasharray="3 6"/>')
        parts.append(txt(30, y + 3, int(cap * i / 4), size=10, color=MUTED, anchor="end"))
    coordinates = []
    for i, (_, value) in enumerate(points):
        x = x0 + i * (x1 - x0) / (len(points) - 1)
        y = y1 - value / cap * (y1 - y0)
        coordinates.append((x, y))
    parts.append('<defs><linearGradient id="a-area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#38BDF8" stop-opacity=".30"/><stop offset="1" stop-color="#F59E0B" stop-opacity=".015"/></linearGradient></defs>')
    path = ' '.join(f'{x:.1f},{y:.1f}' for x, y in coordinates)
    parts.append(f'<polygon points="{x0},{y1} {path} {x1},{y1}" fill="url(#a-area)"/>')
    parts.append(f'<polyline points="{path}" fill="none" stroke="{ORANGE}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    for x, y in coordinates:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{ORANGE}" stroke="{BG}" stroke-width="1.5"/>')
    shown_months = set()
    for i, (date, _) in enumerate(points):
        marker = (date.year, date.month)
        if marker not in shown_months:
            shown_months.add(marker)
            x = x0 + i * (x1 - x0) / (len(points) - 1)
            parts.append(txt(x, 259, date.strftime('%b'), size=11, color=MUTED, anchor="middle"))
    parts.append('</svg>')
    return ''.join(parts)


def main() -> None:
    username = os.environ.get("GH_USER", "").strip()
    token = os.environ.get("GH_TOKEN", "").strip()
    if not username or not token:
        raise SystemExit("Set GH_USER and GH_TOKEN. The workflow provides these automatically.")
    user = fetch_data(username, token)
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [(dt.date.fromisoformat(d["date"]), int(d["contributionCount"]))
            for week in cal["weeks"] for d in week["contributionDays"]]
    if not days:
        raise RuntimeError("GitHub returned an empty contribution calendar")
    OUT.mkdir(parents=True, exist_ok=True)
    output = {
        "stats.svg": card_stats(username, user, cal["totalContributions"]),
        "streak.svg": card_streak(username, days),
        "activity.svg": card_activity(username, days),
    }
    for filename, contents in output.items():
        (OUT / filename).write_text(contents, encoding="utf-8")
        print(f"Updated {OUT / filename}")


if __name__ == "__main__":
    main()
