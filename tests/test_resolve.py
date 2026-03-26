"""Tests for the dogfood/resolve script."""

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

import pytest

# ── Import resolve script as module ────────────────────────────────────────

ROOT = Path(__file__).parent.parent


def _import_resolve():
    filepath = str(ROOT / "dogfood" / "resolve")
    loader = importlib.machinery.SourceFileLoader("dogfood_resolve", filepath)
    spec = importlib.util.spec_from_loader("dogfood_resolve", loader, origin=filepath)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = filepath
    sys.modules["dogfood_resolve"] = module
    spec.loader.exec_module(module)
    return module


resolve = _import_resolve()


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vendored").mkdir()
    return tmp_path


@pytest.fixture
def make_config(tmp_repo):
    """Write a monolithic .vendored/config.json."""
    def _make(config_dict):
        path = tmp_repo / ".vendored" / "config.json"
        path.write_text(json.dumps(config_dict, indent=2) + "\n")
        return str(path)
    return _make


@pytest.fixture
def make_per_vendor_configs(tmp_repo):
    """Write per-vendor config files to .vendored/configs/."""
    def _make(vendors_dict):
        configs_dir = tmp_repo / ".vendored" / "configs"
        configs_dir.mkdir(exist_ok=True)
        for name, cfg in vendors_dict.items():
            path = configs_dir / f"{name}.json"
            path.write_text(json.dumps(cfg, indent=2) + "\n")
        return str(configs_dir)
    return _make


# ── Tests: vendor_from_repo ───────────────────────────────────────────────

class TestVendorFromRepo:
    def test_extracts_repo_name(self):
        assert resolve.vendor_from_repo("mangimangi/git-dogfood") == "git-dogfood"

    def test_extracts_repo_name_different_owner(self):
        assert resolve.vendor_from_repo("acme/my-tool") == "my-tool"

    def test_handles_bare_name(self):
        assert resolve.vendor_from_repo("git-dogfood") == "git-dogfood"


# ── Tests: vendor_config_exists ──────────────────────────────────────────

class TestVendorConfigExists:
    def test_per_vendor_config_exists(self, make_per_vendor_configs):
        make_per_vendor_configs({
            "git-dogfood": {"_vendor": {"repo": "mangimangi/git-dogfood"}},
        })
        assert resolve.vendor_config_exists("git-dogfood") is True

    def test_per_vendor_config_missing(self, tmp_repo):
        (tmp_repo / ".vendored" / "configs").mkdir()
        assert resolve.vendor_config_exists("git-dogfood") is False

    def test_monolithic_config_has_vendor(self, make_config):
        make_config({"vendors": {"git-dogfood": {"repo": "mangimangi/git-dogfood"}}})
        assert resolve.vendor_config_exists("git-dogfood") is True

    def test_monolithic_config_missing_vendor(self, make_config):
        make_config({"vendors": {"other": {"repo": "o/other"}}})
        assert resolve.vendor_config_exists("git-dogfood") is False

    def test_no_config_at_all(self, tmp_repo):
        assert resolve.vendor_config_exists("git-dogfood") is False


# ── Tests: main ────────────────────────────────────────────────────────────

class TestMain:
    def test_outputs_vendor_from_repo_name(self, make_per_vendor_configs, monkeypatch, capsys):
        make_per_vendor_configs({
            "git-dogfood": {"_vendor": {"repo": "mangimangi/git-dogfood"}},
        })
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=git-dogfood" in out

    def test_consumer_repo_self_installs(self, make_per_vendor_configs, monkeypatch, capsys):
        make_per_vendor_configs({
            "my-tool": {"_vendor": {"repo": "acme/my-tool"}},
        })
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/my-tool")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=my-tool" in out

    def test_monolithic_config(self, make_config, monkeypatch, capsys):
        make_config({"vendors": {"git-dogfood": {"repo": "mangimangi/git-dogfood"}}})
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=git-dogfood" in out

    def test_no_config_no_output(self, tmp_repo, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/my-tool")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out

    def test_no_github_repository(self, tmp_repo, monkeypatch, capsys):
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out

    def test_no_config_no_crash(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/foo")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out

    def test_config_name_must_match_repo_name(self, make_per_vendor_configs, monkeypatch, capsys):
        """Config named 'dogfood' won't match repo 'git-dogfood'."""
        make_per_vendor_configs({
            "dogfood": {"_vendor": {"repo": "mangimangi/git-dogfood"}},
        })
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out
