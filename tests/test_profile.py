import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_profile as profile
import update_competitive as competitive


def pr(number, date='2026-10-28T12:00:00Z'):
    return {'number': number, 'title': 'Fix <types> & A | B [test]',
            'html_url': f'https://github.com/org/repo/pull/{number}',
            'repository_url': 'https://api.github.com/repos/org/repo',
            'updated_at': date, 'pull_request': {'merged_at': date}}


class ProfileTests(unittest.TestCase):
    def test_counts_order_escape_and_preservation(self):
        section, assets = profile.render([pr(1, '2026-10-01'), pr(2)], [pr(3)], 'user', '2026-10-29')
        self.assertIn('2 merged PRs · 1 repositories · 1 open PRs', section)
        self.assertIn('#2', assets['assets/generated/merge-1.svg'])
        self.assertIn('&#124;', section)
        for svg in assets.values():
            ElementTree.fromstring(svg)
        original = 'intro\n' + profile.START + 'old' + profile.END + '\nfooter'
        self.assertEqual(profile.replace_section(original, section), 'intro\n' + section + '\nfooter')

    def test_foundation_highlights_only_verified_owners(self):
        known = pr(4)
        known['repository_url'] = 'https://api.github.com/repos/kubernetes-sigs/inference-perf'
        section, assets = profile.render([pr(5), known], [], 'user', '2026-10-29')
        self.assertIn('Kubernetes · CNCF', assets['assets/generated/merge-1.svg'])
        self.assertIn('1 merged PRs</b> across Kubernetes', section)
        self.assertIsNone(profile.foundation(pr(5)))
        self.assertIn('No open pull requests', section)

    def test_missing_markers_fail(self):
        with self.assertRaises(ValueError):
            profile.replace_section('manual profile', 'new')

    @patch('update_profile.subprocess.run')
    def test_pagination_and_incomplete_search(self, run):
        run.side_effect = [SimpleNamespace(stdout=json.dumps({'incomplete_results': False, 'total_count': 2, 'items': [pr(1)]})),
                           SimpleNamespace(stdout=json.dumps({'incomplete_results': False, 'total_count': 2, 'items': [pr(2)]}))]
        self.assertEqual(len(profile.search('user', 'merged')), 2)
        run.side_effect = None
        run.return_value = SimpleNamespace(stdout=json.dumps({'incomplete_results': True, 'total_count': 1, 'items': [pr(1)]}))
        with self.assertRaises(RuntimeError):
            profile.search('user', 'merged')

    def test_codechef_missing_and_valid_data(self):
        sample = '<div class="rating-number"> 1152 </div> Highest Rating 1182 Total Problems Solved: 34 No. of Contests Participated: <b>13</b>'
        self.assertEqual(competitive.parse_codechef(sample), ('1152', '1182 peak · 34 solved · 13 contests'))
        with self.assertRaises(ValueError):
            competitive.parse_codechef('<html>Access denied</html>')

    def test_stale_and_missing_scores_are_labelled(self):
        svg = competitive.render({'Codeforces': {'value': '808', 'detail': 'A & B', 'updated': '2026-10-28'}}, '2026-10-29')
        ElementTree.fromstring(svg)
        self.assertIn('Last verified 2026-10-28', svg)
        self.assertIn('refresh unavailable', svg)
        self.assertIn('Unavailable', svg)

    @patch('update_competitive.cf_api')
    def test_codeforces_counts_unique_accepted_problems(self, api):
        api.side_effect = [[{'rating': 808, 'maxRating': 892}], [1, 2],
                           [{'verdict': v, 'problem': {'contestId': c, 'index': 'A'}}
                            for v, c in [('OK', 1), ('OK', 1), ('WRONG_ANSWER', 2), ('OK', 3)]]]
        self.assertEqual(competitive.codeforces(), ('808', '892 peak · 2 solved · 2 contests'))


if __name__ == '__main__':
    unittest.main()
