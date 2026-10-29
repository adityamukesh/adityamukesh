# Profile refresh

`Refresh profile statistics` runs daily at 02:23 UTC (07:53 India time), on generator changes, or from the Actions **Run workflow** button. GitHub schedules are best effort, so the run may start later. No personal access token or external service subscription is required: GitHub searches use the repository's built-in `GITHUB_TOKEN`.

The workflow updates:

- All-time merged/open public PR counts in repositories owned by others; the latest merged cards and recent open PR links.
- A prominent Linux Foundation/CNCF section for verified project owners in `FOUNDATIONS` in `scripts/update_profile.py`. New merges in those organizations are included automatically. Add other organizations only after checking their official affiliation. This does not imply LFX mentorship participation or personal organization membership.
- Codeforces rating, maximum rating, unique accepted problems and rated contests through its API.
- LeetCode accepted-problem counts through its public GraphQL endpoint.
- CodeChef's displayed profile rating, maximum rating, solved count and contest count. Its displayed current rating may lag its contest-history graph while a new rating is being finalized.

Source affiliations: [Kubernetes](https://www.cncf.io/projects/kubernetes/), [OpenTelemetry](https://www.cncf.io/projects/opentelemetry/), [Valkey](https://valkey.io/).

Competitive sources refresh independently. If one is unavailable or changes its response format, its last verified values and date remain visible and the workflow reports a failure after publishing the successful updates. No missing data is replaced with zero. Incomplete GitHub search results stop publication. GitHub's 1,000-result search cap is guarded rather than silently truncating totals; beyond that, the query needs date partitions.

The existing 3D graph has its own daily workflow; both writers share a concurrency group. GitHub also caches README images, so a successful refresh may take time to become visible.

GitHub may disable scheduled workflows in public repositories after 60 days without repository activity. If a workflow becomes disabled, enable it again in Actions. You do not need to edit the profile each day.

Local validation (Python 3.11+, GitHub CLI and curl):

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_profile.py
python3 scripts/update_competitive.py
```

Edit prose outside the `CONTRIBUTIONS` markers normally. The marked section, `assets/generated/`, and `assets/competitive.svg` are generated. Personal goals, project descriptions and skills remain manually maintained.

## Contribution calendar and visual design

The hourly `Refresh contribution calendar` workflow replaces third-party stats/streak cards with a locally generated, timestamped card. It reads the public GitHub contribution-calendar page, including the heading's last-year total and daily counts. It fails without overwriting the card if GitHub changes the markup or returns incomplete data. Current streak allows a contribution-free current day; longest streak is explicitly limited to the displayed calendar window. Counts can still differ temporarily from a signed-in view or newly recorded activity because GitHub caches its responses. This is a snapshot, not a real-time counter or an all-time contribution total.

The 3D graph remains daily, but its separate total is removed after generation to avoid competing definitions/snapshots. The graph already includes a language chart. External statistics and streak images were removed to eliminate broken images and independent caches. The introduction emphasizes verified merged work; project affiliation labels do not claim personal membership.

The custom card links to GitHub’s native contribution total instead of duplicating it. This avoids displaying a stale numeric total beside GitHub’s newer count. Only the explicitly timestamped streak values are shown in the custom card.
