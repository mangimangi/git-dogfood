"""Tests for install.sh — the git-dogfood installation script."""

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
INSTALL_SH = str(ROOT / "install.sh")


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_mock_bin(bin_dir: Path, name: str, script: str) -> Path:
    """Create a mock executable in bin_dir."""
    path = bin_dir / name
    path.write_text(f"#!/bin/bash\n{script}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def _run_install(work_dir: Path, version: str = "1.0.0", repo: str = "o/gd",
                 env_extra: dict = None, mock_bin: Path = None) -> subprocess.CompletedProcess:
    """Run install.sh in work_dir with mock commands on PATH."""
    env = {
        "PATH": f"{mock_bin}:{os.environ['PATH']}" if mock_bin else os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/root"),
    }
    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        ["bash", INSTALL_SH, version, repo],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env=env,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def work_dir(tmp_path):
    """A clean working directory simulating a consumer repo."""
    return tmp_path


@pytest.fixture
def mock_bin(tmp_path):
    """Directory for mock executables."""
    d = tmp_path / "mock_bin"
    d.mkdir()
    return d


@pytest.fixture
def mock_curl(mock_bin):
    """A mock curl that writes dummy content to the -o destination."""
    _make_mock_bin(mock_bin, "curl", """\
# Parse -o flag to find output destination
dest=""
while [ $# -gt 0 ]; do
    case "$1" in
        -o) dest="$2"; shift 2 ;;
        *) shift ;;
    esac
done
if [ -n "$dest" ]; then
    echo "#!/usr/bin/env python3" > "$dest"
    echo "# mock resolve script" >> "$dest"
fi
""")
    return mock_bin


# ── Tests: Directory creation ──────────────────────────────────────────────

class TestDirectoryCreation:
    def test_creates_dogfood_dir(self, work_dir, mock_curl):
        _run_install(work_dir, mock_bin=mock_curl)
        assert (work_dir / ".dogfood").is_dir()

    def test_creates_github_workflows_dir(self, work_dir, mock_curl):
        _run_install(work_dir, mock_bin=mock_curl)
        assert (work_dir / ".github" / "workflows").is_dir()


# ── Tests: Version file ───────────────────────────────────────────────────

class TestVersionFile:
    def test_version_file_written(self, work_dir, mock_curl):
        _run_install(work_dir, version="2.3.4", mock_bin=mock_curl)
        version_file = work_dir / ".dogfood" / ".version"
        assert version_file.exists()
        assert version_file.read_text().strip() == "2.3.4"

    def test_version_file_overwritten_on_update(self, work_dir, mock_curl):
        _run_install(work_dir, version="1.0.0", mock_bin=mock_curl)
        _run_install(work_dir, version="2.0.0", mock_bin=mock_curl)
        assert (work_dir / ".dogfood" / ".version").read_text().strip() == "2.0.0"


# ── Tests: fetch_file fallback ─────────────────────────────────────────────

class TestFetchFileFallback:
    def test_uses_curl_when_no_gh_token(self, work_dir, mock_curl):
        """Without GH_TOKEN, install.sh should use curl."""
        result = _run_install(work_dir, mock_bin=mock_curl)
        assert result.returncode == 0
        # Resolve script should exist (written by mock curl)
        assert (work_dir / ".dogfood" / "resolve").exists()

    def test_uses_gh_api_when_gh_token_set(self, work_dir, mock_bin):
        """With GH_TOKEN set and gh on PATH, install.sh should use gh api."""
        # Track that gh was called
        _make_mock_bin(mock_bin, "gh", """\
echo "gh called with: $*" >> "$MOCK_LOG"
# Return base64-encoded dummy content for --jq '.content'
echo "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwo="
""")
        # Also need a mock base64 or let the real one decode
        # The gh output pipes to base64 -d, so we need valid base64
        mock_log = work_dir / "gh_calls.log"
        result = _run_install(
            work_dir,
            mock_bin=mock_bin,
            env_extra={"GH_TOKEN": "test-token", "MOCK_LOG": str(mock_log)},
        )
        assert result.returncode == 0
        assert mock_log.exists(), f"gh was not called. stderr: {result.stderr}"


# ── Tests: Workflow template install ───────────────────────────────────────

class TestWorkflowInstall:
    def test_installs_workflow_on_first_run(self, work_dir, mock_curl):
        _run_install(work_dir, mock_bin=mock_curl)
        wf = work_dir / ".github" / "workflows" / "dogfood.yml"
        assert wf.exists()

    def test_skips_workflow_if_exists(self, work_dir, mock_curl):
        # Pre-create the workflow
        (work_dir / ".github" / "workflows").mkdir(parents=True)
        wf = work_dir / ".github" / "workflows" / "dogfood.yml"
        wf.write_text("# existing workflow\n")

        result = _run_install(work_dir, mock_bin=mock_curl)
        assert result.returncode == 0
        # Should not overwrite
        assert wf.read_text() == "# existing workflow\n"
        assert "already exists, skipping" in result.stdout


# ── Tests: Vendor config registration ─────────────────────────────────────

class TestVendorRegistration:
    def test_registers_in_vendor_config(self, work_dir, mock_curl):
        # Create prerequisite .vendored/config.json
        (work_dir / ".vendored").mkdir()
        (work_dir / ".vendored" / "config.json").write_text(
            json.dumps({"vendors": {}}, indent=2) + "\n"
        )

        result = _run_install(work_dir, repo="mangimangi/git-dogfood", mock_bin=mock_curl)
        assert result.returncode == 0

        config = json.loads((work_dir / ".vendored" / "config.json").read_text())
        assert "git-dogfood" in config["vendors"]
        vendor = config["vendors"]["git-dogfood"]
        assert vendor["repo"] == "mangimangi/git-dogfood"
        assert vendor["install_branch"] == "chore/install-git-dogfood"
        assert ".dogfood/**" in vendor["protected"]

    def test_preserves_existing_vendors(self, work_dir, mock_curl):
        (work_dir / ".vendored").mkdir()
        (work_dir / ".vendored" / "config.json").write_text(
            json.dumps({
                "vendors": {"other-tool": {"repo": "o/ot"}}
            }, indent=2) + "\n"
        )

        _run_install(work_dir, mock_bin=mock_curl)

        config = json.loads((work_dir / ".vendored" / "config.json").read_text())
        assert "other-tool" in config["vendors"]
        assert "git-dogfood" in config["vendors"]

    def test_no_registration_without_config(self, work_dir, mock_curl):
        """If .vendored/config.json doesn't exist, skip registration."""
        result = _run_install(work_dir, mock_bin=mock_curl)
        assert result.returncode == 0
        assert not (work_dir / ".vendored" / "config.json").exists()


# ── Tests: Missing prerequisites ──────────────────────────────────────────

class TestPrerequisites:
    def test_fails_without_version_arg(self, work_dir):
        result = subprocess.run(
            ["bash", INSTALL_SH],
            cwd=work_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
