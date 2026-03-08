#!/usr/bin/env python3
"""GitHub Sync for Video Analysis Library.

Syncs video analysis reports to a GitHub repo for persistent dashboard via GitHub Pages.
Uses GitHub REST API directly -- no git clone needed.
"""

import os
import sys
import json
import base64
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, ".sync_config.json")
QUEUE_PATH = os.path.join(SKILL_DIR, ".sync_queue.json")

GITHUB_API = "https://api.github.com"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [SYNC] {msg}")


# ─── Config Management ────────────────────────────────────────────────────────

def load_config():
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return None


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def is_configured():
    cfg = load_config()
    return cfg is not None and cfg.get("github_token") and cfg.get("repo_name")


# ─── GitHub API Client ────────────────────────────────────────────────────────

class GitHubAPI:
    def __init__(self, token, owner, repo):
        self.token = token
        self.owner = owner
        self.repo = repo

    def _request(self, method, path, data=None, retry=3):
        url = f"{GITHUB_API}{path}" if path.startswith("/") else path
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "video-learn-sync",
        }
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")

        for attempt in range(retry):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_body = resp.read().decode("utf-8")
                    if resp_body:
                        return json.loads(resp_body)
                    return {}
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code == 404:
                    return None
                if e.code == 409 and "empty" in err_body.lower():
                    return None
                if e.code == 422 and "already exists" in err_body.lower():
                    return {"already_exists": True}
                if e.code == 429 or e.code >= 500:
                    wait = (attempt + 1) * 5
                    log(f"  API {e.code}, retry in {wait}s...")
                    time.sleep(wait)
                    continue
                raise Exception(f"GitHub API {method} {path}: {e.code} {err_body[:200]}")
            except urllib.error.URLError as e:
                if attempt < retry - 1:
                    time.sleep(3)
                    continue
                raise Exception(f"Network error: {e}")
        raise Exception(f"GitHub API failed after {retry} retries")

    def get_user(self):
        return self._request("GET", "/user")

    def create_repo(self, name, description="", private=False):
        return self._request("POST", "/user/repos", {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": True,
        })

    def enable_pages(self):
        try:
            return self._request("POST", f"/repos/{self.owner}/{self.repo}/pages", {
                "source": {"branch": "main", "path": "/"}
            })
        except Exception as e:
            if "already" in str(e).lower():
                return {"already_exists": True}
            raise

    def get_pages_url(self):
        result = self._request("GET", f"/repos/{self.owner}/{self.repo}/pages")
        if result:
            return result.get("html_url", f"https://{self.owner}.github.io/{self.repo}/")
        return f"https://{self.owner}.github.io/{self.repo}/"

    def get_file(self, path):
        """Get file content and SHA. Returns None if not found."""
        return self._request("GET", f"/repos/{self.owner}/{self.repo}/contents/{path}")

    def put_file(self, path, content_bytes, message, sha=None):
        """Create or update a file."""
        data = {
            "message": message,
            "content": base64.b64encode(content_bytes).decode("ascii"),
        }
        if sha:
            data["sha"] = sha
        return self._request("PUT", f"/repos/{self.owner}/{self.repo}/contents/{path}", data)

    def upload_file(self, repo_path, local_content, message):
        """Upload file, handling create vs update."""
        existing = self.get_file(repo_path)
        sha = existing.get("sha") if existing else None
        if sha:
            # Check if content changed
            existing_content = base64.b64decode(existing.get("content", ""))
            if existing_content == local_content:
                return None  # Skip unchanged
        return self.put_file(repo_path, local_content, message, sha)

    def list_dir(self, path):
        """List directory contents. Returns list or None."""
        result = self._request("GET", f"/repos/{self.owner}/{self.repo}/contents/{path}")
        if isinstance(result, list):
            return result
        return None


# ─── Thumbnail Extraction ─────────────────────────────────────────────────────

