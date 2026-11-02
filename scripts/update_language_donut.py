"""Overlay a real byte-weighted language donut on the upstream 3D composite.

Only aggregated language totals are published. Private repo identifiers,
URLs, API responses and per-repo counts are never written to disk or logs.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from render_contributions import render, text

ROOT = Path(__file__).resolve().parents[1]
NS = '{http://www.w3.org/2000/svg}'


def api(path, token):
    request = urllib.request.Request('https://api.github.com' + path, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'User-Agent': 'profile-language-summary',
    })
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not leak an endpoint containing a private repository name.
        raise RuntimeError(f'Language API failed (HTTP {error.code}); check token access. Existing committed assets are preserved.') from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('Language API network failure; existing committed assets are preserved.') from None


def collect(username, token, include_private):
    if include_private:
        viewer = api('/user', token)
        if viewer['login'].lower() != username.lower():
            raise RuntimeError('PROFILE_READ_TOKEN must belong to the profile owner')
    languages = {}
    stars = forks = 0
    page = 1
    while True:
        path = (f'/user/repos?affiliation=owner&visibility=all&per_page=100&page={page}'
                if include_private else f'/users/{username}/repos?type=owner&per_page=100&page={page}')
        batch = api(path, token)
        for repo in batch:
            if repo['fork'] or repo['owner']['login'].lower() != username.lower():
                continue
            stars += repo['stargazers_count']
            forks += repo['forks_count']
            for language, count in api(f'/repos/{repo["full_name"]}/languages', token).items():
                languages[language] = languages.get(language, 0) + count
        if len(batch) < 100:
            break
        page += 1
    return languages, stars, forks


def main():
    token = os.environ.get('GH_TOKEN', '')
    username = os.environ.get('GH_USER', '')
    private = os.environ.get('INCLUDE_PRIVATE', 'false').lower() == 'true'
    if not token or not username:
        raise SystemExit('GH_TOKEN and GH_USER are required')
    languages, stars, forks = collect(username, token, private)
    scope = 'Token-visible owned repos incl. private' if private else 'Public owned non-fork repositories'
    # Reuse only the donut component; the upstream calendar and type radar stay intact.
    preview = ET.fromstring(render([(dt.date.today(), 0)], languages, 0, 0, repo_scope=scope))
    donut = preview.find(f'.//{NS}g[@id="language-donut"]')
    settings = json.loads((ROOT / 'conf/profile-3d.json').read_text())
    path = ROOT / 'profile-3d-contrib' / settings['fileName']
    tree = ET.parse(path)
    root = tree.getroot()
    overlay = ET.SubElement(root, NS + 'g', {'id': 'byte-language-overlay'})
    ET.SubElement(overlay, NS + 'rect', {'x': '24', 'y': '505', 'width': '550', 'height': '280', 'fill': '#0D1117'})
    overlay.append(donut)
    footer = ET.SubElement(root, NS + 'g', {'id': 'all-repository-totals'})
    ET.SubElement(footer, NS + 'rect', {'x': '595', 'y': '786', 'width': '440', 'height': '64', 'fill': '#0D1117'})
    for x, label in [(660, f'Stars  {stars:,}'), (820, f'Forks  {forks:,}')]:
        footer.append(ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg">' + text(x, 830, label, 19) + '</svg>')[0])
    # Serialize only after all API calls complete successfully.
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree.write(path, encoding='unicode')
    print('Updated language donut from aggregated code bytes; repository identifiers are not published.')


if __name__ == '__main__':
    main()
