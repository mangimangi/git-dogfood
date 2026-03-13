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


# ── Tests: _extract_vendor_registry ──────────────────────────────────────

class TestExtractVendorRegistry:
    def test_extracts_vendor_key(self):
        raw = {"_vendor": {"repo": "o/gd", "protected": [".dogfood/**"]}, "extra": "ignored"}
        assert resolve._extract_vendor_registry(raw) == {"repo": "o/gd", "protected": [".dogfood/**"]}

    def test_uses_all_keys_when_no_vendor(self):
        raw = {"repo": "o/gd", "protected": [".dogfood/**"]}
        assert resolve._extract_vendor_registry(raw) == raw


# ── Tests: find_dogfood_vendor ─────────────────────────────────────────────

class TestFindDogfoodVendor:
    def test_finds_vendor_by_repo(self):
        config = {
            "vendors": {
                "git-dogfood": {"repo": "mangimangi/git-dogfood"},
            }
        }
        assert resolve.find_dogfood_vendor(config, "mangimangi/git-dogfood") == "git-dogfood"

    def test_finds_pearls_in_pearls_repo(self):
        config = {
            "vendors": {
                "git-vendored": {"repo": "mangimangi/git-vendored"},
                "git-dogfood": {"repo": "mangimangi/git-dogfood"},
                "pearls": {"repo": "mangimangi/pearls"},
            }
        }
        assert resolve.find_dogfood_vendor(config, "mangimangi/pearls") == "pearls"

    def test_returns_none_when_no_match(self):
        config = {
            "vendors": {
                "git-vendored": {"repo": "mangimangi/git-vendored"},
                "pearls": {"repo": "mangimangi/pearls"},
            }
        }
        assert resolve.find_dogfood_vendor(config, "mangimangi/other-tool") is None

    def test_empty_vendors(self):
        assert resolve.find_dogfood_vendor({"vendors": {}}, "mangimangi/foo") is None

    def test_no_vendors_key(self):
        assert resolve.find_dogfood_vendor({}, "mangimangi/foo") is None


# ── Tests: load_vendor_config (per-vendor configs) ───────────────────────

class TestLoadVendorConfigPerVendor:
    def test_loads_per_vendor_configs(self, make_per_vendor_configs):
        make_per_vendor_configs({
            "git-dogfood": {"_vendor": {"repo": "o/gd"}},
            "git-semver": {"_vendor": {"repo": "o/gs"}},
        })
        config = resolve.load_vendor_config()
        assert "vendors" in config
        assert "git-dogfood" in config["vendors"]
        assert config["vendors"]["git-dogfood"]["repo"] == "o/gd"
        assert "git-semver" in config["vendors"]

    def test_extracts_vendor_key_from_per_vendor(self, make_per_vendor_configs):
        make_per_vendor_configs({
            "git-dogfood": {
                "_vendor": {"repo": "o/gd", "protected": [".dogfood/**"]},
                "prefix": "gdf",
            },
        })
        config = resolve.load_vendor_config()
        assert config["vendors"]["git-dogfood"]["repo"] == "o/gd"
        assert "prefix" not in config["vendors"]["git-dogfood"]

    def test_per_vendor_takes_precedence_over_monolithic(self, tmp_repo, make_config, make_per_vendor_configs):
        make_config({"vendors": {"old-vendor": {"repo": "o/old"}}})
        make_per_vendor_configs({"git-dogfood": {"_vendor": {"repo": "o/gd"}}})
        config = resolve.load_vendor_config()
        assert "git-dogfood" in config["vendors"]
        assert "old-vendor" not in config["vendors"]

    def test_ignores_non_json_files(self, tmp_repo):
        configs_dir = tmp_repo / ".vendored" / "configs"
        configs_dir.mkdir()
        (configs_dir / "README.md").write_text("not json")
        (configs_dir / "git-dogfood.json").write_text(json.dumps({"_vendor": {"repo": "o/gd"}}))
        config = resolve.load_vendor_config()
        assert "git-dogfood" in config["vendors"]

    def test_empty_configs_dir_falls_back(self, tmp_repo, make_config):
        (tmp_repo / ".vendored" / "configs").mkdir()
        make_config({"vendors": {"git-dogfood": {"repo": "o/gd"}}})
        config = resolve.load_vendor_config()
        assert "git-dogfood" in config["vendors"]


# ── Tests: load_vendor_config (monolithic fallback) ──────────────────────

class TestLoadVendorConfigMonolithic:
    def test_loads_config(self, make_config):
        make_config({"vendors": {"x": {"repo": "o/x"}}})
        config = resolve.load_vendor_config()
        assert "vendors" in config

    def test_missing_file_returns_none(self, tmp_repo):
        assert resolve.load_vendor_config("/nonexistent/config.json") is None


# ── Tests: main ────────────────────────────────────────────────────────────

class TestMain:
    def test_outputs_vendor_matching_repo(self, make_per_vendor_configs, monkeypatch, capsys):
        make_per_vendor_configs({
            "git-dogfood": {"_vendor": {"repo": "mangimangi/git-dogfood"}},
            "pearls": {"_vendor": {"repo": "mangimangi/pearls"}},
        })
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=git-dogfood" in out

    def test_outputs_pearls_in_pearls_repo(self, make_per_vendor_configs, monkeypatch, capsys):
        make_per_vendor_configs({
            "git-dogfood": {"_vendor": {"repo": "mangimangi/git-dogfood"}},
            "pearls": {"_vendor": {"repo": "mangimangi/pearls"}},
        })
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/pearls")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=pearls" in out

    def test_no_match_no_output(self, make_config, monkeypatch, capsys):
        make_config({"vendors": {"pearls": {"repo": "mangimangi/pearls"}}})
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/other")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out

    def test_no_github_repository(self, make_config, monkeypatch, capsys):
        make_config({"vendors": {"pearls": {"repo": "o/p"}}})
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

    def test_monolithic_config(self, make_config, monkeypatch, capsys):
        make_config({"vendors": {"git-dogfood": {"repo": "mangimangi/git-dogfood"}}})
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=git-dogfood" in out