def extract_thumbnail(meta_json_path, output_jpg_path):
    """Extract thumbnail from analysis.json _frames or meta.json base64 field."""
    report_dir = os.path.dirname(meta_json_path)
    thumb_b64 = ""

    # Prefer _frames from analysis.json (full-quality frame captures)
    analysis_path = os.path.join(report_dir, "analysis.json")
    if os.path.isfile(analysis_path):
        with open(analysis_path, "r") as f:
            analysis = json.load(f)
        frames = analysis.get("_frames", [])
        if frames:
            thumb_b64 = frames[0].get("base64", "")

    # Fallback to meta.json thumbnail (only if large enough to be valid)
    if not thumb_b64 or len(thumb_b64) < 1000:
        with open(meta_json_path, "r") as f:
            meta = json.load(f)
        meta_thumb = meta.get("thumbnail", "")
        if meta_thumb and len(meta_thumb) > 1000:
            thumb_b64 = meta_thumb

    if not thumb_b64 or len(thumb_b64) < 1000:
        return False

    # Decode and save
    try:
        img_data = base64.b64decode(thumb_b64)
        if len(img_data) < 500:  # Too small to be a valid image
            return False
        with open(output_jpg_path, "wb") as f:
            f.write(img_data)
        return True
    except Exception:
        return False


# ─── Platform Detection ───────────────────────────────────────────────────────

def detect_platform(analysis_data, meta_data, slug):
    """Detect the video platform from source URL or analysis data."""
    # Primary: check source_url
    source_url = (analysis_data.get("_meta", {}).get("source_url", "")
                  or meta_data.get("source_url", "")).lower()
    if source_url:
        if "bilibili" in source_url:
            return "Bilibili"
        if "youtube" in source_url or "youtu.be" in source_url:
            return "YouTube"
        if "xiaohongshu" in source_url or "xhslink" in source_url:
            return "Xiaohongshu"
        if "douyin" in source_url:
            return "Douyin"

    # Fallback: check analysis platform_fit (video-optimize style)
    algo = analysis_data.get("algorithm_fitness", {})
    fits = algo.get("platform_fit", [])
    for fit in fits:
        if fit.get("recommended"):
            p = fit.get("platform", "")
            if "YouTube" in p or "youtube" in p:
                return "YouTube"
            if "B站" in p or "bilibili" in p or "Bilibili" in p:
                return "Bilibili"
            if "抖音" in p:
                return "Douyin"
            if "小红书" in p:
                return "Xiaohongshu"

    return "Unknown"


def detect_source_url(analysis_data):
    """Try to detect original video URL from analysis data."""
    meta = analysis_data.get("_meta", {})
    return meta.get("source_url", "")


# ─── Video Embed Helpers ──────────────────────────────────────────────────────

def _extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _extract_bilibili_bvid(url):
    """Extract Bilibili BV ID from URL."""
    m = re.search(r'(BV[a-zA-Z0-9]{10})', url)
    return m.group(1) if m else None




# ─── Report-GH Generation ─────────────────────────────────────────────────────


