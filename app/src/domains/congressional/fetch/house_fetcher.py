"""
House disclosure source fetcher (phase scaffolding).
"""

from __future__ import annotations

import logging
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .base import ensure_dir

logger = logging.getLogger(__name__)


class HouseDisclosureFetcher:
    BASE_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs"

    def __init__(self, raw_dir: Path, csv_dir: Path):
        self.raw_dir = ensure_dir(raw_dir / "house")
        self.csv_dir = ensure_dir(csv_dir)

    def sync(self, start_year: int = 2023) -> Dict[str, object]:
        this_year = datetime.utcnow().year
        downloaded: List[str] = []
        existing: List[str] = []
        failed: List[str] = []
        refreshed: List[str] = []
        parser_runs: List[Dict[str, object]] = []

        force_refresh_current_year = os.environ.get(
            "CAPITOLSCOPE_HOUSE_FORCE_REFRESH_CURRENT_YEAR", "true"
        ).lower() in {"1", "true", "yes", "on"}
        run_legacy_parser = os.environ.get(
            "CAPITOLSCOPE_HOUSE_RUN_LEGACY_PARSER", "true"
        ).lower() in {"1", "true", "yes", "on"}

        for year in range(start_year, this_year + 1):
            filename = f"{year}FD.zip"
            target = self.raw_dir / filename
            should_refresh = force_refresh_current_year and year == this_year
            if target.exists() and not should_refresh:
                existing.append(str(target))
                continue
            url = f"{self.BASE_URL}/{filename}"
            try:
                logger.info("Downloading House disclosure index: year=%s url=%s", year, url)
                with urllib.request.urlopen(url, timeout=45) as resp:
                    target.write_bytes(resp.read())
                if should_refresh:
                    refreshed.append(str(target))
                else:
                    downloaded.append(str(target))
            except Exception as exc:
                logger.warning("Failed to download House index for %s: %s", year, exc)
                failed.append(str(year))

        if run_legacy_parser:
            parser_runs = self._run_house_csv_generation(start_year=start_year, end_year=this_year)

        return {
            "source": "house",
            "downloaded_files": downloaded,
            "refreshed_files": refreshed,
            "existing_files": existing,
            "failed_years": failed,
            "parser_runs": parser_runs,
        }

    def _run_house_csv_generation(self, start_year: int, end_year: int) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        # house_fetcher.py -> fetch -> congressional -> domains -> src -> app
        # We want /app as repo root inside the container.
        repo_root = Path(__file__).resolve().parents[4]
        legacy_script = repo_root / "legacy" / "ingestion" / "fetch_congress_data.py"
        if not legacy_script.exists():
            logger.warning("Legacy House parser script not found: %s", legacy_script)
            return results

        force_refresh_current_year = os.environ.get(
            "CAPITOLSCOPE_HOUSE_FORCE_REFRESH_CURRENT_YEAR", "true"
        ).lower() in {"1", "true", "yes", "on"}

        for year in range(start_year, end_year + 1):
            csv_path = self.csv_dir / f"{year}FD.csv"
            should_generate = (year == end_year and force_refresh_current_year) or not csv_path.exists()
            if not should_generate:
                continue

            cmd = [
                "python",
                str(legacy_script),
                str(year),
                "--delay",
                os.environ.get("CAPITOLSCOPE_HOUSE_FETCH_DELAY", "2.0"),
                "--concurrent",
                os.environ.get("CAPITOLSCOPE_HOUSE_FETCH_CONCURRENT", "2"),
                "--retries",
                os.environ.get("CAPITOLSCOPE_HOUSE_FETCH_RETRIES", "3"),
                "--retry-delay",
                os.environ.get("CAPITOLSCOPE_HOUSE_FETCH_RETRY_DELAY", "5.0"),
            ]
            try:
                logger.info("Running legacy House parser for year=%s", year)
                proc = subprocess.run(
                    cmd,
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    timeout=int(os.environ.get("CAPITOLSCOPE_HOUSE_FETCH_TIMEOUT_SECONDS", "1800")),
                )
                ok = proc.returncode == 0
                results.append(
                    {
                        "year": year,
                        "status": "success" if ok else "failed",
                        "return_code": proc.returncode,
                        "csv_path": str(csv_path),
                        "stdout_tail": proc.stdout[-2000:],
                        "stderr_tail": proc.stderr[-2000:],
                    }
                )
            except Exception as exc:
                logger.warning("Legacy parser run failed for year=%s: %s", year, exc)
                results.append(
                    {
                        "year": year,
                        "status": "failed",
                        "error": str(exc),
                        "csv_path": str(csv_path),
                    }
                )
        return results

