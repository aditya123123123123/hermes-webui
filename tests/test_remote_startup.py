"""Tests for remote-access startup path (start-remote.sh + env-var wiring)."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
START_REMOTE = REPO_ROOT / "start-remote.sh"


def test_start_remote_script_exists_and_is_executable():
    assert START_REMOTE.exists(), "start-remote.sh is missing"
    assert os.access(START_REMOTE, os.X_OK), "start-remote.sh is not executable"


def test_start_remote_shell_syntax():
    """bash -n (no-execute) validates syntax without running the script."""
    result = subprocess.run(
        ["bash", "-n", str(START_REMOTE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"bash -n reported syntax error:\n{result.stderr}"


def test_hermes_webui_host_env_overrides_config(monkeypatch):
    """HERMES_WEBUI_HOST must propagate into api.config.HOST at import time.

    Re-importing api.config with a patched env is the canonical check — the
    module reads os.getenv at module level, so a fresh import with the env var
    set must yield the override value.

    Skipped on Python < 3.10 because api.config uses `Type | None` union syntax
    (PEP 604) which is a SyntaxError on 3.9.
    """
    import importlib
    import pytest

    if sys.version_info < (3, 10):
        pytest.skip("api.config uses PEP-604 syntax requiring Python 3.10+")

    monkeypatch.setenv("HERMES_WEBUI_HOST", "100.64.0.1")

    import api.config as config_mod
    importlib.reload(config_mod)

    assert config_mod.HOST == "100.64.0.1"

    # Cleanup: reload without the override so later tests see the default.
    monkeypatch.delenv("HERMES_WEBUI_HOST", raising=False)
    importlib.reload(config_mod)


def test_start_remote_exits_nonzero_without_tailscale_or_explicit_host(tmp_path):
    """Without Tailscale and without HERMES_REMOTE_BIND_HOST, the script must
    exit non-zero and print an actionable error rather than silently binding to
    127.0.0.1 or hanging.

    We run the script with a PATH that has no `tailscale` binary and no env
    override, so the Tailscale detection always misses.  We also pass a fake
    HERMES_WEBUI_PYTHON so the script fails before exec'ing a real server.
    """
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    # Provide a fake python3 so start.sh doesn't error on "Python not found"
    # before we get to test the expected failure path.  This python does nothing.
    fake_python = fake_bin / "python3"
    fake_python.write_text("#!/usr/bin/env python3\nimport sys; sys.exit(0)\n")
    fake_python.chmod(0o755)

    env = {
        # Strip tailscale from PATH; keep only fake_bin + minimal system tools.
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "HERMES_WEBUI_PYTHON": str(fake_python),
        # Explicitly unset so the script cannot find a host.
        # (os.environ strips these if we don't include them, which is correct.)
    }

    result = subprocess.run(
        ["bash", str(START_REMOTE)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0, (
        "Expected non-zero exit when no Tailscale and no HERMES_REMOTE_BIND_HOST, "
        f"got 0.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "HERMES_REMOTE_BIND_HOST" in result.stdout or "Tailscale" in result.stdout, (
        "Expected helpful error message in stdout"
    )


def test_start_remote_filters_internal_all_interfaces_flag(tmp_path):
    """--all-interfaces is for start-remote.sh only; bootstrap.py does not
    accept it, so the wrapper must consume the flag before exec'ing start.sh.
    """
    fake_python = tmp_path / "fake_python.py"
    argv_file = tmp_path / "argv.txt"
    fake_python.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        f"open({str(argv_file)!r}, 'w').write('\\n'.join(sys.argv) + '\\nHOST=' + os.environ.get('HERMES_WEBUI_HOST',''))\n"
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "HERMES_WEBUI_PYTHON": str(fake_python),
        "HERMES_WEBUI_PASSWORD": "test-password",
    })

    result = subprocess.run(
        ["bash", str(START_REMOTE), "--all-interfaces", "--foreground"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    argv = argv_file.read_text()
    assert "--all-interfaces" not in argv
    assert "--foreground" in argv
    assert "HOST=0.0.0.0" in argv


def test_remote_access_docs_exist():
    docs = REPO_ROOT / "docs" / "remote-access.md"
    assert docs.exists(), "docs/remote-access.md is missing"
    text = docs.read_text(encoding="utf-8")
    assert "Tailscale" in text
    assert "SSH" in text
    assert "HERMES_WEBUI_PASSWORD" in text
