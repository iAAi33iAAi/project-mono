"""
COLONY COMMIT PIPELINE - GitHub API Commit System
PROJECT-MONO | ALGA_FOLD_KERNEL | Node 001
Gives Colony agents ability to commit code to GitHub.
Every commit passes through OpenClaw governance.
"""
import base64, hashlib, os, time, json, requests
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path

GITHUB_API = "https://api.github.com"
DEFAULT_REPO = os.getenv("GITHUB_REPO", "iAAi33iAAi/project-mono")
DEFAULT_BRANCH = os.getenv("GITHUB_BRANCH", "main")

CODEX_RULES = {
    "non_extraction": "No extraction without sovereign consent.",
    "human_sovereignty": "Human authority is irrevocable.",
    "lineage_required": "Every action carries provenance.",
}
EXTRACTION_SIGNALS = ["extract_user", "harvest_data", "scrape_private", "sell_data",
    "mine_behavior", "track_without_consent", "shadow_profile", "bypass_consent"]

class CommitStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"

@dataclass
class CommitRequest:
    file_path: str
    content: str
    message: str
    agent: str
    branch: str = DEFAULT_BRANCH
    request_id: str = ""
    status: CommitStatus = CommitStatus.PENDING
    timestamp: str = ""
    commit_sha: Optional[str] = None
    def __post_init__(self):
        if not self.request_id:
            self.request_id = hashlib.sha256(f"{self.file_path}|{self.agent}|{time.time()}".encode()).hexdigest()[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

@dataclass
class CommitResult:
    request_id: str
    status: CommitStatus
    file_path: str
    commit_sha: Optional[str] = None
    error: Optional[str] = None
    lineage: dict = field(default_factory=dict)

def openclaw_precommit_check(request):
    result = {"request_id": request.request_id, "agent": request.agent,
              "allowed": True, "blocked_by": None, "violations": []}
    content_lower = request.content.lower()
    for signal in EXTRACTION_SIGNALS:
        if signal in content_lower:
            result["allowed"] = False
            result["blocked_by"] = "non_extraction"
            result["violations"].append(f"Extraction signal: {signal}")
    if not request.agent or not request.agent.strip():
        result["allowed"] = False
        result["blocked_by"] = "lineage_required"
        result["violations"].append("Anonymous commits forbidden")
    if not request.content.strip():
        result["allowed"] = False
        result["blocked_by"] = "lineage_required"
        result["violations"].append("Empty content")
    return result

class ColonyCommitPipeline:
    def __init__(self, token=None, repo=DEFAULT_REPO, branch=DEFAULT_BRANCH):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.repo = repo
        self.branch = branch
        self.headers = {"Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github.v3+json"}
        self.commit_log = []
        self.pending_queue = []
        print(f"[COMMIT] Pipeline initialized for {self.repo}")

    def commit_file(self, file_path, content, message, agent="Builder"):
        request = CommitRequest(file_path=file_path, content=content,
                                message=message, agent=agent)
        print(f"[COMMIT] === commit_init === {file_path} by {agent}")
        governance = openclaw_precommit_check(request)
        if not governance["allowed"]:
            print(f"[OPENCLAW] BLOCKED: {governance['blocked_by']}")
            result = CommitResult(request.request_id, CommitStatus.BLOCKED,
                                 file_path, error=f"Blocked: {governance['blocked_by']}")
            self.commit_log.append(result)
            return result
        print("[OPENCLAW] APPROVED")
        if not self.token:
            print("[COMMIT] DRY RUN - no token")
            result = CommitResult(request.request_id, CommitStatus.PENDING,
                                 file_path, error="No token - dry run")
            self.commit_log.append(result)
            return result
        try:
            api_result = self._push_to_github(request)
            sha = api_result.get("sha", "")
            print(f"[COMMIT] SUCCESS - SHA: {sha[:8]}")
            result = CommitResult(request.request_id, CommitStatus.COMMITTED,
                                 file_path, commit_sha=sha)
            self.commit_log.append(result)
            return result
        except Exception as e:
            print(f"[COMMIT] FAILED: {e}")
            result = CommitResult(request.request_id, CommitStatus.FAILED,
                                 file_path, error=str(e))
            self.commit_log.append(result)
            return result

    def commit_batch(self, files, message, agent="Colony Manager"):
        results = []
        for i, f in enumerate(files, 1):
            print(f"[BATCH] [{i}/{len(files)}] {f['path']}")
            results.append(self.commit_file(f["path"], f["content"],
                           f"{message} [{i}/{len(files)}]", agent))
        return results

    def queue_commit(self, file_path, content, message, agent="Builder"):
        req = CommitRequest(file_path=file_path, content=content,
                            message=message, agent=agent)
        self.pending_queue.append(req)
        print(f"[QUEUE] Queued: {file_path} - awaiting Architect approval")
        return req

    def approve_and_push_all(self):
        print(f"[QUEUE] Architect approved {len(self.pending_queue)} commits")
        results = [self.commit_file(r.file_path, r.content, r.message, r.agent)
                   for r in self.pending_queue]
        self.pending_queue.clear()
        return results

    def _push_to_github(self, request):
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{request.file_path}"
        resp = requests.get(url, headers=self.headers, params={"ref": request.branch})
        existing_sha = resp.json().get("sha") if resp.status_code == 200 else None
        payload = {"message": request.message,
                   "content": base64.b64encode(request.content.encode()).decode(),
                   "branch": request.branch,
                   "committer": {"name": f"Colony-{request.agent.replace(' ','-')}",
                                 "email": "colony@project-mono.sovereign"}}
        if existing_sha:
            payload["sha"] = existing_sha
        resp = requests.put(url, headers=self.headers, json=payload)
        if resp.status_code in (200, 201):
            return {"sha": resp.json().get("commit", {}).get("sha", "")}
        raise RuntimeError(f"GitHub API {resp.status_code}: {resp.text[:200]}")

    def status(self):
        return {"repo": self.repo, "branch": self.branch,
                "token_configured": bool(self.token),
                "committed": sum(1 for r in self.commit_log if r.status == CommitStatus.COMMITTED),
                "blocked": sum(1 for r in self.commit_log if r.status == CommitStatus.BLOCKED),
                "pending": len(self.pending_queue)}

def quick_commit(file_path, content, message, agent="Builder", token=None):
    return ColonyCommitPipeline(token=token).commit_file(file_path, content, message, agent)

if __name__ == "__main__":
    print("COLONY COMMIT PIPELINE | PROJECT-MONO | Node 001")
    p = ColonyCommitPipeline()
    p.commit_file("src/demo.py", 'print("sovereign")', "test commit", "Builder")
    p.commit_file("src/evil.py", "def extract_user_data(): pass", "bad commit", "Guardian")
    p.commit_file("src/anon.py", "# anon", "anon push", "")
    print(json.dumps(p.status(), indent=2))
