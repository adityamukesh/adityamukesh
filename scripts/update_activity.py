#!/usr/bin/env python3
"""Use the same public contribution calendar visitors see on GitHub."""
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.target = None
        self.text = ''
        self.heading = False
        self.heading_text = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-date' in attrs:
            self.cells[attrs['id']] = attrs['data-date']
        if tag == 'tool-tip':
            self.target = attrs.get('for')
            self.text = ''
        if tag == 'h2' and attrs.get('id') == 'js-contribution-activity-description':
            self.heading = True

    def handle_data(self, data):
        if self.target:
            self.text += data
        if self.heading:
            self.heading_text += data

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.target:
            match = re.match(r'(No|[\d,]+) contributions? on ', self.text.strip())
            if match and self.target in self.cells:
                self.counts[self.cells[self.target]] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
            self.target = None
        if tag == 'h2':
            self.heading = False


def parse_calendar(page):
    parser = CalendarParser()
    parser.feed(page)
    match = re.search(r'([\d,]+)\s+contributions?\s+in the last year', parser.heading_text)
    if not match or len(parser.counts) < 365 or len(parser.cells) != len(parser.counts):
        raise ValueError('Incomplete or changed GitHub calendar; preserving previous card')
    days = sorted((date.fromisoformat(d), n) for d, n in parser.counts.items())
    if any(b[0] - a[0] != timedelta(days=1) for a, b in zip(days, days[1:])):
        raise ValueError('Calendar has gaps')
    return int(match[1].replace(',', '')), days


def streaks(days):
    longest = running = 0
    for _, count in days:
        running = running + 1 if count else 0
        longest = max(longest, running)
    tail = days if days[-1][1] else days[:-1]
    current = 0
    for _, count in reversed(tail):
        if not count:
            break
        current += 1
    return current, longest


def render(total, days, stamp):
    current, longest = streaks(days)
    values = [('View live ↗', 'TOTAL ON GITHUB', '#58a6ff'),
              (current, 'CURRENT STREAK · DAYS', '#3fb950'),
              (longest, 'LONGEST IN WINDOW · DAYS', '#a371f7')]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="830" height="192" viewBox="0 0 830 192" role="img">',
             '<title>GitHub live contribution total link and streak snapshot</title>',
             '<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#142033"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
             '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>',
             '<rect x=".5" y=".5" width="829" height="191" rx="16" fill="url(#bg)" stroke="#30363d"/>']
    for i, (value, label, color) in enumerate(values):
        x = 138 + i * 277
        parts += [f'<text x="{x}" y="79" text-anchor="middle" fill="{color}" font-size="{28 if isinstance(value, str) else 44}" font-weight="700">{value}</text>',
                  f'<text x="{x}" y="110" text-anchor="middle" fill="#c9d1d9" font-size="10" letter-spacing="1">{label}</text>']
    parts += [f'<text x="415" y="151" text-anchor="middle" fill="#9da7b3" font-size="11">GitHub public calendar · {days[0][0]} to {days[-1][0]}</text>',
              f'<text x="415" y="173" text-anchor="middle" fill="#9da7b3" font-size="10">Checked {stamp} · refreshes hourly · GitHub may cache counts</text>', '</svg>\n']
    return '\n'.join(parts)


def hide_3d_total():
    for path in (ROOT / 'profile-3d-contrib').glob('*.svg'):
        original = path.read_text()
        # Remove only the adjacent numeric total and its label; keep the graph.
        updated = re.sub(r'<text\b[^>]*>[\d,]+</text><text\b[^>]*>contributions</text>', '', original)
        if updated != original:
            path.write_text(updated)


def main():
    page = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--retry', '2', '--max-time', '30',
                           'https://github.com/users/adityamukesh/contributions'], check=True, capture_output=True, text=True).stdout
    total, days = parse_calendar(page)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    (ROOT / 'assets/generated/activity.svg').write_text(render(total, days, stamp))
    print(f'Public GitHub calendar: {total} contributions; window ending {days[-1][0]}')
    hide_3d_total()


if __name__ == '__main__':
    main()
