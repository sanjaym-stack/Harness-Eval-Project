"""Run the standard harness-eval comparison for this repository."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def project_python() -> Path:
    """Return the project virtualenv interpreter, creating the environment if needed."""
    executable = "python.exe" if os.name == "nt" else "python"
    virtualenv_directory = ROOT / ".venv"
    virtualenv_python = virtualenv_directory / ("Scripts" if os.name == "nt" else "bin") / executable
    if not virtualenv_python.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(virtualenv_directory)],
            cwd=ROOT,
            check=True,
        )
    return virtualenv_python


def install_dependencies(python_executable: Path) -> None:
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
