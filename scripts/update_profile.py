#!/usr/bin/env python3
"""Refresh public contribution data; requires Python 3.11+ and authenticated gh."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- CONTRIBUTIONS:START -->'
END = '<!-- CONTRIBUTIONS:END -->'
# Verified project affiliations, not claims of personal LFX membership.
FOUNDATIONS = {
    'kubernetes': 'Kubernetes · CNCF',
    'kubernetes-sigs': 'Kubernetes · CNCF',
    'open-telemetry': 'OpenTelemetry · CNCF',
    'valkey-io': 'Valkey · Linux Foundation',
}


def foundation(item):
    return FOUNDATIONS.get(repository(item).split('/')[0].lower())



def search(username, state):
    query = f'author:{username} is:pr is:public -user:{username} is:{state}'
    items = []
    for page in range(1, 11):
        result = subprocess.run(
            ['gh', 'api', '--method', 'GET', 'search/issues', '-f', f'q={query}',
             '-f', 'per_page=100', '-f', f'page={page}', '-f', 'sort=updated'],
            check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        if data['incomplete_results'] or data['total_count'] > 1000:
            raise RuntimeError('Search is incomplete; preserving the published profile')
        items.extend(data['items'])
        if len(items) >= data['total_count']:
            unique = {item['html_url']: item for item in items}
            if len(unique) != data['total_count']:
                raise RuntimeError('Search changed during pagination; retry the refresh')
            return list(unique.values())
    raise RuntimeError('Search exceeded pagination limit')


def repository(item):
    return item['repository_url'].removeprefix('https://api.github.com/repos/')


def dashboard(merged, projects, featured, opened):
    stats = [(merged, 'MERGED PRS', '#67e8f9'),
             (featured, 'LF / CNCF MERGES', '#c4b5fd'),
             (projects, 'REPOSITORIES', '#fbbf24'),
             (opened, 'OPEN PRS', '#6ee7b7')]
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="830" height="128" viewBox="0 0 830 128" role="img">',
              '<title>Public open-source contribution dashboard</title>',
              '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>']
    for i, (value, label, color) in enumerate(stats):
        x = i * 210
        pieces.extend([f'<g transform="translate({x} 0)">',
                       '<rect x=".5" y=".5" width="199" height="119" rx="14" fill="#101a2b" stroke="#29374f"/>',
                       f'<path d="M18 1H182" stroke="{color}" stroke-opacity=".7"/>',
                       f'<circle cx="172" cy="25" r="4" fill="{color}" fill-opacity=".6"/>',
                       f'<text x="20" y="65" font-size="40" font-weight="700" fill="{color}">{value}</text>',
                       f'<text x="20" y="94" font-size="10" letter-spacing="1" fill="#aab8cc">{label}</text>', '</g>'])
    return '\n'.join(pieces + ['</svg>\n'])


def card(item):
    title = escape(item['title'])
    repo = repository(item)
    lines = textwrap.wrap(item['title'], width=44, max_lines=2, placeholder='…')
    texts = '\n'.join(f'<text x="18" y="{80 + i * 20}" font-size="14" font-weight="500" fill="#edf2fa">{escape(line)}</text>' for i, line in enumerate(lines))
    merged = item['pull_request']['merged_at'][:10]
    affiliation = escape(foundation(item) or 'Open source')
    owner = repo.split('/')[0].lower()
    accent, label = {
        'kubernetes-sigs': ('#7db4ff', 'KUBERNETES'),
        'kubernetes': ('#7db4ff', 'KUBERNETES'),
        'open-telemetry': ('#fbbf24', 'OPENTELEMETRY'),
        'valkey-io': ('#5eead4', 'VALKEY'),
    }.get(owner, ('#c4b5fd', 'OPEN SOURCE'))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="182" viewBox="0 0 400 182" role="img">
<title>{escape(repo)} #{item['number']} — {title}</title>
<style>text {{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}}</style>
<defs>
<linearGradient id="card-bg" x2="1" y2="1"><stop stop-color="#172236"/><stop offset="1" stop-color="#0c1320"/></linearGradient>
<radialGradient id="glow" cx="1" cy="0" r="1"><stop stop-color="{accent}" stop-opacity=".09"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
</defs>
<rect x=".5" y=".5" width="399" height="175" rx="14" fill="url(#card-bg)" stroke="#2b3a50"/>
<rect x="1" y="1" width="398" height="174" rx="14" fill="url(#glow)"/>
<path d="M18 1H382" stroke="{accent}" stroke-opacity=".8"/>
<circle cx="21" cy="25" r="3" fill="{accent}"/>
<text x="32" y="29" font-size="10" font-weight="700" letter-spacing="1.2" fill="{accent}">{label}</text>
<rect x="311" y="14" width="72" height="22" rx="11" fill="{accent}" fill-opacity=".09" stroke="{accent}" stroke-opacity=".25"/>
<text x="347" y="28.5" text-anchor="middle" font-size="9" font-weight="600" fill="{accent}">MERGED</text>
<text x="18" y="51" font-size="10" fill="#8fa1b8">{escape(textwrap.shorten(repo, width=53, placeholder='…'))}</text>
{texts}
<text x="18" y="125" font-size="10" fill="{accent}">{affiliation}</text>
<path d="M18 141H382" stroke="#29374b"/>
<text x="18" y="162" font-size="11" font-weight="600" fill="#b9c8df">#{item['number']}</text>
<text x="382" y="162" text-anchor="end" font-size="10" fill="#8fa1b8">{merged}  ↗</text>
</svg>
'''


def render(merged, opened, username, today):
    merged = sorted(merged, key=lambda x: (x['pull_request']['merged_at'], x['html_url']), reverse=True)
    opened = sorted(opened, key=lambda x: (x['updated_at'], x['html_url']), reverse=True)
    projects = len({repository(item) for item in merged})
    featured = [item for item in merged if foundation(item)]
    others = [item for item in merged if not foundation(item)]
    lines = [START, f'<p align="center"><img src="assets/generated/dashboard.svg" width="830" alt="{len(merged)} merged PRs · {projects} repositories · {len(opened)} open PRs · {len(featured)} Linux Foundation/CNCF merges"/></p>',
             f'<p align="center"><sub>Public contributions to other owners’ repositories · refreshed {today} · updates daily</sub></p>',
             '<h3 align="center">Linux Foundation &amp; CNCF contributions</h3>',
             f'<p align="center"><b>{len(featured)} merged PRs</b> across Kubernetes, OpenTelemetry and Valkey</p>',
             '<div align="center">']
    assets = {'assets/generated/dashboard.svg': dashboard(len(merged), projects, len(featured), len(opened))}
    selected = featured[:4] or merged[:4]
    for i, item in enumerate(selected, 1):
        path = f'assets/generated/merge-{i}.svg'
        assets[path] = card(item)
        lines.append(f'<a href="{escape(item["html_url"], quote=True)}"><img src="{path}" alt="{escape(repository(item) + " #" + str(item["number"]) + " — " + item["title"], quote=True)}" width="400"/></a>')
    lines.extend(['</div>', '', '<details>', '<summary><b>Explore all merged contributions ↗</b></summary>', '', '| Project | Merged contribution |', '| :--- | :--- |'])
    for item in merged:
        label = escape(item['title']).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', ' ')
        project = escape(repository(item))
        if foundation(item):
            project = f'**{project}**'
        lines.append(f'| {project} | [#{item["number"]} · {label}]({item["html_url"]}) |')
    lines.extend(['', '</details>', '', f'[View merged PRs on GitHub](https://github.com/search?q=is%3Apr+is%3Amerged+is%3Apublic+author%3A{username}+-user%3A{username}&type=pullrequests)', '',
                  '<details>', '<summary><b>Work in progress · recent open pull requests</b></summary>', '', '| Project | Contribution |', '| :--- | :--- |'])
    for item in opened[:10]:
        label = escape(item['title']).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', ' ')
        lines.append(f'| {escape(repository(item))} | [#{item["number"]} · {label}]({item["html_url"]}) |')
    if not opened:
        lines.append('| — | No open pull requests |')
    lines.extend(['', '</details>', END])
    return '\n'.join(lines), assets


def replace_section(readme, section):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError('Expected exactly one contribution marker pair')
    before, rest = readme.split(START)
    _, after = rest.split(END)
    return before + section + after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', default='adityamukesh')
    args = parser.parse_args()
    merged = search(args.username, 'merged')
    opened = search(args.username, 'open')
    section, assets = render(merged, opened, args.username, datetime.now(timezone.utc).date().isoformat())
    readme = ROOT / 'README.md'
    updated = replace_section(readme.read_text(), section)
    for path, svg in assets.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg)
    for old in (ROOT / 'assets/generated').glob('merge-*.svg'):
        if old.relative_to(ROOT).as_posix() not in assets:
            old.unlink()
    readme.write_text(updated)


if __name__ == '__main__':
    main()
