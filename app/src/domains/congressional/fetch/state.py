"""
State/checkpoint persistence for disclosure sync runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .base import atomic_write_json, ensure_dir, utc_now_iso


class SyncStateStore:
    def __init__(self, state_dir: Path):
        self.state_dir = ensure_dir(state_dir)
        self.state_file = self.state_dir / "checkpoint.json"
        self.runs_dir = ensure_dir(self.state_dir / "runs")

    def read(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def write(self, payload: Dict[str, Any]) -> None:
        atomic_write_json(self.state_file, payload)

    def write_run_manifest(self, payload: Dict[str, Any]) -> Path:
        stamp = utc_now_iso().replace(":", "-")
        out = self.runs_dir / f"{stamp}.json"
        atomic_write_json(out, payload)
        return out

