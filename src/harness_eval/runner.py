"""Workspace isolation and agent command runner."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from harness_eval.models import TaskSpec


class WorkspaceManager:
    """Creates isolated environments for benchmark runs."""

    def __init__(self, base_project_dir: Path):
        self.base_project_dir = base_project_dir.resolve()

    def create_isolated_workspace(self, temp_root: Path) -> Path:
        """Copies the base project snapshot into an isolated directory."""
        workspace = temp_root / "workspace"
        shutil.copytree(
            self.base_project_dir,
            workspace,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"),
        )
        return workspace

    @staticmethod
    def inject_harness(workspace: Path, harness_dir: Path) -> None:
        """Copies harness instructions and files into the workspace."""
        for item in harness_dir.iterdir():
            target = workspace / item.name
            if item.is_file():
                shutil.copy2(item, target)
            elif item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)


class AgentRunner:
    """Executes a configurable agent command or deterministic mock."""

    def __init__(
        self,
        command_template: Optional[str] = None,
        timeout_seconds: int = 180,
        mock_mode: bool = False,
        harness_dir: Optional[Path] = None,
    ):
        self.command_template = command_template
        self.timeout_seconds = timeout_seconds
        self.mock_mode = mock_mode
        self.harness_dir = harness_dir

    def run(
        self,
        workspace: Path,
        task_prompt: str,
        task_spec: TaskSpec,
        harness_name: str,
    ) -> Tuple[int, float, Optional[int], Optional[int], Optional[str]]:
        start_time = time.time()

        if self.mock_mode:
            return self._run_mock(workspace, task_spec, harness_name, start_time)

        if not self.command_template:
            raise ValueError("Agent command template is required when not in mock mode.")

        cmd = self.command_template.format(
            workspace=str(workspace),
            prompt_file=str(workspace / task_spec.prompt_file),
            task_id=task_spec.id,
        )

        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            duration = round(time.time() - start_time, 2)
            input_tokens, output_tokens = self._parse_usage(res.stdout)
            return (
                res.returncode,
                duration,
                input_tokens,
                output_tokens,
                res.stderr if res.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return -1, round(time.time() - start_time, 2), None, None, f"Timeout after {self.timeout_seconds}s"
        except Exception as exc:  # pragma: no cover - defensive path
            return 1, round(time.time() - start_time, 2), None, None, str(exc)

    @staticmethod
    def _parse_usage(stdout: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract input and output token counts from structured agent output."""
        for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue
            usage = data.get("usage")
            if not isinstance(usage, dict):
                continue
            return usage.get("input_tokens"), usage.get("output_tokens")
        return None, None

    def _run_mock(
        self,
        workspace: Path,
        task_spec: TaskSpec,
        harness_name: str,
        start_time: float,
    ) -> Tuple[int, float, Optional[int], Optional[int], Optional[str]]:
        time.sleep(0.05)
        duration = round(time.time() - start_time, 2)

        harness_text = ""
        if self.harness_dir:
            agents_md_path = self.harness_dir / "AGENTS.md"
            if agents_md_path.exists():
                harness_text = agents_md_path.read_text(encoding="utf-8")

        wants_validation = "ge=1" in harness_text or "validate" in harness_text.lower()
        wants_types = "response_model" in harness_text or "pydantic" in harness_text.lower()

        app_users = workspace / "app" / "users.py"
        if app_users.exists() and task_spec.id == "task-001":
            if wants_validation or wants_types:
                app_users.write_text(
                    'from typing import Any, Dict, List\n'
                    'from fastapi import APIRouter, Query\n'
                    'from pydantic import BaseModel\n\n'
                    'router = APIRouter()\n'
                    'USERS_DB = [{"id": i, "name": f"User_{i}"} for i in range(1, 101)]\n\n'
                    '\n'
                    'class UserResponse(BaseModel):\n'
                    '    items: List[Dict[str, Any]]\n'
                    '    total: int\n'
                    '    page: int\n'
                    '    page_size: int\n\n\n'
                    '@router.get("/users", response_model=UserResponse)\n'
                    'def get_users(\n'
                    '    page: int = Query(1, ge=1),\n'
                    '    page_size: int = Query(10, ge=1, le=100),\n'
                    ') -> UserResponse:\n'
                    '    start = (page - 1) * page_size\n'
                    '    end = start + page_size\n'
                    '    return {"items": USERS_DB[start:end], "total": len(USERS_DB), "page": page, "page_size": page_size}\n'
                )
                return 0, duration, 1400, 450, None
            app_users.write_text(
                'from fastapi import APIRouter\n\n'
                'router = APIRouter()\n'
                'USERS_DB = [{"id": i, "name": f"User_{i}"} for i in range(1, 101)]\n\n'
                '@router.get("/users")\n'
                'def get_users(page: int = 1, page_size: int = 10):\n'
                '    start = (page - 1) * page_size\n'
                '    return {"items": USERS_DB[start:start+page_size], "total": len(USERS_DB), "page": page, "page_size": page_size}\n'
            )
            return 0, duration, 800, 200, None

        if app_users.exists() and task_spec.id == "task-002":
            existing = app_users.read_text()
            if harness_name == "candidate":
                addition = '''

from fastapi import HTTPException

@router.get("/users/{user_id}")
def get_user(user_id: int):
    for u in USERS_DB:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail=f"User {user_id} not found")
'''
                app_users.write_text(existing + addition)
                return 0, duration, 900, 220, None

            addition = '''

@router.get("/users/{user_id}")
def get_user(user_id: int):
    for u in USERS_DB:
        if u["id"] == user_id:
            return u
    return None
'''
            app_users.write_text(existing + addition)
            return 0, duration, 700, 150, None

        return 0, duration, 500, 100, None
