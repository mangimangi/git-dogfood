"""Tests for the dogfood/resolve script."""

import importlib.machinery
import importlib.util
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


# ── Tests: vendor_from_repo ───────────────────────────────────────────────

class TestVendorFromRepo:
    def test_extracts_repo_name(self):
        assert resolve.vendor_from_repo("mangimangi/git-dogfood") == "git-dogfood"

    def test_extracts_repo_name_different_owner(self):
        assert resolve.vendor_from_repo("acme/my-tool") == "my-tool"

    def test_handles_bare_name(self):
        assert resolve.vendor_from_repo("git-dogfood") == "git-dogfood"


# ── Tests: main ────────────────────────────────────────────────────────────

class TestMain:
    def test_outputs_vendor_from_repo_name(self, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_REPOSITORY", "mangimangi/git-dogfood")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=git-dogfood" in out

    def test_outputs_vendor_for_any_repo(self, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/my-tool")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=my-tool" in out

    def test_no_github_repository(self, monkeypatch, capsys):
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out

    def test_empty_github_repository(self, monkeypatch, capsys):
        monkeypatch.setenv("GITHUB_REPOSITORY", "")
        resolve.main()
        out = capsys.readouterr().out
        assert "vendor=" not in out
