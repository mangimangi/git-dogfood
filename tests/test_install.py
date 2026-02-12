"""Tests for install.sh — the git-dogfood installation script."""

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
                 env_extra: dict = None, mock_bin: Path = None,
                 use_env_vars: bool = False, positional_args: list = None) -> subprocess.CompletedProcess:
    """Run install.sh in work_dir with mock commands on PATH.

    Args:
        use_env_vars: If True, pass version/repo via VENDOR_REF/VENDOR_REPO env vars
                      instead of positional args.
        positional_args: Override the positional args list entirely. If None,
                         defaults to [version, repo] (unless use_env_vars=True,
                         then no positional args).
    """
    env = {
        "PATH": f"{mock_bin}:{os.environ['PATH']}" if mock_bin else os.environ["PATH"],
        "HOME": os.environ.get("HOME", "/root"),
    }
    if env_extra:
        env.update(env_extra)

    if positional_args is not None:
        args = positional_args
    elif use_env_vars:
        env["VENDOR_REF"] = version
        env["VENDOR_REPO"] = repo
        args = []
    else:
        args = [version, repo]

    return subprocess.run(
        ["bash", INSTALL_SH] + args,
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

    def test_creates_custom_install_dir(self, work_dir, mock_curl):
        _run_install(work_dir, mock_bin=mock_curl,
                     env_extra={"VENDOR_INSTALL_DIR": ".vendored/pkg/git-dogfood"})
        assert (work_dir / ".vendored" / "pkg" / "git-dogfood").is_dir()


# ── Tests: V2 env var inputs ─────────────────────────────────────────────

class TestV2EnvVars:
    def test_accepts_vendor_ref_and_repo(self, work_dir, mock_curl):
        result = _run_install(work_dir, version="3.0.0", repo="acme/gd",
                              mock_bin=mock_curl, use_env_vars=True)
        assert result.returncode == 0
        assert "v3.0.0" in result.stdout

    def test_vendor_install_dir(self, work_dir, mock_curl):
        custom_dir = ".vendored/pkg/git-dogfood"
        result = _run_install(work_dir, mock_bin=mock_curl,
                              env_extra={"VENDOR_INSTALL_DIR": custom_dir})
        assert result.returncode == 0
        assert (work_dir / custom_dir / "resolve").exists()

    def test_install_dir_defaults_to_dogfood(self, work_dir, mock_curl):
        result = _run_install(work_dir, mock_bin=mock_curl)
        assert result.returncode == 0
        assert (work_dir / ".dogfood" / "resolve").exists()

    def test_env_vars_override_positional_args(self, work_dir, mock_curl):
        """VENDOR_REF/VENDOR_REPO take precedence over $1/$2."""
        result = _run_install(work_dir, mock_bin=mock_curl,
                              positional_args=["1.0.0", "old/repo"],
                              env_extra={"VENDOR_REF": "5.0.0",
                                         "VENDOR_REPO": "new/repo"})
        assert result.returncode == 0
        assert "v5.0.0" in result.stdout
        assert "new/repo" in result.stdout


# ── Tests: V1 artifacts removed ──────────────────────────────────────────

class TestV1ArtifactsRemoved:
    def test_no_version_file_written(self, work_dir, mock_curl):
        """V2 framework handles version tracking — install.sh must not write .version."""
        _run_install(work_dir, version="2.3.4", mock_bin=mock_curl)
        assert not (work_dir / ".dogfood" / ".version").exists()

    def test_vendor_config_not_modified(self, work_dir, mock_curl):
        """V2 framework handles registration — install.sh must not touch config.json."""
        import json
        (work_dir / ".vendored").mkdir()
        original = {"vendors": {"other-tool": {"repo": "o/ot"}}}
        (work_dir / ".vendored" / "config.json").write_text(
            json.dumps(original, indent=2) + "\n"
        )
        _run_install(work_dir, mock_bin=mock_curl)
        config = json.loads((work_dir / ".vendored" / "config.json").read_text())
        assert config == original


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


# ── Tests: Manifest emission ─────────────────────────────────────────────

class TestManifest:
    def test_manifest_written_when_env_set(self, work_dir, mock_curl):
        manifest = work_dir / "manifest.txt"
        result = _run_install(work_dir, mock_bin=mock_curl,
                              env_extra={"VENDOR_MANIFEST": str(manifest)})
        assert result.returncode == 0
        assert manifest.exists()
        lines = manifest.read_text().strip().splitlines()
        assert ".dogfood/resolve" in lines

    def test_manifest_includes_workflow_on_first_install(self, work_dir, mock_curl):
        manifest = work_dir / "manifest.txt"
        result = _run_install(work_dir, mock_bin=mock_curl,
                              env_extra={"VENDOR_MANIFEST": str(manifest)})
        assert result.returncode == 0
        lines = manifest.read_text().strip().splitlines()
        assert ".dogfood/resolve" in lines
        assert ".github/workflows/dogfood.yml" in lines

    def test_manifest_excludes_workflow_when_exists(self, work_dir, mock_curl):
        # Pre-create the workflow
        (work_dir / ".github" / "workflows").mkdir(parents=True)
        (work_dir / ".github" / "workflows" / "dogfood.yml").write_text("# existing\n")

        manifest = work_dir / "manifest.txt"
        result = _run_install(work_dir, mock_bin=mock_curl,
                              env_extra={"VENDOR_MANIFEST": str(manifest)})
        assert result.returncode == 0
        lines = manifest.read_text().strip().splitlines()
        assert ".dogfood/resolve" in lines
        assert ".github/workflows/dogfood.yml" not in lines

    def test_no_manifest_when_env_unset(self, work_dir, mock_curl):
        result = _run_install(work_dir, mock_bin=mock_curl)
        assert result.returncode == 0
        # No manifest file should be created anywhere in work_dir
        manifests = list(work_dir.glob("manifest*"))
        assert len(manifests) == 0

    def test_manifest_uses_custom_install_dir(self, work_dir, mock_curl):
        manifest = work_dir / "manifest.txt"
        custom_dir = ".vendored/pkg/git-dogfood"
        result = _run_install(work_dir, mock_bin=mock_curl,
                              env_extra={"VENDOR_MANIFEST": str(manifest),
                                         "VENDOR_INSTALL_DIR": custom_dir})
        assert result.returncode == 0
        lines = manifest.read_text().strip().splitlines()
        assert f"{custom_dir}/resolve" in lines


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
