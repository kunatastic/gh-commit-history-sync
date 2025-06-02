import os
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from tqdm import tqdm

# === CONFIGURATION ===
GITHUB_USERNAME = "kunatastic"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
EMAIL_ID = os.environ.get("EMAILID")

if not GITHUB_TOKEN or not EMAIL_ID:
    raise EnvironmentError("GITHUB_TOKEN and EMAILID must be set in environment variables.")

BASE_URL = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# === HELPERS ===
def get_all_repos():
    repos = []
    page = 1
    while True:
        url = f"{BASE_URL}/user/repos"
        params = {
            "per_page": 100,
            "page": page,
            "affiliation": "owner,collaborator,organization_member"
        }
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1

    return repos

def get_commits(repo_full_name, since_date):
    owner, repo = repo_full_name.split("/")
    commits = []
    page = 1
    while True:
        url = f"{BASE_URL}/repos/{owner}/{requests.utils.quote(repo, safe='')}/commits"
        params = {
            "author": GITHUB_USERNAME,
            "since": since_date.isoformat(),
            "per_page": 100,
            "page": page
        }
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code != 200:
            break
        page_commits = r.json()
        if not page_commits:
            break
        commits.extend(page_commits)
        page += 1
    return commits

def save_commits_to_mdx(commits_by_repo):
    output_dir = "./data"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".mdx")
    lines = [f"# GitHub Commits - {datetime.now(timezone.utc).date()}\n"]

    # Sort repos by latest commit date (desc)
    sorted_repos = sorted(
        commits_by_repo.items(),
        key=lambda item: max(c['commit']['author']['date'] for c in item[1]),
        reverse=True
    )

    for (full_name, is_private), commits in sorted_repos:
        visibility = "private" if is_private else "public"
        lines.append(f"\n## {full_name} ({visibility})\n")

        for commit in sorted(commits, key=lambda c: c['commit']['author']['date'], reverse=True):
            raw_date = commit['commit']['author']['date']
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            formatted = dt.strftime("%Y-%m-%d %H:%M")
            msg = commit['commit']['message'].strip().replace("\n", " ")
            url = commit['html_url']
            lines.append(f"- `{formatted}` [{msg}]({url})")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Commit log saved to {filename}")

# === MAIN ===
def main():
    since = datetime.now(timezone.utc) - timedelta(days=7)
    repos = get_all_repos()
    commits_by_repo = defaultdict(list)

    total = len(repos)
    for i, repo in enumerate(tqdm(repos, desc="Fetching commits", unit="repo"), start=1):
        full_name = repo["full_name"]
        print(f"[{i}/{total}] Fetching commits from {full_name}")

        commits = get_commits(full_name, since)
        if commits:
            commits_by_repo[(repo["full_name"], repo["private"])].extend(commits)

    save_commits_to_mdx(commits_by_repo)

if __name__ == "__main__":
    main()
