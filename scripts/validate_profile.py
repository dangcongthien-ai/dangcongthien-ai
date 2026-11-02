"""Check README structure and local image integrity without dependencies."""
from pathlib import Path
import re
import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


class Images(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag != 'img':
            return
        attrs = dict(attrs)
        src = attrs['src']
        assert src.startswith('./'), f'Nonlocal image: {src}'
        path = ROOT / src
        assert path.is_file(), f'Missing image: {src}'
        assert path.name in [p.name for p in path.parent.iterdir()], f'Case mismatch: {src}'
        assert 'alt' in attrs, f'Missing alternative text: {src}'
        if path.suffix.lower() == '.png':
            data = path.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n', f'Invalid PNG: {src}'
            assert data[12:16] == b'IHDR', f'Missing PNG image header: {src}'
            assert int.from_bytes(data[16:20], 'big') > 0 and int.from_bytes(data[20:24], 'big') > 0


def main():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    headings = re.findall(r'^## (.+)$', readme, re.M)
    assert headings == [
        'About Me', 'What I Do', 'Languages & Tools',
        'Contribution Overview', 'Connect',
    ], headings
    Images().feed(readme)
    files = list((ROOT / 'assets').rglob('*.svg')) + list((ROOT / 'profile-3d-contrib').glob('*.svg'))
    for path in files:
        root = ET.parse(path).getroot()
        assert root.tag == '{http://www.w3.org/2000/svg}svg', path
        assert root.get('viewBox'), path
        assert not root.findall('.//{http://www.w3.org/2000/svg}script'), path
    settings = json.loads((ROOT / 'conf/profile-3d.json').read_text())
    graph = ROOT / 'profile-3d-contrib' / settings['fileName']
    assert graph.is_file(), 'Configured 3D output is missing'
    assert f'./profile-3d-contrib/{settings["fileName"]}' in readme
    if '--require-full-3d' in sys.argv:
        root = ET.parse(graph).getroot()
        assert root.get('viewBox') == '0 0 1280 850', 'Expected the full composite'
        assert len(root.findall('.//{http://www.w3.org/2000/svg}text')) > 15, 'Missing composite chart labels'
        calendar = root.find('.//{http://www.w3.org/2000/svg}g[@id="daily-calendar"]')
        if calendar is not None:
            snapshot = json.loads((ROOT / 'profile-3d-contrib/public-snapshot.json').read_text())
            dates = snapshot['daily_contributions']
            assert len(calendar) == len(dates), 'Daily column count differs from source snapshot'
            titles = [node.text for node in calendar.findall('.//{http://www.w3.org/2000/svg}title')]
            assert titles == [f'{day["date"]}: {day["count"]} contributions' for day in dates]
            assert root.find('.//{http://www.w3.org/2000/svg}g[@id="language-donut"]') is not None
            assert root.find('.//{http://www.w3.org/2000/svg}g[@id="activity-radar"]') is not None
            all_text = ''.join(root.itertext())
            assert f'{sum(day["count"] for day in dates):,}' in all_text
            for language, size in snapshot['languages'].items():
                assert f'{language}: {size:,} bytes' in all_text
            print('PASS: 3D columns and language values match real source snapshot')
        print('PASS: full 3D composite generated')
    print(f'PASS: five ordered sections, local image paths, {len(files)} valid SVG assets.')


if __name__ == '__main__':
    main()