def generate_report_gh(report_dir, source_url="", dashboard_url="../../../"):
    """Generate a GitHub-friendly report HTML from report-lite.html.
    The new dark theme report is already self-contained, just needs
    the back-nav link updated to point to the dashboard."""
    lite_path = os.path.join(report_dir, "report-lite.html")
    if not os.path.isfile(lite_path):
        return None

    with open(lite_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Update back-nav link to point to dashboard
    html = html.replace('href="../../../"', f'href="{dashboard_url}"')

    return html


# ─── Sync Functions ───────────────────────────────────────────────────────────

def sync_report(report_dir, config=None):
    """Sync a single report directory to GitHub."""
    if config is None:
        config = load_config()
    if not config:
        log("Not configured. Run: python3 github_sync.py setup")
        return False

    report_dir = str(report_dir)
    slug = os.path.basename(report_dir)

    meta_path = os.path.join(report_dir, "meta.json")
    analysis_path = os.path.join(report_dir, "analysis.json")

    if not os.path.isfile(meta_path):
        log(f"  Skipping {slug}: no meta.json")
        return False

    log(f"Syncing: {slug}")

    api = GitHubAPI(config["github_token"], config["repo_owner"], config["repo_name"])

    # 1. Upload meta.json
    with open(meta_path, "rb") as f:
        meta_bytes = f.read()
    meta_data = json.loads(meta_bytes)
    api.upload_file(f"data/videos/{slug}/meta.json", meta_bytes, f"Update meta: {slug}")
    log(f"  meta.json uploaded")

    # 2. Upload analysis.json (stripped of _frames, _video_path, _video_base64)
    if os.path.isfile(analysis_path):
        with open(analysis_path, "r") as f:
            analysis = json.load(f)

        # Strip large/local fields
        clean_analysis = {k: v for k, v in analysis.items()
                         if k not in ("_frames", "_video_path", "_video_base64")}
        clean_bytes = json.dumps(clean_analysis, ensure_ascii=False, indent=2).encode("utf-8")
        api.upload_file(f"data/videos/{slug}/analysis.json", clean_bytes, f"Update analysis: {slug}")
        log(f"  analysis.json uploaded ({len(clean_bytes)/1024:.0f}KB)")
    else:
        analysis = {}

    # 3. Upload thumbnail
    thumb_path = os.path.join(report_dir, "thumbnail.jpg")
    if not os.path.isfile(thumb_path):
        extract_thumbnail(meta_path, thumb_path)
    if os.path.isfile(thumb_path):
        with open(thumb_path, "rb") as f:
            thumb_bytes = f.read()
        api.upload_file(f"data/videos/{slug}/thumbnail.jpg", thumb_bytes, f"Update thumbnail: {slug}")
        log(f"  thumbnail.jpg uploaded ({len(thumb_bytes)/1024:.0f}KB)")

    # 4. Generate and upload report-gh.html
    source_url = detect_source_url(analysis)
    report_html = generate_report_gh(report_dir, source_url, "../../../")
    if report_html:
        report_bytes = report_html.encode("utf-8")
        api.upload_file(f"data/videos/{slug}/report.html", report_bytes, f"Update report: {slug}")
        log(f"  report.html uploaded ({len(report_bytes)/1024:.0f}KB)")

    log(f"  Done: {slug}")
    return True


def update_catalog(config=None):
    """Rebuild catalog.json from all video directories in the repo."""
    if config is None:
        config = load_config()
    if not config:
        return

    api = GitHubAPI(config["github_token"], config["repo_owner"], config["repo_name"])

    # List all video directories
    videos_list = api.list_dir("data/videos")
    if not videos_list:
        log("No videos found in repo")
        return

    catalog = {
        "last_updated": datetime.now().isoformat(),
        "total_videos": 0,
        "videos": []
    }

    for item in videos_list:
        if item.get("type") != "dir":
            continue
        slug = item["name"]

        # Get meta.json
        meta_file = api.get_file(f"data/videos/{slug}/meta.json")
        if not meta_file:
            continue

        try:
            meta = json.loads(base64.b64decode(meta_file["content"]))
        except Exception:
            continue

        # Get analysis.json for platform detection
        platform = "Unknown"
        source_url = ""
        analysis_file = api.get_file(f"data/videos/{slug}/analysis.json")
        if analysis_file:
            try:
                analysis = json.loads(base64.b64decode(analysis_file["content"]))
                platform = detect_platform(analysis, meta, slug)
                source_url = detect_source_url(analysis)
            except Exception:
                pass

        # Extract date from slug
        date_match = re.match(r"(\d{8})_", slug)
        date_str = ""
        if date_match:
            d = date_match.group(1)
            date_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

        video_entry = {
            "slug": slug,
            "title": meta.get("title", slug),
            "score": meta.get("overall_score", 0),
            "summary": meta.get("summary", ""),
            "duration": meta.get("duration", 0),
            "date": date_str or meta.get("analyzed_at", "")[:10],
            "platform": platform,
            "source_url": source_url,
            "thumbnail": f"data/videos/{slug}/thumbnail.jpg",
            "report": f"data/videos/{slug}/report.html",
            "type": meta.get("type", "optimize"),
        }

        # Learning-specific fields
        if meta.get("type") == "learning":
            video_entry["topic"] = meta.get("topic", "")
            video_entry["category"] = meta.get("category", "")
            video_entry["difficulty"] = meta.get("difficulty", "intermediate")
            video_entry["learning_rating"] = meta.get("learning_rating", 0)
            video_entry["score"] = meta.get("learning_rating", 0)  # Use learning_rating as score

        catalog["videos"].append(video_entry)

    # Sort by date descending
    catalog["videos"].sort(key=lambda v: v["date"], reverse=True)
    catalog["total_videos"] = len(catalog["videos"])

    # Upload catalog
    catalog_bytes = json.dumps(catalog, ensure_ascii=False, indent=2).encode("utf-8")
    api.upload_file("data/catalog.json", catalog_bytes, f"Update catalog: {catalog['total_videos']} videos")
    log(f"Catalog updated: {catalog['total_videos']} videos")
    return catalog


def sync_all_local(archive_dir="./outputs/reports", config=None):
    """Sync all local reports to GitHub."""
    if config is None:
        config = load_config()
    if not config:
        log("Not configured. Run: python3 github_sync.py setup")
        return

    archive_dir = os.path.abspath(archive_dir)
    if not os.path.isdir(archive_dir):
        log(f"Archive directory not found: {archive_dir}")
        return

    synced = 0
    for name in sorted(os.listdir(archive_dir)):
        report_dir = os.path.join(archive_dir, name)
        meta_path = os.path.join(report_dir, "meta.json")
        if os.path.isdir(report_dir) and os.path.isfile(meta_path):
            try:
                if sync_report(report_dir, config):
                    synced += 1
            except Exception as e:
                log(f"  Error syncing {name}: {e}")

    if synced > 0:
        update_catalog(config)

    log(f"Synced {synced} reports")


# ─── Queue Management ─────────────────────────────────────────────────────────

def load_queue():
    if os.path.isfile(QUEUE_PATH):
        with open(QUEUE_PATH, "r") as f:
            return json.load(f)
    return {"pending": []}


def save_queue(queue):
    with open(QUEUE_PATH, "w") as f:
        json.dump(queue, f, indent=2)


def enqueue(report_dir):
    queue = load_queue()
    report_dir = str(report_dir)
    if not any(p["report_dir"] == report_dir for p in queue["pending"]):
        queue["pending"].append({
            "report_dir": report_dir,
            "queued_at": datetime.now().isoformat(),
            "retry_count": 0,
        })
        save_queue(queue)
        log(f"Queued for later sync: {os.path.basename(report_dir)}")


def process_queue(config=None):
    queue = load_queue()
    if not queue["pending"]:
        return

    if config is None:
        config = load_config()
    if not config:
        return

    log(f"Processing queue: {len(queue['pending'])} pending")
    successful = []

    for item in queue["pending"]:
        try:
            sync_report(item["report_dir"], config)
            successful.append(item["report_dir"])
        except Exception as e:
            item["retry_count"] = item.get("retry_count", 0) + 1
            if item["retry_count"] > 5:
                log(f"  Giving up on: {item['report_dir']}")
                successful.append(item["report_dir"])
            else:
                log(f"  Retry {item['retry_count']}/5: {e}")

    queue["pending"] = [p for p in queue["pending"] if p["report_dir"] not in successful]
    save_queue(queue)

    if successful:
        update_catalog(config)


# ─── Auto-sync Entry Point ────────────────────────────────────────────────────

def auto_sync(report_dir):
    """Called automatically after video analysis pipeline.
    Syncs the report and handles errors gracefully."""
    if not is_configured():
        return

    config = load_config()

    # Process any queued items first
    try:
        process_queue(config)
    except Exception:
        pass

    # Sync the new report
    try:
        sync_report(report_dir, config)
        update_catalog(config)
        pages_url = config.get("pages_url", "")
        if pages_url:
            log(f"Dashboard: {pages_url}")
    except Exception as e:
        log(f"Sync failed, queued for later: {e}")
        enqueue(report_dir)


# ─── Setup Wizard ─────────────────────────────────────────────────────────────

def setup(token=None, repo_name="Learningallthetime"):
    """First-time setup: configure token, create repo, enable Pages, push frontend."""
    log("=== GitHub Sync Setup ===")

    # 1. Token
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        log("ERROR: No GitHub token provided.")
        log("Pass token as argument or set GITHUB_TOKEN env var")
        return None

    # 2. Validate token and get user info
    api = GitHubAPI(token, "", "")
    user = api._request("GET", "/user")
    if not user:
        log("ERROR: Invalid token")
        return None

    owner = user["login"]
    log(f"Authenticated as: {owner}")

    # 3. Create or find repo
    api.owner = owner
    api.repo = repo_name

    # Check if repo exists
    existing = api._request("GET", f"/repos/{owner}/{repo_name}")
    if existing and not existing.get("message"):
        log(f"Repo already exists: {owner}/{repo_name}")
    else:
        log(f"Creating repo: {owner}/{repo_name}")
        result = api.create_repo(repo_name, "Video Analysis Learning Library - Auto-updated dashboard")
        if result:
            log(f"Repo created: {owner}/{repo_name}")
            time.sleep(2)  # Wait for GitHub to initialize

    # 4. Push frontend files
    log("Pushing frontend files...")
    from gh_frontend import generate_dashboard_html, generate_readme

    dashboard = generate_dashboard_html()
    api.upload_file("index.html", dashboard.encode("utf-8"), "Initial dashboard")

    readme = generate_readme(owner, repo_name)
    api.upload_file("README.md", readme.encode("utf-8"), "Initial README")

    # Empty catalog
    empty_catalog = json.dumps({
        "last_updated": datetime.now().isoformat(),
        "total_videos": 0,
        "videos": []
    }, indent=2)
    api.upload_file("data/catalog.json", empty_catalog.encode("utf-8"), "Initial empty catalog")

    # 5. Enable GitHub Pages
    log("Enabling GitHub Pages...")
    api.enable_pages()
    time.sleep(2)
    pages_url = api.get_pages_url()
    log(f"Pages URL: {pages_url}")

    # 6. Save config
    config = {
        "github_token": token,
        "repo_owner": owner,
        "repo_name": repo_name,
        "pages_url": pages_url,
        "auto_sync": True,
        "setup_at": datetime.now().isoformat(),
    }
    save_config(config)
    log(f"Config saved to: {CONFIG_PATH}")

    log("=== Setup Complete ===")
    log(f"Dashboard will be at: {pages_url}")
    log("Run 'python3 github_sync.py sync-all' to sync existing reports")

    return config


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Sync for Video Analysis Library")
    subparsers = parser.add_subparsers(dest="command")

    p_setup = subparsers.add_parser("setup", help="First-time setup wizard")
    p_setup.add_argument("--token", default=None, help="GitHub personal access token")
    p_setup.add_argument("--repo", default="Learningallthetime", help="Repository name")

    p_sync = subparsers.add_parser("sync", help="Sync a single report")
    p_sync.add_argument("report_dir", help="Path to report directory")

    p_all = subparsers.add_parser("sync-all", help="Sync all local reports")
    p_all.add_argument("--archive-dir", default="./outputs/reports", help="Local archive directory")

    p_catalog = subparsers.add_parser("update-catalog", help="Rebuild catalog from repo")

    p_queue = subparsers.add_parser("process-queue", help="Process queued sync items")

    args = parser.parse_args()

    if args.command == "setup":
        setup(token=args.token, repo_name=args.repo)
    elif args.command == "sync":
        sync_report(args.report_dir)
        update_catalog()
    elif args.command == "sync-all":
        sync_all_local(args.archive_dir)
    elif args.command == "update-catalog":
        update_catalog()
    elif args.command == "process-queue":
        process_queue()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
