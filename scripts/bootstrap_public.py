"""Optional token-free initial snapshot from GitHub's public calendar.

Daily automation uses GraphQL and the pinned upstream 3D generator instead.
"""
import datetime as dt
from html.parser import HTMLParser
import json
import re
import urllib.request
from pathlib import Path

import generate_profile_cards as cards
from render_contributions import render


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.counts = {}, {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'td' and a.get('data-date'):
            self.cells[a['id']] = dt.date.fromisoformat(a['data-date'])
        if tag == 'tool-tip':
            self.tooltip = a.get('for')

    def handle_data(self, data):
        if self.tooltip and data.strip():
            match = re.match(r'(No|[\d,]+) contributions? on ', data.strip())
            if match:
                self.counts[self.tooltip] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tooltip = None


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'dangcongthien-profile'})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode()



def main():
    username = 'dangcongthien-ai'
    source = get(f'https://github.com/users/{username}/contributions')
    calendar = Calendar()
    calendar.feed(source)
    if not calendar.cells or calendar.cells.keys() - calendar.counts.keys():
        raise RuntimeError('Public calendar format changed; existing assets preserved')
    days = sorted((date, calendar.counts[key]) for key, date in calendar.cells.items())
    expected = re.search(r'([\d,]+)\s+contributions\s+in the last year', source)
    total = sum(n for _, n in days)
    if not expected or total != int(expected[1].replace(',', '')):
        raise RuntimeError('Daily contribution sum does not match GitHub total')
    profile = json.loads(get(f'https://api.github.com/users/{username}'))
    info = {'repositories': {'totalCount': profile['public_repos']},
            'followers': {'totalCount': profile['followers']},
            'contributionsCollection': {'totalCommitContributions': None}}
    repos = []
    page = 1
    while True:
        batch = json.loads(get(f'https://api.github.com/users/{username}/repos?type=owner&per_page=100&page={page}'))
        repos.extend(repo for repo in batch if not repo['fork'])
        if len(batch) < 100:
            break
        page += 1
    languages = {}
    for repo in repos:
        for language, size in json.loads(get(repo['languages_url'])).items():
            languages[language] = languages.get(language, 0) + size
    stars = sum(repo['stargazers_count'] for repo in repos)
    forks = sum(repo['forks_count'] for repo in repos)
    composite = render(days, languages, stars, forks)
    snapshot = {
        'fetched_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'calendar_source': f'https://github.com/users/{username}/contributions',
        'repositories': [repo['html_url'] for repo in repos],
        'language_basis': 'GitHub language bytes in public owned non-fork repositories',
        'languages': languages, 'stars': stars, 'forks': forks,
        'radar_basis': 'Share of calendar contributions by weekday, not contribution types',
        'daily_contributions': [{'date': str(date), 'count': count} for date, count in days],
    }
    outputs = {
        'assets/stats.svg': cards.card_stats(username, info, total),
        'assets/streak.svg': cards.card_streak(username, days),
        'assets/activity.svg': cards.card_activity(username, days),
        'profile-3d-contrib/profile-professional.svg': composite,
        'profile-3d-contrib/public-snapshot.json': json.dumps(snapshot, indent=2) + '\n',
    }
    for name, value in outputs.items():
        (cards.ROOT / name).write_text(value, encoding='utf-8')
    print(f'Validated {len(days)} daily counts, {total} total contributions; generated full composite and cards.')


if __name__ == '__main__':
    main()
