"""Render a complete public-data composite without inventing activity types.

Language share is GitHub language bytes, not skills or time spent coding.
The initial radar shows weekday contribution shares because public calendar
data does not expose GraphQL's commit/issue/review breakdown.
"""
import datetime as dt
import math
from html import escape

BG = '#0D1117'
TEXT = '#E6EDF3'
MUTED = '#8B949E'
COLORS = ['#64748B', '#F97316', '#38BDF8', '#22C55E', '#EF4444']


def text(x, y, value, size=16, color=TEXT, anchor='start', weight=400):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'


def render(days, languages, stars, forks, repo_scope='Public non-fork repositories'):
    total = sum(count for _, count in days)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="850" viewBox="0 0 1280 850" role="img" aria-labelledby="title desc">',
             '<title id="title">GitHub contribution landscape</title>',
             '<desc id="desc">Actual daily contributions, public repository language bytes, weekday activity share, stars and forks. Radar is not a commit or issue breakdown.</desc>',
             '<style>text{font-family:Segoe UI,Arial,sans-serif}</style>',
             f'<rect width="1280" height="850" rx="16" fill="{BG}"/>',
             '<defs><linearGradient id="header-accent"><stop stop-color="#F97316"/><stop offset=".5" stop-color="#EF4444"/><stop offset="1" stop-color="#38BDF8"/></linearGradient></defs>',
             '<rect x="34" y="62" width="1212" height="3" rx="1.5" fill="url(#header-accent)"/>',
             text(34, 44, 'CONTRIBUTION LANDSCAPE', 17, '#FB923C', weight=600),
             text(1245, 43, f'{days[0][0]} / {days[-1][0]}', 14, MUTED, 'end')]
    start = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)
    peak = max(1, max(count for _, count in days))
    palette = ['#21262D', '#164E63', '#0284C7', '#F97316', '#EF4444']
    parts.append('<g id="daily-calendar">')
    for date, count in days:
        week, weekday = divmod((date - start).days, 7)
        x, y = 116 + week * 20 - weekday * 14, 205 + week * 8.4 + weekday * 7
        height = 2 if not count else 7 + 100 * (count / peak) ** .65
        color = palette[0 if not count else min(4, 1 + int(count / peak * 3))]
        parts.append(f'<g><title>{date}: {count} contributions</title>'
                     f'<path d="M{x},{y} l11,6 v{-height} l-11,-6Z" fill="{color}" opacity=".65"/>'
                     f'<path d="M{x+11},{y+6} l11,-6 v{-height} l-11,6Z" fill="{color}" opacity=".85"/>'
                     f'<path d="M{x},{y-height} l11,-6 l11,6 l-11,6Z" fill="{color}"/></g>')
    parts.append('</g><g id="language-donut">')
    parts.append(text(42, 534, 'LANGUAGES', 16, '#FB923C', weight=600))
    parts.append(text(42, 558, f'{repo_scope} · code bytes', 13, MUTED))
    cx, cy, radius = 155, 668, 81
    circumference = 2 * math.pi * radius
    offset = 0
    language_total = sum(languages.values())
    shown = sorted(languages.items(), key=lambda item: -item[1])
    other_details = ''
    if len(shown) > 5:
        other_details = '; ' + '; '.join(f'{name}: {size:,} bytes' for name, size in shown[4:])
        shown = shown[:4] + [('Other', sum(size for _, size in shown[4:]))]
    for i, (name, size) in enumerate(shown):
        share = size / language_total
        color = COLORS[(i + 1) % len(COLORS)]
        length = circumference * share
        details = other_details if name == 'Other' else ''
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="33" stroke-dasharray="{length:.6f} {circumference-length:.6f}" stroke-dashoffset="{-offset:.6f}" transform="rotate(-90 {cx} {cy})"><title>{escape(name)}: {size:,} bytes ({share:.2%}){escape(details)}</title></circle>')
        offset += length
        row = 626 + i * 37
        parts.append(f'<rect x="280" y="{row-12}" width="11" height="11" rx="2" fill="{color}"/>')
        parts.append(text(304, row, f'{name}  {share:.1%}', 16))
    if not language_total:
        parts.append(text(cx, cy, 'No language data', 14, MUTED, 'middle'))
    else:
        parts += [text(cx, cy-3, len(languages), 28, TEXT, 'middle', 600), text(cx, cy+22, 'languages', 13, MUTED, 'middle')]
    parts.append('</g><g id="activity-radar">')
    parts += [text(981, 91, 'ACTIVITY DISTRIBUTION', 16, '#FB923C', 'middle', 600),
              text(981, 115, 'Contribution share by weekday (%)', 13, MUTED, 'middle')]
    cx, cy, radius = 981, 267, 114
    def point(index, scale):
        angle = -math.pi / 2 + index * math.tau / 7
        return cx + math.cos(angle)*radius*scale, cy + math.sin(angle)*radius*scale
    for scale in [.25, .5, .75, 1]:
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in (point(i,scale) for i in range(7)))
        parts.append(f'<polygon points="{coords}" fill="none" stroke="#30363D" stroke-dasharray="3 4"/>')
    counts = [sum(n for date,n in days if date.weekday()==i) for i in range(7)]
    for i, label in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']):
        x,y=point(i,1)
        parts.append(f'<path d="M{cx},{cy}L{x},{y}" stroke="#30363D"/>')
        x,y=point(i,1.24)
        parts.append(text(round(x,2),round(y+5,2),label,14,MUTED,'middle'))
    values = [count / total if total else 0 for count in counts]
    coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in (point(i,share) for i,share in enumerate(values)))
    parts.append(f'<polygon points="{coords}" fill="#0284C7" fill-opacity=".3" stroke="#38BDF8" stroke-width="2.5"><title>{escape(", ".join(f"{label}: {share:.2%}" for label,share in zip(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],values)))}</title></polygon>')
    parts.append(text(981, 445, 'Grid: 25 / 50 / 75 / 100%', 12, MUTED, 'middle'))
    parts += ['</g>',text(340, 813, f'{total:,}', 30, TEXT, 'end', 600), text(355, 812, 'contributions', 19, MUTED),
              text(660, 812, f'Stars  {stars:,}', 19), text(820, 812, f'Forks  {forks:,}', 19), '</svg>']
    return ''.join(parts)
