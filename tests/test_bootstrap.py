"""Bootstrap tests for project scaffolding."""
import subprocess
import sys


def test_bootstrap_help():
    """Test that the pipeline runner shows help with expected arguments."""
    result = subprocess.run(
        [sys.executable, "-m", "app.pipeline.run_daily", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "--mode" in result.stdout, "Missing --mode in help"
    assert "--fixture" in result.stdout, "Missing --fixture in help"


def test_missing_module_error():
    """Test that missing module gives clear error."""
    result = subprocess.run(
        [sys.executable, "-m", "app.pipeline.missing"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0, "Missing module should fail"
    assert "No module named" in result.stderr or "ModuleNotFoundError" in result.stderr
