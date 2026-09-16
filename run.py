"""Run the standard harness-eval comparison for this repository."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def project_python() -> str:
    """Return the project virtualenv interpreter when it is available."""
    executable = "python.exe" if os.name == "nt" else "python"
    virtualenv_python = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / executable
    return str(virtualenv_python) if virtualenv_python.exists() else sys.executable


def install_dependencies(python_executable: str) -> None:
    """Install requirements and register the project in the active environment."""
    pip_command = [
        python_executable,
        "-m",
        "pip",
        "--disable-pip-version-check",
        "--no-input",
    ]
    subprocess.run(
        [*pip_command, "install", "-r", str(ROOT / "requirements.txt")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [*pip_command, "install", "--no-deps", "-e", str(ROOT)],
        cwd=ROOT,
        check=True,
    )


def main() -> int:
    python_executable = project_python()
    install_dependencies(python_executable)

    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not existing_pythonpath
        else os.pathsep.join((source_path, existing_pythonpath))
    )

    command = [
        python_executable,
        "-m",
        "harness_eval.cli",
        "compare",
        "--baseline",
        str(ROOT / "harnesses" / "baseline"),
        "--candidate",
        str(ROOT / "harnesses" / "candidate"),
        "--tasks",
        str(ROOT / "benchmark" / "tasks"),
        "--project",
        str(ROOT / "benchmark" / "example_project"),
        "--runs",
        "1",
        "--mock",
        "--output-dir",
        str(ROOT / "results"),
    ]
    completed = subprocess.run(command, cwd=ROOT, env=environment)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
