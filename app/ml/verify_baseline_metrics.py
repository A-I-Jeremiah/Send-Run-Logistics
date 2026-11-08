"""
Verify baseline metrics.

  python -m app.ml.verify_baseline_metrics
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.ml.train import evaluate_baseline_


def main(survey_path: str | None = None) -> None:
    bl = evaluate_baseline_(survey_path)
    print("Baseline metrics:")
    for split in ("train", "test"):
        m = bl[split]
        print(f"  {split.capitalize():5s}  R2={m['r2']:.4f}  MAE={m['mae']:,.2f}  RMSE={m['rmse']:,.2f}")
    

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    main(path)
