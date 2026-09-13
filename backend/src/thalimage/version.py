"""Build version reporting.

The package version comes from installed metadata; the commit comes from
git when the source tree is a checkout. A container built without .git
has neither, so the commit can be baked in as THALIMAGE_COMMIT instead.
"""

import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


@dataclass(frozen=True)
class VersionInfo:
    version: str
    commit: Optional[str]


def describe_commit(repo_root: Path) -> Optional[str]:
    """Describe the checked-out commit, or None if this is not a checkout.

    Returns the nearest tag where one exists (`v1.2.3`, or `v1.2.3-4-gabc1234`
    once commits have landed on top), otherwise the short hash. A modified
    working tree is marked `-dirty`.
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


@lru_cache
def version_info() -> VersionInfo:
    """Version and commit for this build. Resolved once per process."""
    try:
        version = package_version("thalimage")
    except PackageNotFoundError:
        version = "0.0.0"

    commit = os.environ.get("THALIMAGE_COMMIT") or describe_commit(REPO_ROOT)
    return VersionInfo(version=version, commit=commit)
