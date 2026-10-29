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


def card(item):
    title = escape(item['title'])
    repo = repository(item)
    lines = textwrap.wrap(item['title'], width=44, max_lines=2, placeholder='…')
    texts = '\n'.join(f'<text x="16" y="{57 + i * 20}" font-size="14" fill="#e6edf3">{escape(line)}</text>' for i, line in enumerate(lines))
    merged = item['pull_request']['merged_at'][:10]
    affiliation = escape(foundation(item) or 'Open source')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="144" viewBox="0 0 400 144" role="img">
<title>{escape(repo)} #{item['number']} — {title}</title>
<style>text {{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}}</style>
<defs><linearGradient id="card-bg" x2="1" y2="1"><stop stop-color="#172236"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>
<rect x=".5" y=".5" width="399" height="143" rx="12" fill="url(#card-bg)" stroke="#30363d"/>
<path d="M16 1H384" stroke="#a371f7" stroke-opacity=".65"/>
<text x="16" y="25" font-size="11" fill="#a371f7">{escape(textwrap.shorten(repo, width=43, placeholder='…'))}</text>
{texts}
<text x="16" y="96" font-size="10" fill="#58a6ff">{affiliation}</text>
<path d="M16 111H384" stroke="#30363d"/>
<text x="16" y="130" font-size="11" fill="#d2a8ff">MERGED · #{item['number']}</text>
<text x="384" y="130" text-anchor="end" font-size="11" fill="#9da7b3">{merged}</text>
</svg>
'''


def render(merged, opened, username, today):
    merged = sorted(merged, key=lambda x: (x['pull_request']['merged_at'], x['html_url']), reverse=True)
    opened = sorted(opened, key=lambda x: (x['updated_at'], x['html_url']), reverse=True)
    projects = len({repository(item) for item in merged})
    featured = [item for item in merged if foundation(item)]
    others = [item for item in merged if not foundation(item)]
    lines = [START, f'<p align="center"><b>{len(merged)} merged PRs</b> · {projects} repositories · {len(opened)} open PRs</p>',
             f'<p align="center"><sub>Public contributions to other owners’ repositories · refreshed {today} · updates daily</sub></p>',
             '<h3 align="center">Linux Foundation &amp; CNCF contributions</h3>',
             f'<p align="center"><b>{len(featured)} merged PRs</b> across Kubernetes, OpenTelemetry and Valkey</p>',
             '<div align="center">']
    assets = {}
    selected = featured[:8] + others[:6]
    for i, item in enumerate(selected, 1):
        if i == len(featured[:8]) + 1:
            lines.extend(['</div>', '<h3 align="center">More open-source contributions</h3>', '<div align="center">'])
        path = f'assets/generated/merge-{i}.svg'
        assets[path] = card(item)
        lines.append(f'<a href="{escape(item["html_url"], quote=True)}"><img src="{path}" alt="{escape(repository(item) + " #" + str(item["number"]) + " — " + item["title"], quote=True)}" width="400"/></a>')
    lines.extend(['</div>', '', f'[View all merged pull requests](https://github.com/search?q=is%3Apr+is%3Amerged+is%3Apublic+author%3A{username}+-user%3A{username}&type=pullrequests)', '',
                  '<details>', '<summary><b>Recent open pull requests</b></summary>', '', '| Project | Contribution |', '| :--- | :--- |'])
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
