from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable


def append_progress_row(path: Path, row: Dict[str, Any], headers: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        if write_header:
            writer.writeheader()
        writer.writerow(row)
