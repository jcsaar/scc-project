import os
import subprocess
from pathlib import Path

import pytest


def test_offline_launcher_smoke_starts_both_services() -> None:
    root = Path(__file__).parents[3]
    environment = os.environ.copy()
    environment.update({"BACKEND_PORT": "18991", "FRONTEND_PORT": "15191"})

    completed = subprocess.run(
        [str(root / "scripts" / "dev.sh"), "--smoke"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if "operation not permitted" in completed.stderr.lower():
        pytest.skip("The test sandbox does not permit binding localhost ports")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Backend ready" in completed.stdout
    assert "Dashboard ready" in completed.stdout
