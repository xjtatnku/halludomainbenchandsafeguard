from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .utils import ensure_parent


def write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    ensure_parent(path)
    if not rows:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            handle.write("")
        return

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_legacy_verification_rows(validated_rows: list[dict]) -> list[dict]:
    table_data: list[dict] = []
    for row in validated_rows:
        model = row.get("model", "Unknown")
        prompt_id = row.get("prompt_id", "Unknown")
        verified_links = row.get("verified_links", [])
        if not verified_links:
            table_data.append(
                {
                    "Prompt ID": prompt_id,
                    "Model": model,
                    "URL": "NO_URL_EXTRACTED",
                    "Status": "-",
                    "Code/Detail": "-",
                }
            )
            continue

        for link in verified_links:
            result = link.get("result", "")
            if result == "live":
                status_label = "Live"
            elif result == "unknown":
                status_label = "Unknown"
            else:
                status_label = "Dead"
            table_data.append(
                {
                    "Prompt ID": prompt_id,
                    "Model": model,
                    "URL": link.get("url", ""),
                    "Status": status_label,
                    "Code/Detail": link.get("reason", "") or "-",
                }
            )
    return table_data


def write_legacy_reports(validated_rows: list[dict], *, output_csv: Path, dead_only_csv: Path) -> None:
    table_data = build_legacy_verification_rows(validated_rows)
    write_csv(output_csv, table_data)
    dead_rows = [row for row in table_data if row["Status"] == "Dead"]
    write_csv(dead_only_csv, dead_rows)
