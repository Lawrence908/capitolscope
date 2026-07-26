"""
Orchestration for congressional disclosure fetch + import workflow.

Each source is fetched independently and defensively: a source that raises or
returns a failed result degrades the overall run to ``partial`` (or ``failed``
if nothing succeeds) instead of aborting, and an operator alert is emitted.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .alerts import emit_ingestion_alert
from .base import ensure_dir, utc_now_iso
from .house_fetcher import HouseDisclosureFetcher
from .senate_fetcher import SenateDisclosureFetcher
from .state import SyncStateStore

logger = logging.getLogger(__name__)


class DisclosureSyncOrchestrator:
    def __init__(self) -> None:
        base_data = Path(os.environ.get("CAPITOLSCOPE_DATA_DIR", "/app/data/congress"))
        self.base_data = ensure_dir(base_data)
        self.csv_dir = ensure_dir(Path(os.environ.get("CAPITOLSCOPE_CSV_IMPORT_DIR", str(self.base_data / "csv"))))
        self.pdf_dir = ensure_dir(Path(os.environ.get("CAPITOLSCOPE_PDF_DIR", str(self.base_data / "pdf"))))
        self.state = SyncStateStore(self.base_data / "state")
        self.house = HouseDisclosureFetcher(self.base_data / "raw", self.csv_dir)
        self.senate = SenateDisclosureFetcher(self.base_data / "raw", self.csv_dir)

    def _run_source(self, name: str, fetcher: Any) -> Tuple[Dict[str, Any], List[str]]:
        """Run one source's sync(), converting any exception into a failed result.

        Returns (result_dict, errors). ``errors`` is non-empty when the source
        failed outright or reported partial failures (e.g. failed years / failed
        parser runs).
        """
        errors: List[str] = []
        try:
            result = fetcher.sync()
        except Exception as exc:  # a broken source must not abort sibling sources
            logger.exception("Source %s raised during sync", name)
            return (
                {"source": name, "status": "failed", "error": str(exc)},
                [f"{name}: sync raised: {exc}"],
            )

        # Inspect structured result for partial failures.
        failed_years = result.get("failed_years") or []
        if failed_years:
            errors.append(f"{name}: failed years {failed_years}")
        for run in result.get("parser_runs") or []:
            if run.get("status") == "failed":
                detail = run.get("error") or (run.get("stderr_tail") or "").strip().splitlines()[-1:] or ["unknown"]
                errors.append(f"{name}: parser failed for {run.get('year')}: {detail}")
        if result.get("status") == "failed" or result.get("error"):
            errors.append(f"{name}: {result.get('error', 'reported failure')}")

        return result, errors

    def run(self, date_from: str | None = None) -> Dict[str, Any]:
        started = datetime.utcnow()
        prior_state = self.state.read()

        house, house_errors = self._run_source("house", self.house)
        senate, senate_errors = self._run_source("senate", self.senate)

        all_errors = house_errors + senate_errors
        house_ok = not house_errors
        senate_ok = not senate_errors

        if house_ok and senate_ok:
            status = "success"
        elif not house_ok and not senate_ok:
            status = "failed"
        else:
            status = "partial"

        result = {
            "status": status,
            "date_from": date_from,
            "started_at": started.isoformat(),
            "finished_at": utc_now_iso(),
            "source_results": {
                "house": house,
                "senate": senate,
            },
            "source_health": {"house": house_ok, "senate": senate_ok},
            "errors": all_errors,
            "csv_directory": str(self.csv_dir),
            "prior_checkpoint_exists": bool(prior_state),
        }
        self.state.write(
            {
                "last_run": result["finished_at"],
                "last_status": status,
                "last_date_from": date_from,
                "last_errors": all_errors,
            }
        )
        run_manifest = self.state.write_run_manifest(result)
        result["run_manifest"] = str(run_manifest)

        if status != "success":
            emit_ingestion_alert(
                summary=f"Congressional fetch orchestration {status}",
                errors=all_errors,
                context={
                    "date_from": date_from,
                    "house_ok": house_ok,
                    "senate_ok": senate_ok,
                    "run_manifest": str(run_manifest),
                },
            )

        return result
