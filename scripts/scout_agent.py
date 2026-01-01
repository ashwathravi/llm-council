#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import re
from pathlib import Path

# Configuration
PASSPORTS_DIR = Path(".agent/passports")
KANBAN_FILE = Path(".agent/kanban.md")
TEMPLATE_FILE = Path(".agent/templates/feature_passport.md")

def get_git_remote_url():
    """Try to get the remote URL to deduce owner/repo."""
    try:
        # Simple parsing of .git/config or assuming passed as arg
        # For now, default to env or user arg, fallback to hardcoded for demo
        return os.environ.get("GITHUB_REPOSITORY", "") # e.g. "owner/repo"
    except Exception:
        return ""

def get_current_user(token):
    """Get the authenticated user's login."""
    # Try gh cli first for speed if available
    import shutil
    import subprocess
    if shutil.which("gh"):
        try:
            return subprocess.check_output(["gh", "api", "user", "-q", ".login"], text=True).strip()
        except:
            pass
    
    # Fallback to API
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ScoutAgent"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())['login']
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None

def fetch_assigned_issues(token, repo):
    """Fetch issues assigned to the authenticated user."""
    username = get_current_user(token)
    if not username:
        print("Could not determine current user. Cannot filter assigned issues.")
        return []
        
    print(f"Fetching issues assigned to: {username}")
    url = f"https://api.github.com/repos/{repo}/issues?state=open&assignee={username}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ScoutAgent"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"Error fetching issues: {e}")
        return []

def create_passport(issue):
    """Create a passport file from an issue."""
    issue_number = issue['number']
    safe_title = re.sub(r'[^a-z0-9]+', '_', issue['title'].lower()).strip('_')
    filename = f"GH-{issue_number}_{safe_title}.md"
    filepath = PASSPORTS_DIR / filename

    if filepath.exists():
        print(f"Passport already exists for #{issue_number}: {filename}")
        return None

    if not TEMPLATE_FILE.exists():
        print("Template file not found!")
        return None

    # Read template
    with open(TEMPLATE_FILE, "r") as f:
        content = f.read()

    # Fill template
    content = content.replace("[Enter Feature Name]", issue['title'])
    
    # Inject Issue URL into context (Naive string replacement for Section 1.1)
    context_injection = f"**Original Issue**: [{issue['html_url']}]({issue['html_url']})\n\n{issue['body']}"
    # Replace the placeholder or append to section 1.1
    # We look for "### 1.1 Idea & Context (User Input)"
    target_header = "### 1.1 Idea & Context (User Input)"
    if target_header in content:
        content = content.replace(target_header, f"{target_header}\n\n{context_injection}")

    # Write file
    with open(filepath, "w") as f:
        f.write(content)
    
    print(f"Created passport: {filepath}")
    return filepath

def update_kanban(passport_path, title):
    """Add the new passport to Kanban."""
    if not passport_path:
        return

    link = f"[{title}](passports/{passport_path.name})"
    entry = f"{link}" # Just the link

    if not KANBAN_FILE.exists():
        print("Kanban file not found!")
        return

    with open(KANBAN_FILE, "r") as f:
        lines = f.readlines()

    # Find "Planning" section
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if "## 🧠 Planning" in line or "## 🧠 Phase 1" in line: # Handle variations
            if not inserted:
                new_lines.append(f"\n{entry}\n")
                inserted = True
    
    if not inserted:
        # Fallback if header not found
        new_lines.append(f"\n{entry}\n")

    with open(KANBAN_FILE, "w") as f:
        f.writelines(new_lines)
    
    print(f"Updated Kanban with {title}")

def get_gh_cli_token():
    """Try to get token from gh CLI."""
    import shutil
    import subprocess
    
    if not shutil.which("gh"):
        return None
        
    try:
        # 'gh auth token' prints the token to stdout
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return None

def main():
    token = os.environ.get("GITHUB_TOKEN") or get_gh_cli_token()
    repo = os.environ.get("GITHUB_REPOSITORY") or get_git_remote_url()
    
    # Try to parse owner/repo from git config if not in env
    if not repo:
        try:
             # Very naive check for origin url
             import subprocess
             origin_url = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
             # Match git@github.com:owner/repo.git or https://github.com/owner/repo.git
             match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", origin_url)
             if match:
                 repo = f"{match.group(1)}/{match.group(2)}"
        except Exception:
            pass

    if not token or not repo:
        print("Usage: GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 scout_agent.py")
        print("Running in DEMO mode with mock data since credentials missing.")
        
        # DEMO MODE
        mock_issue = {
            "number": 999,
            "title": "Automated Scout Integration",
            "html_url": "https://github.com/example/repo/issues/999",
            "body": "As a user, I want the agent to automatically pick up issues so I don't have to copy-paste."
        }
        path = create_passport(mock_issue)
        update_kanban(path, mock_issue['title'])
        return

    print(f"Scout Agent 🦅 scanning {repo}...")
    issues = fetch_assigned_issues(token, repo)
    print(f"Found {len(issues)} assigned issues.")
    
    for issue in issues:
        path = create_passport(issue)
        if path:
            update_kanban(path, issue['title'])

if __name__ == "__main__":
    main()
