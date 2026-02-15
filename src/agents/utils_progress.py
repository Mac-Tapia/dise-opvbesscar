"""Progress tracking utilities for agent training.

Consolidated from old citylearnv2.dataset_builder.progress module.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def append_progress_row(
    filepath: Path | str,
    row_data: Dict[str, Any],
    headers: Optional[List[str]] = None,
) -> None:
    """Append a row to CSV progress file.

    Args:
        filepath: Path to CSV file
        row_data: Dict with column values
        headers: Optional column names for CSV header (written on first call)
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    file_exists = filepath.exists()
    
    try:
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            if headers is None:
                headers = list(row_data.keys())
            
            writer = csv.DictWriter(f, fieldnames=headers)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(row_data)
    except Exception as e:
        logger.warning(f"Could not write progress to {filepath}: {e}")


def render_progress_plot(
    progress_csv: Path | str,
    output_path: Optional[Path | str] = None,
) -> Optional[Path]:
    """Render progress CSV as a visualization.

    This is a stub implementation. Full visualization would require matplotlib.

    Args:
        progress_csv: Path to progress CSV
        output_path: Optional output path for plot

    Returns:
        Path to output plot if created, None otherwise
    """
    # Stub: Real visualization would use matplotlib/seaborn
    try:
        import pandas as pd
        df = pd.read_csv(progress_csv)
        logger.info(f"[OK] Progress CSV loaded: {len(df)} rows, columns: {list(df.columns)[:5]}")
        return None  # Real implementation would plot and save
    except Exception as e:
        logger.warning(f"Could not load progress CSV: {e}")
        return None


__all__ = ["append_progress_row", "render_progress_plot"]
