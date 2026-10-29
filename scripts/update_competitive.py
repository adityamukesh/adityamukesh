#!/usr/bin/env python3
"""Refresh scores from platform-owned endpoints without third-party credentials."""
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def request(url, payload=None):
    args = ['curl', '--fail', '--silent', '--show-error', '--retry', '2',
            '--max-time', '30', '--user-agent', 'Mozilla/5.0', url]
    if payload is not None:
        args += ['-H', 'Content-Type: application/json', '--data', json.dumps(payload)]
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def cf_api(path):
    data = json.loads(request('https://codeforces.com/api/' + path))
    if data['status'] != 'OK':
        raise ValueError('Codeforces API did not return OK')
    time.sleep(2)  # Respect the API request interval.
    return data['result']


def codeforces():
    user = cf_api('user.info?handles=adityamukesh111')[0]
    contests = cf_api('user.rating?handle=adityamukesh111')
    solved = set()
    offset = 1
    while True:
        submissions = cf_api(f'user.status?handle=adityamukesh111&from={offset}&count=1000')
        for submission in submissions:
            if submission.get('verdict') == 'OK':
                problem = submission['problem']
                solved.add((problem.get('contestId', problem.get('problemsetName')), problem['index']))
        if len(submissions) < 1000:
            break
        offset += 1000
    return str(user.get('rating', 'Unrated')), f"{user.get('maxRating', 0)} peak · {len(solved)} solved · {len(contests)} contests"


def leetcode():
    query = 'query { matchedUser(username: "aditya_mukesh123") { submitStatsGlobal { acSubmissionNum { difficulty count } } } }'
    data = json.loads(request('https://leetcode.com/graphql/', {'query': query}))
    if data.get('errors'):
        raise ValueError('LeetCode returned GraphQL errors')
    counts = {row['difficulty']: row['count'] for row in data['data']['matchedUser']['submitStatsGlobal']['acSubmissionNum']}
    if any(not isinstance(counts[key], int) or counts[key] < 0 for key in ['All', 'Easy', 'Medium', 'Hard']):
        raise ValueError('Invalid LeetCode counts')
    return str(counts['All']), f"{counts['Easy']} Easy · {counts['Medium']} Medium · {counts['Hard']} Hard"


def parse_codechef(page):
    patterns = [r'class="rating-number">\s*(\d+)\s*</div>', r'Highest Rating\s+(\d+)',
                r'Total Problems Solved:\s*(\d+)', r'No\. of Contests Participated:\s*<b>(\d+)</b>']
    matches = [re.search(pattern, page) for pattern in patterns]
    if not all(matches):
        raise ValueError('CodeChef page format changed or profile is unavailable')
    rating, peak, solved, contests = [match.group(1) for match in matches]
    return rating, f'{peak} peak · {solved} solved · {contests} contests'


def render(stats, today):
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="830" height="140" viewBox="0 0 830 140" role="img">',
              '<title>Competitive programming statistics</title>',
              '<style>text {font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}</style>']
    for name, x, color in [('Codeforces', 0, '#58a6ff'), ('LeetCode', 286, '#ffa116'), ('CodeChef', 572, '#e3b341')]:
        data = stats.get(name, {})
        stamp = data.get('updated', 'never')
        status = f'Checked {stamp}' if stamp == today else f'Last verified {stamp} · refresh unavailable'
        pieces.extend([f'<g transform="translate({x}, 0)">',
                       '<rect x=".5" y=".5" width="257" height="138" rx="12" fill="#0d1117" stroke="#30363d"/>',
                       f'<text x="16" y="25" font-size="12" fill="{color}">{name.upper()}</text>',
                       f'<text x="16" y="69" font-size="32" font-weight="700" fill="#e6edf3">{escape(data.get("value", "Unavailable"))}</text>',
                       f'<text x="16" y="96" font-size="11" fill="#9da7b3">{escape(data.get("detail", "Source could not be reached"))}</text>',
                       f'<text x="16" y="122" font-size="9" fill="#9da7b3">{escape(status)}</text>', '</g>'])
    return '\n'.join(pieces + ['</svg>', ''])


def main():
    cache = ROOT / 'assets/generated/competitive.json'
    stats = json.loads(cache.read_text()) if cache.exists() else {}
    today = datetime.now(timezone.utc).date().isoformat()
    failed = []
    for name, fetch in [('Codeforces', codeforces), ('LeetCode', leetcode), ('CodeChef', lambda: parse_codechef(request('https://www.codechef.com/users/coder_baby12')))]:
        try:
            value, detail = fetch()
            stats[name] = {'value': value, 'detail': detail, 'updated': today}
            print(f'{name}: {value}; {detail}')
        except (subprocess.SubprocessError, ValueError, KeyError, TypeError, IndexError) as exc:
            failed.append(name)
            print(f'::warning::{name} refresh failed ({type(exc).__name__}); preserving last verified data')
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(stats, indent=2, sort_keys=True) + '\n')
    (ROOT / 'assets/competitive.svg').write_text(render(stats, today))
    return bool(failed)


if __name__ == '__main__':
    sys.exit(main())
