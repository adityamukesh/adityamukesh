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

The existing 3D graph has its own daily workflow; both writers share a concurrency group. GitHub Stats, language and streak images are externally hosted and retain their providers' refresh/cache schedules. GitHub also caches README images, so a successful refresh may take time to become visible.

GitHub may disable scheduled workflows in public repositories after 60 days without repository activity. If a workflow becomes disabled, enable it again in Actions. You do not need to edit the profile each day.

Local validation (Python 3.11+, GitHub CLI and curl):

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_profile.py
python3 scripts/update_competitive.py
```

Edit prose outside the `CONTRIBUTIONS` markers normally. The marked section, `assets/generated/`, and `assets/competitive.svg` are generated. Personal goals, project descriptions and skills remain manually maintained.
