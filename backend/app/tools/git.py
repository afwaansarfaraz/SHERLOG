"""Git History and Configuration Diff Investigation Tool.

Provides typed, read-only inspection of git repository state:
- Commit logs filtered by count, path, and timeframe
- Unified diffs between commits or working tree
- File content inspection at specific Git revisions

Security & Safety Guarantees:
- Strictly executes via `shell=False` with parameterized argument arrays
- Enforces strict path sanitization (prohibits traversal '..' and absolute paths)
- Applies execution timeouts and bounds on output size
- Treats all retrieved git text as untrusted evidence
"""

import logging
from pathlib import Path
import subprocess
import time
from typing import List, Optional

from backend.app.config import settings
from backend.app.tools.schemas import (
    EvidenceStatus,
    GitCommitSummary,
    GitDiffInput,
    GitDiffResult,
    GitLogInput,
    GitLogResult,
    GitShowInput,
    GitShowResult,
)

logger = logging.getLogger(__name__)


class GitTool:
    """Read-only tool inspecting repository commit history and configuration diffs."""

    def __init__(
        self,
        repo_path: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.repo_path = Path(repo_path or settings.GIT_REPO_PATH).resolve()
        self.timeout = timeout_seconds or settings.OBSERVABILITY_TIMEOUT_SECONDS

    def _run_git_cmd(
        self,
        args: List[str],
        timeout: Optional[float] = None,
    ) -> subprocess.CompletedProcess:
        """Execute a git command with shell=False and strict execution bounds."""
        effective_timeout = timeout or self.timeout
        cmd = ["git"] + args
        return subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,  # strictly prevent shell injection
            timeout=effective_timeout,
            check=False,
        )

    def get_commits(self, log_in: GitLogInput) -> GitLogResult:
        """Retrieve recent Git commit history with author, date, and changed files.

        Args:
            log_in: Validated input specifying commit count, path, and revision filters.

        Returns:
            GitLogResult containing list of commit summaries.
        """
        start_time = time.perf_counter()

        # Format: %H (hash)|%h (short)|%an (author)|%ae (email)|%aI (ISO date)|%s (subject)
        format_spec = "%H|%h|%an|%ae|%aI|%s"
        cmd_args = [
            "log",
            f"-n{log_in.max_count}",
            f"--pretty=format:{format_spec}",
            "--name-only",
        ]
        if log_in.since:
            cmd_args.append(f"--since={log_in.since}")
        if log_in.revision:
            cmd_args.append(log_in.revision)
        if log_in.path:
            cmd_args.extend(["--", log_in.path])

        try:
            res = self._run_git_cmd(cmd_args)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if res.returncode != 0:
                logger.warning("git log failed with code %d: %s", res.returncode, res.stderr)
                return GitLogResult(
                    status=EvidenceStatus.ERROR,
                    error_type="GitCommandError",
                    error_message=f"git log failed: {res.stderr.strip() or 'non-zero exit code'}",
                    execution_time_ms=elapsed_ms,
                )

            output = res.stdout.strip()
            if not output:
                return GitLogResult(
                    status=EvidenceStatus.EMPTY,
                    commits=[],
                    total_commits=0,
                    execution_time_ms=elapsed_ms,
                )

            # Parse log entries with changed files
            commits: List[GitCommitSummary] = []
            blocks = output.split("\n\n")

            for block in blocks:
                lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
                if not lines:
                    continue

                header = lines[0]
                parts = header.split("|")
                if len(parts) < 6:
                    continue

                commit_hash, short_hash, author, email, date_str, subject = parts[:6]
                changed_files = lines[1:] if len(lines) > 1 else []

                commits.append(
                    GitCommitSummary(
                        commit_hash=commit_hash,
                        short_hash=short_hash,
                        author_name=author,
                        author_email=email,
                        authored_date=date_str,
                        subject=subject,
                        files_changed=changed_files,
                    )
                )

            status = EvidenceStatus.EMPTY if not commits else EvidenceStatus.SUCCESS

            return GitLogResult(
                status=status,
                commits=commits,
                total_commits=len(commits),
                execution_time_ms=elapsed_ms,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitLogResult(
                status=EvidenceStatus.TIMEOUT,
                error_type="TimeoutError",
                error_message=f"git log command timed out after {self.timeout}s",
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitLogResult(
                status=EvidenceStatus.ERROR,
                error_type="UnexpectedError",
                error_message=f"Unexpected error executing git log: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

    def get_diff(self, diff_in: GitDiffInput) -> GitDiffResult:
        """Inspect unified diff between two revisions or working directory.

        Args:
            diff_in: Validated input specifying revisions, file path, and line bounds.

        Returns:
            GitDiffResult containing the diff text.
        """
        start_time = time.perf_counter()
        cmd_args = ["diff"]

        if diff_in.commit_a and diff_in.commit_b:
            cmd_args.append(f"{diff_in.commit_a}..{diff_in.commit_b}")
        elif diff_in.commit_a:
            cmd_args.append(diff_in.commit_a)

        if diff_in.path:
            cmd_args.extend(["--", diff_in.path])

        try:
            res = self._run_git_cmd(cmd_args)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if res.returncode != 0:
                logger.warning("git diff failed with code %d: %s", res.returncode, res.stderr)
                return GitDiffResult(
                    status=EvidenceStatus.ERROR,
                    error_type="GitCommandError",
                    error_message=f"git diff failed: {res.stderr.strip()}",
                    execution_time_ms=elapsed_ms,
                )

            raw_diff = res.stdout or ""
            if not raw_diff.strip():
                return GitDiffResult(
                    status=EvidenceStatus.EMPTY,
                    diff_content="",
                    lines_count=0,
                    execution_time_ms=elapsed_ms,
                )

            lines = raw_diff.splitlines()
            is_truncated = False
            if len(lines) > diff_in.max_lines:
                lines = lines[:diff_in.max_lines]
                lines.append(f"\n# [TRUNCATED - EXCEEDED MAXIMUM {diff_in.max_lines} LINES]")
                is_truncated = True

            diff_text = "\n".join(lines)

            return GitDiffResult(
                status=EvidenceStatus.SUCCESS,
                diff_content=diff_text,
                lines_count=len(lines),
                is_truncated=is_truncated,
                execution_time_ms=elapsed_ms,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitDiffResult(
                status=EvidenceStatus.TIMEOUT,
                error_type="TimeoutError",
                error_message=f"git diff timed out after {self.timeout}s",
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitDiffResult(
                status=EvidenceStatus.ERROR,
                error_type="UnexpectedError",
                error_message=f"Unexpected error running git diff: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )

    def show_file(self, show_in: GitShowInput) -> GitShowResult:
        """View file content at a specific Git commit or revision.

        Args:
            show_in: Validated input with revision and path.

        Returns:
            GitShowResult containing the file contents.
        """
        start_time = time.perf_counter()
        target_spec = f"{show_in.revision}:{show_in.path}"
        cmd_args = ["show", target_spec]

        try:
            res = self._run_git_cmd(cmd_args)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if res.returncode != 0:
                logger.warning("git show %s failed: %s", target_spec, res.stderr)
                return GitShowResult(
                    status=EvidenceStatus.ERROR,
                    error_type="GitFileNotFound",
                    error_message=f"Path '{show_in.path}' not found at revision '{show_in.revision}': {res.stderr.strip()}",
                    execution_time_ms=elapsed_ms,
                )

            content = res.stdout or ""
            if not content.strip():
                return GitShowResult(
                    status=EvidenceStatus.EMPTY,
                    content="",
                    lines_count=0,
                    execution_time_ms=elapsed_ms,
                )

            lines = content.splitlines()
            is_truncated = False
            if len(lines) > show_in.max_lines:
                lines = lines[:show_in.max_lines]
                lines.append(f"\n# [TRUNCATED - EXCEEDED MAXIMUM {show_in.max_lines} LINES]")
                is_truncated = True

            return GitShowResult(
                status=EvidenceStatus.SUCCESS,
                content="\n".join(lines),
                lines_count=len(lines),
                is_truncated=is_truncated,
                execution_time_ms=elapsed_ms,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitShowResult(
                status=EvidenceStatus.TIMEOUT,
                error_type="TimeoutError",
                error_message=f"git show timed out after {self.timeout}s",
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return GitShowResult(
                status=EvidenceStatus.ERROR,
                error_type="UnexpectedError",
                error_message=f"Unexpected error executing git show: {str(exc)}",
                execution_time_ms=elapsed_ms,
            )
