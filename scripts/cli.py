"""CLI helper for launching recruitment assistant services locally."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Locate the repository root for running uv-managed commands."""
    current = Path(__file__).resolve()
    git_root: Path | None = None
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
        if git_root is None and (parent / ".git").exists():
            git_root = parent
    if git_root is not None:
        return git_root
    return current.parents[1]


ROOT = find_repo_root()


def run_command(command: list[str]) -> int:
    """Execute the provided command within the repo root."""
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> None:
    """Parse CLI args and dispatch the requested workflow."""
    parser = argparse.ArgumentParser(
        description="Run recruitment-assistant workflows via uv-managed commands."
    )
    parser.add_argument(
        "target",
        choices=["api", "ui", "test"],
        help="Component to exercise (API server, UI, or test suite).",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override the default port for api (8000) or ui (8501).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Pass --reload to uvicorn when running the API server.",
    )
    parser.add_argument(
        "--extra",
        nargs=argparse.REMAINDER,
        help="Additional arguments appended to the invoked command.",
    )

    args = parser.parse_args()
    extra = args.extra or []

    if args.target == "api":
        port = args.port or 8000
        command = [
            "uv",
            "run",
            "uvicorn",
            "recruitment_assistant.api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ]
        if args.reload:
            command.append("--reload")
    elif args.target == "ui":
        port = args.port or 8501
        command = [
            "uv",
            "run",
            "python",
            "-m",
            "streamlit",
            "run",
            "recruitment_assistant/ui/app.py",
            "--server.port",
            str(port),
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ]
    else:  # args.target == "test"
        command = ["uv", "run", "pytest"]

    command.extend(extra)
    code = run_command(command)
    if code != 0:
        sys.exit(code)


if __name__ == "__main__":
    main()
