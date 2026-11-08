"""
End-to-end pipeline.

  python -m app.scripts.run_pipeline
  python -m app.scripts.run_pipeline --survey "data/Survey_Logistics_Dataset_200 (1).xlsx"

Produces:
  - data/waybill_pricing_clean.csv (audit export, n=180)
  - trained_models/pricing_pipeline.joblib
  - Console metrics.
"""
from __future__ import annotations

import argparse
import sys 

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.ml.data_collection.pipeline import build_master_dataset
from app.ml.train import train_and_save


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--survey", default=None)
    parser.add_argument("--clean-csv", default="data/waybill_pricing_clean.csv")
    parser.add_argument("--model-out", default="trained_models/pricing_pipeline.joblib")
    parser.add_argument("--skip-train", action="store_true")
    args = parser.parse_args()

    df = build_master_dataset(survey_path=args.survey, output_path=args.clean_csv)
    print(f"Clean audit CSV ready: n={len(df)}")

    if not args.skip_train:
        print("\n--- Train XGBoost (notebook protocol) ---")
        train_and_save(survey_path=args.survey, output_path=args.model_out)


if __name__ == "__main__":
    main()
