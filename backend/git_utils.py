"""Utility for cloning Git repositories into temporary directories."""

import re
import shutil
import subprocess
import tempfile

# Only allow HTTPS Git URLs (no SSH, file://, or other schemes)
_GIT_URL_PATTERN = re.compile(
    r"^https://[a-zA-Z0-9._\-]+(?:\.[a-zA-Z]{2,})+/[a-zA-Z0-9._\-/]+(?:\.git)?$"
)

# Clone depth limit — we only need the latest snapshot, not full history
_CLONE_DEPTH = 1

# Maximum repo size timeout (seconds)
_CLONE_TIMEOUT = 120


def is_git_url(value: str) -> bool:
    """Return True if the value looks like a valid HTTPS Git URL."""
    return bool(_GIT_URL_PATTERN.match(value))


def clone_repo(git_url: str) -> str:
    """Clone a Git repo to a temporary directory and return the path.

    Only HTTPS URLs are accepted. The caller is responsible for cleaning up
    the returned directory when done (use cleanup_clone).

    Raises:
        ValueError: If the URL is not a valid HTTPS Git URL.
        RuntimeError: If git clone fails.
    """
    if not is_git_url(git_url):
        raise ValueError(
            "Only HTTPS Git URLs are supported (e.g. https://github.com/user/repo)"
        )

    tmp_dir = tempfile.mkdtemp(prefix="opustest_clone_")
    try:
        subprocess.run(
            ["git", "clone", "--depth", str(_CLONE_DEPTH), "--", git_url, tmp_dir],
            check=True,
            capture_output=True,
            text=True,
            timeout=_CLONE_TIMEOUT,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError("git clone timed out — the repository may be too large")

    return tmp_dir


def cleanup_clone(path: str) -> None:
    """Remove a cloned repo directory."""
    shutil.rmtree(path, ignore_errors=True)
